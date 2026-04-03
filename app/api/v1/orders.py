from __future__ import annotations

from fastapi import APIRouter, Header, Request, Response

from app.api.deps import IdempotencyDep, OrderServiceDep
from app.core.auth import (
    RequireCancelCreate,
    RequireOrdersCreate,
    RequireOrdersRead,
    RequireOrdersRefresh,
    RequireTopupCreate,
)
from app.core.idempotency import IdempotencyStatus, compute_request_fingerprint
from app.schemas.common import ApiResponse
from app.schemas.order import (
    CancelOrderResponse,
    CreateOrderRequest,
    EsimDetailOut,
    OrderDetailOut,
    OrderOut,
    OrderRefreshResponse,
    TopupRequest,
    TopupResponse,
)

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post(
    "",
    response_model=ApiResponse[OrderOut],
    status_code=201,
    summary="Create a new eSIM order",
    description=(
        "Places an order with the provider for the specified package. "
        "Supports idempotency via the Idempotency-Key header."
    ),
)
async def create_order(
    body: CreateOrderRequest,
    request: Request,
    service: OrderServiceDep,
    idempotency: IdempotencyDep,
    _caller: RequireOrdersCreate,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
) -> Response:
    if idempotency_key:
        raw_body = await request.body()
        fingerprint = compute_request_fingerprint("POST", "/v1/orders", raw_body)

        existing = await idempotency.check_or_lock(idempotency_key, fingerprint)
        if existing and existing.status == IdempotencyStatus.COMPLETED:
            return Response(
                content=existing.response_body,
                status_code=existing.status_code or 201,
                media_type="application/json",
            )

    try:
        order = await service.create_order(
            package_code=body.package_code,
            quantity=body.quantity,
            idempotency_key=idempotency_key,
        )

        response_data = ApiResponse(data=OrderOut.model_validate(order))
        response_json = response_data.model_dump_json()

        if idempotency_key:
            await idempotency.complete(
                idempotency_key,
                status_code=201,
                response_body=response_json,
                request_fingerprint=fingerprint,  # type: ignore[possibly-undefined]
            )

        return Response(content=response_json, status_code=201, media_type="application/json")

    except Exception:
        if idempotency_key:
            await idempotency.release(idempotency_key)
        raise


@router.get(
    "/{order_id}",
    response_model=ApiResponse[OrderOut],
    summary="Get order details",
)
async def get_order(order_id: str, service: OrderServiceDep, _caller: RequireOrdersRead) -> ApiResponse[OrderOut]:
    order = await service.get_order(order_id)
    return ApiResponse(data=OrderOut.model_validate(order))


@router.post(
    "/{order_id}/refresh",
    response_model=ApiResponse[OrderRefreshResponse],
    summary="Refresh order status from provider",
    description=(
        "Queries the eSIM Access provider for the latest order and eSIM state, "
        "merges it into the internal record, and returns the updated details."
    ),
)
async def refresh_order(
    order_id: str,
    service: OrderServiceDep,
    _caller: RequireOrdersRefresh,
) -> ApiResponse[OrderRefreshResponse]:
    sync_result = await service.refresh_order_status(order_id)

    esim_details = [EsimDetailOut.model_validate(e) for e in sync_result.esims]

    order_detail = OrderDetailOut(
        **OrderOut.model_validate(sync_result.order).model_dump(),
        esims=esim_details,
    )

    return ApiResponse(
        data=OrderRefreshResponse(
            order=order_detail,
            state_changed=sync_result.state_changed,
            source="manual_refresh",
        )
    )


@router.get(
    "/{order_id}/esims",
    response_model=ApiResponse[list[EsimDetailOut]],
    summary="Get eSIMs associated with an order",
)
async def get_order_esims(
    order_id: str,
    service: OrderServiceDep,
    _caller: RequireOrdersRead,
) -> ApiResponse[list[EsimDetailOut]]:
    esims = await service.get_order_esims(order_id)
    return ApiResponse(data=[EsimDetailOut.model_validate(e) for e in esims])


@router.post(
    "/{order_id}/topup",
    response_model=ApiResponse[TopupResponse],
    summary="Top up an existing eSIM",
    description="Applies a top-up package to an eSIM associated with the given order.",
)
async def topup_order(
    order_id: str,
    body: TopupRequest,
    request: Request,
    service: OrderServiceDep,
    idempotency: IdempotencyDep,
    _caller: RequireTopupCreate,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
) -> Response:
    if idempotency_key:
        raw_body = await request.body()
        fingerprint = compute_request_fingerprint("POST", f"/v1/orders/{order_id}/topup", raw_body)
        existing = await idempotency.check_or_lock(idempotency_key, fingerprint)
        if existing and existing.status == IdempotencyStatus.COMPLETED:
            return Response(
                content=existing.response_body,
                status_code=existing.status_code or 200,
                media_type="application/json",
            )

    try:
        topup_order_result = await service.topup_order(
            order_id=order_id,
            package_code=body.package_code,
            iccid=body.iccid,
            idempotency_key=idempotency_key,
        )

        response_data = ApiResponse(
            data=TopupResponse(
                order_id=topup_order_result.id,
                iccid=body.iccid,
                package_code=body.package_code,
                status=topup_order_result.status,
            )
        )
        response_json = response_data.model_dump_json()

        if idempotency_key:
            await idempotency.complete(
                idempotency_key,
                status_code=200,
                response_body=response_json,
                request_fingerprint=fingerprint,  # type: ignore[possibly-undefined]
            )

        return Response(content=response_json, status_code=200, media_type="application/json")
    except Exception:
        if idempotency_key:
            await idempotency.release(idempotency_key)
        raise


@router.post(
    "/{order_id}/cancel",
    response_model=ApiResponse[CancelOrderResponse],
    summary="Cancel an order",
)
async def cancel_order(
    order_id: str,
    request: Request,
    service: OrderServiceDep,
    idempotency: IdempotencyDep,
    _caller: RequireCancelCreate,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
) -> Response:
    if idempotency_key:
        raw_body = await request.body()
        fingerprint = compute_request_fingerprint("POST", f"/v1/orders/{order_id}/cancel", raw_body)
        existing = await idempotency.check_or_lock(idempotency_key, fingerprint)
        if existing and existing.status == IdempotencyStatus.COMPLETED:
            return Response(
                content=existing.response_body,
                status_code=existing.status_code or 200,
                media_type="application/json",
            )

    try:
        order = await service.cancel_order(order_id)
        response_data = ApiResponse(
            data=CancelOrderResponse(
                order_id=order.id,
                status=order.status,
                message="Order cancelled successfully",
            )
        )
        response_json = response_data.model_dump_json()

        if idempotency_key:
            await idempotency.complete(
                idempotency_key,
                status_code=200,
                response_body=response_json,
                request_fingerprint=fingerprint,  # type: ignore[possibly-undefined]
            )

        return Response(content=response_json, status_code=200, media_type="application/json")
    except Exception:
        if idempotency_key:
            await idempotency.release(idempotency_key)
        raise
