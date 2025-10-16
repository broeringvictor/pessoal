from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Sequence, cast
import glob
import tempfile
import shutil
from uuid import UUID
from datetime import datetime
from decimal import Decimal
import contextlib

from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from pydantic import BaseModel
from sqlalchemy.exc import OperationalError, ProgrammingError

from api.configurations.logging_config import logger as app_logger
from application.conta_luz.handlers import ContaLuzSyncService
from application.conta_luz.query import ContaLuzQueryService
from application.conta_luz.response import ContaLuzOut
from application.conta_luz.irepository import ContaLuzRepositoryPort
from infrastructure.data.db_context import get_database_session
from infrastructure.repository.conta_luz.repository import ContaLuzRepository

router = APIRouter(prefix="/contas-luz", tags=["contas-luz"])


class SyncRequest(BaseModel):
    pdf_paths: Optional[List[str]] = None
    recursive: bool = (
        True  # permite vasculhar subpastas quando um diretório for informado
    )


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


class ContaLuzItem(BaseModel):
    id: UUID
    referencia: str
    valor: Decimal
    created_at: datetime
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None


class ListaContaLuzResponse(BaseModel):
    items: List[ContaLuzItem]
    offset: int
    limit: int
    count: int


def _normalize_path_text(path_text: str) -> str:
    # Normaliza barras invertidas simples para barras normais (ajuda quando JSON vem com Windows-style)
    return path_text.replace("\\", "/")


def _has_wildcards(texto: str) -> bool:
    return any(sinal in texto for sinal in ("*", "?", "["))


def _expand_to_pdf_files(path_texts: Sequence[str], recursive: bool) -> List[str]:
    arquivos: List[str] = []
    for texto in path_texts:
        normalizado = _normalize_path_text(texto)
        # Se o usuário enviou um padrão glob (ex.: /assets/**/*.pdf), expandimos via glob
        if _has_wildcards(normalizado):
            resultados = glob.glob(normalizado, recursive=True)
            for encontrado in sorted(resultados):
                caminho_encontrado = Path(encontrado)
                if (
                    caminho_encontrado.is_file()
                    and caminho_encontrado.suffix.lower() == ".pdf"
                ):
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
    # Remove duplicados mantendo ordem
    vistos: set[str] = set()
    unicos: List[str] = []
    for caminho in arquivos:
        if caminho not in vistos:
            vistos.add(caminho)
            unicos.append(caminho)
    return unicos


@router.get("", response_model=List[ContaLuzOut])
def listar_contas_luz(
    deslocamento: int = Query(0, ge=0, alias="offset"),
    limite: int = Query(50, ge=1, le=200, alias="limit"),
    incluir_deletadas: bool = Query(False, alias="include_deleted"),
    ordem_descendente: bool = Query(True, alias="order_desc"),
):
    with get_database_session() as sessao_banco:
        repositorio: ContaLuzRepositoryPort = cast(
            ContaLuzRepositoryPort, ContaLuzRepository(sessao_banco)
        )
        servico_consulta = ContaLuzQueryService(repositorio=repositorio)
        entidades = servico_consulta.listar(
            offset=deslocamento,
            limit=limite,
            include_deleted=incluir_deletadas,
            order_desc=ordem_descendente,
        )
        return [ContaLuzOut.from_entity(entidade) for entidade in entidades]


