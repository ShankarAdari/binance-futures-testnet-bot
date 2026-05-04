"""
bot/strategies.py
=================
Plug-and-Play Strategy Layer
=============================
Each strategy is a class that accepts a price history list and emits a
`Signal` (BUY / SELL / HOLD).

Strategies are intentionally side-effect-free: they never call the API
directly.  The CLI (or a future scheduler) reads the signal and decides
whether to place an order.

Built-in strategies
-------------------
1. MovingAverageCrossover — fast MA crosses above/below slow MA
2. RSIStrategy            — oversold → BUY, overbought → SELL

Adding a new strategy
---------------------
1. Subclass `BaseStrategy`
2. Implement `generate_signal(prices) -> Signal`
3. Register it in `STRATEGY_REGISTRY`

Usage
-----
    from bot.strategies import get_strategy
    strategy = get_strategy("rsi")
    signal = strategy.generate_signal([60000, 60100, 59900, ...])
    print(signal.direction, signal.reason)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Callable

from bot.exceptions import InsufficientDataError
from core.config import settings
from core.constants import SignalDirection

logger = logging.getLogger("bot.strategies")


# ── Signal DTO ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Signal:
    """Immutable result produced by a strategy."""
    direction: SignalDirection
    reason: str
    confidence: float = 1.0   # 0.0 – 1.0 (informational only)

    def __str__(self) -> str:
        return f"[{self.direction.value}] {self.reason} (confidence {self.confidence:.0%})"


# ── Base Class ────────────────────────────────────────────────────────────────

class BaseStrategy:
    """Abstract base for all strategies."""

    name: str = "base"

    def generate_signal(self, prices: List[float]) -> Signal:
        raise NotImplementedError

    def _require_min_length(self, prices: List[float], min_len: int) -> None:
        if len(prices) < min_len:
            raise InsufficientDataError(
                f"Strategy '{self.name}' needs at least {min_len} price points, "
                f"got {len(prices)}."
            )

    @staticmethod
    def _sma(prices: List[float], period: int) -> float:
        """Simple moving average of the last `period` prices."""
        window = prices[-period:]
        return sum(window) / len(window)

    @staticmethod
    def _ema(prices: List[float], period: int) -> float:
        """Exponential moving average (Wilder's smoothing)."""
        k = 2.0 / (period + 1)
        ema = prices[0]
        for price in prices[1:]:
            ema = price * k + ema * (1 - k)
        return ema

    @staticmethod
    def _rsi(prices: List[float], period: int) -> float:
        """Compute RSI (Relative Strength Index)."""
        if len(prices) < period + 1:
            return 50.0
        deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
        gains = [d for d in deltas if d > 0]
        losses = [-d for d in deltas if d < 0]
        avg_gain = sum(gains[-period:]) / period if gains else 0.0
        avg_loss = sum(losses[-period:]) / period if losses else 0.0
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1 + rs))


# ── Strategy 1: Moving Average Crossover ──────────────────────────────────────

