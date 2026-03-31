"""Runtime helpers shared by the CLI and UI entry points."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

from .exceptions import ConfigurationError

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"


def load_environment() -> None:
    """Load local environment variables from the project root."""
    load_dotenv(dotenv_path=ENV_PATH)


def require_setting(value: str | None, *, setting_name: str) -> str:
    if value:
        return value
    raise ConfigurationError(
        f"Missing {setting_name}. Set it in your environment or pass it on the CLI."
    )
