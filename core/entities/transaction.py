from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional, Union
from uuid import UUID

from core.shared.entities import Entity
from core.value_object import (
    Valor,
    MesReferencia,
    Descricao,
    TransactionType,
    DataEvento,
)


@dataclass(slots=True, init=False)
class Transaction(Entity):
    """Entidade de domínio para registrar uma transação financeira.

    Campos são Value Objects do domínio para garantir validação e semântica.
    """

    descricao: Descricao 
    data_evento: DataEvento
    mes_referencia: MesReferencia
    valor_monetario: Valor
    tipo: TransactionType = field(
        default_factory=lambda: TransactionType.criar_de_nome("ENTRADA")
    )

    def __init__(
        self,
        *,
        descricao: Descricao,
        data_evento: DataEvento,
        mes_referencia: MesReferencia,
        valor_monetario: Valor,
        tipo: TransactionType
    ) -> None:
        # Atribui campos de domínio
        self.descricao = descricao
        self.data_evento = data_evento
        self.mes_referencia = mes_referencia
        self.valor_monetario = valor_monetario
        self.tipo = tipo if isinstance(tipo, TransactionType) and tipo is not None else TransactionType.criar_de_nome("ENTRADA")
        # Inicializa campos de auditoria/identidade
        Entity.__post_init__(self)

    # Fábricas expressivas
    @classmethod
    def criar(
        cls,
        descricao_transacao: str,
        texto_data_evento: str,
        texto_mes_referencia: str,
        valor_monetario: Optional[Union[str, int, float, Decimal]] = None,
        tipo: Optional[Union[int, str, TransactionType]] = None,
    ) -> "Transaction":
        
        descricao_vo = Descricao.criar_de_texto(descricao_transacao)
        data_vo = DataEvento.criar_de_texto(texto_data_evento)
        ref_vo = MesReferencia.criar_de_texto(texto_mes_referencia)
        valor_vo = (
            None
            if valor_monetario is None
            else (valor_monetario if isinstance(valor_monetario, Valor) else Valor.criar_de_bruto(valor_monetario))
        )
        tipo_vo = (
            tipo
            if isinstance(tipo, TransactionType)
            else (
                TransactionType.criar_de_codigo(tipo)
                if tipo is not None
                else None
            )
        )
        return cls(
            descricao=descricao_vo,
            data_evento=data_vo,
            mes_referencia=ref_vo,
            valor_monetario=valor_vo,
            tipo=tipo_vo,
        )

    @classmethod
    def reconstituir(
        cls,
        identificador: UUID,
        descricao_transacao: str,
        data_evento: Union[str, date, datetime],
        mes_referencia: Union[str, date, datetime],
        valor_monetario: Optional[Union[Valor, str, int, float, Decimal]],
        tipo: Optional[Union[int, str, TransactionType]],
        criado_em: datetime,
        atualizado_em: datetime,
    ) -> "Transaction":
        # Data Evento
        vo_data = (
            DataEvento.criar_de_texto(data_evento)
            if isinstance(data_evento, str)
            else DataEvento.criar_de_data(data_evento)
        )

        # Mês de Referência
        vo_ref = (
            MesReferencia.criar_de_texto(mes_referencia)
            if isinstance(mes_referencia, str)
            else MesReferencia.criar_de_data(mes_referencia)
        )

        # Descrição
        vo_desc = Descricao.criar_de_texto(descricao_transacao)

        # Valor monetário (opcional)
        if valor_monetario is None:
            vo_valor: Optional[Valor] = None
        elif isinstance(valor_monetario, Valor):
            vo_valor = valor_monetario
        else:
            vo_valor = Valor.criar_de_bruto(valor_monetario)

        # Tipo de transação (opcional -> padrão ENTRADA)
        if isinstance(tipo, TransactionType):
            vo_tipo = tipo
        elif tipo is None:
            vo_tipo = None
        else:
            vo_tipo = TransactionType.criar_de_codigo(tipo)

        instancia = cls(
            descricao=vo_desc,
            data_evento=vo_data,
            mes_referencia=vo_ref,
            valor_monetario=vo_valor,
            tipo=vo_tipo,
        )
        # Ajusta campos de identidade/auditoria
        instancia.id = identificador
        instancia.created_at = criado_em
        instancia.updated_at = atualizado_em
        return instancia

    # Mutações consistentes com VO
    def alterar_data_evento(self, nova_data: Union[str, date, datetime]) -> None:
        self.data_evento = (
            DataEvento.criar_de_texto(nova_data)
            if isinstance(nova_data, str)
            else DataEvento.criar_de_data(nova_data)
        )
        self.registrar_atualizacao()

    def alterar_mes_referencia(self, novo_mes_referencia: Union[str, date, datetime]) -> None:
        self.mes_referencia = (
            MesReferencia.criar_de_texto(novo_mes_referencia)
            if isinstance(novo_mes_referencia, str)
            else MesReferencia.criar_de_data(novo_mes_referencia)
        )
        self.registrar_atualizacao()

    def alterar_descricao_transacao(self, nova_descricao_transacao: str) -> None:
        self.descricao = self.descricao.atualizar_descricao(nova_descricao_transacao)
        self.registrar_atualizacao()

    def substituir_valor_monetario(
        self, novo_valor_monetario: Optional[Union[Valor, str, int, float, Decimal]]
    ) -> None:
        if novo_valor_monetario is None:
            self.valor_monetario = None
        elif isinstance(novo_valor_monetario, Valor):
            self.valor_monetario = novo_valor_monetario
        else:
            self.valor_monetario = Valor.criar_de_bruto(novo_valor_monetario)
        self.registrar_atualizacao()

    # Mapeamento para persistência (Postgres-friendly)
    def como_registro_banco(self) -> dict[str, Any]:
        return {
            "identificador": self.id,
            "descricao_transacao": self.descricao.para_banco(),
            "data_evento": self.data_evento.para_banco(),  # date (YYYY-MM-DD)
            "mes_referencia": self.mes_referencia.para_banco(),  # date (YYYY-MM-01)
            "valor_monetario_centavos": (
                self.valor_monetario.to_centavos()
                if self.valor_monetario is not None
                else None
            ),
            "criado_em": self.created_at,
            "atualizado_em": self.updated_at,
        }
