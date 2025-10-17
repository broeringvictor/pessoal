from __future__ import annotations

import uuid as _uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import ClassVar, Optional

# Prefer uuid_extensions.uuid7 (from PyPI package uuid7), fallback to uuid6.uuid7, then stdlib if available
try:  # pragma: no cover - import resolution
    from uuid_extensions import uuid7 as _uuid7_fn  # type: ignore
except Exception:  # pragma: no cover
    _uuid7_fn = None  # type: ignore[assignment]

try:  # pragma: no cover
    import uuid6 as _uuid6_mod  # type: ignore
except Exception:  # pragma: no cover
    _uuid6_mod = None  # type: ignore[assignment]


def _generate_uuid7() -> _uuid.UUID:
    # 1) uuid_extensions (preferred)
    if _uuid7_fn is not None:
        return _uuid7_fn()
    # 2) uuid6 fallback
    if _uuid6_mod is not None:
        return _uuid6_mod.uuid7()
    # 3) stdlib (if present in this Python)
    if hasattr(_uuid, "uuid7"):
        return getattr(_uuid, "uuid7")()  # type: ignore[misc]
    # Should not happen given dependencies; raise to surface misconfiguration
    raise RuntimeError("Nenhuma implementação de UUIDv7 disponível. Instale 'uuid7' ou 'uuid6'.")


@dataclass(kw_only=True)
class Entity:
    """Entidade base: gera UUIDv7 e created_at (UTC) automaticamente ao instanciar."""

    # Identidade baseada em tempo (UUIDv7)
    id: _uuid.UUID = field(init=False, default_factory=_generate_uuid7)

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
        if not isinstance(getattr(self, "id", None), _uuid.UUID):
            self.id = _generate_uuid7()
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