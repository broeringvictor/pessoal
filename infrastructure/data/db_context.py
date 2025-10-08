from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from urllib.parse import quote_plus

# Try to load environment variables from .env if python-dotenv is available
try:  # optional dependency
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover - fallback when python-dotenv is missing
    def load_dotenv(*_args, **_kwargs):  # noop fallback
        return False

# Load .env (noop if fallback)
load_dotenv()

# Prefer full DATABASE_URL; otherwise, compose from parts
_database_url_provided = os.getenv("DATABASE_URL")

if _database_url_provided:
    SQLALCHEMY_DATABASE_URL = _database_url_provided
else:
    database_user = os.getenv("DB_USER", "postgres")
    database_password_raw = os.getenv("DB_PASSWORD")  # sensitive: must be set via env/.env
    if not database_password_raw:
        raise RuntimeError(
            "DB_PASSWORD is not set. Define it in your environment or .env, or provide DATABASE_URL."
        )
    database_host = os.getenv("DB_HOST", "localhost")
    database_port = int(os.getenv("DB_PORT", "5432"))
    database_name = os.getenv("DB_NAME", "postgres")

    database_password = quote_plus(database_password_raw)
    SQLALCHEMY_DATABASE_URL = (
        f"postgresql://{database_user}:{database_password}@{database_host}:{database_port}/{database_name}"
    )

# Create engine with sane defaults
database_engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    future=True,
)

# Declarative base for ORM models
Base = declarative_base()

# Session factory for repositories/services
SessionLocal = sessionmaker(
    bind=database_engine,
    autocommit=False,
    autoflush=False,
    future=True,
)


def get_database_session():
    """
    Context-managed database session.

    Example:
        from infrastructure.data.db_context import get_database_session
        with get_database_session() as session:
            session.execute("SELECT 1")
    """
    from contextlib import contextmanager

    @contextmanager
    def _session_context():
        session = SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    return _session_context()
