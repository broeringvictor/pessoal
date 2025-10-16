from __future__ import annotations

from dataclasses import dataclass
from typing import Union

from core.enums.e_transacao import ETransaction


@dataclass(frozen=True, slots=True)
class TransactionType:
    """Value Object de domínio para o tipo de transação.

    Entrada: código numérico (1, 2, 3, 4) conforme ETransaction.
    Persistência: salvar como nome textual (ENTRADA, SAIDA, TRANSFERENCIA, INVESTIMENTO).
    Imutável e com igualdade por valor.
    """

    tipo_transacao: ETransaction

    def __init__(self, *_args, **_kwargs) -> None:  # type: ignore[override]
        raise TypeError("Use as fábricas da classe (ex.: TransactionType.criar_de_codigo).")

    @classmethod
    def _criar_interno(cls, tipo: ETransaction) -> "TransactionType":
        instancia = object.__new__(cls)
        object.__setattr__(instancia, "tipo_transacao", tipo)
        return instancia  # type: ignore[return-value]

    # Fábricas
    @classmethod
    def criar_de_codigo(cls, codigo: Union[int, str]) -> "TransactionType":
        try:
            codigo_inteiro = int(codigo)
        except (ValueError, TypeError):
            raise TypeError("Código do tipo de transação deve ser um inteiro (1, 2, 3 ou 4).")
        try:
            tipo = ETransaction(codigo_inteiro)
        except ValueError:
            mapa = ", ".join(f"{e.value}={e.name}" for e in ETransaction)
            raise ValueError(f"Código inválido. Utilize um dos seguintes: {mapa}.")
        return cls._criar_interno(tipo)

    @classmethod
    def criar_de_nome(cls, nome: str) -> "TransactionType":
        try:
            tipo = ETransaction[nome.upper()]
        except KeyError:
            opcoes = ", ".join(e.name for e in ETransaction)
            raise ValueError(f"Nome inválido. Utilize um dos seguintes: {opcoes}.")
        return cls._criar_interno(tipo)

    # Conversões e persistência
    def para_banco(self) -> str:
        """Valor textual a ser salvo no banco (ex.: 'ENTRADA')."""
        return self.tipo_transacao.name

    def como_enum(self) -> ETransaction:
        return self.tipo_transacao

    def como_codigo(self) -> int:
        return self.tipo_transacao.value

    def como_texto(self) -> str:
        return self.tipo_transacao.name

    # Atualizações imutáveis
    def atualizar_tipo_por_codigo(self, novo_codigo: Union[int, str]) -> "TransactionType":
        return type(self).criar_de_codigo(novo_codigo)

    def atualizar_tipo_por_nome(self, novo_nome: str) -> "TransactionType":
        return type(self).criar_de_nome(novo_nome)

    # Conveniências semânticas
    def e_entrada(self) -> bool:
        return self.tipo_transacao is ETransaction.ENTRADA

    def e_saida(self) -> bool:
        return self.tipo_transacao is ETransaction.SAIDA

    def e_transferencia(self) -> bool:
        return self.tipo_transacao is ETransaction.TRANSFERENCIA

    def e_investimento(self) -> bool:
        return self.tipo_transacao is ETransaction.INVESTIMENTO

    def __str__(self) -> str:
        return self.tipo_transacao.name
