import pytest
import requests
from conftest import NODE_ID, FakeResponse, load_fixture

from nym_stats import cli, http_client, store

TOKEN = "123456:SYNTHETIC-TOKEN-FOR-TESTS"


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # so no real .env is picked up
    monkeypatch.setenv("NYM_NODE_ID", str(NODE_ID))
    monkeypatch.setenv("NYM_API_URL", "https://nym-api.example.invalid/api")
    monkeypatch.setenv("NYM_STATS_DB", str(tmp_path / "test.sqlite3"))
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", TOKEN)
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    monkeypatch.setattr(http_client, "BACKOFF_SECONDS", 0)
    return tmp_path


def serve(monkeypatch, responder):
    """Route every requests.Session.request through `responder(method, url)`."""
    monkeypatch.setattr(
        requests.Session, "request", lambda self, method, url, **kw: responder(method, url)
    )


def test_fetch_stores_one_reading_per_day(env, monkeypatch):
    bodies = {
        "bonded": load_fixture("bonded.json"),
        "performance": load_fixture("performance.json"),
        "uptime-history": load_fixture("uptime_history.json"),
    }
    calls = []

    def responder(method, url):
        calls.append(url)
        return FakeResponse(200, next(v for k, v in bodies.items() if f"/{k}" in url))

    serve(monkeypatch, responder)
    assert cli.main(["fetch"]) == 0
    assert cli.main(["fetch"]) == 0  # same day: skipped before any request
    assert len(calls) == 3
    conn = store.connect(env / "test.sqlite3")
    assert len(store.recent_readings(conn, NODE_ID, 10)) == 1
    conn.close()


def test_failed_fetch_exits_nonzero_and_is_recorded(env, monkeypatch, caplog):
    serve(monkeypatch, lambda method, url: FakeResponse(503))
    assert cli.main(["fetch"]) == 1
    assert "fetch failed: nym-api bonded: HTTP 503" in caplog.text
    conn = store.connect(env / "test.sqlite3")
    assert store.recent_attempt_errors(conn, NODE_ID, 5)[0].startswith("nym-api bonded")
    conn.close()


def test_telegram_failure_never_logs_the_token(env, monkeypatch, caplog, capsys):
    def responder(method, url):
        raise requests.ConnectionError(f"could not connect to {url}")

    serve(monkeypatch, responder)
    assert cli.main(["notify"]) == 1
    output = caplog.text + capsys.readouterr().err
    assert "telegram sendMessage: ConnectionError" in output
    assert TOKEN not in output


def test_notify_requires_telegram_settings(env, monkeypatch, caplog):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "")
    assert cli.main(["notify"]) == 1
    assert "TELEGRAM_BOT_TOKEN" in caplog.text
