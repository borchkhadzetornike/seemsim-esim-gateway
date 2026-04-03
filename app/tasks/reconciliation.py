"""Background reconciliation tasks.

Uses the ProviderStateSyncer for rich state merging (eSIM creation,
status mapping, history recording). Idempotent and safe for concurrent
execution via distributed locking on Redis.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import redis.asyncio as aioredis
import structlog

from app.core.config import get_settings
from app.core.database import get_session_factory
from app.core.redis import get_redis_pool
from app.providers.esim_access.adapter import EsimAccessProvider
from app.providers.esim_access.auth import EsimAccessAuth
from app.providers.esim_access.client import EsimAccessClient
from app.repositories.order import OrderRepository
from app.services.catalog import CatalogService
from app.services.state_sync import ProviderStateSyncer

logger = structlog.get_logger(__name__)

LOCK_TTL = 120
STALE_MINUTES = 10


async def _acquire_lock(redis: aioredis.Redis, lock_name: str) -> bool:  # type: ignore[type-arg]
    return bool(await redis.set(f"lock:{lock_name}", "1", nx=True, ex=LOCK_TTL))


async def _release_lock(redis: aioredis.Redis, lock_name: str) -> None:  # type: ignore[type-arg]
    await redis.delete(f"lock:{lock_name}")


def _build_provider() -> EsimAccessProvider:
    settings = get_settings()
    auth = EsimAccessAuth(
        access_code=settings.esim_access_access_code,
        secret_key=settings.esim_access_secret_key,
    )
    client = EsimAccessClient(auth=auth, base_url=settings.esim_access_base_url)
    return EsimAccessProvider(client=client)


async def reconcile_pending_orders() -> int:
    """Check provider for status updates on orders that are stale or incomplete.

    Selection criteria:
      - Non-terminal status (not consumed, cancelled, failed)
      - Has a provider_order_no
      - Either never synced OR last synced more than STALE_MINUTES ago

    Uses ProviderStateSyncer for rich merging (creates eSIM records,
    maps statuses, records history).
    """
    redis = get_redis_pool()
    if not await _acquire_lock(redis, "reconcile_orders"):
        logger.info("reconcile_orders_skipped_lock_held")
        return 0

    try:
        session_factory = get_session_factory()
        provider = _build_provider()
        reconciled = 0

        async with session_factory() as session:
            repo = OrderRepository(session)
            syncer = ProviderStateSyncer(provider, session)

            stale_threshold = datetime.now(UTC) - timedelta(minutes=STALE_MINUTES)
            orders = await repo.get_orders_needing_sync(
                stale_threshold=stale_threshold,
                limit=50,
            )

            logger.info("reconcile_orders_start", count=len(orders))

            for order in orders:
                try:
                    result = await syncer.sync_order(order, "reconciliation")
                    if result.state_changed:
                        reconciled += 1
                except Exception as exc:
                    logger.warning(
                        "order_reconciliation_failed",
                        order_id=order.id,
                        error=str(exc),
                    )

            await session.commit()

        logger.info("reconcile_orders_complete", reconciled=reconciled)
        return reconciled
    finally:
        await _release_lock(redis, "reconcile_orders")


async def sync_catalog_task() -> None:
    """Periodic catalog sync."""
    redis = get_redis_pool()
    if not await _acquire_lock(redis, "catalog_sync"):
        logger.info("catalog_sync_skipped_lock_held")
        return

    try:
        session_factory = get_session_factory()
        provider = _build_provider()

        async with session_factory() as session:
            service = CatalogService(provider=provider, session=session)
            result = await service.sync_catalog()
            await session.commit()
            logger.info(
                "catalog_sync_task_complete",
                products=result.products_synced,
                packages=result.packages_synced,
            )
    finally:
        await _release_lock(redis, "catalog_sync")


async def run_scheduler() -> None:
    """Simple async scheduler loop for background tasks.

    In production, replace with APScheduler, Celery, or a Kubernetes CronJob.
    """
    settings = get_settings()
    logger.info("background_scheduler_starting")

    while True:
        try:
            await reconcile_pending_orders()
        except Exception as exc:
            logger.error("reconciliation_task_error", error=str(exc))

        await asyncio.sleep(settings.reconciliation_interval_seconds)

        try:
            await sync_catalog_task()
        except Exception as exc:
            logger.error("catalog_sync_task_error", error=str(exc))

        await asyncio.sleep(settings.catalog_sync_interval_seconds)
