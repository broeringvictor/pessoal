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
    """Base entity: generates UUIDv7 and created_at (UTC) automatically on instantiation."""

    # Time-based identity (UUIDv7)
    id: _uuid.UUID = field(init=False, default_factory=_generate_uuid7)

    # Basic auditing
    created_at: datetime = field(init=False, default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = field(default=None, init=False)
    deleted_at: Optional[datetime] = field(default=None, init=False)

    # Reserved fields
    _RESERVED: ClassVar[frozenset[str]] = frozenset(
        {"id", "created_at", "updated_at", "deleted_at"}
    )

    def __post_init__(self) -> None:
        # Ensure initialization even when subclasses define custom __init__
        if not isinstance(getattr(self, "id", None), _uuid.UUID):
            self.id = _generate_uuid7()
        if getattr(self, "created_at", None) is None:
            self.created_at = datetime.now(timezone.utc)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    # Portuguese legacy methods (kept for compatibility)
    def registrar_atualizacao(self) -> None:
        self.updated_at = datetime.now(timezone.utc)

    def registrar_exclusao(self) -> None:
        self.deleted_at = datetime.now(timezone.utc)

    def restaurar_exclusao(self) -> None:
        self.deleted_at = None
        self.updated_at = datetime.now(timezone.utc)

    # English aliases (preferred going forward)
    def register_update(self) -> None:
        self.registrar_atualizacao()

    def register_deletion(self) -> None:
        self.registrar_exclusao()

    def restore_deletion(self) -> None:
        self.restaurar_exclusao()
