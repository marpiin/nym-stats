import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import pytest

from nym_stats import store
from nym_stats.snapshot import NodeSnapshot

FIXTURES = Path(__file__).parent / "fixtures"
NODE_ID = 900001  # synthetic; real node ids are far lower


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@dataclass
class FakeResponse:
    status_code: int
    body: object = None
    text: str = ""

    def json(self) -> object:
        if self.body is None:
            raise ValueError("no JSON")
        return self.body


@dataclass
class FakeSession:
    """Plays back queued responses (or raises queued exceptions) and records requests."""

    responses: list
    calls: list = field(default_factory=list)

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def make_snapshot(
    day: str, operator_nym: float, performance: float | None = 0.95, pledge_nym: float = 100.0
) -> NodeSnapshot:
    return NodeSnapshot(
        node_id=NODE_ID,
        taken_at=datetime.fromisoformat(f"{day}T12:00:00").replace(tzinfo=UTC),
        operator_nym=operator_nym,
        pledge_nym=pledge_nym,
        delegates_nym=5000.0,
        profit_margin=0.2,
        operating_cost_nym=40.0,
        performance=performance,
        uptime_percent=100,
        uptime_date=day,
    )


@pytest.fixture
def conn(tmp_path):
    connection = store.connect(tmp_path / "test.sqlite3")
    yield connection
    connection.close()
