from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import ClassVar, Optional
import uuid

# Gerador resiliente de UUIDv7: tenta 'uuid7', depois 'uuid-extensions'
try:
    import uuid7 as _uuid7_lib  # type: ignore

    def gerar_uuidv7() -> uuid.UUID:
        return _uuid7_lib.uuid7()
except Exception:  # pragma: no cover - fallback
    try:
        import uuid_extensions as _uuidext_lib  # type: ignore

        def gerar_uuidv7() -> uuid.UUID:  # type: ignore[no-redef]
            return _uuidext_lib.uuid7()
    except Exception as fallback_exc:  # pragma: no cover - last resort
        def gerar_uuidv7() -> uuid.UUID:  # type: ignore[no-redef]
            raise ImportError(
                "Nenhuma implementação de UUIDv7 encontrada. Instale 'uuid7' ou 'uuid-extensions'."
            ) from fallback_exc


@dataclass(kw_only=True)
class Entity:
    """Entidade base: gera UUIDv7 e created_at (UTC) automaticamente ao instanciar."""

    # Identidade baseada em tempo (UUIDv7)
    id: uuid.UUID = field(init=False, default_factory=gerar_uuidv7)

    # Auditoria básica
    created_at: datetime = field(init=False, default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = field(default=None, init=False)
    deleted_at: Optional[datetime] = field(default=None, init=False)

    # Campos reservados para auditoria que tipicamente não devem ser manipulados diretamente
    _RESERVED: ClassVar[frozenset[str]] = frozenset(
        {"id", "created_at", "updated_at", "deleted_at"}
    )

    def __post_init__(self) -> None:
        # Garante inicialização mesmo quando subclasses definem __init__ customizado
        if not isinstance(getattr(self, "id", None), uuid.UUID):
            self.id = gerar_uuidv7()
        if getattr(self, "created_at", None) is None:
            self.created_at = datetime.now(timezone.utc)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    # --- Novos métodos de ciclo de vida/auditoria ---
    def registrar_atualizacao(self) -> None:
        """Atualiza o carimbo de tempo de atualização para agora (UTC)."""
        self.updated_at = datetime.now(timezone.utc)

    def registrar_exclusao(self) -> None:
        """Marca como excluído (soft delete) com carimbo de tempo (UTC)."""
        self.deleted_at = datetime.now(timezone.utc)

    def restaurar_exclusao(self) -> None:
        """Remove a marca de exclusão (soft delete) e atualiza 'updated_at'."""
        self.deleted_at = None
        self.updated_at = datetime.now(timezone.utc)
