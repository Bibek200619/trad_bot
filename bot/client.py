"""HTTP client wrapper for Binance Futures Testnet."""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from decimal import Decimal
from typing import Any
from urllib.parse import urlencode

import httpx

from .exceptions import BinanceAPIError, BinanceNetworkError, ValidationError

DEFAULT_BASE_URL = "https://testnet.binancefuture.com"
SIGNED_ENDPOINT_RECV_WINDOW_MS = 5_000
_REDACTED_REQUEST_FIELDS = {"signature"}


class BinanceFuturesClient:
    """Minimal signed REST client for Binance Futures Testnet."""

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 10.0,
    ) -> None:
        self.api_key = api_key
        self.api_secret = api_secret.encode("utf-8")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
        self._session = httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={"X-MBX-APIKEY": self.api_key},
        )
        self._time_offset_ms = 0
        self._time_synced = False
        self._exchange_info: dict[str, Any] | None = None

    def __enter__(self) -> "BinanceFuturesClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self._session.close()

    def sync_time(self) -> None:
        payload = self._request("GET", "/fapi/v1/time")
        server_time_ms = int(payload["serverTime"])
        local_time_ms = int(time.time() * 1000)
        self._time_offset_ms = server_time_ms - local_time_ms
        self._time_synced = True
        self.logger.info(
            "binance_time_synced",
            extra={
                "event": "binance_time_synced",
                "server_time_ms": server_time_ms,
                "offset_ms": self._time_offset_ms,
            },
        )

    def get_exchange_info(self, *, refresh: bool = False) -> dict[str, Any]:
        if self._exchange_info is None or refresh:
            self._exchange_info = self._request("GET", "/fapi/v1/exchangeInfo")
        return self._exchange_info

    def get_symbol_info(self, symbol: str) -> dict[str, Any]:
        exchange_info = self.get_exchange_info()
        for symbol_info in exchange_info.get("symbols", []):
            if symbol_info.get("symbol") == symbol:
                return symbol_info
        raise ValidationError(f"Unsupported or unknown symbol: {symbol}")

    def get_latest_price(self, symbol: str) -> Decimal:
        payload = self._request("GET", "/fapi/v1/ticker/price", params={"symbol": symbol})
        return Decimal(payload["price"])

    def place_order(self, params: dict[str, str]) -> dict[str, Any]:
        if not self._time_synced:
            self.sync_time()
        return self._request("POST", "/fapi/v1/order", params=params, signed=True)

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        signed: bool = False,
    ) -> dict[str, Any]:
        payload = dict(params or {})
        if signed:
            payload["timestamp"] = self._timestamp_ms()
            payload["recvWindow"] = SIGNED_ENDPOINT_RECV_WINDOW_MS
            payload["signature"] = self._sign(payload)

        sanitized_payload = self._sanitize_params(payload)
        self.logger.info(
            "binance_request",
            extra={
                "event": "binance_request",
                "method": method,
                "path": path,
                "params": sanitized_payload,
                "signed": signed,
            },
        )

        request_kwargs: dict[str, Any]
        if method.upper() == "GET":
            request_kwargs = {"params": payload}
        else:
            request_kwargs = {"data": payload}

        try:
            response = self._session.request(method, path, **request_kwargs)
        except httpx.RequestError as exc:
            self.logger.error(
                "binance_network_error",
                extra={
                    "event": "binance_network_error",
                    "method": method,
                    "path": path,
                    "error": str(exc),
                },
            )
            raise BinanceNetworkError(f"Network error while calling Binance: {exc}") from exc

        data = self._parse_response(response)
        self.logger.info(
            "binance_response",
            extra={
                "event": "binance_response",
                "method": method,
                "path": path,
                "status_code": response.status_code,
                "response": self._response_preview(data),
            },
        )

        if response.is_error:
            error_code = data.get("code") if isinstance(data, dict) else None
            error_message = data.get("msg") if isinstance(data, dict) else response.text
            raise BinanceAPIError(
                error_message or "Binance API request failed",
                status_code=response.status_code,
                error_code=error_code,
            )

        if not isinstance(data, dict):
            raise BinanceAPIError(
                "Unexpected non-JSON response from Binance",
                status_code=response.status_code,
            )

        return data

    def _timestamp_ms(self) -> int:
        return int(time.time() * 1000) + self._time_offset_ms

    def _sign(self, params: dict[str, Any]) -> str:
        query_string = urlencode(params, doseq=True)
        return hmac.new(
            self.api_secret,
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _sanitize_params(self, params: dict[str, Any]) -> dict[str, Any]:
        return {
            key: ("<redacted>" if key in _REDACTED_REQUEST_FIELDS else value)
            for key, value in params.items()
        }

    def _parse_response(self, response: httpx.Response) -> dict[str, Any] | str:
        try:
            return response.json()
        except ValueError:
            return response.text

    def _response_preview(self, data: dict[str, Any] | str) -> dict[str, Any] | str:
        if not isinstance(data, dict):
            return data

        if "symbols" in data and isinstance(data["symbols"], list):
            return {
                "timezone": data.get("timezone"),
                "symbols_count": len(data["symbols"]),
            }

        return data
