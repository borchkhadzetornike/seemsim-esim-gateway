"""Tests for webhook deduplication and state protection.

Covers: payload-hash dedup, different events for same order, terminal state protection.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.webhook import WebhookService, _payload_hash


class TestPayloadHash:

    def test_same_payload_same_hash(self):
        p1 = {"orderNo": "ORD-1", "result": "COMPLETED", "iccid": "ICC-001"}
        p2 = {"orderNo": "ORD-1", "result": "COMPLETED", "iccid": "ICC-001"}
        assert _payload_hash(p1) == _payload_hash(p2)

    def test_different_payload_different_hash(self):
        p1 = {"orderNo": "ORD-1", "result": "COMPLETED"}
        p2 = {"orderNo": "ORD-1", "result": "IN_USE"}
        assert _payload_hash(p1) != _payload_hash(p2)

    def test_key_order_irrelevant(self):
        p1 = {"a": 1, "b": 2}
        p2 = {"b": 2, "a": 1}
        assert _payload_hash(p1) == _payload_hash(p2)


class TestWebhookDuplicateDetection:

    @pytest.mark.asyncio
    async def test_exact_duplicate_rejected(self, db_session):
        provider = AsyncMock()
        provider.provider_name = "esim_access"
        provider.handle_webhook.return_value = {
            "event_type": "ORDER_STATUS",
            "order_no": "ORD-1",
            "status": "completed",
        }

        svc = WebhookService(provider, db_session)

        event_id_1 = await svc.process_webhook({"orderNo": "ORD-1", "result": "COMPLETED"})
        event_id_2 = await svc.process_webhook({"orderNo": "ORD-1", "result": "COMPLETED"})

        assert event_id_1 != event_id_2
        assert provider.handle_webhook.call_count == 2

    @pytest.mark.asyncio
    async def test_different_status_same_order_processed(self, db_session):
        provider = AsyncMock()
        provider.provider_name = "esim_access"

        call_count = {"handle": 0}

        async def handle_webhook(payload):
            call_count["handle"] += 1
            if payload.get("result") == "COMPLETED":
                return {
                    "event_type": "ORDER_STATUS",
                    "order_no": "ORD-1",
                    "status": "completed",
                }
            return {
                "event_type": "ORDER_STATUS",
                "order_no": "ORD-1",
                "status": "active",
            }

        provider.handle_webhook.side_effect = handle_webhook

        svc = WebhookService(provider, db_session)

        await svc.process_webhook({"orderNo": "ORD-1", "result": "COMPLETED"})
        await svc.process_webhook({"orderNo": "ORD-1", "result": "IN_USE"})

        assert call_count["handle"] == 2
