from __future__ import annotations

from pathlib import Path
from typing import List, cast
import contextlib
from fastapi import APIRouter, HTTPException, Query, UploadFile, File

from api.configurations.logging_config import logger as app_logger
from application.conta_agua.query import ContaAguaQuery
from application.conta_agua.response import ContaAguaOut
from application.shared.response import Response
from core.entities.conta_agua import ContaAgua
from infrastructure.data.db_context import get_database_session
from infrastructure.repository.conta_agua.repository import ContaAguaRepository
from api.Shared.upload_pdf import UploadPDF

router = APIRouter(prefix="/contas-agua", tags=["contas-agua"]) 




@router.get("", response_model=List[ContaAguaOut])
def listar_contas_agua(
    deslocamento: int = Query(0, ge=0, alias="offset"),
    limite: int = Query(50, ge=1, le=200, alias="limit"),
    incluir_deletadas: bool = Query(False, alias="include_deleted"),
    ordem_descendente: bool = Query(True, alias="order_desc"),
):
    with get_database_session() as sessao_banco:
        repositorio = ContaAguaRepository(sessao_banco)
        servico_consulta = ContaAguaQuery(repositorio=repositorio)
        entidades = servico_consulta.listar(
            offset=deslocamento,
            limit=limite,
            include_deleted=incluir_deletadas,
            order_desc=ordem_descendente,
        )
        return [ContaAguaOut.from_entity(entidade) for entidade in entidades]

@router.post("/pdfs", response_model=Response)
def importacoes_por_arquivos(files: List[UploadFile] = File(...)) -> Response:
    """Recebe PDFs via multipart, delega ao caso de uso e retorna um envelope Response."""
    if not files:
        raise HTTPException(status_code=400, detail="Envie pelo menos um arquivo PDF em 'files'.")

    caminhos_temporarios, arquivos_invalidos = UploadPDF.persistir_uploads_em_temporarios(files)

    if arquivos_invalidos and not caminhos_temporarios:
        raise HTTPException(
            status_code=400,
            detail=f"Nenhum PDF válido foi enviado. Inválidos: {arquivos_invalidos}",
        )

    app_logger.info(
        "Received SAMAE uploaded PDFs",
        extra={
            "uploaded_count": len(files),
            "accepted_count": len(caminhos_temporarios),
            "rejected": arquivos_invalidos,
        },
    )

    try:
        resumo = UploadPDF.sincronizar_contas_a_partir_de_pdfs(caminhos_temporarios)
    finally:
        for caminho in caminhos_temporarios:
            with contextlib.suppress(OSError):
                Path(caminho).unlink(missing_ok=True)

    app_logger.info(
        "SAMAE upload sync completed",
        extra={
            "files_processed": resumo.get("files_processed"),
            "files_failed": resumo.get("files_failed"),
            "created_count": resumo.get("created"),
            "skipped_count": resumo.get("skipped"),
        },
    )

    entidades_criadas = cast(List[ContaAgua], resumo.get("created_entities") or resumo.get("entities") or [])
    return ContaAguaOut.response_importacao(
        entidades=entidades_criadas,
        mensagem="Contas de água importadas com sucesso",
        codigo=201,
    )
