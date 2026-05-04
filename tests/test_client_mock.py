"""
tests/test_client_mock.py
=========================
Unit tests for bot.client.BinanceFuturesClient using mocked HTTP responses.

All tests use unittest.mock to intercept httpx calls — no real network
traffic is made.
"""

import json
import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch, PropertyMock

from bot.client import BinanceFuturesClient
from bot.exceptions import APIError, AuthenticationError, RateLimitError


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    """Client with fake credentials (no real API calls)."""
    return BinanceFuturesClient(
        api_key="test_api_key_abc123",
        api_secret="test_api_secret_xyz789",
    )


def _make_response(status_code: int, body: dict) -> MagicMock:
    """Build a mock httpx.Response."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = body
    mock_resp.text = json.dumps(body)
    return mock_resp


# ── Market Order Mock ──────────────────────────────────────────────────────────

class TestPlaceMarketOrder:
    MARKET_RESPONSE = {
        "orderId": 111222333,
        "symbol": "BTCUSDT",
        "status": "FILLED",
        "clientOrderId": "mock_client_id",
        "price": "0",
        "avgPrice": "60000.50",
        "origQty": "0.001",
        "executedQty": "0.001",
        "type": "MARKET",
        "side": "BUY",
        "time": 1714550000000,
    }

    def test_market_buy_success(self, client):
        with patch.object(client._session, "post", return_value=_make_response(200, self.MARKET_RESPONSE)):
            result = client.place_order(
                symbol="BTCUSDT",
                side="BUY",
                order_type="MARKET",
                quantity=Decimal("0.001"),
            )
        assert result["orderId"] == 111222333
        assert result["status"] == "FILLED"
        assert result["symbol"] == "BTCUSDT"

    def test_market_sell_success(self, client):
        sell_response = {**self.MARKET_RESPONSE, "side": "SELL", "orderId": 444555666}
        with patch.object(client._session, "post", return_value=_make_response(200, sell_response)):
            result = client.place_order(
                symbol="BTCUSDT",
                side="SELL",
                order_type="MARKET",
                quantity=Decimal("0.001"),
            )
        assert result["side"] == "SELL"


# ── Limit Order Mock ───────────────────────────────────────────────────────────

class TestPlaceLimitOrder:
    LIMIT_RESPONSE = {
        "orderId": 999888777,
        "symbol": "ETHUSDT",
        "status": "NEW",
        "price": "3500.00",
        "avgPrice": "0",
        "origQty": "0.1",
        "executedQty": "0",
        "type": "LIMIT",
        "side": "BUY",
        "time": 1714550100000,
    }

    def test_limit_buy_success(self, client):
        with patch.object(client._session, "post", return_value=_make_response(200, self.LIMIT_RESPONSE)):
            result = client.place_order(
                symbol="ETHUSDT",
                side="BUY",
                order_type="LIMIT",
                quantity=Decimal("0.1"),
                price=Decimal("3500.00"),
            )
        assert result["status"] == "NEW"
        assert result["price"] == "3500.00"

    def test_limit_order_response_has_order_id(self, client):
        with patch.object(client._session, "post", return_value=_make_response(200, self.LIMIT_RESPONSE)):
            result = client.place_order(
                symbol="ETHUSDT", side="BUY", order_type="LIMIT",
                quantity=Decimal("0.1"), price=Decimal("3500.00"),
            )
        assert "orderId" in result


# ── Error Handling Mocks ───────────────────────────────────────────────────────

class TestAPIErrorHandling:
    def test_invalid_api_key_raises_authentication_error(self, client):
        error_body = {"code": -2014, "msg": "API-key format invalid."}
        with patch.object(client._session, "post", return_value=_make_response(401, error_body)):
            with pytest.raises((AuthenticationError, APIError)):
                client.place_order("BTCUSDT", "BUY", "MARKET", Decimal("0.001"))

    def test_rate_limit_raises_rate_limit_error(self, client):
        error_body = {"code": -1003, "msg": "Too many requests."}
        with patch.object(client._session, "post", return_value=_make_response(429, error_body)):
            with pytest.raises((RateLimitError, APIError)):
                client.place_order("BTCUSDT", "BUY", "MARKET", Decimal("0.001"))

    def test_binance_error_code_raises_api_error(self, client):
        error_body = {"code": -1121, "msg": "Invalid symbol."}
        with patch.object(client._session, "post", return_value=_make_response(400, error_body)):
            with pytest.raises(APIError):
                client.place_order("INVALID", "BUY", "MARKET", Decimal("0.001"))

    def test_api_error_contains_binance_code(self, client):
        error_body = {"code": -1121, "msg": "Invalid symbol."}
        with patch.object(client._session, "post", return_value=_make_response(400, error_body)):
            with pytest.raises(APIError) as exc_info:
                client.place_order("INVALID", "BUY", "MARKET", Decimal("0.001"))
            assert exc_info.value.binance_code == -1121


# ── Price Endpoint Mock ────────────────────────────────────────────────────────

class TestGetPrice:
    def test_get_price_returns_float(self, client):
        price_response = {"symbol": "BTCUSDT", "price": "63000.50"}
        with patch.object(client._session, "get", return_value=_make_response(200, price_response)):
            price = client.get_price("BTCUSDT")
        assert isinstance(price, float)
        assert price == pytest.approx(63000.50)

    def test_get_price_invalid_symbol_raises(self, client):
        error_body = {"code": -1121, "msg": "Invalid symbol."}
        with patch.object(client._session, "get", return_value=_make_response(400, error_body)):
            with pytest.raises(APIError):
                client.get_price("INVALID")
