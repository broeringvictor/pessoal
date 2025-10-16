from __future__ import annotations

from datetime import date, datetime
from typing import Union

from core.shared.value_objects.normalizar_data import NormalizarData


class DataEvento(NormalizarData):
    """Domain Value Object for the calendar date of an Entrada.

    - Inherits validation and normalization (DD/MM/YYYY) from NormalizarData.
    - Provides factories, persistence helpers, and semantic aliases for the domain.
    """

    def __init__(self, *_args, **_kwargs) -> None:  # type: ignore[override]
        raise TypeError(
            "Use the class factories (e.g., DataEvento.criar_de_texto or criar_de_data)."
        )

    @classmethod
    def _criar_interno(cls, texto: str) -> "DataEvento":
        base = NormalizarData(texto)
        instancia = object.__new__(cls)
        # Copy normalized state from base Value Object
        object.__setattr__(instancia, "data", base.data)
        object.__setattr__(instancia, "dia", base.dia)
        object.__setattr__(instancia, "mes", base.mes)
        object.__setattr__(instancia, "ano", base.ano)
        object.__setattr__(instancia, "data_iso", base.data_iso)
        return instancia  # type: ignore[return-value]

    # Declarative factories
    @classmethod
    def criar_de_texto(cls, texto: str) -> "DataEvento":
        return cls._criar_interno(texto)

    @classmethod
    def criar_de_data(cls, valor_data: Union[date, datetime]) -> "DataEvento":
        return cls._criar_interno(f"{valor_data.day:02d}/{valor_data.month:02d}/{valor_data.year}")

    # Persistence helpers
    def para_banco(self) -> date:
        """Return a Python date for Postgres drivers (optimal)."""
        return self.as_date()

    def como_iso(self) -> str:
        """Return ISO string YYYY-MM-DD for persistence."""
        return self.as_postgres_value()

    # Semantic helpers
    def como_texto(self) -> str:
        """Return normalized DD/MM/YYYY used in the domain."""
        return self.data

    def atualizar_data(self, novo_texto: str) -> "DataEvento":
        """Return a new VO with updated date from raw text."""
        return type(self)._criar_interno(novo_texto)

    def esta_normalizada(self) -> bool:
        """Check if internal representation is DD/MM/YYYY consistent with parsed parts."""
        return self.data == f"{self.dia:02d}/{self.mes:02d}/{self.ano}"
