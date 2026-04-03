from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import ProviderOrder


class OrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, order: ProviderOrder) -> ProviderOrder:
        self._session.add(order)
        await self._session.flush()
        return order

    async def get_by_id(self, order_id: str) -> ProviderOrder | None:
        return await self._session.get(ProviderOrder, order_id)

    async def get_by_id_locked(self, order_id: str) -> ProviderOrder | None:
        """Get order with row-level lock for safe concurrent updates."""
        stmt = (
            select(ProviderOrder)
            .where(ProviderOrder.id == order_id)
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_transaction_id(self, transaction_id: str) -> ProviderOrder | None:
        stmt = select(ProviderOrder).where(ProviderOrder.transaction_id == transaction_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_provider_order_no(self, order_no: str) -> ProviderOrder | None:
        stmt = select(ProviderOrder).where(ProviderOrder.provider_order_no == order_no)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_pending_orders(self) -> list[ProviderOrder]:
        stmt = select(ProviderOrder).where(ProviderOrder.status.in_(["pending", "processing"]))
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_orders_needing_sync(
        self,
        stale_threshold: datetime,
        limit: int = 50,
    ) -> list[ProviderOrder]:
        """Find orders that need provider state refresh.

        Criteria: non-terminal, has provider_order_no, and either
        never synced or synced before the stale_threshold.
        """
        terminal = ["consumed", "cancelled", "failed"]
        stmt = (
            select(ProviderOrder)
            .where(
                ProviderOrder.status.notin_(terminal),
                ProviderOrder.provider_order_no.isnot(None),
            )
            .where(
                sa.or_(
                    ProviderOrder.last_provider_sync_at.is_(None),
                    ProviderOrder.last_provider_sync_at < stale_threshold,
                )
            )
            .order_by(ProviderOrder.created_at)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(
        self,
        order_id: str,
        status: str,
        provider_order_no: str | None = None,
        iccid: str | None = None,
        failure_reason: str | None = None,
        raw_response: dict | None = None,
    ) -> ProviderOrder | None:
        order = await self.get_by_id(order_id)
        if not order:
            return None
        order.status = status
        if provider_order_no:
            order.provider_order_no = provider_order_no
        if iccid:
            order.iccid = iccid
        if failure_reason:
            order.failure_reason = failure_reason
        if raw_response:
            order.raw_provider_response = raw_response
        return order
