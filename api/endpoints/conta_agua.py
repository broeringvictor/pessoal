from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Sequence, cast, BinaryIO
import glob
import tempfile
import shutil
import contextlib
from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.exc import OperationalError, ProgrammingError

from api.configurations.logging_config import logger as app_logger
from application.conta_agua.handlers import ContaAguaSyncService
from application.conta_agua.query import ContaAguaQuery
from application.conta_agua.dto import ContaAguaOut
from application.conta_agua.interface import ContaAguaRepositoryPort
from infrastructure.data.db_context import get_database_session
from infrastructure.repository.conta_agua.repository import ContaAguaRepository

router = APIRouter(prefix="/contas-agua", tags=["contas-agua"]) 


class SyncRequest(BaseModel):
    pdf_paths: Optional[List[str]] = None
    recursive: bool = True


class SyncResult(BaseModel):
    pdf_count: int
    files_processed: int
    files_failed: int
    failed_files: List[str]
    rows_parsed: int
    distinct_references_found: int
    created: int
    skipped: int
    created_references: List[str]


def _normalize_path_text(path_text: str) -> str:
    return path_text.replace("\\", "/")


def _has_wildcards(texto: str) -> bool:
    return any(sinal in texto for sinal in ("*", "?", "["))


def _expand_to_pdf_files(path_texts: Sequence[str], recursive: bool) -> List[str]:
    arquivos: List[str] = []
    for texto in path_texts:
        normalizado = _normalize_path_text(texto)
        if _has_wildcards(normalizado):
            resultados = glob.glob(normalizado, recursive=True)
            for encontrado in sorted(resultados):
                caminho_encontrado = Path(encontrado)
                if caminho_encontrado.is_file() and caminho_encontrado.suffix.lower() == ".pdf":
                    arquivos.append(str(caminho_encontrado.resolve()))
            continue
        caminho = Path(normalizado)
        if caminho.is_dir():
            padrao = "**/*.pdf" if recursive else "*.pdf"
            encontrados = [str(p.resolve()) for p in sorted(caminho.glob(padrao))]
            arquivos.extend(encontrados)
        else:
            if normalizado.lower().endswith(".pdf") and caminho.exists():
                arquivos.append(str(caminho.resolve()))
    vistos: set[str] = set()
    unicos: List[str] = []
    for caminho in arquivos:
        if caminho not in vistos:
            vistos.add(caminho)
            unicos.append(caminho)
    return unicos


@router.get("", response_model=List[ContaAguaOut])
def listar_contas_agua(
    deslocamento: int = Query(0, ge=0, alias="offset"),
    limite: int = Query(50, ge=1, le=200, alias="limit"),
    incluir_deletadas: bool = Query(False, alias="include_deleted"),
    ordem_descendente: bool = Query(True, alias="order_desc"),
):
    with get_database_session() as sessao_banco:
        repositorio: ContaAguaRepositoryPort = cast(
            ContaAguaRepositoryPort, ContaAguaRepository(sessao_banco)
        )
        servico_consulta = ContaAguaQuery(repositorio=repositorio)
        entidades = servico_consulta.listar(
            offset=deslocamento,
            limit=limite,
            include_deleted=incluir_deletadas,
            order_desc=ordem_descendente,
        )
        return [ContaAguaOut.from_entity(entidade) for entidade in entidades]


