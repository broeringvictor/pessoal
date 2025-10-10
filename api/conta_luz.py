from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Sequence
import glob
import tempfile
import shutil

from fastapi import APIRouter, HTTPException, UploadFile, File, Body
from pydantic import BaseModel
from sqlalchemy.exc import OperationalError, ProgrammingError

from api.logging_config import logger as app_logger
from application.conta_luz.handlers import ContaLuzSyncService
from infrastructure.data.db_context import get_database_session
from infrastructure.repository.conta_luz.repository import ContaLuzRepository

router = APIRouter(prefix="/conta-luz", tags=["conta-luz"])


class SyncRequest(BaseModel):
    pdf_paths: Optional[List[str]] = None
    recursive: bool = True  # permite vasculhar subpastas quando um diretório for informado


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
    # Remove duplicados mantendo ordem
    vistos: set[str] = set()
    unicos: List[str] = []
    for caminho in arquivos:
        if caminho not in vistos:
            vistos.add(caminho)
            unicos.append(caminho)
    return unicos


@router.post("/sync-from-pdf", response_model=SyncResult)
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
        entradas_validas = [p for p in request.pdf_paths if isinstance(p, str) and p.strip()]
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
            base_dir = Path(__file__).resolve().parents[1]
            assets_dir = base_dir / "core" / "assets"
            if not assets_dir.exists():
                raise HTTPException(status_code=400, detail=f"Assets directory not found: {assets_dir}")
            pdf_paths = [str(caminho) for caminho in sorted(assets_dir.glob("*.pdf"))]
            if not pdf_paths:
                raise HTTPException(status_code=400, detail=f"No PDFs found under {assets_dir}")
            app_logger.info("Using default assets directory", extra={"pdf_count": len(pdf_paths)})
    else:
        # fallback: core/assets
        base_dir = Path(__file__).resolve().parents[1]  # api/ -> raiz do projeto
        assets_dir = base_dir / "core" / "assets"
        if not assets_dir.exists():
            raise HTTPException(status_code=400, detail=f"Assets directory not found: {assets_dir}")
        pdf_paths = [str(caminho) for caminho in sorted(assets_dir.glob("*.pdf"))]
        if not pdf_paths:
            raise HTTPException(status_code=400, detail=f"No PDFs found under {assets_dir}")
        app_logger.info("Using default assets directory", extra={"pdf_count": len(pdf_paths)})

    try:
        with get_database_session() as session:
            repositorio = ContaLuzRepository(session)
            servico = ContaLuzSyncService(repositorio)
            resumo = servico.sync_from_pdfs(pdf_paths)
    except OperationalError as err:
        app_logger.exception("Database connectivity error during sync")
        raise HTTPException(status_code=503, detail="Database unavailable or unreachable.") from err
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


@router.post("/sync-from-upload", response_model=SyncResult)
def sync_from_upload(files: List[UploadFile] = File(...)) -> SyncResult:
    """
    Recebe um ou mais PDFs via multipart/form-data e executa a sincronização.

    Curl de exemplo:
      curl -X POST "http://localhost:8000/conta-luz/sync-from-upload" \
           -F "files=@/caminho/para/arquivo1.pdf" \
           -F "files=@/caminho/para/arquivo2.pdf"
    """
    if not files:
        raise HTTPException(status_code=400, detail="Envie pelo menos um arquivo PDF em 'files'.")

    caminhos_temporarios: List[str] = []
    arquivos_invalidos: List[str] = []

    for arquivo in files:
        nome_original = arquivo.filename or "arquivo_sem_nome.pdf"
        # Checagem superficial de tipo; ainda assim persistimos como .pdf
        if arquivo.content_type not in {"application/pdf", "application/octet-stream"} and not nome_original.lower().endswith(".pdf"):
            arquivos_invalidos.append(nome_original)
            continue
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temporario:
                # Evita carregar tudo em memória; stream para disco
                shutil.copyfileobj(arquivo.file, temporario)
                caminhos_temporarios.append(temporario.name)
        finally:
            try:
                arquivo.file.close()
            except Exception:
                pass

    if arquivos_invalidos and not caminhos_temporarios:
        raise HTTPException(status_code=400, detail=f"Nenhum PDF válido foi enviado. Inválidos: {arquivos_invalidos}")

    app_logger.info(
        "Received uploaded PDFs",
        extra={"uploaded_count": len(files), "accepted_count": len(caminhos_temporarios), "rejected": arquivos_invalidos},
    )

    try:
        with get_database_session() as session:
            repositorio = ContaLuzRepository(session)
            servico = ContaLuzSyncService(repositorio)
            resumo = servico.sync_from_pdfs(caminhos_temporarios)
    except OperationalError as err:
        app_logger.exception("Database connectivity error during sync")
        raise HTTPException(status_code=503, detail="Database unavailable or unreachable.") from err
    except ProgrammingError as err:
        app_logger.exception("Database schema error during sync (missing tables?)")
        raise HTTPException(
            status_code=500,
            detail="Database schema missing. Run migrations: 'uv run alembic upgrade head' or set INIT_DB_SCHEMA=1 once.",
        ) from err
    finally:
        # Limpa os temporários
        for caminho in caminhos_temporarios:
            try:
                Path(caminho).unlink(missing_ok=True)
            except Exception:
                # Não falha a requisição por erro de limpeza
                pass

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


@router.post("/sync-from-binary", response_model=SyncResult)
def sync_from_binary(data: bytes = Body(..., media_type="application/pdf")) -> SyncResult:
    """
    Recebe um único PDF como corpo binário (Content-Type: application/pdf) e executa a sincronização.

    Exemplos:
      curl -X POST "http://localhost:8000/conta-luz/sync-from-binary" \
           -H "Content-Type: application/pdf" \
           --data-binary @/caminho/para/fatura.pdf

      PowerShell:
        Invoke-WebRequest -Uri "http://localhost:8000/conta-luz/sync-from-binary" -Method POST \
          -InFile "C:\\caminho\\fatura.pdf" -ContentType "application/pdf"
    """
    if not data:
        raise HTTPException(status_code=400, detail="Corpo da requisição vazio. Envie um PDF no corpo (application/pdf).")

    caminho_temporario: Optional[str] = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temporario:
            temporario.write(data)
            caminho_temporario = temporario.name

        with get_database_session() as session:
            repositorio = ContaLuzRepository(session)
            servico = ContaLuzSyncService(repositorio)
            resumo = servico.sync_from_pdfs([caminho_temporario])
    except OperationalError as err:
        app_logger.exception("Database connectivity error during sync")
        raise HTTPException(status_code=503, detail="Database unavailable or unreachable.") from err
    except ProgrammingError as err:
        app_logger.exception("Database schema error during sync (missing tables?)")
        raise HTTPException(
            status_code=500,
            detail="Database schema missing. Run migrations: 'uv run alembic upgrade head' or set INIT_DB_SCHEMA=1 once.",
        ) from err
    finally:
        if caminho_temporario:
            try:
                Path(caminho_temporario).unlink(missing_ok=True)
            except Exception:
                pass

    app_logger.info(
        "Binary upload sync completed",
        extra={
            "files_processed": resumo.get("files_processed"),
            "files_failed": resumo.get("files_failed"),
            "created_count": resumo.get("created"),
            "skipped_count": resumo.get("skipped"),
        },
    )

    return SyncResult(**resumo)
