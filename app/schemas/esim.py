from __future__ import annotations

from datetime import datetime

from app.schemas.common import BaseSchema


class EsimPackageInfo(BaseSchema):
    package_code: str
    package_name: str | None = None
    slug: str | None = None
    volume: int | None = None
    duration: int | None = None
    location_code: str | None = None
    esim_tran_no: str | None = None
    transaction_id: str | None = None
    created_at: str | None = None


class EsimOut(BaseSchema):
    id: str
    iccid: str
    order_id: str
    provider_esim_tran_no: str | None = None
    imsi: str | None = None
    smdp_address: str | None = None
    matching_id: str | None = None
    activation_code: str | None = None
    qr_code_url: str | None = None
    short_url: str | None = None
    status: str
    smdp_status: str | None = None
    esim_status: str | None = None
    msisdn: str | None = None
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
    package_list: list[EsimPackageInfo] = []
    created_at: datetime
    updated_at: datetime


class TopupPackageOut(BaseSchema):
    package_code: str
    name: str
    data_volume_mb: int | None = None
    duration_days: int | None = None
    price: float
    currency: str
    countries: list[str] = []


class EsimStatusOut(BaseSchema):
    iccid: str
    status: str
    data_usage_remaining_mb: float | None = None
    days_remaining: int | None = None
    last_updated: datetime


class EsimStatusHistoryOut(BaseSchema):
    previous_status: str | None = None
    new_status: str
    source: str
    recorded_at: datetime
