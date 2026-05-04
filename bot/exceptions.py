"""
exceptions.py
=============
Custom exception hierarchy for the trading bot.

All exceptions inherit from BotError so callers can catch the entire
family with a single `except BotError` clause if desired.
"""

from __future__ import annotations


class BotError(Exception):
    """Base class for all trading-bot errors."""

    def __init__(self, message: str, detail: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail

    def __str__(self) -> str:
        if self.detail:
            return f"{self.message} — {self.detail}"
        return self.message


# ── Validation ──────────────────────────────────────────────────────────────

class ValidationError(BotError):
    """Raised when input validation fails before any API call is made."""


class SymbolValidationError(ValidationError):
    """Raised when the trading symbol is invalid."""


class QuantityValidationError(ValidationError):
    """Raised when the quantity is invalid (e.g. zero, negative)."""


class PriceValidationError(ValidationError):
    """Raised when the price is invalid or missing for order types that need it."""


class OrderSideError(ValidationError):
    """Raised when an unrecognised order side is supplied."""


class OrderTypeError(ValidationError):
    """Raised when an unrecognised order type is supplied."""


# ── API / Network ────────────────────────────────────────────────────────────

class APIError(BotError):
    """Raised when the Binance API returns an error response."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        binance_code: int | None = None,
        detail: str | None = None,
    ) -> None:
        super().__init__(message, detail)
        self.status_code = status_code
        self.binance_code = binance_code

    def __str__(self) -> str:
        parts = [self.message]
        if self.binance_code is not None:
            parts.append(f"Binance code {self.binance_code}")
        if self.detail:
            parts.append(self.detail)
        return " | ".join(parts)


class AuthenticationError(APIError):
    """Raised when API key/secret is missing, invalid, or rejected."""


class RateLimitError(APIError):
    """Raised when Binance returns HTTP 429 or 418 (ban)."""


class NetworkError(BotError):
    """Raised on connection timeout, DNS failure, or other transport errors."""


class MaxRetriesExceeded(NetworkError):
    """Raised when the retry budget is exhausted without a successful response."""


# ── Risk ─────────────────────────────────────────────────────────────────────

class RiskError(BotError):
    """Base class for risk-management violations."""


class PositionSizeError(RiskError):
    """Raised when the requested quantity exceeds the maximum allowed position size."""


class DailyLossCapError(RiskError):
    """Raised when placing the order would breach the daily loss cap."""


class ExposureError(RiskError):
    """Raised when total notional exposure would exceed configured limits."""


# ── Strategy ─────────────────────────────────────────────────────────────────

class StrategyError(BotError):
    """Raised when a strategy cannot produce a signal (e.g. insufficient data)."""


class InsufficientDataError(StrategyError):
    """Raised when the price history is too short for the strategy's lookback."""
