from __future__ import annotations

import time
import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ProviderError, ResourceNotFoundError
from app.models.esim import Esim, EsimStatusHistory
from app.models.operation_log import OperationLog
from app.models.order import ProviderOrder
from app.providers.base import BaseEsimProvider
from app.repositories.esim import EsimRepository
from app.repositories.operation_log import OperationLogRepository
from app.repositories.order import OrderRepository
from app.services.state_sync import ProviderStateSyncer, SyncResult

logger = structlog.get_logger(__name__)


class OrderService:
    def __init__(self, provider: BaseEsimProvider, session: AsyncSession) -> None:
        self._provider = provider
        self._order_repo = OrderRepository(session)
        self._esim_repo = EsimRepository(session)
        self._log_repo = OperationLogRepository(session)
        self._state_syncer = ProviderStateSyncer(provider, session)
        self._session = session

    async def create_order(
        self, package_code: str, quantity: int, idempotency_key: str | None = None
    ) -> ProviderOrder:
        transaction_id = str(uuid.uuid4())
        order_id = str(uuid.uuid4())

        order = ProviderOrder(
            id=order_id,
            provider_name=self._provider.provider_name,
            transaction_id=transaction_id,
            package_code=package_code,
            quantity=quantity,
            status="pending",
            idempotency_key=idempotency_key,
            raw_provider_request={"packageCode": package_code, "quantity": quantity},
        )
        await self._order_repo.create(order)
        await self._session.flush()

        start = time.perf_counter()
        op_log_id = str(uuid.uuid4())

        try:
            result = await self._provider.create_order(package_code, quantity, transaction_id)
            elapsed_ms = int((time.perf_counter() - start) * 1000)

            order.provider_order_no = result.order_no
            order.status = result.status
            order.iccid = result.iccid
            order.raw_provider_response = result.raw

            if result.iccid:
                await self._create_esim_from_order(order, result.iccid)

            await self._log_repo.create(
                OperationLog(
                    id=op_log_id,
                    operation="create_order",
                    provider_name=self._provider.provider_name,
                    idempotency_key=idempotency_key,
                    status="success",
                    duration_ms=elapsed_ms,
                    request_payload=order.raw_provider_request,
                    response_payload=result.raw,
                )
            )

            logger.info(
                "order_created",
                order_id=order_id,
                provider_order_no=result.order_no,
                status=result.status,
            )

            # --- Immediate post-order sync ---
            # Query provider for full eSIM details right after order placement.
            # Safe: if sync fails, order is still persisted in pending state.
            try:
                sync_result = await self._state_syncer.sync_order(order, "post_order_sync")
                logger.info(
                    "post_order_sync_complete",
                    order_id=order_id,
                    state_changed=sync_result.state_changed,
                    esim_count=len(sync_result.esims),
                )
            except Exception as sync_exc:
                logger.warning(
                    "post_order_sync_failed",
                    order_id=order_id,
                    error=str(sync_exc),
                )

        except ProviderError as exc:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            order.status = "failed"
            order.failure_reason = str(exc)

            await self._log_repo.create(
                OperationLog(
                    id=op_log_id,
                    operation="create_order",
                    provider_name=self._provider.provider_name,
                    idempotency_key=idempotency_key,
                    status="failed",
                    duration_ms=elapsed_ms,
                    request_payload=order.raw_provider_request,
                    error_message=str(exc),
                )
            )
            logger.error("order_creation_failed", order_id=order_id, error=str(exc))
            raise

        return order

    async def get_order(self, order_id: str) -> ProviderOrder:
        order = await self._order_repo.get_by_id(order_id)
        if not order:
            raise ResourceNotFoundError(detail=f"Order {order_id} not found")
        return order

    async def refresh_order_status(self, order_id: str) -> SyncResult:
        """Refresh order state from provider using the state syncer."""
        order = await self.get_order(order_id)
        if not order.provider_order_no:
            return SyncResult(order=order)

        return await self._state_syncer.sync_order(order, "manual_refresh")

    async def get_order_esims(self, order_id: str) -> list[Esim]:
        await self.get_order(order_id)
        return await self._esim_repo.get_by_order_id(order_id)

    async def topup_order(
        self,
        order_id: str,
        package_code: str,
        iccid: str,
        idempotency_key: str | None = None,
    ) -> ProviderOrder:
        transaction_id = str(uuid.uuid4())
        topup_order_id = str(uuid.uuid4())

        topup_order = ProviderOrder(
            id=topup_order_id,
            provider_name=self._provider.provider_name,
            transaction_id=transaction_id,
            package_code=package_code,
            quantity=1,
            status="pending",
            iccid=iccid,
            idempotency_key=idempotency_key,
            raw_provider_request={"packageCode": package_code, "iccid": iccid},
        )
        await self._order_repo.create(topup_order)
        await self._session.flush()

        try:
            result = await self._provider.topup_esim(iccid, package_code, transaction_id)
            topup_order.provider_order_no = result.order_no
            topup_order.status = result.status
            topup_order.raw_provider_response = result.raw
        except ProviderError as exc:
            topup_order.status = "failed"
            topup_order.failure_reason = str(exc)
            raise

        return topup_order

    async def cancel_order(self, order_id: str) -> ProviderOrder:
        order = await self.get_order(order_id)
        if not order.provider_order_no:
            raise ResourceNotFoundError(detail="Cannot cancel order without provider order number")

        result = await self._provider.cancel_order(order.provider_order_no)
        order.status = "cancelled"
        order.raw_provider_response = result.raw

        logger.info("order_cancelled", order_id=order_id)
        return order

    async def _create_esim_from_order(self, order: ProviderOrder, iccid: str) -> Esim:
        """Legacy eSIM creation path for providers that return iccid in order response.

        For eSIM Access, the post-order sync handles eSIM creation with richer data.
        This method is retained for backward compatibility.
        """
        existing = await self._esim_repo.get_by_iccid(iccid)
        if existing:
            return existing

        esim_id = str(uuid.uuid4())
        esim = Esim(
            id=esim_id,
            iccid=iccid,
            provider_name=self._provider.provider_name,
            order_id=order.id,
            status="allocated",
        )

        try:
            profile = await self._provider.get_esim(iccid)
            esim.smdp_address = profile.smdp_address
            esim.matching_id = profile.matching_id
            esim.activation_code = profile.activation_code
            esim.status = profile.status or "allocated"
            esim.msisdn = profile.msisdn
            esim.raw_provider_data = profile.raw
        except ProviderError:
            logger.warning("esim_profile_fetch_failed", iccid=iccid, order_id=order.id)

        await self._esim_repo.create(esim)

        history = EsimStatusHistory(
            id=str(uuid.uuid4()),
            esim_id=esim_id,
            iccid=iccid,
            previous_status=None,
            new_status=esim.status,
            source="order_creation",
            recorded_at=esim.created_at,
        )
        await self._esim_repo.add_status_history(history)

        return esim
