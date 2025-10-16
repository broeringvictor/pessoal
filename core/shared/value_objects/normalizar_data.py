from __future__ import annotations

from dataclasses import dataclass
import re
from datetime import date

# Regex compilada para melhor desempenho em parsing repetido
_PADRAO_DATA_DD_MM_YYYY = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")


@dataclass(frozen=True, slots=True)
class NormalizarData:
    """Value Object para data no formato DD/MM/YYYY.

    - Aceita strings como "1/9/2025" ou "01/09/2025" e normaliza para "01/09/2025".
    - Valida dia, mês e ano usando calendário gregoriano (inclui anos bissextos).
    - Fornece representação ISO "YYYY-MM-DD" para persistência no Postgres.
    """

    data: str
    dia: int = 0
    mes: int = 0
    ano: int = 0
    data_iso: str = ""

    def __post_init__(self) -> None:
        texto_entrada = self.data.strip()
        correspondencia = _PADRAO_DATA_DD_MM_YYYY.search(texto_entrada)
        if not correspondencia:
            raise ValueError(f"Data inválida: '{self.data}'. Esperado DD/MM/YYYY.")

        dia = int(correspondencia.group(1))
        mes = int(correspondencia.group(2))
        ano = int(correspondencia.group(3))

        # Validação precisa e rápida via datetime.date
        try:
            data_validada = date(ano, mes, dia)
        except ValueError as erro:
            raise ValueError(f"Data inválida: {erro}") from None

        data_br_normalizada = f"{dia:02d}/{mes:02d}/{ano}"
        data_iso_normalizada = data_validada.isoformat()  # YYYY-MM-DD

        # Atribuição em dataclass congelado
        object.__setattr__(self, "data", data_br_normalizada)
        object.__setattr__(self, "dia", dia)
        object.__setattr__(self, "mes", mes)
        object.__setattr__(self, "ano", ano)
        object.__setattr__(self, "data_iso", data_iso_normalizada)

    def __str__(self) -> str:  # pragma: no cover
        return self.data

    def as_tuple(self) -> tuple[int, int, int]:
        return (self.dia, self.mes, self.ano)

    def as_postgres_value(self) -> str:
        """Retorna a data em ISO (YYYY-MM-DD) pronta para persistir no Postgres."""
        return self.data_iso

    def as_date(self) -> date:
        """Retorna datetime.date, ideal para drivers como psycopg (mais eficiente)."""
        return date(self.ano, self.mes, self.dia)
