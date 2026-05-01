"""
orders.py
=========
High-level order management layer.

Sits between the CLI and the raw API client:
  CLI → OrderManager → BinanceFuturesClient → Binance API

Responsibilities
----------------
* Coordinate validation (via OrderValidator) with API calls (via BinanceFuturesClient)
* Parse and enrich API responses into normalised OrderResult objects
* Format human-readable order summaries for the CLI layer
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Optional

from .client import BinanceFuturesClient, BinanceAPIError
from .validators import OrderValidator
from .logging_config import get_logger

log = get_logger(__name__)


# ── Data Transfer Object ───────────────────────────────────────────────────────

@dataclass
class OrderResult:
    """Normalised representation of a placed order response."""

    order_id: int
    client_order_id: str
    symbol: str
    side: str
    order_type: str
    status: str
    quantity: Decimal
    executed_qty: Decimal
    avg_price: Decimal
    price: Decimal              # limit price (0 for MARKET)
    stop_price: Decimal
    time_in_force: Optional[str]
    raw: dict = field(repr=False)   # original API payload

    @classmethod
    def from_api_response(cls, data: dict) -> "OrderResult":
        """Build an OrderResult from a raw Binance API order response dict."""
        def _dec(key: str, default: str = "0") -> Decimal:
            return Decimal(str(data.get(key) or default))

        return cls(
            order_id=int(data.get("orderId", 0)),
            client_order_id=data.get("clientOrderId", ""),
            symbol=data.get("symbol", ""),
            side=data.get("side", ""),
            order_type=data.get("type", ""),
            status=data.get("status", ""),
            quantity=_dec("origQty"),
            executed_qty=_dec("executedQty"),
            avg_price=_dec("avgPrice"),
            price=_dec("price"),
            stop_price=_dec("stopPrice"),
            time_in_force=data.get("timeInForce"),
            raw=data,
        )

    def is_filled(self) -> bool:
        return self.status == "FILLED"

    def fill_percent(self) -> Decimal:
        if self.quantity == 0:
            return Decimal("0")
        return (self.executed_qty / self.quantity * 100).quantize(Decimal("0.01"))


# ── Order Manager ──────────────────────────────────────────────────────────────

class OrderManager:
    """
    High-level order placement and management facade.

    Parameters
    ----------
    client    : Authenticated BinanceFuturesClient instance
    validator : OrderValidator instance (defaults to a new instance)
    """

    def __init__(
        self,
        client: BinanceFuturesClient,
        validator: Optional[OrderValidator] = None,
    ) -> None:
        self._client = client
        self._validator = validator or OrderValidator()

    # ── Core order placement ───────────────────────────────────────────────────

    def place_market_order(
        self,
        symbol: str,
        side: str,
        quantity: str | float | Decimal,
        reduce_only: bool = False,
    ) -> OrderResult:
        """
        Place a MARKET order.

        Parameters
        ----------
        symbol      : e.g. "BTCUSDT"
        side        : "BUY" or "SELL"
        quantity    : Number of contracts / coins
        reduce_only : If True, closes existing position only

        Returns
        -------
        OrderResult

        Raises
        ------
        ValueError     on invalid input
        BinanceAPIError on API failures
        """
        log.info("Preparing MARKET %s order: symbol=%s qty=%s", side, symbol, quantity)

        params = self._validator.validate(
            symbol=symbol,
            side=side,
            order_type="MARKET",
            quantity=quantity,
            reduce_only=reduce_only,
        )

        response = self._client.place_order(
            symbol=params["symbol"],
            side=params["side"],
            order_type="MARKET",
            quantity=params["quantity"],
            reduce_only=params["reduce_only"],
        )

        result = OrderResult.from_api_response(response)
        log.info(
            "MARKET order placed ✓  orderId=%s  status=%s  executedQty=%s  avgPrice=%s",
            result.order_id, result.status, result.executed_qty, result.avg_price,
        )
        return result

    def place_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: str | float | Decimal,
        price: str | float | Decimal,
        time_in_force: str = "GTC",
        reduce_only: bool = False,
    ) -> OrderResult:
        """
        Place a LIMIT order.

        Parameters
        ----------
        symbol        : e.g. "BTCUSDT"
        side          : "BUY" or "SELL"
        quantity      : Number of contracts / coins
        price         : Limit price
        time_in_force : "GTC" (default), "IOC", "FOK", "GTX"
        reduce_only   : If True, closes existing position only

        Returns
        -------
        OrderResult

        Raises
        ------
        ValueError     on invalid input
        BinanceAPIError on API failures
        """
        log.info(
            "Preparing LIMIT %s order: symbol=%s qty=%s price=%s tif=%s",
            side, symbol, quantity, price, time_in_force,
        )

        params = self._validator.validate(
            symbol=symbol,
            side=side,
            order_type="LIMIT",
            quantity=quantity,
            price=price,
            time_in_force=time_in_force,
            reduce_only=reduce_only,
        )

        response = self._client.place_order(
            symbol=params["symbol"],
            side=params["side"],
            order_type="LIMIT",
            quantity=params["quantity"],
            price=params["price"],
            time_in_force=params["time_in_force"],
            reduce_only=params["reduce_only"],
        )

        result = OrderResult.from_api_response(response)
        log.info(
            "LIMIT order placed ✓  orderId=%s  status=%s  price=%s  qty=%s",
            result.order_id, result.status, result.price, result.quantity,
        )
        return result

    def place_stop_market_order(
        self,
        symbol: str,
        side: str,
        quantity: str | float | Decimal,
        stop_price: str | float | Decimal,
        reduce_only: bool = False,
    ) -> OrderResult:
        """
        Place a STOP_MARKET order (stop-loss / trailing stop).

        Parameters
        ----------
        stop_price : When the market reaches this price, a MARKET order fires
        """
        log.info(
            "Preparing STOP_MARKET %s order: symbol=%s qty=%s stop=%s",
            side, symbol, quantity, stop_price,
        )

        params = self._validator.validate(
            symbol=symbol,
            side=side,
            order_type="STOP_MARKET",
            quantity=quantity,
            stop_price=stop_price,
            reduce_only=reduce_only,
        )

        response = self._client.place_order(
            symbol=params["symbol"],
            side=params["side"],
            order_type="STOP_MARKET",
            quantity=params["quantity"],
            stop_price=params["stop_price"],
            reduce_only=params["reduce_only"],
        )

        result = OrderResult.from_api_response(response)
        log.info(
            "STOP_MARKET order placed ✓  orderId=%s  status=%s  stopPrice=%s",
            result.order_id, result.status, result.stop_price,
        )
        return result

    def place_stop_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: str | float | Decimal,
        price: str | float | Decimal,
        stop_price: str | float | Decimal,
        time_in_force: str = "GTC",
        reduce_only: bool = False,
    ) -> OrderResult:
        """
        Place a STOP_LIMIT order (bonus feature).

        When the market hits *stop_price*, a LIMIT order at *price* is placed.
        """
        log.info(
            "Preparing STOP_LIMIT %s order: symbol=%s qty=%s price=%s stop=%s",
            side, symbol, quantity, price, stop_price,
        )

        params = self._validator.validate(
            symbol=symbol,
            side=side,
            order_type="STOP_LIMIT",
            quantity=quantity,
            price=price,
            stop_price=stop_price,
            time_in_force=time_in_force,
            reduce_only=reduce_only,
        )

        response = self._client.place_order(
            symbol=params["symbol"],
            side=params["side"],
            order_type="STOP_LIMIT",
            quantity=params["quantity"],
            price=params["price"],
            stop_price=params["stop_price"],
            time_in_force=params["time_in_force"],
            reduce_only=params["reduce_only"],
        )

        result = OrderResult.from_api_response(response)
        log.info(
            "STOP_LIMIT order placed ✓  orderId=%s  status=%s  price=%s  stopPrice=%s",
            result.order_id, result.status, result.price, result.stop_price,
        )
        return result

    # ── Query helpers ──────────────────────────────────────────────────────────

    def get_open_orders(self, symbol: Optional[str] = None) -> list[OrderResult]:
        """Return all open orders as OrderResult objects."""
        raw_orders = self._client.get_open_orders(symbol)
        return [OrderResult.from_api_response(o) for o in raw_orders]

    def cancel_order(self, symbol: str, order_id: int) -> dict:
        """Cancel an open order and return the raw API response."""
        return self._client.cancel_order(symbol, order_id)

    def get_symbol_price(self, symbol: str) -> Decimal:
        """Return the current market price for a symbol as Decimal."""
        resp = self._client.get_symbol_price(symbol)
        return Decimal(str(resp.get("price", "0")))

    # ── Formatting ─────────────────────────────────────────────────────────────

    @staticmethod
    def format_result(result: OrderResult) -> dict[str, Any]:
        """Return a display-friendly dict of the most important order fields."""
        return {
            "Order ID": result.order_id,
            "Client Order ID": result.client_order_id,
            "Symbol": result.symbol,
            "Side": result.side,
            "Type": result.order_type,
            "Status": result.status,
            "Quantity": str(result.quantity),
            "Executed Qty": str(result.executed_qty),
            "Avg Fill Price": str(result.avg_price),
            "Limit Price": str(result.price) if result.price > 0 else "N/A",
            "Stop Price": str(result.stop_price) if result.stop_price > 0 else "N/A",
            "Time In Force": result.time_in_force or "N/A",
            "Fill %": str(result.fill_percent()),
        }
