"""
tests/test_validators.py
========================
Unit tests for bot.validators.OrderValidator

Covers all validation paths: valid inputs, invalid symbols, bad quantities,
missing prices, wrong enums, and edge cases with Decimal precision.
"""

import pytest
from decimal import Decimal

from bot.validators import OrderValidator


@pytest.fixture
def validator():
    return OrderValidator()


# ── Symbol validation ──────────────────────────────────────────────────────────

class TestSymbolValidation:
    def test_valid_symbol_uppercased(self, validator):
        result = validator.validate(
            symbol="btcusdt", side="BUY", order_type="MARKET", quantity="0.001"
        )
        assert result["symbol"] == "BTCUSDT"

    def test_valid_symbol_already_upper(self, validator):
        result = validator.validate(
            symbol="ETHUSDT", side="BUY", order_type="MARKET", quantity="0.01"
        )
        assert result["symbol"] == "ETHUSDT"

    def test_empty_symbol_raises(self, validator):
        with pytest.raises(ValueError, match="[Ss]ymbol"):
            validator.validate(symbol="", side="BUY", order_type="MARKET", quantity="0.001")

    def test_whitespace_symbol_raises(self, validator):
        with pytest.raises(ValueError):
            validator.validate(symbol="   ", side="BUY", order_type="MARKET", quantity="0.001")

    def test_symbol_with_spaces_raises(self, validator):
        with pytest.raises(ValueError):
            validator.validate(symbol="BTC USDT", side="BUY", order_type="MARKET", quantity="0.001")


# ── Side validation ────────────────────────────────────────────────────────────

class TestSideValidation:
    def test_buy_side(self, validator):
        result = validator.validate(symbol="BTCUSDT", side="BUY", order_type="MARKET", quantity="0.001")
        assert result["side"] == "BUY"

    def test_sell_side(self, validator):
        result = validator.validate(symbol="BTCUSDT", side="SELL", order_type="MARKET", quantity="0.001")
        assert result["side"] == "SELL"

    def test_lowercase_side_normalised(self, validator):
        result = validator.validate(symbol="BTCUSDT", side="buy", order_type="MARKET", quantity="0.001")
        assert result["side"] == "BUY"

    def test_invalid_side_raises(self, validator):
        with pytest.raises(ValueError, match="[Ss]ide|BUY|SELL"):
            validator.validate(symbol="BTCUSDT", side="LONG", order_type="MARKET", quantity="0.001")

    def test_empty_side_raises(self, validator):
        with pytest.raises(ValueError):
            validator.validate(symbol="BTCUSDT", side="", order_type="MARKET", quantity="0.001")


# ── Order type validation ──────────────────────────────────────────────────────

class TestOrderTypeValidation:
    def test_market_type(self, validator):
        result = validator.validate(symbol="BTCUSDT", side="BUY", order_type="MARKET", quantity="0.001")
        assert result["order_type"] == "MARKET"

    def test_limit_type(self, validator):
        result = validator.validate(
            symbol="BTCUSDT", side="BUY", order_type="LIMIT",
            quantity="0.001", price="60000"
        )
        assert result["order_type"] == "LIMIT"

    def test_stop_market_type(self, validator):
        result = validator.validate(
            symbol="BTCUSDT", side="SELL", order_type="STOP_MARKET",
            quantity="0.001", stop_price="58000"
        )
        assert result["order_type"] == "STOP_MARKET"

    def test_stop_limit_type(self, validator):
        result = validator.validate(
            symbol="BTCUSDT", side="SELL", order_type="STOP_LIMIT",
            quantity="0.001", price="57500", stop_price="58000"
        )
        assert result["order_type"] == "STOP_LIMIT"

    def test_lowercase_order_type_normalised(self, validator):
        result = validator.validate(
            symbol="BTCUSDT", side="BUY", order_type="market", quantity="0.001"
        )
        assert result["order_type"] == "MARKET"

    def test_invalid_order_type_raises(self, validator):
        with pytest.raises(ValueError, match="[Oo]rder.*type|MARKET|LIMIT"):
            validator.validate(symbol="BTCUSDT", side="BUY", order_type="OCO", quantity="0.001")


# ── Quantity validation ────────────────────────────────────────────────────────

