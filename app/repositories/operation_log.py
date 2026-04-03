from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.operation_log import OperationLog


class OperationLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, log: OperationLog) -> OperationLog:
        self._session.add(log)
        await self._session.flush()
        return log
