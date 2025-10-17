# core/entities/expenses/expense_variable.py
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Union


from core.entities import Expense
from core.entities.expenses.expense_variable_type import ExpenseVariableType
from core.value_object import Descricao, Valor, TipoDespesa, MesReferencia

# ALTERADO: A classe agora herda de Expense
@dataclass(slots=True, init=False)
class ExpenseVariable(Expense):
    """
    Entidade para despesas variáveis que especializa a entidade Expense.
    """
    # Atributos específicos desta subclasse
    reference_date: date
    expense_variable_type_id: Optional[int] = None


    # NOVO: Construtor customizado para inicializar a classe pai (Expense)
    def __init__(
            self,
            *,
            reference_date: date,
            amount: Decimal, # Recebe o valor bruto
            expense_variable_type_id: Optional[int] = None,
            id: Optional[int] = None,
            created_at: Optional[datetime] = None,
            # ... outros campos de Entity se houver
    ):
        # 1. Prepara os dados para a classe pai 'Expense'
        descricao_vo = Descricao(f"{self.bill_label} ref. {reference_date.month:02d}/{reference_date.year}")
        amount_vo = Valor(amount)
        # Assumindo que TipoDespesa é um VO/Enum, fixamos como 'VARIAVEL'
        tipo_despesa_vo = TipoDespesa("VARIAVEL")

        # 2. Chama o construtor da classe pai
        super().__init__(
            description=descricao_vo,
            amount=amount_vo,
            expense_type=tipo_despesa_vo,
            id=id,
            created_at=created_at
        )

        # 3. Define os atributos específicos desta classe
        self.reference_date = reference_date
        self.expense_variable_type_id = expense_variable_type_id

    # --- Métodos auxiliares permanecem os mesmos ---
    @staticmethod
    def _normalizar_mes_referencia(mes_referencia: Union[str, date, datetime, MesReferencia]) -> date:
        # ... (sem alterações)
        if isinstance(mes_referencia, MesReferencia): return mes_referencia.para_banco()
        if isinstance(mes_referencia, (date, datetime)): return MesReferencia.criar_de_data(mes_referencia).para_banco()
        return MesReferencia.criar_de_texto(str(mes_referencia)).para_banco()

    @staticmethod
    def _normalizar_valor(valor: Union[str, int, float, Decimal, Valor]) -> Decimal:
        # ... (sem alterações)
        if isinstance(valor, Valor): return valor.valor
        return Valor.criar_de_bruto(valor).valor

    @staticmethod
    def _obter_tipo_id(tipo_despesa: Optional[Union[int, "ExpenseVariableType"]]) -> Optional[int]:
        # ... (sem alterações)
        if isinstance(tipo_despesa, ExpenseVariableType): return tipo_despesa.id
        if tipo_despesa is not None: return int(tipo_despesa)
        return None

    # ----------------- Fábrica (Create) - ALTERADO -----------------
    @classmethod
    def criar(
            cls,
            *,
            mes_referencia: Union[str, date, datetime, MesReferencia],
            valor: Union[str, int, float, Decimal, Valor],
            tipo_despesa: Optional[Union[int, "ExpenseVariableType"]] = None,
    ) -> "ExpenseVariable":
        """Método de fábrica para criar uma nova despesa variável."""
        ref_date = cls._normalizar_mes_referencia(mes_referencia)
        amount_decimal = cls._normalizar_valor(valor)
        type_id = cls._obter_tipo_id(tipo_despesa)

        # Chama o novo __init__ com os dados normalizados
        return cls(
            reference_date=ref_date,
            amount=amount_decimal,
            expense_variable_type_id=type_id
        )

    # ----------------- Atualização Completa (Update) - ALTERADO -----------------
    def atualizar(
            self,
            *,
            mes_referencia: Union[str, date, datetime, MesReferencia],
            valor: Union[str, int, float, Decimal, Valor],
            tipo_despesa: Optional[Union[int, "ExpenseVariableType"]] = None,
    ) -> "ExpenseVariable":
        """Atualiza os campos da despesa com novos valores."""
        # Atualiza os campos específicos
        self.reference_date = self._normalizar_mes_referencia(mes_referencia)
        self.expense_variable_type_id = self._obter_tipo_id(tipo_despesa)

        # Atualiza os campos da classe pai (os VOs)
        self.amount = Valor(self._normalizar_valor(valor))
        self.description = Descricao(f"{self.bill_label} ref. {self.referencia}")

        self.registrar_atualizacao()
        return self

    # ----------------- Atualização Parcial (Patch) - ALTERADO -----------------
    def patch(
            self,
            *,
            mes_referencia: Optional[Union[str, date, datetime, MesReferencia]] = None,
            valor: Optional[Union[str, int, float, Decimal, Valor]] = None,
            tipo_despesa: Optional[Union[int, "ExpenseVariableType"]] = None,
    ) -> "ExpenseVariable":
        """Atualiza apenas os campos fornecidos."""
        houve_alteracao = False
        if mes_referencia is not None:
            self.reference_date = self._normalizar_mes_referencia(mes_referencia)
            # Atualiza também a descrição na classe pai
            self.description = Descricao(f"{self.bill_label} ref. {self.referencia}")
            houve_alteracao = True

        if valor is not None:
            # Atualiza o VO de Valor na classe pai
            self.amount = Valor(self._normalizar_valor(valor))
            houve_alteracao = True

        if tipo_despesa is not None:
            self.expense_variable_type_id = self._obter_tipo_id(tipo_despesa)
            houve_alteracao = True

        if houve_alteracao:
            self.registrar_atualizacao()
        return self

    # ----------------- Propriedades de Apresentação -----------------
    @property
    def referencia(self) -> str:
        """Retorna o mês/ano de referência formatado."""
        return f"{self.reference_date.month:02d}/{self.reference_date.year}"

    # Este método agora pode ser removido ou simplificado,
    # pois a descrição principal está no VO `self.description`.
    def descricao_curta(self) -> str:
        """Gera uma descrição curta da despesa."""
        return f"{self.description.valor}: {self.amount.para_formatar_real()}"