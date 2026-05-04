"""
core/__init__.py
================
Core package — exports config and constants.
"""

from .config import settings
from .constants import OrderType, OrderSide, PositionSide

__all__ = ["settings", "OrderType", "OrderSide", "PositionSide"]