class MovingAverageCrossover(BaseStrategy):
    """
    Classic MA-crossover strategy.

    Signal logic:
        BUY  — fast MA crosses above slow MA (golden cross)
        SELL — fast MA crosses below slow MA (death cross)
        HOLD — no cross detected
    """

    name = "moving_average"

    def __init__(
        self,
        fast_period: int | None = None,
        slow_period: int | None = None,
    ) -> None:
        self.fast = fast_period or settings.ma_fast_period
        self.slow = slow_period or settings.ma_slow_period

    def generate_signal(self, prices: List[float]) -> Signal:
        min_len = self.slow + 1
        self._require_min_length(prices, min_len)

        fast_now = self._sma(prices, self.fast)
        slow_now = self._sma(prices, self.slow)
        # Previous bar (one step back)
        fast_prev = self._sma(prices[:-1], self.fast)
        slow_prev = self._sma(prices[:-1], self.slow)

        logger.debug(
            "MA crossover | fast=%.4f slow=%.4f | prev fast=%.4f slow=%.4f",
            fast_now, slow_now, fast_prev, slow_prev,
        )

        if fast_prev <= slow_prev and fast_now > slow_now:
            signal = Signal(
                direction=SignalDirection.BUY,
                reason=f"Golden cross: fast MA({self.fast})={fast_now:.2f} "
                       f"crossed above slow MA({self.slow})={slow_now:.2f}",
                confidence=min((fast_now - slow_now) / slow_now * 100, 1.0),
            )
        elif fast_prev >= slow_prev and fast_now < slow_now:
            signal = Signal(
                direction=SignalDirection.SELL,
                reason=f"Death cross: fast MA({self.fast})={fast_now:.2f} "
                       f"crossed below slow MA({self.slow})={slow_now:.2f}",
                confidence=min((slow_now - fast_now) / slow_now * 100, 1.0),
            )
        else:
            signal = Signal(
                direction=SignalDirection.HOLD,
                reason=f"No crossover — fast MA={fast_now:.2f}, slow MA={slow_now:.2f}",
                confidence=1.0,
            )

        logger.info("Strategy '%s' generated: %s", self.name, signal)
        return signal


# ── Strategy 2: RSI-Based ─────────────────────────────────────────────────────

class RSIStrategy(BaseStrategy):
    """
    RSI momentum strategy.

    Signal logic:
        BUY  — RSI drops below oversold threshold (e.g. 30)
        SELL — RSI rises above overbought threshold (e.g. 70)
        HOLD — RSI in neutral zone
    """

    name = "rsi"

    def __init__(
        self,
        period: int | None = None,
        overbought: float | None = None,
        oversold: float | None = None,
    ) -> None:
        self.period = period or settings.rsi_period
        self.overbought = overbought or settings.rsi_overbought
        self.oversold = oversold or settings.rsi_oversold

    def generate_signal(self, prices: List[float]) -> Signal:
        self._require_min_length(prices, self.period + 1)
        rsi_value = self._rsi(prices, self.period)

        logger.debug("RSI(%d) = %.4f | OB=%.1f OS=%.1f",
                     self.period, rsi_value, self.overbought, self.oversold)

        if rsi_value < self.oversold:
            signal = Signal(
                direction=SignalDirection.BUY,
                reason=f"RSI({self.period})={rsi_value:.2f} — oversold (< {self.oversold})",
                confidence=(self.oversold - rsi_value) / self.oversold,
            )
        elif rsi_value > self.overbought:
            signal = Signal(
                direction=SignalDirection.SELL,
                reason=f"RSI({self.period})={rsi_value:.2f} — overbought (> {self.overbought})",
                confidence=(rsi_value - self.overbought) / (100 - self.overbought),
            )
        else:
            signal = Signal(
                direction=SignalDirection.HOLD,
                reason=f"RSI({self.period})={rsi_value:.2f} — neutral zone",
                confidence=1.0,
            )

        logger.info("Strategy '%s' generated: %s", self.name, signal)
        return signal


# ── Strategy 3: Combined MA + RSI ─────────────────────────────────────────────

