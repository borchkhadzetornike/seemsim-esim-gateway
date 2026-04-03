"""Unit tests for the eSIM Access HTTP client with mocked responses.

Tests verify exact endpoint paths and response envelope parsing per
the eSIM Access contract (docs.esimaccess.com).
"""

from __future__ import annotations

import httpx
import pytest
import respx

from app.core.errors import (
    ProviderAuthenticationError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderValidationError,
)
from app.providers.esim_access.auth import EsimAccessAuth
from app.providers.esim_access.client import EsimAccessClient


@pytest.fixture
def auth() -> EsimAccessAuth:
    return EsimAccessAuth(access_code="test", secret_key="secret")


@pytest.fixture
def client(auth: EsimAccessAuth) -> EsimAccessClient:
    return EsimAccessClient(auth=auth, base_url="https://mock-api.test")


ENVELOPE_SUCCESS = {"success": True, "errorCode": "0", "errorMsg": None, "obj": {}}


def success_envelope(obj: dict | list | None = None) -> dict:
    return {"success": True, "errorCode": "0", "errorMsg": None, "obj": obj}


class TestExactEndpointPaths:
    @respx.mock
    @pytest.mark.asyncio
    async def test_package_list_path(self, client: EsimAccessClient) -> None:
        route = respx.post("https://mock-api.test/api/v1/open/package/list").mock(
            return_value=httpx.Response(200, json=success_envelope({"packageList": []}))
        )
        await client.request("/api/v1/open/package/list", {})
        assert route.called

    @respx.mock
    @pytest.mark.asyncio
    async def test_order_path(self, client: EsimAccessClient) -> None:
        route = respx.post("https://mock-api.test/api/v1/open/esim/order").mock(
            return_value=httpx.Response(200, json=success_envelope({"orderNo": "X"}))
        )
        await client.request("/api/v1/open/esim/order", {"transactionId": "t1", "packageInfoList": []})
        assert route.called

    @respx.mock
    @pytest.mark.asyncio
    async def test_query_path(self, client: EsimAccessClient) -> None:
        route = respx.post("https://mock-api.test/api/v1/open/esim/query").mock(
            return_value=httpx.Response(
                200, json=success_envelope({"esimList": [], "pager": {"pageNum": 1, "pageSize": 5, "total": 0}})
            )
        )
        await client.request("/api/v1/open/esim/query", {"pager": {"pageNum": 1, "pageSize": 5}})
        assert route.called

    @respx.mock
    @pytest.mark.asyncio
    async def test_topup_path(self, client: EsimAccessClient) -> None:
        route = respx.post("https://mock-api.test/api/v1/open/esim/topup").mock(
            return_value=httpx.Response(200, json=success_envelope({}))
        )
        await client.request("/api/v1/open/esim/topup", {"iccid": "X", "packageCode": "Y"})
        assert route.called

    @respx.mock
    @pytest.mark.asyncio
    async def test_cancel_path(self, client: EsimAccessClient) -> None:
        route = respx.post("https://mock-api.test/api/v1/open/esim/cancel").mock(
            return_value=httpx.Response(200, json=success_envelope({}))
        )
        await client.request("/api/v1/open/esim/cancel", {"iccid": "X"})
        assert route.called

    @respx.mock
    @pytest.mark.asyncio
    async def test_balance_path(self, client: EsimAccessClient) -> None:
        route = respx.post("https://mock-api.test/api/v1/open/balance/query").mock(
            return_value=httpx.Response(200, json=success_envelope({"balance": 500000}))
        )
        await client.request("/api/v1/open/balance/query", {})
        assert route.called


