from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence
import logging

from core.entities.expenses.conta_luz import ContaLuz
from core.dataframe.celesc_extrator import extrair_contas_luz
from .irepository import ContaLuzRepositoryPort


_logger = logging.getLogger("pessoal.application.conta_luz")


@dataclass(slots=True)
class ContaLuzSyncService:
    """Aplicação (camada de casos de uso) para sincronizar faturas CELESC com o banco."""

    repository: ContaLuzRepositoryPort

    def sync_from_pdfs(self, pdf_paths: Sequence[str]) -> dict:
        """
        Lê PDFs, extrai contas (Referência, Valor), compara com o banco e insere as ausentes.
        Retorna um resumo da operação, incluindo arquivos que falharam na extração.
        """
        _logger.info("Starting sync from PDFs", extra={"pdf_count": len(pdf_paths)})
        referencias_existentes = self.repository.list_existing_references()
        _logger.debug(
            "Existing references loaded",
            extra={"existing_count": len(referencias_existentes)},
        )

        referencias_coletadas: dict[str, ContaLuz] = {}
        total_linhas_extraidas = 0
        arquivos_com_falha: list[str] = []

        for caminho_pdf in pdf_paths:
            try:
                contas = extrair_contas_luz(caminho_pdf)
                _logger.info(
                    "Extracted accounts from PDF",
                    extra={"pdf": caminho_pdf, "accounts_found": len(contas)},
                )
            except (RuntimeError, ValueError, FileNotFoundError, OSError) as exc:
                arquivos_com_falha.append(caminho_pdf)
                _logger.exception(
                    "Failed to extract from PDF",
                    extra={"pdf": caminho_pdf, "failed_count": len(arquivos_com_falha)},
                )
                continue

            total_linhas_extraidas += len(contas)
            for conta in contas:
                # última ocorrência prevalece, caso haja duplicidades no PDF
                referencias_coletadas[conta.referencia] = conta

        referencias_novas = [
            ref for ref in referencias_coletadas if ref not in referencias_existentes
        ]
        contas_para_inserir = [referencias_coletadas[ref] for ref in referencias_novas]

        _logger.info(
            "Computed new references",
            extra={
                "distinct_found": len(referencias_coletadas),
                "new_count": len(referencias_novas),
                "to_insert": len(contas_para_inserir),
            },
        )

        inseridos = 0
        if contas_para_inserir:
            inseridos = self.repository.add_many(contas_para_inserir)
            _logger.info(
                "Queued entities for insert",
                extra={"inserted_count": inseridos},
            )
        else:
            _logger.info("No new references to insert")

        resumo = {
            "pdf_count": len(pdf_paths),
            "files_processed": len(pdf_paths) - len(arquivos_com_falha),
            "files_failed": len(arquivos_com_falha),
            "failed_files": arquivos_com_falha,
            "rows_parsed": total_linhas_extraidas,
            "distinct_references_found": len(referencias_coletadas),
            "created": inseridos,
            "skipped": len(referencias_coletadas) - inseridos,
            "created_references": referencias_novas,
        }
        # Evita chaves reservadas do LogRecord como 'created'
        safe_extra = {
            k: v for k, v in resumo.items() if k not in {"failed_files", "created"}
        }
        safe_extra["created_count"] = resumo["created"]
        _logger.info("Sync summary", extra=safe_extra)
        return resumo
