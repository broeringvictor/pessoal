from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Sequence
import glob

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import OperationalError

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
    if request.pdf_paths:
        pdf_paths = _expand_to_pdf_files(request.pdf_paths, request.recursive)
        app_logger.info("Expanded paths", extra={"input_count": len(request.pdf_paths), "pdf_count": len(pdf_paths)})
        if not pdf_paths:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Nenhum PDF encontrado nos caminhos fornecidos. "
                    "Envie caminhos de arquivos .pdf, um diretório contendo PDFs, ou padrões glob (*.pdf)."
                ),
            )
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

    app_logger.info(
        "Sync completed",
        extra={
            "pdf_count": resumo.get("pdf_count"),
            "rows_parsed": resumo.get("rows_parsed"),
            "distinct_references_found": resumo.get("distinct_references_found"),
            "created": resumo.get("created"),
            "skipped": resumo.get("skipped"),
        },
    )

    return SyncResult(**resumo)
