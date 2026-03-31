"""Lightweight Flask UI for the Binance Futures Testnet bot."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import Flask, render_template, request

from bot.client import DEFAULT_BASE_URL, BinanceFuturesClient
from bot.exceptions import TradingBotError
from bot.logging_config import configure_logging
from bot.orders import OrderService
from bot.response_utils import summarize_order_response
from bot.runtime import load_environment, require_setting
from bot.validators import extract_symbol_rules

DEFAULT_FORM_DATA = {
    "symbol": "BTCUSDT",
    "side": "BUY",
    "order_type": "MARKET",
    "quantity": "0.002",
    "price": "",
    "time_in_force": "GTC",
}


def create_app() -> Flask:
    load_environment()
    app = Flask(__name__)

    @app.get("/")
    def index() -> str:
        form_data = dict(DEFAULT_FORM_DATA)
        snapshot = get_market_snapshot(form_data["symbol"])
        return render_template(
            "index.html",
            base_url=DEFAULT_BASE_URL,
            form_data=form_data,
            snapshot=snapshot,
            result=None,
        )

    @app.post("/")
    def submit() -> str:
        form_data = get_form_data(request.form)
        snapshot = get_market_snapshot(form_data["symbol"])
        result = submit_order(form_data)
        return render_template(
            "index.html",
            base_url=DEFAULT_BASE_URL,
            form_data=form_data,
            snapshot=snapshot,
            result=result,
        )

    return app


def get_form_data(form: Any) -> dict[str, str]:
    return {
        "symbol": form.get("symbol", DEFAULT_FORM_DATA["symbol"]).strip().upper(),
        "side": form.get("side", DEFAULT_FORM_DATA["side"]).strip().upper(),
        "order_type": form.get("order_type", DEFAULT_FORM_DATA["order_type"]).strip().upper(),
        "quantity": form.get("quantity", DEFAULT_FORM_DATA["quantity"]).strip(),
        "price": form.get("price", "").strip(),
        "time_in_force": form.get("time_in_force", DEFAULT_FORM_DATA["time_in_force"])
        .strip()
        .upper(),
    }


def get_market_snapshot(symbol: str) -> dict[str, str] | None:
    normalized_symbol = symbol.strip().upper()
    if not normalized_symbol:
        return None

    try:
        with BinanceFuturesClient(api_key="", api_secret="", base_url=DEFAULT_BASE_URL) as client:
            latest_price = client.get_latest_price(normalized_symbol)
            symbol_info = client.get_symbol_info(normalized_symbol)
            rules = extract_symbol_rules(symbol_info)
    except TradingBotError as exc:
        return {"symbol": normalized_symbol, "error": str(exc)}
    except Exception as exc:  # pragma: no cover - defensive UI fallback
        return {"symbol": normalized_symbol, "error": f"Unable to load market snapshot: {exc}"}

    return {
        "symbol": normalized_symbol,
        "status": str(symbol_info.get("status", "UNKNOWN")),
        "latest_price": str(latest_price),
        "tick_size": str(rules.price_tick_size),
        "min_qty": str(rules.lot_min_qty),
        "market_min_qty": str(rules.market_min_qty),
        "min_notional": str(rules.min_notional or "n/a"),
        "time_in_force": ", ".join(sorted(rules.time_in_force)),
    }


def submit_order(form_data: dict[str, str]) -> dict[str, Any]:
    load_environment()
    log_path = build_order_log_path(form_data["order_type"])
    configure_logging(str(log_path))

    try:
        api_key = require_setting(os.getenv("BINANCE_API_KEY"), setting_name="BINANCE_API_KEY")
        api_secret = require_setting(
            os.getenv("BINANCE_API_SECRET"),
            setting_name="BINANCE_API_SECRET",
        )

        with BinanceFuturesClient(
            api_key=api_key,
            api_secret=api_secret,
            base_url=DEFAULT_BASE_URL,
        ) as client:
            order_service = OrderService(client)
            order_request = order_service.prepare_order(
                symbol=form_data["symbol"],
                side=form_data["side"],
                order_type=form_data["order_type"],
                quantity=form_data["quantity"],
                price=form_data["price"] or None,
                time_in_force=form_data["time_in_force"],
            )
            response = order_service.place_order(order_request)
    except TradingBotError as exc:
        return {
            "ok": False,
            "message": str(exc),
            "log_path": str(log_path),
        }
    except Exception as exc:  # pragma: no cover - defensive UI fallback
        return {
            "ok": False,
            "message": f"Unexpected error: {exc}",
            "log_path": str(log_path),
        }

    return {
        "ok": True,
        "message": "Order submitted successfully.",
        "request_summary": order_request.to_display_dict(),
        "response_details": summarize_order_response(response),
        "raw_response": response,
        "log_path": str(log_path),
    }


def build_order_log_path(order_type: str) -> Path:
    timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    order_label = order_type.strip().lower() or "order"
    return Path("logs") / f"ui_{order_label}_{timestamp}.log"


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