class CombinedStrategy(BaseStrategy):
    """
    Composite strategy: requires both MA crossover AND RSI confirmation.

    BUY  — golden cross AND RSI oversold/neutral (< overbought)
    SELL — death cross AND RSI overbought/neutral (> oversold)
    HOLD — signals disagree or both HOLD
    """

    name = "combined"

    def __init__(self) -> None:
        self._ma = MovingAverageCrossover()
        self._rsi = RSIStrategy()

    def generate_signal(self, prices: List[float]) -> Signal:
        ma_sig = self._ma.generate_signal(prices)
        rsi_sig = self._rsi.generate_signal(prices)

        if (ma_sig.direction == SignalDirection.BUY
                and rsi_sig.direction != SignalDirection.SELL):
            direction = SignalDirection.BUY
            reason = f"MA+RSI confirm BUY: {ma_sig.reason}"
            conf = (ma_sig.confidence + rsi_sig.confidence) / 2
        elif (ma_sig.direction == SignalDirection.SELL
              and rsi_sig.direction != SignalDirection.BUY):
            direction = SignalDirection.SELL
            reason = f"MA+RSI confirm SELL: {ma_sig.reason}"
            conf = (ma_sig.confidence + rsi_sig.confidence) / 2
        else:
            direction = SignalDirection.HOLD
            reason = f"Conflicting signals — MA: {ma_sig.direction.value}, RSI: {rsi_sig.direction.value}"
            conf = 0.5

        signal = Signal(direction=direction, reason=reason, confidence=conf)
        logger.info("Strategy '%s' generated: %s", self.name, signal)
        return signal


# ── Mock Backtester ───────────────────────────────────────────────────────────

@dataclass
class BacktestResult:
    """Summary of a backtest run."""
    strategy_name: str
    total_trades: int
    wins: int
    losses: int
    total_pnl: float
    win_rate: float

    def __str__(self) -> str:
        return (
            f"[{self.strategy_name}] trades={self.total_trades} "
            f"wins={self.wins} losses={self.losses} "
            f"PnL={self.total_pnl:+.4f} USDT "
            f"win_rate={self.win_rate:.1%}"
        )


def backtest(
    strategy: BaseStrategy,
    prices: List[float],
    quantity: float = 0.001,
    fee_rate: float = 0.0004,
) -> BacktestResult:
    """
    Simple bar-by-bar mock backtest.

    Rules:
    - Look at a growing window of prices
    - When strategy says BUY, enter long (if not already in)
    - When strategy says SELL, close long (if open)
    - Track PnL per round-trip
    """
    min_window = max(
        getattr(strategy, "slow", 21) + 2,
        getattr(strategy, "period", 14) + 2,
        23,
    )

    position_price: float | None = None
    wins = losses = 0
    total_pnl = 0.0

    for i in range(min_window, len(prices)):
        window = prices[:i]
        try:
            signal = strategy.generate_signal(window)
        except InsufficientDataError:
            continue

        current_price = prices[i]

        if signal.direction == SignalDirection.BUY and position_price is None:
            position_price = current_price
            logger.debug("Backtest ENTER LONG @ %.4f", current_price)

        elif signal.direction == SignalDirection.SELL and position_price is not None:
            pnl = (current_price - position_price) * quantity
            fee = (position_price + current_price) * quantity * fee_rate
            net_pnl = pnl - fee
            total_pnl += net_pnl
            if net_pnl > 0:
                wins += 1
            else:
                losses += 1
            logger.debug(
                "Backtest EXIT LONG @ %.4f | PnL=%.6f fee=%.6f net=%.6f",
                current_price, pnl, fee, net_pnl,
            )
            position_price = None

    total_trades = wins + losses
    win_rate = wins / total_trades if total_trades > 0 else 0.0
    result = BacktestResult(
        strategy_name=strategy.name,
        total_trades=total_trades,
        wins=wins,
        losses=losses,
        total_pnl=round(total_pnl, 6),
        win_rate=win_rate,
    )
    logger.info("Backtest complete: %s", result)
    return result


# ── Registry ──────────────────────────────────────────────────────────────────

STRATEGY_REGISTRY: dict[str, Callable[[], BaseStrategy]] = {
    "moving_average": MovingAverageCrossover,
    "rsi": RSIStrategy,
    "combined": CombinedStrategy,
}


def get_strategy(name: str) -> BaseStrategy:
    """Factory — returns an instantiated strategy by name."""
    factory = STRATEGY_REGISTRY.get(name.lower())
    if factory is None:
        available = ", ".join(STRATEGY_REGISTRY.keys())
        raise ValueError(
            f"Unknown strategy '{name}'. Available: {available}"
        )
    return factory()
