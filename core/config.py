"""
core/config.py
==============
Centralised, environment-driven configuration.

Reads values from .env (or real environment variables) and exposes
them as a single typed `Settings` dataclass instance (`settings`).

Usage:
    from core.config import settings
    print(settings.api_key)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the project root (one level up from core/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env", override=False)


@dataclass(frozen=True)
class Settings:
    # ── Credentials ───────────────────────────────────────────────────────────
    api_key: str = field(default_factory=lambda: os.getenv("BINANCE_TESTNET_API_KEY", ""))
    api_secret: str = field(default_factory=lambda: os.getenv("BINANCE_TESTNET_API_SECRET", ""))

    # ── Network ───────────────────────────────────────────────────────────────
    base_url: str = field(
        default_factory=lambda: os.getenv(
            "BINANCE_BASE_URL", "https://testnet.binancefuture.com"
        )
    )
    timeout: float = field(
        default_factory=lambda: float(os.getenv("REQUEST_TIMEOUT", "10.0"))
    )
    max_retries: int = field(
        default_factory=lambda: int(os.getenv("MAX_RETRIES", "3"))
    )

    # ── Risk ──────────────────────────────────────────────────────────────────
    max_position_usdt: float = field(
        default_factory=lambda: float(os.getenv("MAX_POSITION_USDT", "1000.0"))
    )
    daily_loss_cap_usdt: float = field(
        default_factory=lambda: float(os.getenv("DAILY_LOSS_CAP_USDT", "200.0"))
    )
    max_exposure_usdt: float = field(
        default_factory=lambda: float(os.getenv("MAX_EXPOSURE_USDT", "5000.0"))
    )

    # ── Logging ───────────────────────────────────────────────────────────────
    log_level: str = field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO").upper()
    )
    log_dir: Path = field(
        default_factory=lambda: _PROJECT_ROOT / "logs"
    )

    # ── Strategy ──────────────────────────────────────────────────────────────
    default_strategy: str = field(
        default_factory=lambda: os.getenv("DEFAULT_STRATEGY", "moving_average")
    )
    ma_fast_period: int = field(
        default_factory=lambda: int(os.getenv("MA_FAST_PERIOD", "9"))
    )
    ma_slow_period: int = field(
        default_factory=lambda: int(os.getenv("MA_SLOW_PERIOD", "21"))
    )
    rsi_period: int = field(
        default_factory=lambda: int(os.getenv("RSI_PERIOD", "14"))
    )
    rsi_overbought: float = field(
        default_factory=lambda: float(os.getenv("RSI_OVERBOUGHT", "70.0"))
    )
    rsi_oversold: float = field(
        default_factory=lambda: float(os.getenv("RSI_OVERSOLD", "30.0"))
    )

    @property
    def has_credentials(self) -> bool:
        """True when both API key and secret are non-empty."""
        return bool(self.api_key and self.api_secret)


# Singleton settings instance — import this everywhere
settings = Settings()
