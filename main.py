from __future__ import annotations

"""
Entry point to start the FastAPI application.
- Reads PORT (default: 8000) and UVICORN_RELOAD (1/true/yes/on to enable) from environment variables.
- Runs the ASGI app defined in api.app:app.
- Also exposes `app` to support `fastapi dev main.py` auto-discovery.
"""

import os
import uvicorn

# Expose FastAPI app symbol for FastAPI CLI auto-discovery
from api.app import app as app  # noqa: F401  (re-export for tooling)


def _should_reload() -> bool:
    return os.getenv("UVICORN_RELOAD", "0").lower() in {"1", "true", "yes", "on"}


def _get_port() -> int:
    valor_porta = os.getenv("PORT", "8000")
    try:
        return int(valor_porta)
    except ValueError:
        return 8000


def main() -> None:
    uvicorn.run(
        "api.app:app",
        host="0.0.0.0",
        port=_get_port(),
        reload=_should_reload(),
    )


if __name__ == "__main__":
    main()
