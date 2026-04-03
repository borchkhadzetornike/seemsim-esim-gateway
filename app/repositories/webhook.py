from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook_event import ProviderWebhookEvent


class WebhookRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, event: ProviderWebhookEvent) -> ProviderWebhookEvent:
        self._session.add(event)
        await self._session.flush()
        return event

    async def get_by_id(self, event_id: str) -> ProviderWebhookEvent | None:
        return await self._session.get(ProviderWebhookEvent, event_id)

    async def mark_processed(
        self, event_id: str, error: str | None = None
    ) -> ProviderWebhookEvent | None:
        event = await self.get_by_id(event_id)
        if not event:
            return None
        event.processed = True
        event.processed_at = datetime.now(UTC)
        event.processing_status = "failed" if error else "processed"
        event.processing_error = error
        return event

    async def get_unprocessed(self, limit: int = 100) -> list[ProviderWebhookEvent]:
        stmt = (
            select(ProviderWebhookEvent)
            .where(ProviderWebhookEvent.processed.is_(False))
            .order_by(ProviderWebhookEvent.created_at)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def find_processed_duplicate(
        self, order_no: str | None, event_type: str
    ) -> ProviderWebhookEvent | None:
        """Check if a webhook with the same order_no + event_type was already processed."""
        if not order_no:
            return None
        stmt = (
            select(ProviderWebhookEvent)
            .where(
                ProviderWebhookEvent.order_no == order_no,
                ProviderWebhookEvent.event_type == event_type,
                ProviderWebhookEvent.processing_status == "processed",
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
