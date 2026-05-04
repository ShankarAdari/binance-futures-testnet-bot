"""
tests/test_risk.py
==================
Unit tests for bot.risk.RiskManager

All tests use small, deterministic limits to avoid side-effects.
"""

import pytest
from decimal import Decimal

from bot.risk import RiskManager
from bot.exceptions import PositionSizeError, DailyLossCapError, ExposureError


@pytest.fixture
def rm():
    """RiskManager with tight limits for testing."""
    return RiskManager(
        max_position_usdt=100.0,
        daily_loss_cap_usdt=50.0,
        max_exposure_usdt=250.0,
    )


class TestPositionSizeCheck:
    def test_within_limit_passes(self, rm):
        # qty=0.001, price=50000 → notional=50 USDT < 100 limit
        rm.check("BTCUSDT", "BUY", 0.001, 50_000)

    def test_exactly_at_limit_passes(self, rm):
        # notional exactly = limit
        rm.check("BTCUSDT", "BUY", 0.002, 50_000)  # 100 USDT

    def test_exceeds_limit_raises(self, rm):
        with pytest.raises(PositionSizeError):
            rm.check("BTCUSDT", "BUY", 0.003, 50_000)  # 150 USDT > 100


class TestDailyLossCap:
    def test_no_loss_passes(self, rm):
        rm.check("BTCUSDT", "BUY", 0.001, 50_000)

    def test_loss_below_cap_passes(self, rm):
        rm._loss_tracker.record_loss(Decimal("30"))
        rm.check("BTCUSDT", "BUY", 0.001, 50_000)

    def test_loss_at_cap_raises(self, rm):
        rm._loss_tracker.record_loss(Decimal("50"))
        with pytest.raises(DailyLossCapError):
            rm.check("BTCUSDT", "BUY", 0.001, 50_000)

    def test_loss_above_cap_raises(self, rm):
        rm._loss_tracker.record_loss(Decimal("75"))
        with pytest.raises(DailyLossCapError):
            rm.check("BTCUSDT", "BUY", 0.001, 50_000)


class TestExposureCheck:
    def test_first_position_within_exposure(self, rm):
        rm.check("BTCUSDT", "BUY", 0.001, 50_000)   # 50 USDT

    def test_multiple_positions_within_exposure(self, rm):
        # Record a filled position
        rm.record_fill("BTCUSDT", "BUY", 0.001, 50_000)  # adds 50 USDT
        rm.check("ETHUSDT", "BUY", 0.02, 3_000)           # adds 60 USDT → total 110 < 250

    def test_exposure_ceiling_exceeded_raises(self, rm):
        rm.record_fill("BTCUSDT", "BUY", 0.004, 50_000)   # 200 USDT position
        with pytest.raises(ExposureError):
            rm.check("ETHUSDT", "BUY", 0.02, 3_000)       # 60 USDT → total 260 > 250


class TestRecordFill:
    def test_buy_adds_position(self, rm):
        rm.record_fill("BTCUSDT", "BUY", 0.001, 60_000)
        summary = rm.get_exposure_summary()
        assert len(summary["open_positions"]) == 1
        assert summary["open_positions"][0]["symbol"] == "BTCUSDT"

    def test_sell_removes_position(self, rm):
        rm.record_fill("BTCUSDT", "BUY", 0.001, 60_000)
        rm.record_fill("BTCUSDT", "SELL", 0.001, 61_000)
        summary = rm.get_exposure_summary()
        assert len(summary["open_positions"]) == 0

    def test_sell_profitable_no_loss_recorded(self, rm):
        rm.record_fill("BTCUSDT", "BUY", 0.001, 60_000)
        rm.record_fill("BTCUSDT", "SELL", 0.001, 61_000)
        assert rm._loss_tracker.total_loss == Decimal("0")

    def test_sell_at_loss_records_loss(self, rm):
        rm.record_fill("BTCUSDT", "BUY", 0.001, 60_000)
        rm.record_fill("BTCUSDT", "SELL", 0.001, 59_000)
        # loss = (59000-60000)*0.001 = -1 USDT
        assert rm._loss_tracker.total_loss == Decimal("1.0")


class TestExposureSummary:
    def test_empty_summary(self, rm):
        summary = rm.get_exposure_summary()
        assert summary["open_positions"] == []
        assert summary["total_notional_usdt"] == 0.0

    def test_summary_with_position(self, rm):
        rm.record_fill("BTCUSDT", "BUY", 0.001, 60_000)
        summary = rm.get_exposure_summary()
        assert summary["total_notional_usdt"] == pytest.approx(60.0, rel=1e-6)
        assert summary["max_position_usdt"] == 100.0
        assert summary["daily_loss_cap_usdt"] == 50.0
