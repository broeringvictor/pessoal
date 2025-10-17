from __future__ import annotations

from dataclasses import dataclass
from typing import Union

from core.enums.e_expense_type import EExpenseType


@dataclass(frozen=True, slots=True)
class TipoDespesa:
    """Value Object de domínio para o tipo de despesa.

    Entrada: código numérico (1, 2, 3, 4) conforme EExpenseType.
    Persistência: salvar como nome textual (FIXA, RECORRENTE, EMPRESTIMO, CARTAO_CREDITO).
    Imutável e com igualdade por valor.
    """

    tipo_despesa: EExpenseType

    def __init__(self, *_args, **_kwargs) -> None:  # type: ignore[override]
        raise TypeError("Use as fábricas da classe (ex.: ExpenseType.criar_de_codigo).")

    @classmethod
    def _criar_interno(cls, tipo: EExpenseType) -> "TipoDespesa":
        instancia = object.__new__(cls)
        object.__setattr__(instancia, "tipo_despesa", tipo)
        return instancia  # type: ignore[return-value]

    # Fábricas
    @classmethod
    def criar_de_codigo(cls, codigo: Union[int, str]) -> "TipoDespesa":
        try:
            codigo_inteiro = int(codigo)
        except (ValueError, TypeError):
            raise TypeError("Código do tipo de despesa deve ser um inteiro (1, 2, 3 ou 4).")
        try:
            tipo = EExpenseType(codigo_inteiro)
        except ValueError:
            mapa = ", ".join(f"{e.value}={e.name}" for e in EExpenseType)
            raise ValueError(f"Código inválido. Utilize um dos seguintes: {mapa}.")
        return cls._criar_interno(tipo)

    @classmethod
    def criar_de_nome(cls, nome: str) -> "TipoDespesa":
        try:
            tipo = EExpenseType[nome.upper()]
        except KeyError:
            opcoes = ", ".join(e.name for e in EExpenseType)
            raise ValueError(f"Nome inválido. Utilize um dos seguintes: {opcoes}.")
        return cls._criar_interno(tipo)

    # Conversões e persistência
    def para_banco(self) -> str:
        """Valor textual a ser salvo no banco (ex.: 'FIXA')."""
        return self.tipo_despesa.name

    def como_enum(self) -> EExpenseType:
        return self.tipo_despesa

    def como_codigo(self) -> int:
        return self.tipo_despesa.value

    def como_texto(self) -> str:
        return self.tipo_despesa.name

    # Atualizações imutáveis
    def atualizar_tipo_por_codigo(self, novo_codigo: Union[int, str]) -> "TipoDespesa":
        return type(self).criar_de_codigo(novo_codigo)

    def atualizar_tipo_por_nome(self, novo_nome: str) -> "TipoDespesa":
        return type(self).criar_de_nome(novo_nome)

    # Conveniências semânticas
    def e_fixa(self) -> bool:
        return self.tipo_despesa is EExpenseType.FIXA

    def e_recorrente(self) -> bool:
        return self.tipo_despesa is EExpenseType.RECORRENTE

    def e_emprestimo(self) -> bool:
        return self.tipo_despesa is EExpenseType.EMPRESTIMO

    def e_cartao_credito(self) -> bool:
        return self.tipo_despesa is EExpenseType.CARTAO_CREDITO

    def __str__(self) -> str:
        return self.tipo_despesa.name

