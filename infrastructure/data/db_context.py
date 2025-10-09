from __future__ import annotations

import os
from typing import Iterator, Optional
from urllib.parse import quote_plus, urlparse
import logging

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session

# Try to load environment variables from .env if python-dotenv is available
try:  # optional dependency
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover - fallback when python-dotenv is missing
    def load_dotenv(*_args, **_kwargs):  # noop fallback
        return False

# Logger for infrastructure
_logger = logging.getLogger("pessoal.infrastructure.db")

# Declarative base for ORM models (core remains independent)
Base = declarative_base()

# Internal singletons
_engine: Optional[Engine] = None
_SessionLocal: Optional[sessionmaker] = None


def _sanitize_url(url: str) -> str:
    try:
        parsed = urlparse(url)
        if parsed.password:
            netloc = parsed.netloc.replace(parsed.password, "***")
        else:
            netloc = parsed.netloc
        return parsed._replace(netloc=netloc).geturl()
    except Exception:
        return "<redacted>"


def _build_database_url_from_env() -> str:
    """Build DATABASE_URL from environment variables or raise with clear guidance.

    Expected env vars (when DATABASE_URL is not provided):
    - DB_USER (default: postgres)
    - DB_PASSWORD (required)
    - DB_HOST (default: localhost)
    - DB_PORT (default: 5432)
    - DB_NAME (default: postgres)
    """
    load_dotenv()  # load once; safe if called multiple times

    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    database_user = os.getenv("DB_USER", "postgres")
    database_password_raw = os.getenv("DB_PASSWORD")
    if not database_password_raw:
        raise RuntimeError(
            "DB_PASSWORD is not set. Define it in your environment or .env, or provide DATABASE_URL."
        )
    database_host = os.getenv("DB_HOST", "localhost")
    database_port = int(os.getenv("DB_PORT", "5432"))
    database_name = os.getenv("DB_NAME", "postgres")

    database_password = quote_plus(database_password_raw)
    return f"postgresql://{database_user}:{database_password}@{database_host}:{database_port}/{database_name}"


def get_engine() -> Engine:
    """Return a singleton SQLAlchemy Engine, creating it on first use."""
    global _engine
    if _engine is None:
        raw_url = _build_database_url_from_env()
        _logger.info("Creating SQLAlchemy engine", extra={"url": _sanitize_url(raw_url)})
        _engine = create_engine(
            raw_url,
            echo=False,
            pool_pre_ping=True,
            future=True,
        )
    return _engine


def get_session_factory() -> sessionmaker:
    """Return a singleton Session factory (sessionmaker)."""
    global _SessionLocal
    if _SessionLocal is None:
        _logger.debug("Creating Session factory (sessionmaker)")
        _SessionLocal = sessionmaker(
            bind=get_engine(),
            autocommit=False,
            autoflush=False,
            future=True,
        )
    return _SessionLocal


def get_database_session() -> Iterator[Session]:
    """Yield a context-managed database session.

    Example:
        with get_database_session() as session:
            session.execute("SELECT 1")
    """
    from contextlib import contextmanager

    @contextmanager
    def _session_context() -> Iterator[Session]:
        session_factory = get_session_factory()
        session = session_factory()
        _logger.debug("Session opened")
        try:
            yield session
            session.commit()
            _logger.debug("Session committed")
        except Exception:
            _logger.exception("Session rollback due to exception")
            session.rollback()
            raise
        finally:
            session.close()
            _logger.debug("Session closed")

    return _session_context()
