"""FastAPI dependency injection providers."""

from __future__ import annotations

from typing import Annotated

import redis.asyncio as aioredis
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.core.idempotency import IdempotencyManager
from app.core.redis import get_redis
from app.providers.base import BaseEsimProvider
from app.providers.esim_access.adapter import EsimAccessProvider
from app.providers.esim_access.auth import EsimAccessAuth
from app.providers.esim_access.client import EsimAccessClient
from app.services.catalog import CatalogService
from app.services.esim import EsimService
from app.services.order import OrderService
from app.services.webhook import WebhookService

SettingsDep = Annotated[Settings, Depends(get_settings)]
SessionDep = Annotated[AsyncSession, Depends(get_db_session)]
RedisDep = Annotated[aioredis.Redis, Depends(get_redis)]  # type: ignore[type-arg]


def get_esim_access_auth(settings: SettingsDep) -> EsimAccessAuth:
    return EsimAccessAuth(
        access_code=settings.esim_access_access_code,
        secret_key=settings.esim_access_secret_key,
    )


def get_esim_access_client(
    auth: Annotated[EsimAccessAuth, Depends(get_esim_access_auth)],
    settings: SettingsDep,
) -> EsimAccessClient:
    return EsimAccessClient(
        auth=auth,
        base_url=settings.esim_access_base_url,
        timeout_seconds=float(settings.provider_request_timeout_seconds),
        max_retries=settings.provider_max_retries,
    )


def get_provider(
    client: Annotated[EsimAccessClient, Depends(get_esim_access_client)],
) -> BaseEsimProvider:
    return EsimAccessProvider(client=client)


ProviderDep = Annotated[BaseEsimProvider, Depends(get_provider)]


def get_catalog_service(provider: ProviderDep, session: SessionDep) -> CatalogService:
    return CatalogService(provider=provider, session=session)


def get_order_service(provider: ProviderDep, session: SessionDep) -> OrderService:
    return OrderService(provider=provider, session=session)


def get_esim_service(provider: ProviderDep, session: SessionDep) -> EsimService:
    return EsimService(provider=provider, session=session)


def get_webhook_service(provider: ProviderDep, session: SessionDep) -> WebhookService:
    return WebhookService(provider=provider, session=session)


def get_idempotency_manager(redis: RedisDep) -> IdempotencyManager:
    return IdempotencyManager(redis=redis)


CatalogServiceDep = Annotated[CatalogService, Depends(get_catalog_service)]
OrderServiceDep = Annotated[OrderService, Depends(get_order_service)]
EsimServiceDep = Annotated[EsimService, Depends(get_esim_service)]
WebhookServiceDep = Annotated[WebhookService, Depends(get_webhook_service)]
IdempotencyDep = Annotated[IdempotencyManager, Depends(get_idempotency_manager)]
