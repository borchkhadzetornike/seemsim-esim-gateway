"""Abstract provider interface.

Any eSIM provider adapter must implement this interface, enabling
the service layer to remain provider-agnostic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ProviderPackageData:
    package_code: str
    name: str
    type: str
    data_volume_mb: int | None = None
    duration_days: int | None = None
    price: float = 0.0
    currency: str = "USD"
    countries: list[str] = field(default_factory=list)
    location_code: str | None = None
    support_topup_type: int | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderOrderResult:
    order_no: str
    transaction_id: str
    status: str
    iccid: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderEsimProfile:
    iccid: str
    smdp_address: str | None = None
    matching_id: str | None = None
    activation_code: str | None = None
    status: str = "unknown"
    msisdn: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderEsimStatus:
    iccid: str
    status: str
    data_usage_remaining_mb: float | None = None
    days_remaining: int | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderTopupResult:
    order_no: str
    iccid: str
    package_code: str
    status: str
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderCancelResult:
    order_no: str
    status: str
    message: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


class BaseEsimProvider(ABC):
    """Abstract base for eSIM provider adapters."""

    provider_name: str = "unknown"

    @abstractmethod
    async def sync_products(self) -> list[ProviderPackageData]:
        """Fetch all available packages from the provider."""
        ...

    @abstractmethod
    async def create_order(
        self, package_code: str, quantity: int, transaction_id: str
    ) -> ProviderOrderResult: ...

    @abstractmethod
    async def get_order_status(self, order_no: str) -> ProviderOrderResult: ...

    @abstractmethod
    async def get_esim(self, iccid: str) -> ProviderEsimProfile: ...

    @abstractmethod
    async def get_esim_status(self, iccid: str) -> ProviderEsimStatus: ...

    @abstractmethod
    async def topup_esim(
        self, iccid: str, package_code: str, transaction_id: str
    ) -> ProviderTopupResult: ...

    @abstractmethod
    async def cancel_order(self, order_no: str) -> ProviderCancelResult: ...

    @abstractmethod
    async def suspend_esim(self, iccid: str) -> ProviderCancelResult: ...

    async def get_topup_packages(self, iccid: str) -> list[ProviderPackageData]:
        """Fetch top-up eligible packages for a given eSIM."""
        return []

    async def get_balance(self) -> dict[str, Any]:
        """Return provider account balance. Override per provider."""
        from app.core.errors import ProviderCapabilityUnavailableError

        raise ProviderCapabilityUnavailableError(detail="Balance query not supported")

    async def query_order_full(self, order_no: str) -> dict[str, Any]:
        """Return the full provider query response obj for rich state sync.

        Default wraps get_order_status. Override for richer data.
        """
        result = await self.get_order_status(order_no)
        return {"esimList": [result.raw] if result.raw else [], "orderNo": order_no}

    async def handle_webhook(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Process and normalize a webhook payload. Override if provider supports webhooks."""
        return payload
