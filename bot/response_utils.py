"""Presentation helpers for Binance order responses."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from .models import format_decimal


def summarize_order_response(response: dict[str, Any]) -> dict[str, str]:
    return {
        "orderId": str(response.get("orderId", "n/a")),
        "status": str(response.get("status", "n/a")),
        "executedQty": str(response.get("executedQty", "n/a")),
        "avgPrice": derive_avg_price(response),
    }


def derive_avg_price(response: dict[str, Any]) -> str:
    avg_price = response.get("avgPrice")
    if avg_price and avg_price not in {"0", "0.0", "0.00000"}:
        return str(avg_price)

    executed_qty = _safe_decimal(response.get("executedQty"))
    cum_quote = _safe_decimal(response.get("cumQuote"))
    if executed_qty is None or cum_quote is None or executed_qty == 0:
        return "n/a"
    return format_decimal(cum_quote / executed_qty)


def _safe_decimal(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
