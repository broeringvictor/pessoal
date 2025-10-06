from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True, slots=True)
class ReferenciaMensal:
    """Value Object para referência mensal no formato MM/YYYY.

    - Aceita strings como "09/2025" ou "09/2025 (Atual)" e normaliza para "09/2025".
    - Valida mês (01..12) e formata sempre com 2 dígitos para o mês.
    """

    referencia: str
    mes: int = 0
    ano: int = 0

    def __post_init__(self) -> None:
        texto = self.referencia.strip()
        # Remove sufixo opcional (Atual)
        texto = re.sub(r"\s*\(atual\)\s*$", "", texto, flags=re.IGNORECASE)
        # Busca MM/YYYY em qualquer posição
        match = re.search(r"\b(\d{2})/(\d{4})\b", texto)
        if not match:
            raise ValueError(f"Referência inválida: '{self.referencia}'. Esperado MM/YYYY.")
        mes = int(match.group(1))
        ano = int(match.group(2))
        if mes < 1 or mes > 12:
            raise ValueError(f"Mês inválido na referência: '{match.group(1)}'.")

        normalizada = f"{mes:02d}/{ano}"

        # Atribuição em dataclass congelado
        object.__setattr__(self, "referencia", normalizada)
        object.__setattr__(self, "mes", mes)
        object.__setattr__(self, "ano", ano)

    def __str__(self) -> str:  # pragma: no cover
        return self.referencia

    def as_tuple(self) -> tuple[int, int]:
        return (self.mes, self.ano)

