from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.types import JSONBCompat


class ProviderOrder(Base):
    """Tracks orders placed against the provider."""

    __tablename__ = "provider_orders"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider_name: Mapped[str] = mapped_column(String(50), nullable=False, default="esim_access")
    provider_order_no: Mapped[str | None] = mapped_column(String(128), nullable=True)
    transaction_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    package_code: Mapped[str] = mapped_column(String(128), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    provider_status: Mapped[str | None] = mapped_column(String(100), nullable=True)
    iccid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    raw_provider_request: Mapped[dict | None] = mapped_column(JSONBCompat, nullable=True)
    raw_provider_response: Mapped[dict | None] = mapped_column(JSONBCompat, nullable=True)
    last_provider_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_provider_payload: Mapped[dict | None] = mapped_column(JSONBCompat, nullable=True)

    __table_args__ = (
        Index("ix_provider_orders_provider_order", "provider_order_no"),
        Index("ix_provider_orders_transaction", "transaction_id"),
        Index("ix_provider_orders_status", "status"),
        Index("ix_provider_orders_iccid", "iccid"),
    )
