"""Order preparation and submission orchestration."""

from __future__ import annotations

import logging
from typing import Any

from .client import BinanceFuturesClient
from .models import OrderRequest
from .validators import validate_and_build_order


class OrderService:
    """Validate order input and submit it through the Binance client."""

    def __init__(self, client: BinanceFuturesClient) -> None:
        self.client = client
        self.logger = logging.getLogger(__name__)

    def prepare_order(
        self,
        *,
        symbol: str,
        side: str,
        order_type: str,
        quantity: str,
        price: str | None = None,
        time_in_force: str | None = None,
    ) -> OrderRequest:
        normalized_symbol = symbol.strip().upper()
        symbol_info = self.client.get_symbol_info(normalized_symbol)
        reference_price = None
        if order_type.strip().upper() == "MARKET":
            reference_price = self.client.get_latest_price(normalized_symbol)

        order_request = validate_and_build_order(
            symbol_info=symbol_info,
            symbol=normalized_symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            time_in_force=time_in_force,
            reference_price=reference_price,
        )

        self.logger.info(
            "order_validated",
            extra={
                "event": "order_validated",
                "order_request": order_request.to_display_dict(),
            },
        )
        return order_request

    def place_order(self, order_request: OrderRequest) -> dict[str, Any]:
        self.logger.info(
            "order_submission_started",
            extra={
                "event": "order_submission_started",
                "order_request": order_request.to_display_dict(),
            },
        )
        response = self.client.place_order(order_request.to_api_params())
        self.logger.info(
            "order_submission_completed",
            extra={
                "event": "order_submission_completed",
                "order_response": response,
            },
        )
        return response
