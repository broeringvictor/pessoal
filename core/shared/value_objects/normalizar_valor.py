from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
from typing import Union
import re


@dataclass(frozen=True, slots=True)
class ValorMonetario:
    """Value Object imutável para valores monetários normalizados com 2 casas decimais."""

    valor: Decimal

    def __post_init__(self) -> None:
        # Garante 2 casas decimais
        normalizado = self.valor.quantize(Decimal("0.01"))
        object.__setattr__(self, "valor", normalizado)

    @classmethod
    def from_bruto(cls, bruto: Union[str, int, float, Decimal]) -> "ValorMonetario":
        if isinstance(bruto, Decimal):
            valor = bruto

        elif isinstance(bruto, (int, float)):
            valor = Decimal(str(bruto))

        elif isinstance(bruto, str):
            texto = bruto.strip()
            # Remove espaços e símbolo de moeda (R$)
            texto = re.sub(r"\s|R\$", "", texto)

            # Regras de normalização:
            # - Se houver vírgula e ponto: assumir ponto como milhar e vírgula como decimal (ex.: 1.234,56)
            # - Se houver apenas vírgula: tratá-la como decimal (ex.: 1234,56 -> 1234.56)
            # - Se não houver vírgula: manter ponto como decimal, se houver (ex.: 1234.5 -> 1234.5)
            if "," in texto and "." in texto:
                texto_normalizado = texto.replace(".", "").replace(",", ".")
            elif "," in texto:
                texto_normalizado = texto.replace(",", ".")
            else:
                texto_normalizado = (
                    texto  # já está em formato com ponto decimal ou inteiro
                )

            try:
                valor = Decimal(texto_normalizado)
            except InvalidOperation as exc:
                raise ValueError(f"Valor inválido: '{bruto}'.") from exc

        else:
            raise ValueError("Tipo de valor não suportado.")
        return cls(valor)

    @classmethod
    def from_centavos(cls, centavos: int) -> "ValorMonetario":
        valor = (Decimal(int(centavos)) / Decimal(100)).quantize(Decimal("0.01"))
        return cls(valor)

    def to_centavos(self) -> int:
        return int(
            (self.valor * Decimal(100)).quantize(Decimal("1"), rounding=ROUND_HALF_EVEN)
        )

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.valor:.2f}"
