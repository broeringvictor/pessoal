from __future__ import annotations

from infrastructure.data.db_context import database_engine
from infrastructure.data.mappings import start_mappers, metadata_obj


def init_persistence(create_schema: bool = False) -> None:
    """
    Initialize ORM mappings and optionally create database schema.
    - Keeps core independent: only infrastructure knows about SQLAlchemy.
    - Call once on application startup.
    """
    start_mappers()
    if create_schema:
        metadata_obj.create_all(bind=database_engine)

