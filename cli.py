"""CLI entry point for the Binance Futures Testnet trading bot."""

from __future__ import annotations

import argparse
import logging
import os
from typing import Any

from bot.client import DEFAULT_BASE_URL, BinanceFuturesClient
from bot.exceptions import TradingBotError
from bot.logging_config import configure_logging
from bot.models import OrderRequest
from bot.orders import OrderService
from bot.response_utils import summarize_order_response
from bot.runtime import load_environment, require_setting


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Place MARKET or LIMIT orders on Binance Futures Testnet.",
    )
    parser.add_argument("--symbol", required=True, help="Trading pair, e.g. BTCUSDT")
    parser.add_argument(
        "--side",
        required=True,
        help="Order side: BUY or SELL",
    )
    parser.add_argument(
        "--order-type",
        required=True,
        help="Order type: MARKET or LIMIT",
    )
    parser.add_argument(
        "--quantity",
        required=True,
        help="Order quantity using Binance lot size rules",
    )
    parser.add_argument(
        "--price",
        help="Limit price. Required for LIMIT orders and rejected for MARKET orders.",
    )
    parser.add_argument(
        "--time-in-force",
        default="GTC",
        help="Time in force for LIMIT orders. Defaults to GTC.",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("BINANCE_API_KEY"),
        help="Binance API key. Environment variable BINANCE_API_KEY is preferred.",
    )
    parser.add_argument(
        "--api-secret",
        default=os.getenv("BINANCE_API_SECRET"),
        help="Binance API secret. Environment variable BINANCE_API_SECRET is preferred.",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Binance Futures base URL. Defaults to {DEFAULT_BASE_URL}.",
    )
    parser.add_argument(
        "--log-file",
        help="Optional path for the JSON log file.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="HTTP timeout in seconds. Defaults to 10.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    load_environment()
    parser = build_parser()
    args = parser.parse_args(argv)
    log_path = configure_logging(args.log_file)
    logger = logging.getLogger(__name__)

    try:
        api_key = require_setting(args.api_key, setting_name="BINANCE_API_KEY")
        api_secret = require_setting(args.api_secret, setting_name="BINANCE_API_SECRET")

        with BinanceFuturesClient(
            api_key=api_key,
            api_secret=api_secret,
            base_url=args.base_url,
            timeout=args.timeout,
        ) as client:
            order_service = OrderService(client)
            order_request = order_service.prepare_order(
                symbol=args.symbol,
                side=args.side,
                order_type=args.order_type,
                quantity=args.quantity,
                price=args.price,
                time_in_force=args.time_in_force,
            )

            _print_request_summary(order_request)
            response = order_service.place_order(order_request)
            _print_response_details(response)
            print("Result: success")
            print(f"Log file: {log_path}")
            return 0
    except TradingBotError as exc:
        logger.error(
            "trading_bot_failed",
            extra={
                "event": "trading_bot_failed",
                "error": str(exc),
                "error_type": type(exc).__name__,
            },
        )
        print("Result: failure")
        print(f"Reason: {exc}")
        print(f"Log file: {log_path}")
        return 1
    except Exception as exc:  # pragma: no cover - defensive catch for CLI UX
        logger.exception("unexpected_failure")
        print("Result: failure")
        print(f"Reason: Unexpected error: {exc}")
        print(f"Log file: {log_path}")
        return 1
def _print_request_summary(order_request: OrderRequest) -> None:
    print("Order request summary:")
    for key, value in order_request.to_display_dict().items():
        print(f"  {key}: {value}")


def _print_response_details(response: dict[str, Any]) -> None:
    response_details = summarize_order_response(response)
    print("Order response details:")
    for key, value in response_details.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    raise SystemExit(main())