@router.post("/importacoes", response_model=SyncResult)
def sync_from_pdf(request: SyncRequest) -> SyncResult:
    """
    Varre PDFs de faturas CELESC, encontra referências (mm/yyyy) e cria as ausentes no banco.
    - Se `pdf_paths` não for enviado, busca PDFs em `core/assets/*.pdf`.
    - Aceita diretórios em `pdf_paths` (expansão para .pdf; recursivo por padrão).
    - Aceita padrões glob em `pdf_paths` (ex.: "/home/.../assets/**/*.pdf").
    """
    pdf_paths: Sequence[str]
    if request.pdf_paths is not None:
        # Remove entradas vazias/branco
        entradas_validas = [
            p for p in request.pdf_paths if isinstance(p, str) and p.strip()
        ]
        if entradas_validas:
            pdf_paths = _expand_to_pdf_files(entradas_validas, request.recursive)
            app_logger.info(
                "Expanded paths",
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
                        "Nenhum PDF encontrado nos caminhos fornecidos. "
                        "Envie caminhos de arquivos .pdf, um diretório contendo PDFs, ou padrões glob (*.pdf)."
                    ),
                )
        else:
            # Todas as entradas eram vazias; cai no fallback de assets
            app_logger.info("Empty pdf_paths payload; using default assets fallback")
            base_dir = Path(__file__).resolve().parents[2]
            assets_dir = base_dir / "core" / "assets"
            if not assets_dir.exists():
                raise HTTPException(
                    status_code=400, detail=f"Assets directory not found: {assets_dir}"
                )
            pdf_paths = [str(caminho) for caminho in sorted(assets_dir.glob("*.pdf"))]
            if not pdf_paths:
                raise HTTPException(
                    status_code=400, detail=f"No PDFs found under {assets_dir}"
                )
            app_logger.info(
                "Using default assets directory", extra={"pdf_count": len(pdf_paths)}
            )
    else:
        # fallback: core/assets
        base_dir = Path(__file__).resolve().parents[2]  # api/ -> raiz do projeto
        assets_dir = base_dir / "core" / "assets"
        if not assets_dir.exists():
            raise HTTPException(
                status_code=400, detail=f"Assets directory not found: {assets_dir}"
            )
        pdf_paths = [str(caminho) for caminho in sorted(assets_dir.glob("*.pdf"))]
        if not pdf_paths:
            raise HTTPException(
                status_code=400, detail=f"No PDFs found under {assets_dir}"
            )
        app_logger.info(
            "Using default assets directory", extra={"pdf_count": len(pdf_paths)}
        )

    try:
        with get_database_session() as session:
            repositorio: ContaLuzRepositoryPort = cast(
                ContaLuzRepositoryPort, ContaLuzRepository(session)
            )
            servico = ContaLuzSyncService(repositorio)
            resumo = servico.sync_from_pdfs(pdf_paths)
    except OperationalError as err:
        app_logger.exception("Database connectivity error during sync")
        raise HTTPException(
            status_code=503, detail="Database unavailable or unreachable."
        ) from err
    except ProgrammingError as err:
        app_logger.exception("Database schema error during sync (missing tables?)")
        raise HTTPException(
            status_code=500,
            detail="Database schema missing. Run migrations: 'uv run alembic upgrade head' or set INIT_DB_SCHEMA=1 once.",
        ) from err

    app_logger.info(
        "Sync completed",
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
def sync_from_upload(files: List[UploadFile] = File(...)) -> SyncResult:
    """
    Recebe um ou mais PDFs via multipart/form-data e executa a sincronização.

    Curl de exemplo:
      curl -X POST "http://localhost:8000/conta-luz/sync-from-upload" \
           -F "files=@/caminho/para/arquivo1.pdf" \
           -F "files=@/caminho/para/arquivo2.pdf"
    """
    if not files:
        raise HTTPException(
            status_code=400, detail="Envie pelo menos um arquivo PDF em 'files'."
        )

    caminhos_temporarios: List[str] = []
    arquivos_invalidos: List[str] = []

    for arquivo in files:
        nome_original = arquivo.filename or "arquivo_sem_nome.pdf"
        # Checagem superficial de tipo; ainda assim persistimos como .pdf
        if arquivo.content_type not in {
            "application/pdf",
            "application/octet-stream",
        } and not nome_original.lower().endswith(".pdf"):
            arquivos_invalidos.append(nome_original)
            continue
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temporario:
                shutil.copyfileobj(arquivo.file, temporario)
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
        "Received uploaded PDFs",
        extra={
            "uploaded_count": len(files),
            "accepted_count": len(caminhos_temporarios),
            "rejected": arquivos_invalidos,
        },
    )

    try:
        with get_database_session() as session:
            repositorio: ContaLuzRepositoryPort = cast(
                ContaLuzRepositoryPort, ContaLuzRepository(session)
            )
            servico = ContaLuzSyncService(repositorio)
            resumo = servico.sync_from_pdfs(caminhos_temporarios)
    except OperationalError as err:
        app_logger.exception("Database connectivity error during sync")
        raise HTTPException(
            status_code=503, detail="Database unavailable or unreachable."
        ) from err
    except ProgrammingError as err:
        app_logger.exception("Database schema error during sync (missing tables?)")
        raise HTTPException(
            status_code=500,
            detail="Database schema missing. Run migrations: 'uv run alembic upgrade head' or set INIT_DB_SCHEMA=1 once.",
        ) from err
    finally:
        for caminho in caminhos_temporarios:
            with contextlib.suppress(OSError):
                Path(caminho).unlink(missing_ok=True)

    app_logger.info(
        "Upload sync completed",
        extra={
            "files_processed": resumo.get("files_processed"),
            "files_failed": resumo.get("files_failed"),
            "created_count": resumo.get("created"),
            "skipped_count": resumo.get("skipped"),
        },
    )

    return SyncResult(**resumo)
