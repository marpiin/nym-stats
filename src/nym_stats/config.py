from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import TypeVar

from nym_stats.alert_rule import AlertRule

T = TypeVar("T")

DEFAULT_API_URL = "https://validator.nymtech.net/api"
DEFAULT_DB_PATH = "nym_stats.sqlite3"
DEFAULT_MIN_PERFORMANCE = 0.8
DEFAULT_CONSECUTIVE = 3


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Settings:
    node_id: int
    api_url: str
    db_path: Path
    alert_rule: AlertRule
    telegram_chat_id: str
    # Kept out of repr so printing the settings never shows the token.
    telegram_token: str = field(repr=False)


def load_settings(env: Mapping[str, str]) -> Settings:
    node_id = _number(env, "NYM_NODE_ID", None, int)
    if node_id is None:
        raise ConfigError("NYM_NODE_ID is not set")
    min_performance = _number(env, "ALERT_MIN_PERFORMANCE", DEFAULT_MIN_PERFORMANCE, float)
    if not 0 <= min_performance <= 1:
        raise ConfigError("ALERT_MIN_PERFORMANCE must be between 0 and 1")
    consecutive = _number(env, "ALERT_CONSECUTIVE", DEFAULT_CONSECUTIVE, int)
    if consecutive < 1:
        raise ConfigError("ALERT_CONSECUTIVE must be at least 1")
    return Settings(
        node_id=node_id,
        api_url=_value(env, "NYM_API_URL") or DEFAULT_API_URL,
        db_path=Path(_value(env, "NYM_STATS_DB") or DEFAULT_DB_PATH),
        alert_rule=AlertRule(min_performance, consecutive),
        telegram_chat_id=_value(env, "TELEGRAM_CHAT_ID") or "",
        telegram_token=_value(env, "TELEGRAM_BOT_TOKEN") or "",
    )


def _value(env: Mapping[str, str], name: str) -> str | None:
    # An empty value, as left by copying .env.example, means "not set".
    value = env.get(name, "").strip()
    return value or None


def _number(env: Mapping[str, str], name: str, default: T, kind: Callable[[str], T]) -> T:
    value = _value(env, name)
    if value is None:
        return default
    try:
        return kind(value)
    except ValueError:
        raise ConfigError(f"{name} must be a {kind.__name__}, got {value!r}") from None
