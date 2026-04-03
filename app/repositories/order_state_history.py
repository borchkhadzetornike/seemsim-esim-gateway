from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order_state_history import OrderStateHistory


class OrderStateHistoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, entry: OrderStateHistory) -> OrderStateHistory:
        self._session.add(entry)
        await self._session.flush()
        return entry

    async def get_by_order_id(self, order_id: str) -> list[OrderStateHistory]:
        stmt = (
            select(OrderStateHistory)
            .where(OrderStateHistory.order_id == order_id)
            .order_by(OrderStateHistory.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
