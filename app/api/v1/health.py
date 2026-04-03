from __future__ import annotations

from datetime import UTC, datetime

import structlog
from fastapi import APIRouter

from app.core.config import get_settings
from app.core.database import get_engine
from app.core.redis import get_redis_pool
from app.schemas.common import HealthResponse

router = APIRouter(prefix="/health", tags=["Health"])
logger = structlog.get_logger(__name__)


@router.get(
    "/live",
    response_model=HealthResponse,
    summary="Liveness probe",
    description="Returns 200 if the service process is running.",
)
async def liveness() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=get_settings().app_name,
        timestamp=datetime.now(UTC),
    )


@router.get(
    "/ready",
    response_model=HealthResponse,
    summary="Readiness probe",
    description="Returns 200 if the service can handle requests (DB and Redis reachable).",
)
async def readiness() -> HealthResponse:
    checks: dict[str, str] = {}

    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc}"
        logger.error("readiness_db_check_failed", error=str(exc))

    try:
        redis = get_redis_pool()
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc}"
        logger.error("readiness_redis_check_failed", error=str(exc))

    all_ok = all(v == "ok" for v in checks.values())

    return HealthResponse(
        status="ok" if all_ok else "degraded",
        service=get_settings().app_name,
        timestamp=datetime.now(UTC),
        checks=checks,
    )
