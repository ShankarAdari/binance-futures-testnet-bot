"""
bot/risk.py
===========
Risk Management Module
======================
Provides pre-trade risk checks before any order is sent to the exchange.

Features
--------
* Max position size (notional USDT) validation
* Daily loss cap simulation (in-memory; reset on process restart)
* Total position exposure ceiling
* Position exposure logging

Usage
-----
    from bot.risk import RiskManager
    rm = RiskManager()
    rm.check(symbol="BTCUSDT", side="BUY", quantity=0.01, price=60_000)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Dict

from bot.exceptions import DailyLossCapError, ExposureError, PositionSizeError
from core.config import settings

logger = logging.getLogger("bot.risk")


@dataclass
class PositionRecord:
    """In-memory record of an open position."""
    symbol: str
    side: str
    quantity: Decimal
    entry_price: Decimal

    @property
    def notional(self) -> Decimal:
        return self.quantity * self.entry_price


@dataclass
class DailyLossTracker:
    """Tracks realised P&L for the current calendar day (UTC)."""
    _date: date = field(default_factory=date.today)
    _realised_loss: Decimal = field(default=Decimal("0"))

    def record_loss(self, amount: Decimal) -> None:
        """Add a loss amount (positive = loss)."""
        today = date.today()
        if today != self._date:
            # New day — reset
            self._date = today
            self._realised_loss = Decimal("0")
        self._realised_loss += amount
        logger.info(
            "Daily P&L updated | loss so far today: %.4f USDT",
            float(self._realised_loss),
        )

    @property
    def total_loss(self) -> Decimal:
        today = date.today()
        if today != self._date:
            return Decimal("0")
        return self._realised_loss


class RiskManager:
    """
    Central risk-management gate.

    All limits are read from `core.config.settings` so they can be
    overridden via environment variables or .env without code changes.
    """

    def __init__(
        self,
        max_position_usdt: float | None = None,
        daily_loss_cap_usdt: float | None = None,
        max_exposure_usdt: float | None = None,
    ) -> None:
        self.max_position = Decimal(
            str(max_position_usdt or settings.max_position_usdt)
        )
        self.daily_loss_cap = Decimal(
            str(daily_loss_cap_usdt or settings.daily_loss_cap_usdt)
        )
        self.max_exposure = Decimal(
            str(max_exposure_usdt or settings.max_exposure_usdt)
        )

        self._positions: Dict[str, PositionRecord] = {}
        self._loss_tracker = DailyLossTracker()

        logger.info(
            "RiskManager initialised | max_pos=%.2f USDT | daily_cap=%.2f USDT | max_exp=%.2f USDT",
            float(self.max_position),
            float(self.daily_loss_cap),
            float(self.max_exposure),
        )

    # ── Public API ─────────────────────────────────────────────────────────────

    def check(
        self,
        symbol: str,
        side: str,
        quantity: float | Decimal,
        price: float | Decimal,
    ) -> None:
        """
        Run all pre-trade risk checks.

        Raises one of: PositionSizeError, DailyLossCapError, ExposureError
        if any check fails.  Returns None on success.
        """
        qty = Decimal(str(quantity))
        prc = Decimal(str(price))
        notional = qty * prc

        logger.info(
            "Risk check | %s %s qty=%.6f price=%.4f notional=%.4f USDT",
            side, symbol, float(qty), float(prc), float(notional),
        )

        self._check_position_size(symbol, notional)
        self._check_daily_loss()
        self._check_total_exposure(notional)

        logger.info("Risk check PASSED for %s %s qty=%.6f", side, symbol, float(qty))

    def record_fill(
        self,
        symbol: str,
        side: str,
        quantity: float | Decimal,
        avg_price: float | Decimal,
    ) -> None:
        """
        Call this after a successful fill to update internal state.

        For SELL orders the position is closed and P&L is calculated.
        """
        qty = Decimal(str(quantity))
        prc = Decimal(str(avg_price))

        if side == "BUY":
            self._positions[symbol] = PositionRecord(
                symbol=symbol, side=side, quantity=qty, entry_price=prc
            )
            logger.info(
                "Position opened | %s LONG qty=%.6f @ %.4f (notional %.4f USDT)",
                symbol, float(qty), float(prc), float(qty * prc),
            )
        elif side == "SELL" and symbol in self._positions:
            entry = self._positions.pop(symbol)
            pnl = (prc - entry.entry_price) * qty
            if pnl < 0:
                self._loss_tracker.record_loss(-pnl)
            logger.info(
                "Position closed | %s @ %.4f | PnL: %.4f USDT",
                symbol, float(prc), float(pnl),
            )

    def log_exposure(self) -> None:
        """Log a summary of all open positions."""
        if not self._positions:
            logger.info("Exposure report | No open positions")
            return
        total = sum(p.notional for p in self._positions.values())
        logger.info("Exposure report | Total open notional: %.4f USDT", float(total))
        for sym, pos in self._positions.items():
            logger.info(
                "  %s %s qty=%.6f entry=%.4f notional=%.4f USDT",
                sym, pos.side, float(pos.quantity),
                float(pos.entry_price), float(pos.notional),
            )

    def get_exposure_summary(self) -> dict:
        """Return a dict summary of current exposure (useful for the UI/CLI)."""
        positions = []
        total_notional = Decimal("0")
        for sym, pos in self._positions.items():
            positions.append({
                "symbol": sym,
                "side": pos.side,
                "quantity": float(pos.quantity),
                "entry_price": float(pos.entry_price),
                "notional_usdt": float(pos.notional),
            })
            total_notional += pos.notional
        return {
            "open_positions": positions,
            "total_notional_usdt": float(total_notional),
            "daily_loss_usdt": float(self._loss_tracker.total_loss),
            "daily_loss_cap_usdt": float(self.daily_loss_cap),
            "max_position_usdt": float(self.max_position),
            "max_exposure_usdt": float(self.max_exposure),
        }

    # ── Private checks ──────────────────────────────────────────────────────────

    def _check_position_size(self, symbol: str, notional: Decimal) -> None:
        if notional > self.max_position:
            raise PositionSizeError(
                f"Order notional {notional:.4f} USDT exceeds max position size "
                f"{self.max_position:.4f} USDT for {symbol}",
                detail=f"Reduce quantity or increase MAX_POSITION_USDT in .env",
            )

    def _check_daily_loss(self) -> None:
        loss = self._loss_tracker.total_loss
        if loss >= self.daily_loss_cap:
            raise DailyLossCapError(
                f"Daily loss cap of {self.daily_loss_cap:.4f} USDT reached "
                f"(current loss: {loss:.4f} USDT). Trading halted for today.",
                detail="Reset by restarting the bot tomorrow or increasing DAILY_LOSS_CAP_USDT",
            )

    def _check_total_exposure(self, new_notional: Decimal) -> None:
        current = sum(p.notional for p in self._positions.values())
        projected = current + new_notional
        if projected > self.max_exposure:
            raise ExposureError(
                f"Total exposure would reach {projected:.4f} USDT, "
                f"exceeding ceiling of {self.max_exposure:.4f} USDT",
                detail=f"Current open: {current:.4f} USDT | New: {new_notional:.4f} USDT",
            )
