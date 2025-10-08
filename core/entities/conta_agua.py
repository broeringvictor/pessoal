from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone, date
from decimal import Decimal
from typing import Optional, Union

from core.shared.entities import Entity
from core.value_object.mes_referencia import MesReferencia
from core.value_object.valor import Valor


ReferenciaTipo = date
ValorTipo = Decimal


@dataclass(slots=True)
class ContaAgua(Entity):
    """Entidade de conta de água (SAMAE).

    - Referência armazenada como date no primeiro dia do mês (YYYY-MM-01)
    - Normaliza entrada via MesReferencia (aceita str/date/datetime/VO)
    - Valor monetário como Decimal (2 casas)
    - Persistência: Postgres DATE (referência) e NUMERIC (valor)
    """

    referencia_data: ReferenciaTipo = date(1970, 1, 1)
    valor: ValorTipo = Decimal("0.00")

    # ----------------- Propriedades de apresentação -----------------
    @property
    def referencia(self) -> str:
        return f"{self.referencia_data.month:02d}/{self.referencia_data.year}"

    # ----------------- Fábricas de criação -----------------
    @classmethod
    def criar(
        cls,
        mes_referencia: Union[str, date, datetime, MesReferencia],
        valor: Union[str, int, float, Decimal, Valor],
    ) -> "ContaAgua":
        if isinstance(mes_referencia, MesReferencia):
            ref_vo = mes_referencia
        elif isinstance(mes_referencia, (date, datetime)):
            ref_vo = MesReferencia.criar_de_data(mes_referencia)
        else:
            ref_vo = MesReferencia.criar_de_texto(str(mes_referencia))

        val_vo = valor if isinstance(valor, Valor) else Valor.criar_de_bruto(valor)
        return cls(referencia_data=ref_vo.para_banco(), valor=val_vo.valor)

    # ----------------- Comandos de domínio -----------------
    def atualizar(
        self,
        *,
        mes_referencia: Optional[Union[str, date, datetime, MesReferencia]] = None,
        valor: Optional[Union[str, int, float, Decimal, Valor]] = None,
    ) -> "ContaAgua":
        if mes_referencia is not None:
            if isinstance(mes_referencia, MesReferencia):
                ref_vo = mes_referencia
            elif isinstance(mes_referencia, (date, datetime)):
                ref_vo = MesReferencia.criar_de_data(mes_referencia)
            else:
                ref_vo = MesReferencia.criar_de_texto(str(mes_referencia))
            self.referencia_data = ref_vo.para_banco()

        if valor is not None:
            val_vo = valor if isinstance(valor, Valor) else Valor.criar_de_bruto(valor)
            self.valor = val_vo.valor

        self.updated_at = datetime.now(timezone.utc)
        return self

    def deletar(self) -> None:
        self.deleted_at = datetime.now(timezone.utc)

    # ----------------- Consultas auxiliares -----------------
    def referencia_para_banco(self) -> date:
        """Retorna date(ano, mes, 1) para persistência/filters."""
        return self.referencia_data

    def descricao_curta(self) -> str:
        return f"Conta de Água {self.referencia}: R$ {self.valor:.2f}"
