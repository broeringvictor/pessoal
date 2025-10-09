from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Protocol, Sequence

from core.entities.conta_luz import ContaLuz
from core.dataframe.celesc_extrator import extrair_contas_luz


class ContaLuzRepositoryPort(Protocol):
    def list_existing_references(self) -> set[str]:
        ...

    def add_many(self, contas: Iterable[ContaLuz]) -> int:
        ...


@dataclass(slots=True)
class ContaLuzSyncService:
    """Aplicação (camada de casos de uso) para sincronizar faturas CELESC com o banco."""

    repository: ContaLuzRepositoryPort

    def sync_from_pdfs(self, pdf_paths: Sequence[str]) -> dict:
        """
        Lê PDFs, extrai contas (Referência, Valor), compara com o banco e insere as ausentes.
        Retorna um resumo da operação.
        """
        referencias_existentes = self.repository.list_existing_references()

        referencias_coletadas: dict[str, ContaLuz] = {}
        total_linhas_extraidas = 0

        for caminho_pdf in pdf_paths:
            contas = extrair_contas_luz(caminho_pdf)
            total_linhas_extraidas += len(contas)
            for conta in contas:
                # última ocorrência prevalece, caso haja duplicidades no PDF
                referencias_coletadas[conta.referencia] = conta

        referencias_novas = [ref for ref in referencias_coletadas if ref not in referencias_existentes]
        contas_para_inserir = [referencias_coletadas[ref] for ref in referencias_novas]

        inseridos = 0
        if contas_para_inserir:
            inseridos = self.repository.add_many(contas_para_inserir)

        return {
            "pdf_count": len(pdf_paths),
            "rows_parsed": total_linhas_extraidas,
            "distinct_references_found": len(referencias_coletadas),
            "created": inseridos,
            "skipped": len(referencias_coletadas) - inseridos,
            "created_references": referencias_novas,
        }

