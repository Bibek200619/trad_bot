"""Domain models used by the trading bot."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


def format_decimal(value: Decimal) -> str:
    """Render Decimal values without scientific notation."""
    return format(value.normalize(), "f")


@dataclass(frozen=True, slots=True)
class OrderRequest:
    """Normalized order request ready for Binance Futures."""

    symbol: str
    side: str
    order_type: str
    quantity: Decimal
    price: Decimal | None = None
    time_in_force: str | None = None

    def to_api_params(self) -> dict[str, str]:
        params = {
            "symbol": self.symbol,
            "side": self.side,
            "type": self.order_type,
            "quantity": format_decimal(self.quantity),
            "newOrderRespType": "RESULT",
        }

        if self.order_type == "LIMIT":
            if self.price is None:
                raise ValueError("price is required for LIMIT orders")
            params["price"] = format_decimal(self.price)
            params["timeInForce"] = self.time_in_force or "GTC"

        return params

    def to_display_dict(self) -> dict[str, str]:
        payload = {
            "symbol": self.symbol,
            "side": self.side,
            "orderType": self.order_type,
            "quantity": format_decimal(self.quantity),
        }

        if self.price is not None:
            payload["price"] = format_decimal(self.price)
        if self.time_in_force is not None:
            payload["timeInForce"] = self.time_in_force

        return payload
