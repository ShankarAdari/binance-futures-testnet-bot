"""
validators.py
=============
Input validation for all order parameters.

All validators raise ValueError with a human-readable message on failure
so the CLI layer can surface them cleanly to the user.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from .logging_config import get_logger

log = get_logger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────
VALID_ORDER_TYPES = frozenset({"MARKET", "LIMIT", "STOP_MARKET", "STOP_LIMIT"})
VALID_SIDES = frozenset({"BUY", "SELL"})
VALID_TIME_IN_FORCE = frozenset({"GTC", "IOC", "FOK", "GTX"})

# Symbol must be uppercase alphanumeric, 2-20 chars (e.g. BTCUSDT)
_SYMBOL_PATTERN = re.compile(r"^[A-Z0-9]{2,20}$")

# Minimum notional is enforced per symbol; we use a safe default floor
_MIN_QUANTITY = Decimal("0.000001")
_MIN_PRICE = Decimal("0.000001")


# ── Helpers ────────────────────────────────────────────────────────────────────

def _to_decimal(value: str | float | Decimal, field: str) -> Decimal:
    """Convert *value* to Decimal; raise ValueError with *field* name on error."""
    try:
        d = Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise ValueError(
            f"'{field}' must be a valid number, got: {value!r}"
        ) from exc
    return d


# ── Public Validator Class ─────────────────────────────────────────────────────

class OrderValidator:
    """
    Validates all parameters required to place an order.

    Usage
    -----
    >>> v = OrderValidator()
    >>> params = v.validate(symbol="BTCUSDT", side="BUY", order_type="LIMIT",
    ...                     quantity=0.001, price=30000)
    """

    def validate(
        self,
        *,
        symbol: str,
        side: str,
        order_type: str,
        quantity: str | float | Decimal,
        price: Optional[str | float | Decimal] = None,
        stop_price: Optional[str | float | Decimal] = None,
        time_in_force: Optional[str] = None,
        reduce_only: bool = False,
    ) -> dict:
        """
        Validate all order parameters and return a clean, normalised dict
        ready to be forwarded to the API client.

        Parameters
        ----------
        symbol        : Trading pair, e.g. "BTCUSDT"
        side          : "BUY" or "SELL"
        order_type    : "MARKET", "LIMIT", "STOP_MARKET", or "STOP_LIMIT"
        quantity      : Order quantity (base asset)
        price         : Limit price — required for LIMIT / STOP_LIMIT orders
        stop_price    : Trigger price — required for STOP_MARKET / STOP_LIMIT
        time_in_force : "GTC" (default for LIMIT), "IOC", "FOK", "GTX"
        reduce_only   : Close-only flag

        Returns
        -------
        dict with validated, normalised values

        Raises
        ------
        ValueError on any validation failure
        """
        log.debug(
            "Validating order params: symbol=%s side=%s type=%s qty=%s price=%s",
            symbol, side, order_type, quantity, price,
        )

        cleaned: dict = {}

        # 1. Symbol
        cleaned["symbol"] = self._validate_symbol(symbol)

        # 2. Side
        cleaned["side"] = self._validate_side(side)

        # 3. Order type
        cleaned["order_type"] = self._validate_order_type(order_type)

        # 4. Quantity
        cleaned["quantity"] = self._validate_quantity(quantity)

        # 5. Price (conditional)
        order_type_upper = cleaned["order_type"]
        if order_type_upper in {"LIMIT", "STOP_LIMIT"}:
            if price is None:
                raise ValueError(
                    f"'price' is required for {order_type_upper} orders."
                )
            cleaned["price"] = self._validate_price(price)
        elif price is not None:
            log.warning(
                "Price supplied for %s order — it will be ignored by the exchange.",
                order_type_upper,
            )
            cleaned["price"] = None
        else:
            cleaned["price"] = None

        # 6. Stop price (conditional)
        if order_type_upper in {"STOP_MARKET", "STOP_LIMIT"}:
            if stop_price is None:
                raise ValueError(
                    f"'stop_price' is required for {order_type_upper} orders."
                )
            cleaned["stop_price"] = self._validate_price(stop_price)
        else:
            cleaned["stop_price"] = None

        # 7. Time-in-force
        if order_type_upper in {"LIMIT", "STOP_LIMIT"}:
            tif = (time_in_force or "GTC").upper()
            if tif not in VALID_TIME_IN_FORCE:
                raise ValueError(
                    f"'time_in_force' must be one of {sorted(VALID_TIME_IN_FORCE)}, got: {tif!r}"
                )
            cleaned["time_in_force"] = tif
        else:
            cleaned["time_in_force"] = None

        # 8. Reduce-only flag
        if not isinstance(reduce_only, bool):
            raise ValueError("'reduce_only' must be a boolean.")
        cleaned["reduce_only"] = reduce_only

        log.debug("Validation passed: %s", cleaned)
        return cleaned

    # ── Private field validators ───────────────────────────────────────────────

    @staticmethod
    def _validate_symbol(symbol: str) -> str:
        if not isinstance(symbol, str) or not symbol.strip():
            raise ValueError("'symbol' must be a non-empty string.")
        s = symbol.strip().upper()
        if not _SYMBOL_PATTERN.match(s):
            raise ValueError(
                f"'symbol' must be uppercase alphanumeric (2-20 chars), got: {s!r}"
            )
        return s

    @staticmethod
    def _validate_side(side: str) -> str:
        if not isinstance(side, str):
            raise ValueError("'side' must be a string.")
        s = side.strip().upper()
        if s not in VALID_SIDES:
            raise ValueError(
                f"'side' must be one of {sorted(VALID_SIDES)}, got: {s!r}"
            )
        return s

    @staticmethod
    def _validate_order_type(order_type: str) -> str:
        if not isinstance(order_type, str):
            raise ValueError("'order_type' must be a string.")
        t = order_type.strip().upper()
        if t not in VALID_ORDER_TYPES:
            raise ValueError(
                f"'order_type' must be one of {sorted(VALID_ORDER_TYPES)}, got: {t!r}"
            )
        return t

    @staticmethod
    def _validate_quantity(quantity) -> Decimal:
        qty = _to_decimal(quantity, "quantity")
        if qty <= 0:
            raise ValueError(f"'quantity' must be positive, got: {qty}")
        if qty < _MIN_QUANTITY:
            raise ValueError(
                f"'quantity' ({qty}) is below the minimum allowed ({_MIN_QUANTITY})."
            )
        return qty

    @staticmethod
    def _validate_price(price) -> Decimal:
        p = _to_decimal(price, "price")
        if p <= 0:
            raise ValueError(f"'price' must be positive, got: {p}")
        if p < _MIN_PRICE:
            raise ValueError(
                f"'price' ({p}) is below the minimum allowed ({_MIN_PRICE})."
            )
        return p
