import logging
import time
from collections.abc import Callable
from typing import Any

import requests

from nym_stats import __version__

log = logging.getLogger(__name__)

USER_AGENT = f"nym-stats/{__version__}"
TIMEOUT_SECONDS = 10
ATTEMPTS = 3
BACKOFF_SECONDS = 2.0
RETRY_STATUSES = {429, 500, 502, 503, 504}


class RequestFailed(Exception):
    """A request that failed for good. The message never contains the request URL."""


def request_json(
    session: requests.Session,
    method: str,
    url: str,
    *,
    label: str,
    sleep: Callable[[float], None] = time.sleep,
    **kwargs: Any,
) -> dict:
    """Send one request, retrying connection errors and 429/5xx with growing waits.

    `label` is what appears in logs and errors instead of the URL, because the
    Telegram URL contains the bot token.
    """
    for attempt in range(1, ATTEMPTS + 1):
        try:
            response = session.request(
                method, url, timeout=TIMEOUT_SECONDS, headers={"User-Agent": USER_AGENT}, **kwargs
            )
        except requests.RequestException as exc:
            # str(exc) usually repeats the URL, so only the exception type is kept.
            reason = type(exc).__name__
        else:
            if response.status_code < 400:
                return _json_body(response, label)
            reason = f"HTTP {response.status_code} {response.text[:200]}".strip()
            if response.status_code not in RETRY_STATUSES:
                raise RequestFailed(f"{label}: {reason}")
        if attempt < ATTEMPTS:
            delay = BACKOFF_SECONDS * 2 ** (attempt - 1)
            log.warning(
                "%s: %s, retry %d of %d in %.0fs", label, reason, attempt, ATTEMPTS - 1, delay
            )
            sleep(delay)
    raise RequestFailed(f"{label}: {reason} after {ATTEMPTS} attempts")


def _json_body(response: requests.Response, label: str) -> dict:
    try:
        body = response.json()
    except ValueError:
        raise RequestFailed(f"{label}: response is not JSON") from None
    if not isinstance(body, dict):
        raise RequestFailed(f"{label}: expected a JSON object")
    return body
