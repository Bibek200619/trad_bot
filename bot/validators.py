"""Validation helpers for CLI input and Binance exchange rules."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from .exceptions import ValidationError
from .models import OrderRequest

SUPPORTED_SIDES = {"BUY", "SELL"}
SUPPORTED_ORDER_TYPES = {"MARKET", "LIMIT"}
DEFAULT_TIME_IN_FORCE = "GTC"


@dataclass(frozen=True, slots=True)
class SymbolRules:
    """Relevant exchange filters for a single futures symbol."""

    symbol: str
    order_types: set[str]
    time_in_force: set[str]
    price_tick_size: Decimal
    min_price: Decimal
    max_price: Decimal
    lot_min_qty: Decimal
    lot_max_qty: Decimal
    lot_step_size: Decimal
    market_min_qty: Decimal
    market_max_qty: Decimal
    market_step_size: Decimal
    min_notional: Decimal | None


def validate_and_build_order(
    *,
    symbol_info: dict[str, Any],
    symbol: str,
    side: str,
    order_type: str,
    quantity: str,
    price: str | None,
    time_in_force: str | None = None,
    reference_price: Decimal | None = None,
) -> OrderRequest:
    normalized_symbol = normalize_symbol(symbol)
    normalized_side = normalize_side(side)
    normalized_order_type = normalize_order_type(order_type)
    normalized_time_in_force = normalize_time_in_force(
        time_in_force or DEFAULT_TIME_IN_FORCE,
    )

    rules = extract_symbol_rules(symbol_info)

    if normalized_symbol != rules.symbol:
        raise ValidationError(
            f"Symbol mismatch: expected exchange metadata for {rules.symbol}, got {normalized_symbol}."
        )
    if symbol_info.get("status") != "TRADING":
        raise ValidationError(f"Symbol {normalized_symbol} is not currently tradable.")
    if normalized_order_type not in rules.order_types:
        raise ValidationError(
            f"{normalized_order_type} is not supported for {normalized_symbol}."
        )

    quantity_value = parse_positive_decimal(quantity, field_name="quantity")
    quantity_rules = (
        _market_quantity_rules(rules)
        if normalized_order_type == "MARKET"
        else _limit_quantity_rules(rules)
    )
    validate_range(
        quantity_value,
        minimum=quantity_rules["min_qty"],
        maximum=quantity_rules["max_qty"],
        field_name="quantity",
    )
    validate_step_alignment(
        quantity_value,
        step=quantity_rules["step_size"],
        field_name="quantity",
    )

    price_value: Decimal | None = None
    if normalized_order_type == "LIMIT":
        if price is None:
            raise ValidationError("price is required for LIMIT orders.")
        price_value = parse_positive_decimal(price, field_name="price")
        validate_range(
            price_value,
            minimum=rules.min_price,
            maximum=rules.max_price,
            field_name="price",
        )
        validate_step_alignment(
            price_value,
            step=rules.price_tick_size,
            field_name="price",
        )
        if normalized_time_in_force not in rules.time_in_force:
            raise ValidationError(
                f"time in force {normalized_time_in_force} is not supported for {normalized_symbol}."
            )
    elif price is not None:
        raise ValidationError("price must not be provided for MARKET orders.")

    validate_notional(
        quantity_value=quantity_value,
        price_value=price_value,
        reference_price=reference_price,
        min_notional=rules.min_notional,
        order_type=normalized_order_type,
    )

    return OrderRequest(
        symbol=normalized_symbol,
        side=normalized_side,
        order_type=normalized_order_type,
        quantity=quantity_value,
        price=price_value,
        time_in_force=(
            normalized_time_in_force if normalized_order_type == "LIMIT" else None
        ),
    )


def normalize_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if not normalized:
        raise ValidationError("symbol is required.")
    return normalized


def normalize_side(side: str) -> str:
    normalized = side.strip().upper()
    if normalized not in SUPPORTED_SIDES:
        raise ValidationError(f"side must be one of {sorted(SUPPORTED_SIDES)}.")
    return normalized


def normalize_order_type(order_type: str) -> str:
    normalized = order_type.strip().upper()
    if normalized not in SUPPORTED_ORDER_TYPES:
        raise ValidationError(
            f"order type must be one of {sorted(SUPPORTED_ORDER_TYPES)}."
        )
    return normalized


def normalize_time_in_force(time_in_force: str) -> str:
    normalized = time_in_force.strip().upper()
    if not normalized:
        raise ValidationError("time in force must not be empty.")
    return normalized


def parse_positive_decimal(raw_value: str, *, field_name: str) -> Decimal:
    try:
        value = Decimal(raw_value)
    except InvalidOperation as exc:
        raise ValidationError(f"{field_name} must be a valid decimal number.") from exc

    if value <= 0:
        raise ValidationError(f"{field_name} must be greater than zero.")
    return value


def extract_symbol_rules(symbol_info: dict[str, Any]) -> SymbolRules:
    filters = {item["filterType"]: item for item in symbol_info.get("filters", [])}
    price_filter = filters.get("PRICE_FILTER")
    lot_filter = filters.get("LOT_SIZE")
    market_lot_filter = filters.get("MARKET_LOT_SIZE", lot_filter)
    min_notional_filter = filters.get("MIN_NOTIONAL")

    if not price_filter or not lot_filter or not market_lot_filter:
        raise ValidationError(
            f"Incomplete exchange filters returned for {symbol_info.get('symbol', '<unknown>')}."
        )

    return SymbolRules(
        symbol=symbol_info["symbol"],
        order_types=set(symbol_info.get("orderTypes", [])),
        time_in_force=set(symbol_info.get("timeInForce", [])),
        price_tick_size=Decimal(price_filter["tickSize"]),
        min_price=Decimal(price_filter["minPrice"]),
        max_price=Decimal(price_filter["maxPrice"]),
        lot_min_qty=Decimal(lot_filter["minQty"]),
        lot_max_qty=Decimal(lot_filter["maxQty"]),
        lot_step_size=Decimal(lot_filter["stepSize"]),
        market_min_qty=Decimal(market_lot_filter["minQty"]),
        market_max_qty=Decimal(market_lot_filter["maxQty"]),
        market_step_size=Decimal(market_lot_filter["stepSize"]),
        min_notional=(
            Decimal(min_notional_filter["notional"])
            if min_notional_filter is not None
            else None
        ),
    )


def validate_range(
    value: Decimal,
    *,
    minimum: Decimal,
    maximum: Decimal,
    field_name: str,
) -> None:
    if minimum and value < minimum:
        raise ValidationError(f"{field_name} must be at least {minimum}.")
    if maximum and value > maximum:
        raise ValidationError(f"{field_name} must be at most {maximum}.")


def validate_step_alignment(
    value: Decimal,
    *,
    step: Decimal,
    field_name: str,
) -> None:
    if step == 0:
        return

    multiplier = value / step
    if multiplier != multiplier.to_integral_value():
        raise ValidationError(f"{field_name} must align with step size {step}.")


def validate_notional(
    *,
    quantity_value: Decimal,
    price_value: Decimal | None,
    reference_price: Decimal | None,
    min_notional: Decimal | None,
    order_type: str,
) -> None:
    if min_notional is None:
        return

    if order_type == "LIMIT":
        assert price_value is not None
        notional = quantity_value * price_value
    else:
        if reference_price is None:
            return
        notional = quantity_value * reference_price

    if notional < min_notional:
        raise ValidationError(
            f"order notional must be at least {min_notional}; got {notional}."
        )


def _market_quantity_rules(rules: SymbolRules) -> dict[str, Decimal]:
    return {
        "min_qty": rules.market_min_qty,
        "max_qty": rules.market_max_qty,
        "step_size": rules.market_step_size,
    }


def _limit_quantity_rules(rules: SymbolRules) -> dict[str, Decimal]:
    return {
        "min_qty": rules.lot_min_qty,
        "max_qty": rules.lot_max_qty,
        "step_size": rules.lot_step_size,
    }
