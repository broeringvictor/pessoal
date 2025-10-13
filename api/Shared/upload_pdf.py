from __future__ import annotations

import contextlib
import glob
import shutil
import tempfile
from pathlib import Path
from typing import BinaryIO, List, Sequence, Tuple, cast

from fastapi import HTTPException, UploadFile
from sqlalchemy.exc import OperationalError, ProgrammingError

from api.configurations.logging_config import logger as app_logger
from application.conta_agua.handlers import ContaAguaSyncService
from infrastructure.data.db_context import get_database_session
from infrastructure.repository.conta_agua.repository import ContaAguaRepository


class UploadPDF:
    """Utilitários compartilhados para tratamento de uploads e arquivos PDF."""

    @staticmethod
    def normalize_path_text(path_text: str) -> str:
        return path_text.replace("\\", "/")

    @staticmethod
    def has_wildcards(texto: str) -> bool:
        return any(sinal in texto for sinal in ("*", "?", "["))

    @staticmethod
    def expand_to_pdf_files(path_texts: Sequence[str], recursive: bool) -> List[str]:
        """Expande caminhos e padrões para uma lista única e ordenada de arquivos PDF existentes."""
        arquivos: List[str] = []
        for texto in path_texts:
            normalizado = UploadPDF.normalize_path_text(texto)
            if UploadPDF.has_wildcards(normalizado):
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

    @staticmethod
    def persistir_uploads_em_temporarios(arquivos_upload: List[UploadFile]) -> Tuple[List[str], List[str]]:
        """Valida uploads e grava PDFs em temporários. Retorna (caminhos_válidos, nomes_inválidos)."""
        caminhos_temporarios: List[str] = []
        arquivos_invalidos: List[str] = []
        for arquivo in arquivos_upload:
            nome_original = arquivo.filename or "arquivo_sem_nome.pdf"
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
        return caminhos_temporarios, arquivos_invalidos

    @staticmethod
    def sincronizar_contas_a_partir_de_pdfs(caminhos_temporarios: List[str]) -> dict:
        """Executa a sincronização no domínio a partir dos PDFs e retorna o resumo do serviço."""
        try:
            with get_database_session() as session:
                repositorio = ContaAguaRepository(session)
                servico = ContaAguaSyncService(repositorio)
                resumo = servico.sync_from_pdfs(caminhos_temporarios)
                return resumo
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