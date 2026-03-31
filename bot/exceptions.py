"""Custom exceptions for the trading bot."""


class TradingBotError(Exception):
    """Base exception for all trading bot errors."""


class ConfigurationError(TradingBotError):
    """Raised when the application configuration is incomplete."""


class ValidationError(TradingBotError):
    """Raised when CLI input fails validation."""


class BinanceNetworkError(TradingBotError):
    """Raised when a network failure prevents an API call."""


class BinanceAPIError(TradingBotError):
    """Raised when Binance returns an API error response."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        error_code: int | None = None,
    ) -> None:
        self.status_code = status_code
        self.error_code = error_code
        details: list[str] = [message]
        if error_code is not None:
            details.append(f"code={error_code}")
        if status_code is not None:
            details.append(f"http_status={status_code}")
        super().__init__(" | ".join(details))
