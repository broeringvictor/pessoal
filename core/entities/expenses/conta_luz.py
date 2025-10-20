from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Union

from core.shared.entities import Entity
from core.shared.value_objects import ReferenciaMensal, ValorMonetario


ReferenciaTipo = str
ValorTipo = Decimal


@dataclass()
class ContaLuz(Entity):
    """Entidade de conta de luz (CELESC)."""

    referencia: ReferenciaTipo = ""
    valor: ValorTipo = Decimal("0.00")

    # ----------------- Fábrica/Construtor de criação -----------------
    @classmethod
    def criar(
        cls, mes_referencia: str, valor: Union[str, int, float, Decimal]
    ) -> "ContaLuz":
        ref_vo = ReferenciaMensal(mes_referencia)
        val_vo = ValorMonetario.from_bruto(valor)
        return cls(referencia=ref_vo.referencia, valor=val_vo.valor)

    @classmethod
    def criar_de_centavos(
        cls, mes_referencia: str, valor_em_centavos: int
    ) -> "ContaLuz":
        """Cria a entidade a partir de um inteiro em centavos (persistência SQLite recomendada: INTEGER)."""
        ref_vo = ReferenciaMensal(mes_referencia)
        val_vo = ValorMonetario.from_centavos(valor_em_centavos)
        return cls(referencia=ref_vo.referencia, valor=val_vo.valor)

    # ----------------- Comandos de domínio (CRUD do agregado) --------
    def atualizar(
        self,
        *,
        mes_referencia: Optional[str] = None,
        valor: Optional[Union[str, int, float, Decimal]] = None,
    ) -> "ContaLuz":
        if mes_referencia is not None:
            self.referencia = ReferenciaMensal(mes_referencia).referencia
        if valor is not None:
            self.valor = ValorMonetario.from_bruto(valor).valor
        self.updated_at = datetime.now(timezone.utc)
        return self

    def atualizar_por_centavos(self, valor_em_centavos: int) -> "ContaLuz":
        """Atualiza o valor a partir de um inteiro em centavos (para escrita vinda do banco)."""
        self.valor = ValorMonetario.from_centavos(valor_em_centavos).valor
        self.updated_at = datetime.now(timezone.utc)
        return self

    def delete(self) -> None:
        self.register_deletion()

    # ----------------- Consultas auxiliares --------------------------
    def valor_em_centavos(self) -> int:
        """Retorna o valor em centavos (INTEGER para SQLite), com arredondamento bancário (half-even)."""
        return ValorMonetario(self.valor).to_centavos()

    def descricao_curta(self) -> str:
        return f"Conta de Luz {self.referencia}: R$ {self.valor:.2f}"
