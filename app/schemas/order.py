from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.schemas.common import BaseSchema


class CreateOrderRequest(BaseSchema):
    package_code: str = Field(..., description="Provider package code to order")
    quantity: int = Field(default=1, ge=1, le=50, description="Number of eSIMs to order")


class OrderOut(BaseSchema):
    id: str
    provider_order_no: str | None = None
    transaction_id: str
    package_code: str
    quantity: int
    status: str
    provider_status: str | None = None
    iccid: str | None = None
    failure_reason: str | None = None
    last_provider_sync_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class EsimDetailOut(BaseSchema):
    """Full eSIM detail output including all provider-sourced fields."""

    id: str
    iccid: str
    order_id: str
    provider_esim_tran_no: str | None = None
    imsi: str | None = None
    msisdn: str | None = None
    activation_code: str | None = None
    smdp_address: str | None = None
    matching_id: str | None = None
    qr_code_url: str | None = None
    short_url: str | None = None
    status: str
    smdp_status: str | None = None
    esim_status: str | None = None
    pin: str | None = None
    puk: str | None = None
    apn: str | None = None
    total_volume: int | None = None
    total_duration: int | None = None
    duration_unit: str | None = None
    order_usage: int | None = None
    activate_time: datetime | None = None
    installation_time: datetime | None = None
    expired_time: datetime | None = None
    support_topup_type: int | None = None
    fup_policy: str | None = None
    created_at: datetime
    updated_at: datetime


class OrderDetailOut(BaseSchema):
    """Enriched order output with eSIM details for refresh responses."""

    id: str
    provider_order_no: str | None = None
    transaction_id: str
    package_code: str
    quantity: int
    status: str
    provider_status: str | None = None
    iccid: str | None = None
    failure_reason: str | None = None
    last_provider_sync_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    esims: list[EsimDetailOut] = []


class OrderRefreshResponse(BaseSchema):
    """Response from POST /v1/orders/{id}/refresh."""

    order: OrderDetailOut
    state_changed: bool
    source: str = "manual_refresh"


class TopupRequest(BaseSchema):
    package_code: str = Field(..., description="Topup package code")
    iccid: str = Field(..., description="ICCID of the eSIM to top up")


class TopupResponse(BaseSchema):
    order_id: str
    iccid: str
    package_code: str
    status: str


class CancelOrderResponse(BaseSchema):
    order_id: str
    status: str
    message: str
