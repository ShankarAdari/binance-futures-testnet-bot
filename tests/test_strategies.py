"""
tests/test_strategies.py
=========================
Unit tests for bot.strategies
"""

import math
import pytest
from bot.strategies import (
    MovingAverageCrossover, RSIStrategy, CombinedStrategy,
    backtest, get_strategy, BacktestResult,
)
from bot.exceptions import InsufficientDataError
from core.constants import SignalDirection


def bullish_series(length=30):
    return [50_000 + i * 100 for i in range(length)]

def bearish_series(length=30):
    return [60_000 - i * 100 for i in range(length)]

def flat_series(length=30):
    return [55_000.0] * length


class TestMovingAverageCrossover:
    def test_flat_series_returns_hold(self):
        s = MovingAverageCrossover(fast_period=3, slow_period=5)
        signal = s.generate_signal(flat_series(20))
        assert signal.direction == SignalDirection.HOLD

    def test_insufficient_data_raises(self):
        s = MovingAverageCrossover(fast_period=9, slow_period=21)
        with pytest.raises(InsufficientDataError):
            s.generate_signal([60_000, 60_100])

    def test_signal_has_reason(self):
        s = MovingAverageCrossover(fast_period=3, slow_period=5)
        signal = s.generate_signal(bullish_series(30))
        assert len(signal.reason) > 0

    def test_confidence_in_range(self):
        s = MovingAverageCrossover(fast_period=3, slow_period=5)
        signal = s.generate_signal(bullish_series(30))
        assert 0.0 <= signal.confidence <= 1.0


class TestRSIStrategy:
    def test_insufficient_data_raises(self):
        s = RSIStrategy(period=14)
        with pytest.raises(InsufficientDataError):
            s.generate_signal([60_000] * 5)

    def test_signal_has_rsi_in_reason(self):
        s = RSIStrategy(period=14, overbought=70, oversold=30)
        signal = s.generate_signal([55_000.0] * 20)
        assert "RSI" in signal.reason

    def test_overbought_bullish_trend(self):
        s = RSIStrategy(period=14, overbought=70, oversold=30)
        prices = [40_000 + i * 300 for i in range(20)]
        signal = s.generate_signal(prices)
        assert signal.direction in (SignalDirection.SELL, SignalDirection.HOLD)

    def test_oversold_bearish_trend(self):
        s = RSIStrategy(period=14, overbought=70, oversold=30)
        prices = [60_000 - i * 300 for i in range(20)]
        signal = s.generate_signal(prices)
        assert signal.direction in (SignalDirection.BUY, SignalDirection.HOLD)


class TestCombinedStrategy:
    def test_returns_valid_direction(self):
        s = CombinedStrategy()
        signal = s.generate_signal(bullish_series(30))
        assert signal.direction in SignalDirection

    def test_reason_non_empty(self):
        s = CombinedStrategy()
        signal = s.generate_signal(bullish_series(30))
        assert len(signal.reason) > 0


class TestBacktest:
    def test_returns_result(self):
        s = MovingAverageCrossover(fast_period=3, slow_period=5)
        prices = [50_000 + (i % 10) * 200 - (i % 5) * 100 for i in range(60)]
        result = backtest(s, prices)
        assert isinstance(result, BacktestResult)

    def test_win_rate_in_range(self):
        s = RSIStrategy(period=5, overbought=60, oversold=40)
        prices = [55_000 + (i % 8) * 300 - (i % 3) * 200 for i in range(80)]
        result = backtest(s, prices)
        assert 0.0 <= result.win_rate <= 1.0

    def test_strategy_name_in_result(self):
        s = RSIStrategy()
        result = backtest(s, bullish_series(50))
        assert result.strategy_name == "rsi"

    def test_total_equals_wins_plus_losses(self):
        s = MovingAverageCrossover(fast_period=3, slow_period=5)
        prices = [50_000 + (i % 10) * 200 - (i % 5) * 100 for i in range(60)]
        result = backtest(s, prices)
        assert result.total_trades == result.wins + result.losses


class TestStrategyRegistry:
    def test_get_ma(self):
        assert isinstance(get_strategy("moving_average"), MovingAverageCrossover)

    def test_get_rsi(self):
        assert isinstance(get_strategy("rsi"), RSIStrategy)

    def test_get_combined(self):
        assert isinstance(get_strategy("combined"), CombinedStrategy)

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown strategy"):
            get_strategy("nonexistent")

    def test_case_insensitive(self):
        assert isinstance(get_strategy("RSI"), RSIStrategy)
