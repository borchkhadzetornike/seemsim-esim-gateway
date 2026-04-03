"""Internal service-to-service authentication and authorization.

Auth model:
  - API key per calling service (Bearer token in Authorization header)
  - Scope-based authorization per endpoint
  - Config-driven client registry (easy to migrate to DB/secrets manager later)

Scopes:
  catalog:read, catalog:sync, orders:create, orders:read, orders:refresh,
  esims:read, balance:read, topup:create, cancel:create,
  reconciliation:run, admin:ops
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Annotated

import structlog
from fastapi import Depends, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.core.errors import AuthenticationError, AuthorizationError

logger = structlog.get_logger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class ServiceClient:
    """Registered internal service that may call the gateway."""

    name: str
    api_key: str
    enabled: bool = True
    scopes: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class CallerIdentity:
    """Authenticated caller context available to request handlers."""

    service_name: str
    scopes: frozenset[str]


class ServiceClientRegistry:
    """In-memory registry of internal service clients loaded from config.

    Upgrade path: replace with DB-backed lookup or secrets-manager integration.
    """

    def __init__(self) -> None:
        self._by_key: dict[str, ServiceClient] = {}

    def load_from_json(self, json_str: str) -> None:
        if not json_str or not json_str.strip() or json_str.strip() == "[]":
            logger.warning("no_internal_service_clients_configured")
            return
        try:
            clients = json.loads(json_str)
        except json.JSONDecodeError as exc:
            logger.error("invalid_service_clients_json", error=str(exc))
            return
        for entry in clients:
            client = ServiceClient(
                name=entry["name"],
                api_key=entry["api_key"],
                enabled=entry.get("enabled", True),
                scopes=frozenset(entry.get("scopes", [])),
            )
            self._by_key[client.api_key] = client
        logger.info("service_clients_loaded", count=len(self._by_key))

    def authenticate(self, api_key: str) -> ServiceClient | None:
        return self._by_key.get(api_key)

    @property
    def client_count(self) -> int:
        return len(self._by_key)


_registry: ServiceClientRegistry | None = None


def get_client_registry() -> ServiceClientRegistry:
    global _registry  # noqa: PLW0603
    if _registry is None:
        _registry = ServiceClientRegistry()
        settings = get_settings()
        _registry.load_from_json(settings.internal_service_clients)
    return _registry


def reset_client_registry() -> None:
    """Reset singleton for testing."""
    global _registry  # noqa: PLW0603
    _registry = None


async def get_caller_identity(
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer_scheme),
) -> CallerIdentity:
    """FastAPI dependency: authenticate the calling service via Bearer API key."""
    if credentials is None:
        raise AuthenticationError(detail="Missing authorization header")

    registry = get_client_registry()
    client = registry.authenticate(credentials.credentials)

    if client is None:
        logger.warning("auth_invalid_key")
        raise AuthenticationError(detail="Invalid API key")

    if not client.enabled:
        logger.warning("auth_disabled_client", service=client.name)
        raise AuthorizationError(detail="Service client is disabled")

    structlog.contextvars.bind_contextvars(caller_service=client.name)
    return CallerIdentity(service_name=client.name, scopes=client.scopes)


def require_scope(*scopes: str):
    """Return a FastAPI dependency that authenticates and checks required scopes."""

    async def _check_scope(
        caller: CallerIdentity = Depends(get_caller_identity),
    ) -> CallerIdentity:
        missing = set(scopes) - caller.scopes
        if missing:
            logger.warning(
                "auth_insufficient_scope",
                required=list(scopes),
                missing=list(missing),
                service=caller.service_name,
            )
            raise AuthorizationError(
                detail=f"Insufficient scope: requires {', '.join(sorted(missing))}"
            )
        return caller

    return _check_scope


# ── Typed scope dependencies for clean route signatures ──────────────
RequireCatalogRead = Annotated[CallerIdentity, Depends(require_scope("catalog:read"))]
RequireCatalogSync = Annotated[CallerIdentity, Depends(require_scope("catalog:sync"))]
RequireOrdersCreate = Annotated[CallerIdentity, Depends(require_scope("orders:create"))]
RequireOrdersRead = Annotated[CallerIdentity, Depends(require_scope("orders:read"))]
RequireOrdersRefresh = Annotated[CallerIdentity, Depends(require_scope("orders:refresh"))]
RequireEsimsRead = Annotated[CallerIdentity, Depends(require_scope("esims:read"))]
RequireBalanceRead = Annotated[CallerIdentity, Depends(require_scope("balance:read"))]
RequireTopupCreate = Annotated[CallerIdentity, Depends(require_scope("topup:create"))]
RequireCancelCreate = Annotated[CallerIdentity, Depends(require_scope("cancel:create"))]
RequireReconciliationRun = Annotated[CallerIdentity, Depends(require_scope("reconciliation:run"))]
RequireAdminOps = Annotated[CallerIdentity, Depends(require_scope("admin:ops"))]
