from datetime import UTC, datetime

import pytest
from conftest import NODE_ID, FakeResponse, FakeSession, load_fixture

from nym_stats import nym_api
from nym_stats.http_client import USER_AGENT
from nym_stats.nym_api import SnapshotError

NOW = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)


def parse(node_id=NODE_ID, bonded=None, performance=None, uptime=None):
    return nym_api.parse_snapshot(
        node_id,
        NOW,
        bonded or load_fixture("bonded.json"),
        performance or load_fixture("performance.json"),
        uptime or load_fixture("uptime_history.json"),
    )


def test_reads_node_from_api_responses():
    snapshot = parse()
    assert snapshot.operator_nym == pytest.approx(112.50000025)
    assert snapshot.pledge_nym == pytest.approx(100.0)
    assert snapshot.operator_rewards_nym == pytest.approx(12.50000025)
    assert snapshot.total_stake_nym == pytest.approx(50_112.50000025)
    assert snapshot.profit_margin == pytest.approx(0.2)
    assert snapshot.operating_cost_nym == pytest.approx(40.0)
    assert snapshot.performance == pytest.approx(0.9512)
    assert (snapshot.uptime_percent, snapshot.uptime_date) == (99, "2026-01-15")


def test_amount_may_be_integer_or_string():
    assert parse(node_id=900002).pledge_nym == pytest.approx(200.0)


def test_missing_field_is_an_error():
    bonded = load_fixture("bonded.json")
    del bonded["data"][0]["rewarding_details"]["operator"]
    with pytest.raises(SnapshotError, match="'operator' missing"):
        parse(bonded=bonded)


def test_null_performance_is_kept_as_unknown():
    assert parse(performance={"node_id": NODE_ID, "performance": None}).performance is None


def test_node_not_bonded():
    with pytest.raises(SnapshotError, match="not bonded"):
        parse(node_id=123)


def test_node_missing_because_page_was_capped():
    bonded = load_fixture("bonded.json")
    bonded["pagination"]["total"] = 9000
    with pytest.raises(SnapshotError, match="capped"):
        parse(node_id=123, bonded=bonded)


def test_fetch_makes_one_request_per_endpoint():
    session = FakeSession(
        [
            FakeResponse(200, load_fixture("bonded.json")),
            FakeResponse(200, load_fixture("performance.json")),
            FakeResponse(200, load_fixture("uptime_history.json")),
        ]
    )
    nym_api.fetch_node_snapshot(session, "https://nym-api.example.invalid/api/", NODE_ID, NOW)
    urls = [url for _, url, _ in session.calls]
    assert urls == [
        "https://nym-api.example.invalid/api/v1/nym-nodes/bonded",
        f"https://nym-api.example.invalid/api/v1/nym-nodes/performance/{NODE_ID}",
        f"https://nym-api.example.invalid/api/v1/nym-nodes/uptime-history/{NODE_ID}",
    ]
    for _, _, kwargs in session.calls:
        assert kwargs["headers"]["User-Agent"] == USER_AGENT
        assert kwargs["timeout"] > 0
