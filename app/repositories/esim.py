from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.esim import Esim, EsimStatusHistory


class EsimRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, esim: Esim) -> Esim:
        self._session.add(esim)
        await self._session.flush()
        return esim

    async def get_by_id(self, esim_id: str) -> Esim | None:
        return await self._session.get(Esim, esim_id)

    async def get_by_iccid(self, iccid: str) -> Esim | None:
        stmt = select(Esim).where(Esim.iccid == iccid)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_iccid_locked(self, iccid: str) -> Esim | None:
        """Get eSIM with row-level lock for safe concurrent updates."""
        stmt = select(Esim).where(Esim.iccid == iccid).with_for_update()
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_order_id(self, order_id: str) -> list[Esim]:
        stmt = select(Esim).where(Esim.order_id == order_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(self, esim_id: str, status: str) -> Esim | None:
        esim = await self.get_by_id(esim_id)
        if not esim:
            return None
        esim.status = status
        return esim

    async def add_status_history(self, history: EsimStatusHistory) -> EsimStatusHistory:
        self._session.add(history)
        await self._session.flush()
        return history

    async def get_status_history(self, esim_id: str) -> list[EsimStatusHistory]:
        stmt = (
            select(EsimStatusHistory)
            .where(EsimStatusHistory.esim_id == esim_id)
            .order_by(EsimStatusHistory.recorded_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
