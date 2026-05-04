"""
bot/__init__.py
===============
Binance Futures Testnet Trading Bot — bot package.
Exposes the primary interfaces for external use.
"""

from .client import BinanceFuturesClient
from .orders import OrderManager
from .validators import OrderValidator
from .risk import RiskManager
from .strategies import get_strategy, STRATEGY_REGISTRY
from .exceptions import (
    BotError, ValidationError, APIError,
    AuthenticationError, RateLimitError, NetworkError,
    RiskError, StrategyError,
)

__all__ = [
    "BinanceFuturesClient",
    "OrderManager",
    "OrderValidator",
    "RiskManager",
    "get_strategy",
    "STRATEGY_REGISTRY",
    "BotError",
    "ValidationError",
    "APIError",
    "AuthenticationError",
    "RateLimitError",
    "NetworkError",
    "RiskError",
    "StrategyError",
]
