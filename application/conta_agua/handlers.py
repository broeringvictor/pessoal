from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence
import logging

from core.entities.conta_agua import ContaAgua
from core.dataframe.samae_extrator import obter_tabela_samae
from .interface import ContaAguaRepositoryPort


_logger = logging.getLogger("pessoal.application.conta_agua")


@dataclass(slots=True)
class ContaAguaSyncService:
    """Aplicação (caso de uso) para sincronizar faturas SAMAE com o banco."""

    repository: ContaAguaRepositoryPort

    def sync_from_pdfs(self, pdf_paths: Sequence[str]) -> dict:
        """
        Para cada PDF, extrai a linha atual (Referência, Valor), compara com o banco
        e insere as referências ausentes.
        """
        _logger.info("Starting SAMAE sync from PDFs", extra={"pdf_count": len(pdf_paths)})
        referencias_existentes = self.repository.list_existing_references()
        _logger.debug(
            "Existing water references loaded",
            extra={"existing_count": len(referencias_existentes)},
        )

        referencias_coletadas: dict[str, ContaAgua] = {}
        total_linhas_extraidas = 0
        arquivos_com_falha: list[str] = []

        for caminho_pdf in pdf_paths:
            try:
                df = obter_tabela_samae(caminho_pdf)
                # Espera-se uma única linha com colunas 'Referência' e 'Valor (R$)'
                if df.empty:
                    raise ValueError("Tabela extraída está vazia.")
                referencia_texto = str(df.iloc[0]["Referência"])  # ex.: "09/2025 (Atual)"
                valor_texto = str(df.iloc[0]["Valor (R$)"])       # ex.: "R$ 1.234,56"
                conta = ContaAgua.criar(referencia_texto, valor_texto)
                referencias_coletadas[conta.referencia] = conta
                total_linhas_extraidas += 1
                _logger.info(
                    "Extracted SAMAE account from PDF",
                    extra={"pdf": caminho_pdf, "reference": conta.referencia},
                )
            except (RuntimeError, ValueError, FileNotFoundError, OSError) as exc:
                arquivos_com_falha.append(caminho_pdf)
                _logger.exception(
                    "Failed to extract SAMAE from PDF",
                    extra={"pdf": caminho_pdf, "failed_count": len(arquivos_com_falha)},
                )
                continue

        referencias_novas = [
            ref for ref in referencias_coletadas if ref not in referencias_existentes
        ]
        contas_para_inserir = [referencias_coletadas[ref] for ref in referencias_novas]

        _logger.info(
            "Computed new water references",
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
                "Queued water entities for insert",
                extra={"inserted_count": inseridos},
            )
        else:
            _logger.info("No new water references to insert")

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
        # Evita colidir com campos reservados do LogRecord
        safe_extra = {k: v for k, v in resumo.items() if k not in {"failed_files", "created"}}
        safe_extra["created_count"] = resumo["created"]
        _logger.info("SAMAE sync summary", extra=safe_extra)
        return resumo

