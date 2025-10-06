import uuid
from datetime import datetime, timezone
from dataclasses import dataclass

from core.shared.entities import Entity


def test_entity_autogenerates_uuid7_and_created_at_on_init():
    e = Entity()
    assert isinstance(e.id, uuid.UUID)
    assert e.id.version == 7
    assert e.created_at is not None
    assert e.created_at.tzinfo is timezone.utc
    assert e.updated_at is None
    assert e.deleted_at is None


@dataclass(slots=True)
class Invoice(Entity):
    descricao: str = ""
    valor: int = 0

    # Exemplo de responsabilidade de filho: update/delete
    def atualizar_valor(self, novo_valor: int) -> None:
        self.valor = novo_valor
        self.updated_at = datetime.now(timezone.utc)

    def marcar_deletado(self) -> None:
        self.deleted_at = datetime.now(timezone.utc)


def test_subclass_controls_its_own_update_and_delete():
    inv = Invoice(descricao="Conta", valor=100)
    # herdou id/created_at automaticamente
    assert isinstance(inv.id, uuid.UUID)
    assert inv.id.version == 7
    assert inv.created_at.tzinfo is timezone.utc
    assert inv.updated_at is None

    inv.atualizar_valor(150)
    assert inv.valor == 150
    assert inv.updated_at is not None

    inv.marcar_deletado()
    assert inv.deleted_at is not None
    assert inv.is_deleted
