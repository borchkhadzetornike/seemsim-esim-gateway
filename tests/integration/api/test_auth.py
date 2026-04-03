"""Integration tests for internal service-to-service authentication."""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock

from app.core.auth import reset_client_registry
from app.core.database import get_db_session
from app.core.redis import get_redis
import app.core.config as config_module

TEST_CLIENTS = [
    {
        "name": "full-access",
        "api_key": "sk_test_full_access",
        "enabled": True,
        "scopes": [
            "catalog:read", "catalog:sync", "orders:create", "orders:read",
            "orders:refresh", "esims:read", "balance:read",
        ],
    },
    {
        "name": "read-only",
        "api_key": "sk_test_read_only",
        "enabled": True,
        "scopes": ["catalog:read", "orders:read", "esims:read"],
    },
    {
        "name": "disabled-svc",
        "api_key": "sk_test_disabled",
        "enabled": False,
        "scopes": ["catalog:read"],
    },
]


@pytest.fixture(autouse=True)
def _setup_auth(monkeypatch):
    monkeypatch.setenv("INTERNAL_SERVICE_CLIENTS", json.dumps(TEST_CLIENTS))
    config_module._settings = None
    reset_client_registry()
    yield
    config_module._settings = None
    reset_client_registry()


@pytest.fixture
async def auth_app(db_session: AsyncSession, mock_redis: AsyncMock) -> FastAPI:
    """App with real auth (no get_caller_identity override)."""
    from app.main import create_app

    application = create_app()

    async def _override_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    async def _override_redis() -> AsyncGenerator[AsyncMock, None]:
        yield mock_redis

    application.dependency_overrides[get_db_session] = _override_db
    application.dependency_overrides[get_redis] = _override_redis
    return application


@pytest.fixture
async def auth_client(auth_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=auth_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def _auth(key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {key}"}


# ── Health endpoints remain unauthenticated ─────────────────────────


@pytest.mark.asyncio
async def test_health_live_no_auth(auth_client: AsyncClient) -> None:
    resp = await auth_client.get("/health/live")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_health_ready_no_auth(auth_client: AsyncClient) -> None:
    resp = await auth_client.get("/health/ready")
    assert resp.status_code == 200


# ── Webhook endpoint remains unauthenticated ────────────────────────


@pytest.mark.asyncio
async def test_webhook_no_auth_required(auth_client: AsyncClient) -> None:
    resp = await auth_client.post(
        "/v1/provider/webhooks/esim-access",
        json={"notifyType": "ORDER_STATUS", "orderNo": "AUTH-TEST"},
    )
    assert resp.status_code == 200


# ── Missing auth header ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_missing_auth_returns_401(auth_client: AsyncClient) -> None:
    resp = await auth_client.get("/v1/catalog/products")
    assert resp.status_code == 401
    body = resp.json()
    assert body["error"]["error_code"] == "AUTHENTICATION_ERROR"


# ── Invalid API key ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_invalid_key_returns_401(auth_client: AsyncClient) -> None:
    resp = await auth_client.get("/v1/catalog/products", headers=_auth("sk_bogus"))
    assert resp.status_code == 401


# ── Disabled client ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_disabled_client_returns_403(auth_client: AsyncClient) -> None:
    resp = await auth_client.get("/v1/catalog/products", headers=_auth("sk_test_disabled"))
    assert resp.status_code == 403
    body = resp.json()
    assert body["error"]["error_code"] == "AUTHORIZATION_ERROR"


# ── Valid key + sufficient scope ─────────────────────────────────────


@pytest.mark.asyncio
async def test_valid_key_catalog_read(auth_client: AsyncClient) -> None:
    resp = await auth_client.get("/v1/catalog/products", headers=_auth("sk_test_full_access"))
    assert resp.status_code == 200


# ── Valid key + insufficient scope ───────────────────────────────────


@pytest.mark.asyncio
async def test_insufficient_scope_returns_403(auth_client: AsyncClient) -> None:
    resp = await auth_client.post(
        "/v1/orders",
        headers=_auth("sk_test_read_only"),
        json={"package_code": "X", "quantity": 1},
    )
    assert resp.status_code == 403
    body = resp.json()
    assert "scope" in body["error"]["detail"].lower()


@pytest.mark.asyncio
async def test_read_only_can_read_orders(auth_client: AsyncClient) -> None:
    resp = await auth_client.get(
        "/v1/orders/nonexistent",
        headers=_auth("sk_test_read_only"),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_read_only_cannot_sync_catalog(auth_client: AsyncClient) -> None:
    resp = await auth_client.post(
        "/v1/catalog/sync",
        headers=_auth("sk_test_read_only"),
    )
    assert resp.status_code == 403
