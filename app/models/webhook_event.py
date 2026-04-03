from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.types import JSONBCompat


def _utc_now() -> datetime:
    return datetime.now(UTC)


class ProviderWebhookEvent(Base):
    """Stores raw incoming webhook events for audit and replay protection."""

    __tablename__ = "provider_webhook_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider_name: Mapped[str] = mapped_column(String(50), nullable=False, default="esim_access")
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    provider_event_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    order_no: Mapped[str | None] = mapped_column(String(128), nullable=True)
    iccid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    transaction_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    payload: Mapped[dict] = mapped_column(JSONBCompat, nullable=False)
    processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    processing_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending"
    )
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=_utc_now,
        nullable=False,
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("ix_webhook_events_type", "event_type"),
        Index("ix_webhook_events_order", "order_no"),
        Index("ix_webhook_events_processed", "processed"),
        Index("ix_webhook_events_processing_status", "processing_status"),
    )
