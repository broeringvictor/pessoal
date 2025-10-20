from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional, Union
from uuid import UUID

from core.shared.entities import Entity
from core.value_object import (
    Valor,
    Descricao,
    TransactionType,
    EventoData,
)


@dataclass(slots=True, init=False)
class Transaction(Entity):
    """Entidade de domínio para registrar uma transação financeira.

    Campos são Value Objects do domínio para garantir validação e semântica.
    """

    descricao: Descricao 
    data_evento: EventoData
    valor: Valor  # Removida opcionalidade
    tipo: TransactionType = field(
        default_factory=lambda: TransactionType.criar_de_nome("ENTRADA")
    )

    def __init__(
        self,
        *,
        descricao: Descricao,
        data_evento: EventoData,
        valor: Valor,  # Não é mais opcional
        tipo: TransactionType
    ) -> None:
        # Atribui campos de domínio
        self.descricao = descricao
        self.data_evento = data_evento
        self.valor = valor
        self.tipo = tipo if isinstance(tipo, TransactionType) and tipo is not None else TransactionType.criar_de_nome("ENTRADA")
        # Inicializa campos de auditoria/identidade
        Entity.__post_init__(self)

    # CRUD - Criar
    @classmethod
    def criar(
        cls,
        descricao: str,
        texto_data_evento: str,
        valor_monetario: Union[str, int, float, Decimal],  # Obrigatório
        tipo: Optional[Union[int, str, TransactionType]] = None,
    ) -> "Transaction":
        
        descricao_vo = Descricao.criar_de_texto(descricao)
        data_vo = EventoData.criar_de_texto(texto_data_evento)
        valor_vo = valor_monetario if isinstance(valor_monetario, Valor) else Valor.criar_de_bruto(valor_monetario)
        tipo_vo = (
            tipo
            if isinstance(tipo, TransactionType)
            else (
                TransactionType.criar_de_codigo(tipo)
                if tipo is not None
                else TransactionType.criar_de_nome("ENTRADA")
            )
        )
        return cls(
            descricao=descricao_vo,
            data_evento=data_vo,
            valor=valor_vo,
            tipo=tipo_vo,
        )

    # CRUD - Reconstituir (para leitura do banco)
    @classmethod
    def reconstituir(
        cls,
        identificador: UUID,
        descricao: str,
        data_evento: Union[str, date, datetime],
        valor_monetario: Union[Valor, str, int, float, Decimal],  # Obrigatório
        tipo: Optional[Union[int, str, TransactionType]],
        criado_em: datetime,
        atualizado_em: Optional[datetime] = None,
    ) -> "Transaction":
        # Data Evento
        vo_data = (
            EventoData.criar_de_texto(data_evento)
            if isinstance(data_evento, str)
            else EventoData.criar_de_data(data_evento)
        )

        # Descrição
        vo_desc = Descricao.criar_de_texto(descricao)

        # Valor monetário (obrigatório)
        vo_valor = (
            valor_monetario
            if isinstance(valor_monetario, Valor)
            else Valor.criar_de_bruto(valor_monetario)
        )

        # Tipo de transação
        if isinstance(tipo, TransactionType):
            vo_tipo = tipo
        elif tipo is None:
            vo_tipo = TransactionType.criar_de_nome("ENTRADA")
        else:
            vo_tipo = TransactionType.criar_de_codigo(tipo)

        instancia = cls(
            descricao=vo_desc,
            data_evento=vo_data,
            valor=vo_valor,
            tipo=vo_tipo,
        )
        # Ajusta campos de identidade/auditoria
        instancia.id = identificador
        instancia.created_at = criado_em
        instancia.updated_at = atualizado_em
        return instancia

    # CRUD - Atualizar (update completo)
    def atualizar(
        self,
        descricao_transacao: str,
        texto_data_evento: str,
        valor_monetario: Union[Valor, str, int, float, Decimal],
        tipo: Optional[Union[int, str, TransactionType]] = None,
    ) -> None:
        """Atualiza todos os campos da transação."""
        self.descricao = Descricao.criar_de_texto(descricao_transacao)
        self.data_evento = EventoData.criar_de_texto(texto_data_evento)
        self.valor = (
            valor_monetario
            if isinstance(valor_monetario, Valor)
            else Valor.criar_de_bruto(valor_monetario)
        )
        self.tipo = (
            tipo
            if isinstance(tipo, TransactionType)
            else (
                TransactionType.criar_de_codigo(tipo)
                if tipo is not None
                else TransactionType.criar_de_nome("ENTRADA")
            )
        )
        self.registrar_atualizacao()

    # CRUD - Patch (atualização parcial)
    def patch(
        self,
        descricao: Optional[str] = None,
        texto_data_evento: Optional[str] = None,
        valor_monetario: Optional[Union[Valor, str, int, float, Decimal]] = None,
        tipo: Optional[Union[int, str, TransactionType]] = None,
    ) -> None:
        """Atualiza apenas os campos informados (patch)."""
        if descricao is not None:
            self.descricao = Descricao.criar_de_texto(descricao)
        
        if texto_data_evento is not None:
            self.data_evento = EventoData.criar_de_texto(texto_data_evento)
        
        if valor_monetario is not None:
            self.valor = (
                valor_monetario
                if isinstance(valor_monetario, Valor)
                else Valor.criar_de_bruto(valor_monetario)
            )
        
        if tipo is not None:
            self.tipo = (
                tipo
                if isinstance(tipo, TransactionType)
                else TransactionType.criar_de_codigo(tipo)
            )
        
        self.registrar_atualizacao()

    # CRUD - Deletar (soft delete)
    def deletar(self) -> None:
        """Marca a transação como deletada (soft delete)."""
        self.registrar_exclusao()

    # Mapeamento para persistência (Postgres-friendly)
    def como_registro_banco(self) -> dict[str, Any]:
        return {
            "identificador": self.id,
            "descricao": self.descricao.para_banco(),
            "data_evento": self.data_evento.para_banco(),  # date (YYYY-MM-DD)
            "valor_monetario_centavos": self.valor.to_centavos(),
            "tipo": self.tipo.para_banco(),
            "criado_em": self.created_at,
            "atualizado_em": self.updated_at,
            "deletado_em": self.deleted_at,
        }
