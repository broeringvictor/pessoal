from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import ClassVar, Optional
import uuid
import time
import secrets


@dataclass(slots=True)
class Entity:
    """Entidade base: gera UUIDv7 e created_at (UTC) automaticamente ao instanciar."""

    # Identificador estável e ordenável temporalmente (UUIDv7)
    id: Optional[uuid.UUID] = None

    # Auditoria básica
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None

    # Campos reservados para auditoria que tipicamente não devem ser manipulados diretamente
    _RESERVED: ClassVar[frozenset[str]] = frozenset({"id", "created_at", "updated_at", "deleted_at"})

    def __post_init__(self) -> None:
        if self.id is None:
            self.id = _uuid7()
        elif not isinstance(self.id, uuid.UUID):
            self.id = uuid.UUID(str(self.id))

        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


def _uuid7() -> uuid.UUID:
    """Gera um UUIDv7 (time-ordered):
    - 48 bits de timestamp em milissegundos (big-endian)
    - 4 bits de versão (0x7) + 12 bits aleatórios
    - 2 bits de variante RFC 4122 (10xx) + 62 bits aleatórios
    """
    # 48 bits de timestamp (ms desde epoch)
    timestamp_ms = int(time.time() * 1000) & ((1 << 48) - 1)

    # Partes aleatórias conforme layout do UUIDv7
    random_12_bits = secrets.randbits(12)
    random_62_bits = secrets.randbits(62)

    uuid_bytes = bytearray(16)

    # Preenche bytes 0..5 com o timestamp em ordem big-endian
    for byte_index in range(6):
        shift = 40 - 8 * byte_index
        uuid_bytes[byte_index] = (timestamp_ms >> shift) & 0xFF

    # Byte 6: 4 bits de versão (0x7) nos bits altos, 4 bits altos do random_12_bits nos bits baixos
    uuid_bytes[6] = 0x70 | ((random_12_bits >> 8) & 0x0F)

    # Byte 7: 8 bits baixos do random_12_bits
    uuid_bytes[7] = random_12_bits & 0xFF

    # Byte 8: variante RFC 4122 (10xx) nos bits altos + 6 bits altos do random_62_bits
    uuid_bytes[8] = 0x80 | ((random_62_bits >> 54) & 0x3F)

    # Bytes 9..15: 56 bits restantes do random_62_bits
    for byte_index in range(9, 16):
        shift = 8 * (15 - byte_index)
        uuid_bytes[byte_index] = (random_62_bits >> shift) & 0xFF

    return uuid.UUID(bytes=bytes(uuid_bytes))
