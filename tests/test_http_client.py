import pytest
import requests
from conftest import FakeResponse, FakeSession

from nym_stats.http_client import ATTEMPTS, RequestFailed, request_json

URL = "https://api.example.invalid/thing"


def call(session, sleeps):
    return request_json(session, "GET", URL, label="test", sleep=sleeps.append)


def test_retries_5xx_with_growing_waits_then_succeeds():
    sleeps = []
    session = FakeSession([FakeResponse(503), FakeResponse(502), FakeResponse(200, {"ok": True})])
    assert call(session, sleeps) == {"ok": True}
    assert sleeps == [2.0, 4.0]


def test_gives_up_after_last_attempt():
    sleeps = []
    session = FakeSession([FakeResponse(500) for _ in range(ATTEMPTS)])
    with pytest.raises(RequestFailed, match=f"HTTP 500 after {ATTEMPTS} attempts"):
        call(session, sleeps)
    assert len(session.calls) == ATTEMPTS


def test_client_error_is_not_retried():
    session = FakeSession([FakeResponse(404, text="not found")])
    with pytest.raises(RequestFailed, match="HTTP 404 not found"):
        call(session, [])
    assert len(session.calls) == 1


def test_error_message_does_not_repeat_the_url():
    telegram_url = "https://api.telegram.org/bot123456:SYNTHETIC-TOKEN/sendMessage"
    session = FakeSession([requests.ConnectionError(f"failed to reach {telegram_url}")] * ATTEMPTS)
    with pytest.raises(RequestFailed) as excinfo:
        request_json(session, "POST", telegram_url, label="telegram", sleep=lambda _: None)
    assert "SYNTHETIC-TOKEN" not in str(excinfo.value)
    assert "ConnectionError" in str(excinfo.value)
