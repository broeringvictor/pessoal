from __future__ import annotations

"""VO de domínio para mês/ano de referência (MM/YYYY).

Especializa o normalizador `ReferenciaMensal`, herdando validação e
normalização de entradas como "09/2025" ou "09/2025 (Atual)".
Mantém semântica de Value Object (imutável e igualdade por valor).
"""

from typing import Tuple

from core.shared.value_objects import ReferenciaMensal


class MesReferencia(ReferenciaMensal):
    """Value Object do domínio para representar uma referência mensal.

    - A propriedade `referencia` fica padronizada em "MM/YYYY".
    - `as_tuple()` retorna `(mes:int, ano:int)`.
    - `para_banco()` retorna inteiro otimizado no formato `AAAAMM`.
    """

    # Impede construção direta; obrigatoriedade de usar fábricas da classe
    def __init__(self, *_args, **_kwargs) -> None:  # type: ignore[override]
        raise TypeError("Use as fábricas da classe (ex.: MesReferencia.criar_de_texto, MesReferencia.do_banco).")

    # Construtor interno para uso exclusivo das fábricas
    @classmethod
    def _criar_interno(cls, texto: str) -> "MesReferencia":
        instancia = object.__new__(cls)
        ReferenciaMensal.__init__(instancia, texto)  # chama validação/normalização do pai
        return instancia  # type: ignore[return-value]

    # Criação declarativa
    @classmethod
    def criar_de_texto(cls, texto: str) -> "MesReferencia":
        return cls._criar_interno(texto)

    @classmethod
    def do_banco(cls, ano_mes: int) -> "MesReferencia":
        """Reconstrói a partir do formato inteiro AAAAMM (ex.: 202509)."""
        ano = ano_mes // 100
        mes = ano_mes % 100
        return cls._criar_interno(f"{mes:02d}/{ano}")

    # Persistência otimizada para banco de dados
    def para_banco(self) -> int:
        """Inteiro no formato AAAAMM (ex.: 202509)."""
        return (self.ano * 100) + self.mes

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
