from __future__ import annotations

"""VO de domínio para mês/ano de referência (MM/YYYY).

Especializa o normalizador `ReferenciaMensal`, herdando validação e
normalização de entradas como "09/2025" ou "09/2025 (Atual)".
Mantém semântica de Value Object (imutável e igualdade por valor).
"""

from datetime import date, datetime
from typing import Tuple, Union

from core.shared.value_objects import ReferenciaMensal


class MesReferencia(ReferenciaMensal):
    """Value Object do domínio para representar uma referência mensal.

    - A propriedade `referencia` fica padronizada em "MM/YYYY".
    - `as_tuple()` retorna `(mes:int, ano:int)`.
    - `para_banco()` retorna `date(ano, mes, 1)` (ótimo para Postgres/filters).
    """

    # Impede construção direta; obrigatoriedade de usar fábricas da classe
    def __init__(self, *_args, **_kwargs) -> None:  # type: ignore[override]
        raise TypeError(
            "Use as fábricas da classe (ex.: MesReferencia.criar_de_texto ou criar_de_data)."
        )

    # Construtor interno para uso exclusivo das fábricas
    @classmethod
    def _criar_interno(cls, texto: str) -> "MesReferencia":
        # Usa o VO base para validar/normalizar e então copia os campos normalizados
        base = ReferenciaMensal(texto)
        instancia = object.__new__(cls)
        object.__setattr__(instancia, "referencia", base.referencia)
        object.__setattr__(instancia, "mes", base.mes)
        object.__setattr__(instancia, "ano", base.ano)
        return instancia  # type: ignore[return-value]

    # Criação declarativa
    @classmethod
    def criar_de_texto(cls, texto: str) -> "MesReferencia":
        return cls._criar_interno(texto)

    @classmethod
    def criar_de_data(cls, valor_data: Union[date, datetime]) -> "MesReferencia":
        ano = valor_data.year
        mes = valor_data.month
        return cls._criar_interno(f"{mes:02d}/{ano}")

    # Persistência otimizada para banco de dados
    def para_banco(self) -> date:
        """Retorna a data do primeiro dia do mês (YYYY-MM-01) para persistência em Postgres (DATE)."""
        return date(self.ano, self.mes, 1)

    def como_data(self) -> date:
        """Alias para `para_banco()`, útil em consultas/filters."""
        return self.para_banco()

    # Atualização imutável
    def atualizar_referencia(self, novo_texto: str) -> "MesReferencia":
        """Retorna um novo VO com a referência atualizada a partir de texto bruto."""
        return type(self)._criar_interno(novo_texto)

    # Verificações
    def esta_normalizada(self) -> bool:
        """Confere se o texto interno está normalizado como MM/YYYY."""
        return self.referencia == f"{self.mes:02d}/{self.ano}"

    # Atalhos semânticos
    def como_par(self) -> Tuple[int, int]:
        """Alias declarativo para `as_tuple()`."""
        return self.as_tuple()

    # DDD: remoção é responsabilidade do agregado/repositório
    def remover(self) -> None:
        return None
