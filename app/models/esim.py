from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.types import JSONBCompat


class Esim(Base):
    """Normalized eSIM record with full provider detail fields."""

    __tablename__ = "esims"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    iccid: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    provider_name: Mapped[str] = mapped_column(String(50), nullable=False, default="esim_access")
    order_id: Mapped[str] = mapped_column(String(64), nullable=False)

    # Profile fields (from initial creation or provider query)
    provider_esim_tran_no: Mapped[str | None] = mapped_column(String(128), nullable=True)
    imsi: Mapped[str | None] = mapped_column(String(64), nullable=True)
    msisdn: Mapped[str | None] = mapped_column(String(32), nullable=True)
    smdp_address: Mapped[str | None] = mapped_column(String(512), nullable=True)
    matching_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    activation_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    qr_code_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    short_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Status fields
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="allocated")
    smdp_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    esim_status: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Connectivity
    pin: Mapped[str | None] = mapped_column(String(32), nullable=True)
    puk: Mapped[str | None] = mapped_column(String(32), nullable=True)
    apn: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Volume / duration
    total_volume: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    total_duration: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    order_usage: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # Timestamps from provider
    activate_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    installation_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expired_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Policy
    support_topup_type: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fup_policy: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Raw provider data
    raw_provider_data: Mapped[dict | None] = mapped_column(JSONBCompat, nullable=True)
    raw_provider_payload: Mapped[dict | None] = mapped_column(JSONBCompat, nullable=True)

    __table_args__ = (
        Index("ix_esims_iccid", "iccid"),
        Index("ix_esims_order", "order_id"),
        Index("ix_esims_status", "status"),
    )


class EsimStatusHistory(Base):
    """Audit trail for eSIM status transitions."""

    __tablename__ = "esim_status_history"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    esim_id: Mapped[str] = mapped_column(String(64), nullable=False)
    iccid: Mapped[str] = mapped_column(String(64), nullable=False)
    previous_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    new_status: Mapped[str] = mapped_column(String(50), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="api")
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_esim_status_history_esim", "esim_id"),
        Index("ix_esim_status_history_iccid", "iccid"),
    )