class TestResponseEnvelopeParsing:
    @respx.mock
    @pytest.mark.asyncio
    async def test_success_true_returns_data(self, client: EsimAccessClient) -> None:
        respx.post("https://mock-api.test/api/v1/open/package/list").mock(
            return_value=httpx.Response(200, json=success_envelope({"packageList": []}))
        )
        result = await client.request("/api/v1/open/package/list", {})
        assert result["success"] is True
        assert result["obj"] == {"packageList": []}

    @respx.mock
    @pytest.mark.asyncio
    async def test_auth_error_code_raises(self, client: EsimAccessClient) -> None:
        respx.post("https://mock-api.test/api/v1/open/package/list").mock(
            return_value=httpx.Response(200, json={
                "success": False, "errorCode": "000101", "errorMsg": "RT-AccessCode is null", "obj": None
            })
        )
        with pytest.raises(ProviderAuthenticationError):
            await client.request("/api/v1/open/package/list", {})

    @respx.mock
    @pytest.mark.asyncio
    async def test_validation_error_code_raises(self, client: EsimAccessClient) -> None:
        respx.post("https://mock-api.test/api/v1/open/esim/order").mock(
            return_value=httpx.Response(200, json={
                "success": False, "errorCode": "000105",
                "errorMsg": "transactionId:must not be blank", "obj": None
            })
        )
        with pytest.raises(ProviderValidationError):
            await client.request("/api/v1/open/esim/order", {})

    @respx.mock
    @pytest.mark.asyncio
    async def test_business_error_3xx_raises_validation(self, client: EsimAccessClient) -> None:
        respx.post("https://mock-api.test/api/v1/open/esim/order").mock(
            return_value=httpx.Response(200, json={
                "success": False, "errorCode": "310241",
                "errorMsg": "base data plan code doesn't exist", "obj": None
            })
        )
        with pytest.raises(ProviderValidationError):
            await client.request("/api/v1/open/esim/order", {})

    @respx.mock
    @pytest.mark.asyncio
    async def test_404_error_code_raises(self, client: EsimAccessClient) -> None:
        respx.post("https://mock-api.test/api/v1/open/bad/path").mock(
            return_value=httpx.Response(200, json={
                "success": False, "errorCode": "404", "errorMsg": "path not found", "obj": None
            })
        )
        with pytest.raises(ProviderValidationError):
            await client.request("/api/v1/open/bad/path", {})


class TestClientErrorHandling:
    @respx.mock
    @pytest.mark.asyncio
    async def test_http_401_raises_auth_error(self, client: EsimAccessClient) -> None:
        respx.post("https://mock-api.test/api/v1/open/package/list").mock(
            return_value=httpx.Response(401, json={})
        )
        with pytest.raises(ProviderAuthenticationError):
            await client.request("/api/v1/open/package/list")

    @respx.mock
    @pytest.mark.asyncio
    async def test_rate_limit_429(self, client: EsimAccessClient) -> None:
        respx.post("https://mock-api.test/api/v1/open/package/list").mock(
            return_value=httpx.Response(429, json={})
        )
        with pytest.raises(ProviderRateLimitError):
            await client.request("/api/v1/open/package/list")

    @respx.mock
    @pytest.mark.asyncio
    async def test_server_error_500(self, client: EsimAccessClient) -> None:
        respx.post("https://mock-api.test/api/v1/open/package/list").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )
        with pytest.raises(ProviderUnavailableError):
            await client.request("/api/v1/open/package/list")

    @respx.mock
    @pytest.mark.asyncio
    async def test_timeout_raises_provider_timeout(self, client: EsimAccessClient) -> None:
        respx.post("https://mock-api.test/api/v1/open/package/list").mock(
            side_effect=httpx.ReadTimeout("timeout")
        )
        with pytest.raises(ProviderTimeoutError):
            await client.request("/api/v1/open/package/list")


class TestClientSendsCorrectHeaders:
    @respx.mock
    @pytest.mark.asyncio
    async def test_sends_rt_auth_headers(self, client: EsimAccessClient) -> None:
        route = respx.post("https://mock-api.test/api/v1/open/package/list").mock(
            return_value=httpx.Response(200, json=success_envelope({"packageList": []}))
        )
        await client.request("/api/v1/open/package/list", {})

        request = route.calls[0].request
        assert "rt-accesscode" in request.headers
        assert "rt-requestid" in request.headers
        assert "rt-timestamp" in request.headers
        assert "rt-signature" in request.headers

    @respx.mock
    @pytest.mark.asyncio
    async def test_does_not_send_yoni_headers(self, client: EsimAccessClient) -> None:
        route = respx.post("https://mock-api.test/api/v1/open/package/list").mock(
            return_value=httpx.Response(200, json=success_envelope({"packageList": []}))
        )
        await client.request("/api/v1/open/package/list")
        request = route.calls[0].request
        assert "appid" not in request.headers
        assert "sign" not in request.headers
