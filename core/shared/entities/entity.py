from __future__ import annotations

import uuid6
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import ClassVar, Optional


@dataclass(kw_only=True)
class Entity:
    """Entidade base: gera UUIDv7 e created_at (UTC) automaticamente ao instanciar."""

    # Identidade baseada em tempo (UUIDv7) usando uuid6 library
    id: uuid6.UUID = field(init=False, default_factory=uuid6.uuid7)

    # Auditoria básica
    created_at: datetime = field(init=False, default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = field(default=None, init=False)
    deleted_at: Optional[datetime] = field(default=None, init=False)

    # Campos reservados
    _RESERVED: ClassVar[frozenset[str]] = frozenset(
        {"id", "created_at", "updated_at", "deleted_at"}
    )

    def __post_init__(self) -> None:
        # Garante inicialização mesmo quando subclasses definem __init__ customizado
        if not isinstance(getattr(self, "id", None), uuid6.UUID):
            self.id = uuid6.uuid7()
        if getattr(self, "created_at", None) is None:
            self.created_at = datetime.now(timezone.utc)

    # O restante da classe permanece o mesmo...
    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def registrar_atualizacao(self) -> None:
        self.updated_at = datetime.now(timezone.utc)

    def registrar_exclusao(self) -> None:
        self.deleted_at = datetime.now(timezone.utc)

    def restaurar_exclusao(self) -> None:
        self.deleted_at = None
        self.updated_at = datetime.now(timezone.utc)