class TestQuantityValidation:
    def test_valid_quantity_string(self, validator):
        result = validator.validate(symbol="BTCUSDT", side="BUY", order_type="MARKET", quantity="0.001")
        assert result["quantity"] == Decimal("0.001")

    def test_valid_quantity_float(self, validator):
        result = validator.validate(symbol="BTCUSDT", side="BUY", order_type="MARKET", quantity=0.01)
        assert result["quantity"] > 0

    def test_zero_quantity_raises(self, validator):
        with pytest.raises(ValueError, match="[Qq]uantity|positive|zero"):
            validator.validate(symbol="BTCUSDT", side="BUY", order_type="MARKET", quantity="0")

    def test_negative_quantity_raises(self, validator):
        with pytest.raises(ValueError, match="[Qq]uantity|positive"):
            validator.validate(symbol="BTCUSDT", side="BUY", order_type="MARKET", quantity="-0.001")

    def test_non_numeric_quantity_raises(self, validator):
        with pytest.raises((ValueError, Exception)):
            validator.validate(symbol="BTCUSDT", side="BUY", order_type="MARKET", quantity="abc")

    def test_very_small_quantity_precision(self, validator):
        result = validator.validate(
            symbol="BTCUSDT", side="BUY", order_type="MARKET", quantity="0.000001"
        )
        assert result["quantity"] == Decimal("0.000001")


# ── Price validation ───────────────────────────────────────────────────────────

class TestPriceValidation:
    def test_market_order_no_price_required(self, validator):
        result = validator.validate(symbol="BTCUSDT", side="BUY", order_type="MARKET", quantity="0.001")
        assert result.get("price") is None

    def test_limit_order_with_price(self, validator):
        result = validator.validate(
            symbol="BTCUSDT", side="BUY", order_type="LIMIT",
            quantity="0.001", price="60000"
        )
        assert result["price"] == Decimal("60000")

    def test_limit_order_without_price_raises(self, validator):
        with pytest.raises(ValueError, match="[Pp]rice|LIMIT"):
            validator.validate(symbol="BTCUSDT", side="BUY", order_type="LIMIT", quantity="0.001")

    def test_limit_order_zero_price_raises(self, validator):
        with pytest.raises(ValueError, match="[Pp]rice|positive|zero"):
            validator.validate(
                symbol="BTCUSDT", side="BUY", order_type="LIMIT",
                quantity="0.001", price="0"
            )

    def test_limit_order_negative_price_raises(self, validator):
        with pytest.raises(ValueError, match="[Pp]rice|positive"):
            validator.validate(
                symbol="BTCUSDT", side="BUY", order_type="LIMIT",
                quantity="0.001", price="-1"
            )

    def test_stop_limit_requires_stop_price(self, validator):
        with pytest.raises(ValueError, match="[Ss]top.*[Pp]rice|stop_price"):
            validator.validate(
                symbol="BTCUSDT", side="SELL", order_type="STOP_LIMIT",
                quantity="0.001", price="57500"
                # missing stop_price
            )

    def test_decimal_precision_preserved(self, validator):
        result = validator.validate(
            symbol="BTCUSDT", side="BUY", order_type="LIMIT",
            quantity="0.00100000", price="59999.99"
        )
        assert result["price"] == Decimal("59999.99")


# ── Combined / integration tests ───────────────────────────────────────────────

class TestCombinedValidation:
    def test_full_market_order_params(self, validator):
        result = validator.validate(
            symbol="solusdt", side="sell", order_type="market", quantity="1.5"
        )
        assert result["symbol"] == "SOLUSDT"
        assert result["side"] == "SELL"
        assert result["order_type"] == "MARKET"
        assert result["quantity"] == Decimal("1.5")

    def test_full_limit_order_params(self, validator):
        result = validator.validate(
            symbol="ETHUSDT", side="BUY", order_type="LIMIT",
            quantity="0.1", price="3500.50"
        )
        assert result["price"] == Decimal("3500.50")
        assert result["quantity"] == Decimal("0.1")

    def test_full_stop_limit_order_params(self, validator):
        result = validator.validate(
            symbol="BTCUSDT", side="SELL", order_type="STOP_LIMIT",
            quantity="0.002", price="57500", stop_price="58000"
        )
        assert result["stop_price"] == Decimal("58000")
        assert result["price"] == Decimal("57500")
