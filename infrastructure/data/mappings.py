from __future__ import annotations

from sqlalchemy import (
    Table,
    Column,
    MetaData,
    String,
    Date,
    DateTime,
    Numeric,
)
from sqlalchemy.orm import registry
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from core.entities.conta_luz import ContaLuz
from core.entities.conta_agua import ContaAgua

# Dedicated registry/metadata for infrastructure mappings (core stays framework-agnostic)
mapper_registry = registry()
metadata_obj: MetaData = mapper_registry.metadata

# --- Tables ---
conta_luz_table = Table(
    "conta_luz",
    metadata_obj,
    Column("id", PG_UUID(as_uuid=True), primary_key=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=True),
    Column("deleted_at", DateTime(timezone=True), nullable=True),
    Column("referencia", String(32), nullable=False),
    Column("valor", Numeric(12, 2), nullable=False),
)

conta_agua_table = Table(
    "conta_agua",
    metadata_obj,
    Column("id", PG_UUID(as_uuid=True), primary_key=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=True),
    Column("deleted_at", DateTime(timezone=True), nullable=True),
    Column("referencia_data", Date, nullable=False),
    Column("valor", Numeric(12, 2), nullable=False),
)


# --- Mapping bootstrap ---
def start_mappers() -> None:
    """Configure classical mappings. Call once at app startup."""
    # Idempotent: SQLAlchemy will no-op if the class is already mapped
    mapper_registry.map_imperatively(ContaLuz, conta_luz_table)
    mapper_registry.map_imperatively(ContaAgua, conta_agua_table)

