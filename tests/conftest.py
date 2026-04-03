from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("ESIM_ACCESS_ACCESS_CODE", "test_access_code")
os.environ.setdefault("ESIM_ACCESS_SECRET_KEY", "test_secret_key")

import app.core.config as config_module
from app.core.auth import CallerIdentity, get_caller_identity
from app.core.database import get_db_session
from app.core.redis import get_redis
from app.models.base import Base
from app.providers.base import BaseEsimProvider

config_module._settings = None

ALL_SCOPES = frozenset({
    "catalog:read", "catalog:sync", "orders:create", "orders:read",
    "orders:refresh", "esims:read", "balance:read", "topup:create",
    "cancel:create", "reconciliation:run", "admin:ops",
})


@pytest.fixture(scope="session")
def event_loop():  # type: ignore[no-untyped-def]
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def engine() -> AsyncGenerator[AsyncEngine, None]:
    engine = create_async_engine("sqlite+aiosqlite:///", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest.fixture
def mock_redis() -> AsyncMock:
    mock = AsyncMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=1)
    mock.ping = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_provider() -> AsyncMock:
    return AsyncMock(spec=BaseEsimProvider)


def _test_caller_override() -> CallerIdentity:
    """Default auth override giving full access to all scopes."""
    return CallerIdentity(service_name="test-client", scopes=ALL_SCOPES)


@pytest.fixture
async def app(db_session: AsyncSession, mock_redis: AsyncMock) -> FastAPI:
    from app.main import create_app

    application = create_app()

    async def _override_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    async def _override_redis() -> AsyncGenerator[AsyncMock, None]:
        yield mock_redis

    application.dependency_overrides[get_db_session] = _override_db
    application.dependency_overrides[get_redis] = _override_redis
    application.dependency_overrides[get_caller_identity] = _test_caller_override

    return application


@pytest.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
