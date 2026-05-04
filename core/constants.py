"""
core/constants.py
=================
Enumerations and immutable constants shared across the entire bot.
"""

from __future__ import annotations

from enum import Enum


class OrderType(str, Enum):
    """Supported Binance Futures order types."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_MARKET = "STOP_MARKET"
    STOP_LIMIT = "STOP_LIMIT"


class OrderSide(str, Enum):
    """Order direction."""
    BUY = "BUY"
    SELL = "SELL"


class PositionSide(str, Enum):
    """Hedge-mode position side (used when hedge mode is ON)."""
    BOTH = "BOTH"
    LONG = "LONG"
    SHORT = "SHORT"


class TimeInForce(str, Enum):
    """Time-in-force policies."""
    GTC = "GTC"   # Good Till Cancel
    IOC = "IOC"   # Immediate Or Cancel
    FOK = "FOK"   # Fill Or Kill
    GTX = "GTX"   # Good Till Crossing (post-only)


class SignalDirection(str, Enum):
    """Strategy signal direction."""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


# ── API Constants ─────────────────────────────────────────────────────────────
TESTNET_BASE_URL: str = "https://testnet.binancefuture.com"
MAINNET_BASE_URL: str = "https://fapi.binance.com"

DEFAULT_RECV_WINDOW: int = 5_000      # ms
DEFAULT_TIMEOUT: float = 10.0         # seconds per request
MAX_RETRIES: int = 3
BACKOFF_BASE: float = 0.5             # seconds; actual delay = BACKOFF_BASE * 2^attempt
BACKOFF_MAX: float = 30.0             # cap

# ── Risk Defaults ─────────────────────────────────────────────────────────────
DEFAULT_MAX_POSITION_USDT: float = 1_000.0   # maximum notional per position
DEFAULT_DAILY_LOSS_CAP_USDT: float = 200.0   # halt trading after this loss
DEFAULT_MAX_EXPOSURE_USDT: float = 5_000.0   # total open notional ceiling
