from __future__ import annotations
from scalar_fastapi import get_scalar_api_reference
import os
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from api.configurations.logging_config import (
    configure_logging,
    generate_request_id,
    set_request_id,
    logger as app_logger,
)
from api.endpoints.conta_luz import router as conta_luz_router
from api.endpoints.conta_agua import router as conta_agua_router
from infrastructure.data.bootstrap import init_persistence


# Configure logging as early as possible
configure_logging()


def _should_create_schema() -> bool:
    return os.getenv("INIT_DB_SCHEMA", "0") in {"1", "true", "TRUE", "yes", "on"}


@asynccontextmanager
async def app_lifespan(_app: FastAPI):
    # Startup
    app_logger.info("Starting application", extra={"component": "lifespan"})
    init_persistence(create_schema=_should_create_schema())
    yield
    # Shutdown
    app_logger.info("Shutting down application", extra={"component": "lifespan"})


app = FastAPI(title="Pessoal API", version="0.1.0", lifespan=app_lifespan)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    """Attach a request id to logs and measure request duration."""
    request_id = request.headers.get("X-Request-ID") or generate_request_id()
    set_request_id(request_id)

    method = request.method
    path = request.url.path
    app_logger.info("Request started", extra={"method": method, "path": path})
    start = time.perf_counter()

    try:
        response: Response = await call_next(request)
    except Exception:
        duration_ms = int((time.perf_counter() - start) * 1000)
        app_logger.exception(
            "Request failed",
            extra={"method": method, "path": path, "duration_ms": duration_ms},
        )
        set_request_id(None)
        raise

    duration_ms = int((time.perf_counter() - start) * 1000)
    response.headers["X-Request-ID"] = request_id
    app_logger.info(
        "Request completed",
        extra={
            "method": method,
            "path": path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )

    set_request_id(None)
    return response


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    # Sanitiza qualquer valor bytes presente nos detalhes de validação
    detalhes_seguro = jsonable_encoder(
        exc.errors(), custom_encoder={bytes: lambda b: b.decode("utf-8", errors="replace")}
    )
    app_logger.error(
        "Validation error",
        extra={
            "path": request.url.path,
            "method": request.method,
            "errors_count": len(exc.errors()),
        },
    )
    return JSONResponse(status_code=422, content={"detail": detalhes_seguro})


@app.get("/scalar", include_in_schema=False)
async def scalar_html():
    return get_scalar_api_reference(
        # Your OpenAPI document
        openapi_url=app.openapi_url,
        # Avoid CORS issues (optional)
        scalar_proxy_url="https://proxy.scalar.com",
    )


# Routers
app.include_router(conta_luz_router)
app.include_router(conta_agua_router)


# Convenience for running via `python -m api.app`
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.app:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("UVICORN_RELOAD", "0") in {"1", "true", "TRUE", "yes", "on"},
    )
