from __future__ import annotations

import logging
import logging.config
import os
import sys
import uuid
from typing import Any, Mapping
from contextvars import ContextVar

# Context variable for correlation id
_request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


class RequestIdFilter(logging.Filter):
    """Injects request_id from contextvars into log records."""

    def filter(self, record: logging.LogRecord) -> bool:  # type: ignore[override]
        try:
            request_id = _request_id_ctx.get() or "-"
        except Exception:
            request_id = "-"
        setattr(record, "request_id", request_id)
        return True


def set_request_id(value: str | None) -> None:
    _request_id_ctx.set(value)


def generate_request_id() -> str:
    return uuid.uuid4().hex


def configure_logging() -> None:
    level = os.getenv("LOG_LEVEL", "INFO").upper()

    handlers: dict[str, Any] = {
        "console": {
            "class": "logging.StreamHandler",
            "stream": sys.stdout,
            "formatter": "standard",
            "filters": ["request_id"],
        }
    }

    formatters: dict[str, Any] = {
        "standard": {
            "format": "%(asctime)s | %(levelname)s | %(name)s | rid=%(request_id)s | %(message)s",
            "datefmt": "%Y-%m-%dT%H:%M:%S%z",
        }
    }

    filters: dict[str, Any] = {
        "request_id": {
            "()": RequestIdFilter,
        }
    }

    loggers: dict[str, Any] = {
        "uvicorn": {"level": level},
        "uvicorn.error": {"level": level},
        "uvicorn.access": {"level": os.getenv("LOG_LEVEL_ACCESS", "WARNING").upper()},
        "sqlalchemy.engine": {"level": os.getenv("LOG_LEVEL_SQL", "WARNING").upper()},
        "pessoal": {"level": level, "handlers": ["console"], "propagate": False},
    }

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": filters,
            "formatters": formatters,
            "handlers": handlers,
            "root": {"level": level, "handlers": ["console"]},
            "loggers": loggers,
        }
    )


# Convenience logger for the app
logger = logging.getLogger("pessoal")

