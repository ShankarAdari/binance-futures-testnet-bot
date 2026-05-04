"""
client.py
=========
Low-level Binance Futures Testnet REST API wrapper.

Responsibilities
----------------
* HMAC-SHA256 request signing
* Timestamp + recvWindow injection
* HTTP request execution with retry and error handling
* Raw response parsing + normalisation
* Structured logging of every request/response cycle

Testnet base URL: https://testnet.binancefuture.com
"""

from __future__ import annotations

import hashlib
import hmac
import time
from decimal import Decimal
from typing import Any, Optional
from urllib.parse import urlencode

import httpx

from .exceptions import APIError, AuthenticationError, RateLimitError, NetworkError, MaxRetriesExceeded
from .logging_config import get_logger

log = get_logger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────
BASE_URL = "https://testnet.binancefuture.com"
RECV_WINDOW = 5_000        # ms — how long server accepts the request
DEFAULT_TIMEOUT = 15.0     # seconds
MAX_RETRIES = 3
RETRY_BACKOFF = 1.5        # seconds between retries


# BinanceAPIError kept as alias for backwards compatibility
BinanceAPIError = APIError


class BinanceFuturesClient:
    """
    Authenticated HTTP client for the Binance USDT-M Futures Testnet.

    Parameters
    ----------
    api_key    : Testnet API key
    api_secret : Testnet API secret
    timeout    : Per-request timeout in seconds
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        if not api_key or not api_secret:
            raise ValueError("Both api_key and api_secret must be non-empty strings.")
        self._api_key = api_key
        self._api_secret = api_secret.encode()        # bytes for HMAC
        self._timeout = timeout
        self._session = httpx.Client(
            base_url=BASE_URL,
            headers={
                "X-MBX-APIKEY": api_key,
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "BinanceFuturesBot/1.0",
            },
            timeout=timeout,
        )
        log.info("BinanceFuturesClient initialised — endpoint: %s", BASE_URL)

    # ── Private helpers ────────────────────────────────────────────────────────

    def _sign(self, params: dict) -> dict:
        """Inject timestamp + recvWindow and append HMAC-SHA256 signature."""
        params["timestamp"] = int(time.time() * 1000)
        params["recvWindow"] = RECV_WINDOW
        query_string = urlencode(params)
        signature = hmac.new(
            self._api_secret,
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature
        return params

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[dict] = None,
        signed: bool = False,
    ) -> Any:
        """
        Execute an HTTP request with optional signing and retry logic.

        Parameters
        ----------
        method : "GET", "POST", "DELETE"
        path   : API path, e.g. "/fapi/v1/order"
        params : Query / body parameters
        signed : Whether to inject timestamp + signature

        Returns
        -------
        Parsed JSON response (dict or list)

        Raises
        ------
        BinanceAPIError — for API-level errors
        httpx.RequestError — for network failures
        """
        params = params or {}
        if signed:
            params = self._sign(params)

        log.debug("→ %s %s  params=%s", method.upper(), path, self._redact(params))

        last_exc: Exception | None = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                if method.upper() == "GET":
                    response = self._session.get(path, params=params)
                elif method.upper() == "POST":
                    response = self._session.post(path, data=params)
                elif method.upper() == "DELETE":
                    response = self._session.delete(path, params=params)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method!r}")

                log.debug(
                    "← %s %s  status=%s  body=%s",
                    method.upper(), path, response.status_code, response.text[:800],
                )

                data = response.json()

                # Binance returns errors as {"code": <int<0>, "msg": "..."}
                if isinstance(data, dict) and data.get("code", 0) < 0:
                    bcode = data["code"]
                    msg = data.get("msg", "Unknown error")
                    sc = response.status_code
                    if sc in (401, 403) or bcode in (-2014, -2015, -1022):
                        raise AuthenticationError(
                            msg, status_code=sc, binance_code=bcode
                        )
                    if sc in (429, 418):
                        raise RateLimitError(
                            msg, status_code=sc, binance_code=bcode
                        )
                    raise APIError(
                        msg, status_code=sc, binance_code=bcode
                    )

                if response.status_code in (401, 403):
                    raise AuthenticationError(
                        "Authentication failed", status_code=response.status_code
                    )
                if response.status_code in (429, 418):
                    raise RateLimitError(
                        "Rate limit hit", status_code=response.status_code
                    )
                response.raise_for_status()
                return data

            except (APIError, AuthenticationError, RateLimitError):
                raise   # never retry business-logic errors

            except (httpx.TimeoutException, httpx.ConnectError) as exc:
                last_exc = exc
                log.warning(
                    "Network error on attempt %d/%d: %s", attempt, MAX_RETRIES, exc
                )
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_BACKOFF * attempt)

            except httpx.HTTPStatusError as exc:
                sc = exc.response.status_code
                raise APIError(
                    exc.response.text,
                    status_code=sc,
                ) from exc

        raise MaxRetriesExceeded(
            f"All {MAX_RETRIES} attempts failed."
        ) from last_exc

    @staticmethod
    def _redact(params: dict) -> dict:
        """Remove sensitive fields before logging."""
        safe = dict(params)
        for key in ("signature",):
            if key in safe:
                safe[key] = "***"
        return safe

    # ── Public API methods ─────────────────────────────────────────────────────

    def get_exchange_info(self) -> dict:
        """Fetch exchange trading rules and symbol information."""
        log.info("Fetching exchange info...")
        return self._request("GET", "/fapi/v1/exchangeInfo")

    def get_account_info(self) -> dict:
        """Fetch account balance and positions."""
        log.info("Fetching account info...")
        return self._request("GET", "/fapi/v2/account", signed=True)

    def get_symbol_price(self, symbol: str) -> dict:
        """Get the latest mark/last price for a symbol."""
        log.info("Fetching price for %s", symbol)
        return self._request("GET", "/fapi/v1/ticker/price", params={"symbol": symbol})

    def get_price(self, symbol: str) -> float:
        """
        Convenience method — returns the current price as a plain float.

        Raises APIError if symbol is invalid.
        """
        data = self.get_symbol_price(symbol)
        return float(data["price"])

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: Decimal,
        price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None,
        time_in_force: Optional[str] = None,
        reduce_only: bool = False,
    ) -> dict:
        """
        Submit a new futures order to Binance.

        Parameters map directly to the POST /fapi/v1/order endpoint.
        All numeric values are forwarded as strings to avoid float precision
        issues.
        """
        params: dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": str(quantity),
        }

        if price is not None:
            params["price"] = str(price)

        if stop_price is not None:
            params["stopPrice"] = str(stop_price)

        if time_in_force is not None:
            params["timeInForce"] = time_in_force

        if reduce_only:
            params["reduceOnly"] = "true"

        log.info(
            "Placing %s %s order on %s — qty=%s price=%s",
            side, order_type, symbol, quantity, price,
        )

        response = self._request("POST", "/fapi/v1/order", params=params, signed=True)

        log.info(
            "Order accepted — orderId=%s status=%s",
            response.get("orderId"),
            response.get("status"),
        )
        return response

    def cancel_order(self, symbol: str, order_id: int) -> dict:
        """Cancel an open order."""
        log.info("Cancelling order %s on %s", order_id, symbol)
        return self._request(
            "DELETE",
            "/fapi/v1/order",
            params={"symbol": symbol, "orderId": order_id},
            signed=True,
        )

    def get_open_orders(self, symbol: Optional[str] = None) -> list:
        """List open orders, optionally filtered by symbol."""
        params = {}
        if symbol:
            params["symbol"] = symbol
        log.info("Fetching open orders%s", f" for {symbol}" if symbol else "")
        return self._request("GET", "/fapi/v1/openOrders", params=params, signed=True)

    def get_order(self, symbol: str, order_id: int) -> dict:
        """Query a specific order by ID."""
        log.info("Querying order %s on %s", order_id, symbol)
        return self._request(
            "GET",
            "/fapi/v1/order",
            params={"symbol": symbol, "orderId": order_id},
            signed=True,
        )

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self._session.close()
        log.debug("HTTP session closed.")

    # ── Context manager support ────────────────────────────────────────────────
    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
