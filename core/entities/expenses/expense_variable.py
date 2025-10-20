# core/entities/expenses/expense_variable.py
from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Union
from uuid import UUID

from core.shared.entities import Entity
from core.entities.expense import Expense  # base class
from core.value_object.evento_data import EventoData
from core.value_object.valor import Valor
from core.entities.expenses.expense_variable_type import ExpenseVariableType


@dataclass(slots=True, init=False)
class ExpenseVariable(Expense):
    """
    Entidade para despesas variáveis (ex.: Conta de Luz/Água).

    Campos de domínio:
    - reference_date: EventoData (VO do dia do evento)
    - amount: Valor (VO monetário)
    - expense_variable_type_id: UUID do tipo de despesa variável (quando houver)
    """
    # Atributos da entidade
    reference_date: EventoData
    amount: Valor
    expense_variable_type_id: Optional[UUID] = None

    # Atributo de apresentação (pode ser definido em subclasses)
    bill_label: str = "Despesa"

    # Sentinel para patch: distinguir parâmetro omitido de None explícito
    _NAO_FORNECIDO: classmethod = object()  # type: ignore[assignment]

    def __init__(
        self,
        *,
        reference_date: EventoData,
        amount: Valor,
        expense_variable_type_id: Optional[UUID] = None,
    ) -> None:
        self.reference_date = reference_date
        self.amount = amount
        self.expense_variable_type_id = expense_variable_type_id
        # garante inicialização de Entity (id/timestamps)
        Entity.__post_init__(self)

    # ----------------- Utilidades -----------------
    @staticmethod
    def _obter_tipo_id(
        tipo_despesa: Optional[Union[UUID, "ExpenseVariableType"]]
    ) -> Optional[UUID]:
        """Extrai o UUID do tipo de despesa, seja de um objeto ou do próprio UUID."""
        if isinstance(tipo_despesa, ExpenseVariableType):
            return tipo_despesa.id
        if isinstance(tipo_despesa, UUID):
            return tipo_despesa
        return None

    # ----------------- Comandos de domínio explícitos -----------------
    def alterar_mes_referencia(
        self,
        novo_mes_referencia: Union[str, date, datetime, EventoData],
    ) -> "ExpenseVariable":
        # Coerção inline para EventoData
        if isinstance(novo_mes_referencia, EventoData):
            self.reference_date = novo_mes_referencia
        elif isinstance(novo_mes_referencia, (date, datetime)):
            self.reference_date = EventoData.criar_de_data(novo_mes_referencia)
        else:
            self.reference_date = EventoData.criar_de_texto(str(novo_mes_referencia))
        self.registrar_atualizacao()
        return self

    def alterar_valor(self, novo_valor: Union[str, int, float, Decimal, Valor]) -> "ExpenseVariable":
        self.amount = novo_valor if isinstance(novo_valor, Valor) else Valor.criar_de_bruto(novo_valor)
        self.registrar_atualizacao()
        return self

    def definir_tipo_despesa(self, tipo_despesa: Optional[Union[UUID, "ExpenseVariableType"]]) -> "ExpenseVariable":
        self.expense_variable_type_id = self._obter_tipo_id(tipo_despesa)
        self.registrar_atualizacao()
        return self

    # ----------------- Fábrica (Create) -----------------
    @classmethod
    def criar(
        cls,
        *,
        mes_referencia: Union[str, date, datetime, EventoData],
        valor: Union[str, int, float, Decimal, Valor],
        tipo_despesa: Optional[Union[UUID, "ExpenseVariableType"]] = None,
    ) -> "ExpenseVariable":
        """Método de fábrica para criar uma nova despesa variável."""
        # Coerção para EventoData
        if isinstance(mes_referencia, EventoData):
            ref_vo = mes_referencia
        elif isinstance(mes_referencia, (date, datetime)):
            ref_vo = EventoData.criar_de_data(mes_referencia)
        else:
            ref_vo = EventoData.criar_de_texto(str(mes_referencia))

        # Coerção para Valor
        amount_vo = valor if isinstance(valor, Valor) else Valor.criar_de_bruto(valor)
        type_id = cls._obter_tipo_id(tipo_despesa)

        return cls(reference_date=ref_vo, amount=amount_vo, expense_variable_type_id=type_id)

    # ----------------- Atualização Completa (Update) -----------------
    def atualizar(
        self,
        *,
        mes_referencia: Union[str, date, datetime, EventoData],
        valor: Union[str, int, float, Decimal, Valor],
        tipo_despesa: Optional[Union[UUID, "ExpenseVariableType"]] = None,
    ) -> "ExpenseVariable":
        """Atualiza os campos da despesa com novos valores."""
        if isinstance(mes_referencia, EventoData):
            self.reference_date = mes_referencia
        elif isinstance(mes_referencia, (date, datetime)):
            self.reference_date = EventoData.criar_de_data(mes_referencia)
        else:
            self.reference_date = EventoData.criar_de_texto(str(mes_referencia))

        self.amount = valor if isinstance(valor, Valor) else Valor.criar_de_bruto(valor)
        self.expense_variable_type_id = self._obter_tipo_id(tipo_despesa)
        self.registrar_atualizacao()
        return self

    # ----------------- Atualização Parcial (Patch) -----------------
    def patch(
        self,
        *,
        mes_referencia: Optional[Union[str, date, datetime, EventoData]] = None,
        valor: Optional[Union[str, int, float, Decimal, Valor]] = None,
        tipo_despesa: object = _NAO_FORNECIDO,  # permite None explícito para limpar
    ) -> "ExpenseVariable":
        """Atualiza apenas os campos fornecidos.
        - mes_referencia/valor: somente se não for None
        - tipo_despesa: aplica VO/UUID ou limpa quando None explícito
        """
        houve_alteracao = False
        if mes_referencia is not None:
            if isinstance(mes_referencia, EventoData):
                self.reference_date = mes_referencia
            elif isinstance(mes_referencia, (date, datetime)):
                self.reference_date = EventoData.criar_de_data(mes_referencia)
            else:
                self.reference_date = EventoData.criar_de_texto(str(mes_referencia))
            houve_alteracao = True
        if valor is not None:
            self.amount = valor if isinstance(valor, Valor) else Valor.criar_de_bruto(valor)
            houve_alteracao = True
        if tipo_despesa is not self._NAO_FORNECIDO:
            self.expense_variable_type_id = self._obter_tipo_id(tipo_despesa)  # type: ignore[arg-type]
            houve_alteracao = True

        if houve_alteracao:
            self.registrar_atualizacao()
        return self

    # ----------------- Exclusão Lógica (Soft Delete) -----------------
    def deletar(self) -> None:
        """Realiza a exclusão lógica da entidade."""
        self.registrar_exclusao()

    # ----------------- Propriedades de Apresentação -----------------
    @property
    def referencia(self) -> str:
        """Retorna o mês/ano de referência formatado."""
        return f"{self.reference_date.mes:02d}/{self.reference_date.ano}"

    def descricao_curta(self) -> str:
        """Gera uma descrição curta da despesa."""
        return f"{self.bill_label} {self.referencia}: R$ {self.amount.valor:.2f}"
