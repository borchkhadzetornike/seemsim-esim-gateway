from __future__ import annotations

from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.types import JSONBCompat


class OrderStateHistory(Base):
    """Audit trail for order state transitions from all sync sources."""

    __tablename__ = "order_state_history"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    order_id: Mapped[str] = mapped_column(String(64), nullable=False)
    old_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    new_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    old_provider_status: Mapped[str | None] = mapped_column(String(100), nullable=True)
    new_provider_status: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    payload_json: Mapped[dict | None] = mapped_column(JSONBCompat, nullable=True)

    __table_args__ = (
        Index("ix_order_state_history_order", "order_id"),
        Index("ix_order_state_history_source", "source"),
    )