@router.post("/importacoes", response_model=SyncResult)
def sync_from_system(request: SyncRequest) -> SyncResult:
    """
    Varre PDFs de faturas SAMAE, encontra a referência atual em cada arquivo e cria as ausentes no banco.
    - Se `pdf_paths` não for enviado, busca PDFs em `core/assets/samae/*.pdf`.
    - Aceita diretórios, arquivos e padrões glob (ex.: "/assets/**/*.pdf").
    - Entrada múltipla é unificada (sem duplicidades) antes do processamento.
    """
    pdf_paths: Sequence[str]
    if request.pdf_paths is not None:
        entradas_validas = [p for p in request.pdf_paths if isinstance(p, str) and p.strip()]
        if entradas_validas:
            pdf_paths = _expand_to_pdf_files(entradas_validas, request.recursive)
            app_logger.info(
                "Expanded SAMAE paths",
                extra={
                    "input_count": len(request.pdf_paths),
                    "filtered_count": len(entradas_validas),
                    "pdf_count": len(pdf_paths),
                },
            )
            if not pdf_paths:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Nenhum PDF encontrado nos caminhos fornecidos. Envie caminhos de arquivos .pdf, "
                        "um diretório contendo PDFs, ou padrões glob (*.pdf)."
                    ),
                )
        else:
            app_logger.info("Empty pdf_paths payload; using default SAMAE assets fallback")
            base_dir = Path(__file__).resolve().parents[2]
            assets_dir = base_dir / "core" / "assets" / "samae"
            if not assets_dir.exists():
                raise HTTPException(status_code=400, detail=f"Assets directory not found: {assets_dir}")
            pdf_paths = [str(c) for c in sorted(assets_dir.glob("*.pdf"))]
            if not pdf_paths:
                raise HTTPException(status_code=400, detail=f"No PDFs found under {assets_dir}")
            app_logger.info("Using SAMAE assets directory", extra={"pdf_count": len(pdf_paths)})
    else:
        base_dir = Path(__file__).resolve().parents[2]
        assets_dir = base_dir / "core" / "assets" / "samae"
        if not assets_dir.exists():
            raise HTTPException(status_code=400, detail=f"Assets directory not found: {assets_dir}")
        pdf_paths = [str(c) for c in sorted(assets_dir.glob("*.pdf"))]
        if not pdf_paths:
            raise HTTPException(status_code=400, detail=f"No PDFs found under {assets_dir}")
        app_logger.info("Using SAMAE assets directory", extra={"pdf_count": len(pdf_paths)})

    try:
        with get_database_session() as session:
            repositorio: ContaAguaRepositoryPort = cast(
                ContaAguaRepositoryPort, ContaAguaRepository(session)
            )
            servico = ContaAguaSyncService(repositorio)
            resumo = servico.sync_from_pdfs(pdf_paths)
    except OperationalError as err:
        app_logger.exception("Database connectivity error during SAMAE sync")
        raise HTTPException(status_code=503, detail="Database unavailable or unreachable.") from err
    except ProgrammingError as err:
        app_logger.exception("Database schema error during SAMAE sync (missing tables?)")
        raise HTTPException(
            status_code=500,
            detail=(
                "Database schema missing. Run migrations: 'uv run alembic upgrade head' or set INIT_DB_SCHEMA=1 once."
            ),
        ) from err

    app_logger.info(
        "SAMAE sync completed",
        extra={
            "pdf_count": resumo.get("pdf_count"),
            "files_processed": resumo.get("files_processed"),
            "files_failed": resumo.get("files_failed"),
            "rows_parsed": resumo.get("rows_parsed"),
            "distinct_references_found": resumo.get("distinct_references_found"),
            "created_count": resumo.get("created"),
            "skipped_count": resumo.get("skipped"),
        },
    )

    return SyncResult(**resumo)


@router.post("/importacoes/arquivos", response_model=SyncResult)
def importacoes_por_arquivos(files: List[UploadFile] = File(...)) -> SyncResult:
    """
    Recebe um ou mais PDFs de faturas SAMAE via multipart/form-data e executa a sincronização.
    """
    if not files:
        raise HTTPException(status_code=400, detail="Envie pelo menos um arquivo PDF em 'files'.")

    caminhos_temporarios: List[str] = []
    arquivos_invalidos: List[str] = []

    for arquivo in files:
        nome_original = arquivo.filename or "arquivo_sem_nome.pdf"
        # Aceita application/pdf e octet-stream; também valida pela extensão .pdf
        if arquivo.content_type not in {"application/pdf", "application/octet-stream"} and not nome_original.lower().endswith(".pdf"):
            arquivos_invalidos.append(nome_original)
            continue
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temporario:
                destino_buffer: BinaryIO = cast(BinaryIO, temporario)
                shutil.copyfileobj(arquivo.file, destino_buffer)
                caminhos_temporarios.append(temporario.name)
        finally:
            with contextlib.suppress(Exception):
                arquivo.file.close()

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
        with get_database_session() as session:
            repositorio: ContaAguaRepositoryPort = cast(
                ContaAguaRepositoryPort, ContaAguaRepository(session)
            )
            servico = ContaAguaSyncService(repositorio)
            resumo = servico.sync_from_pdfs(caminhos_temporarios)
    except OperationalError as err:
        app_logger.exception("Database connectivity error during SAMAE upload sync")
        raise HTTPException(status_code=503, detail="Database unavailable or unreachable.") from err
    except ProgrammingError as err:
        app_logger.exception("Database schema error during SAMAE upload sync (missing tables?)")
        raise HTTPException(
            status_code=500,
            detail=(
                "Database schema missing. Run migrations: 'uv run alembic upgrade head' or set INIT_DB_SCHEMA=1 once."
            ),
        ) from err
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

    return SyncResult(**resumo)
