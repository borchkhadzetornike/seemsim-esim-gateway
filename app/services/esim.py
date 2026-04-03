from __future__ import annotations

import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ResourceNotFoundError
from app.core.utils import utc_now
from app.models.esim import EsimStatusHistory
from app.providers.base import BaseEsimProvider
from app.repositories.esim import EsimRepository

logger = structlog.get_logger(__name__)


class EsimService:
    def __init__(self, provider: BaseEsimProvider, session: AsyncSession) -> None:
        self._provider = provider
        self._repo = EsimRepository(session)

    async def get_esim(self, esim_id: str):  # type: ignore[no-untyped-def]
        esim = await self._repo.get_by_id(esim_id)
        if not esim:
            raise ResourceNotFoundError(detail=f"eSIM {esim_id} not found")
        return esim

    async def get_esim_by_iccid(self, iccid: str):  # type: ignore[no-untyped-def]
        esim = await self._repo.get_by_iccid(iccid)
        if not esim:
            raise ResourceNotFoundError(detail=f"eSIM with ICCID {iccid} not found")
        return esim

    async def get_esim_status(self, esim_id: str):  # type: ignore[no-untyped-def]
        esim = await self.get_esim(esim_id)

        provider_status = await self._provider.get_esim_status(esim.iccid)

        if provider_status.status != esim.status:
            previous = esim.status
            esim.status = provider_status.status

            history = EsimStatusHistory(
                id=str(uuid.uuid4()),
                esim_id=esim.id,
                iccid=esim.iccid,
                previous_status=previous,
                new_status=provider_status.status,
                source="status_refresh",
                recorded_at=utc_now(),
            )
            await self._repo.add_status_history(history)

            logger.info(
                "esim_status_updated",
                esim_id=esim_id,
                from_status=previous,
                to_status=provider_status.status,
            )

        return provider_status

    async def get_status_history(self, esim_id: str) -> list[EsimStatusHistory]:
        await self.get_esim(esim_id)
        return await self._repo.get_status_history(esim_id)
