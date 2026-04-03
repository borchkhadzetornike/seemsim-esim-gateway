from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from app.api.error_handlers import register_error_handlers
from app.api.v1.admin import router as admin_router
from app.api.v1.catalog import router as catalog_router
from app.api.v1.esims import router as esims_router
from app.api.v1.health import router as health_router
from app.api.v1.orders import router as orders_router
from app.api.v1.webhooks import router as webhooks_router
from app.core.auth import get_client_registry
from app.core.config import get_settings
from app.core.database import dispose_engine
from app.core.logging import setup_logging
from app.core.middleware import RequestContextMiddleware
from app.core.redis import close_redis

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    setup_logging(
        log_level=settings.app_log_level,
        json_format=settings.is_production,
    )
    logger.info("service_starting", app_name=settings.app_name, env=settings.app_env)

    _validate_startup_config(settings)

    yield

    logger.info("service_shutting_down")
    await close_redis()
    await dispose_engine()
    logger.info("service_stopped")


def _validate_startup_config(settings) -> None:  # type: ignore[no-untyped-def]
    """Log warnings for missing critical configuration."""
    if not settings.esim_access_access_code:
        logger.error("CRITICAL_CONFIG_MISSING: esim_access_access_code is empty")
    if not settings.esim_access_secret_key:
        logger.error("CRITICAL_CONFIG_MISSING: esim_access_secret_key is empty")

    registry = get_client_registry()
    if registry.client_count == 0:
        logger.warning(
            "NO_SERVICE_CLIENTS_CONFIGURED — all authenticated endpoints will reject requests. "
            "Set INTERNAL_SERVICE_CLIENTS env var."
        )
    else:
        logger.info("service_clients_ready", count=registry.client_count)


def create_app() -> FastAPI:
    app = FastAPI(
        title="eSIM Gateway",
        description=(
            "Internal eSIM provider integration gateway. "
            "Anti-corruption layer for eSIM Access provider. "
            "Not for direct frontend/mobile access."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(RequestContextMiddleware)

    app.include_router(health_router)
    app.include_router(catalog_router, prefix="/v1")
    app.include_router(orders_router, prefix="/v1")
    app.include_router(esims_router, prefix="/v1")
    app.include_router(webhooks_router, prefix="/v1")
    app.include_router(admin_router, prefix="/v1")

    register_error_handlers(app)

    return app


app = create_app()
