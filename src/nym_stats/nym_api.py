"""Reads one node from nym-api. Endpoints and fields are listed in docs/data-sources.md."""

from datetime import datetime
from typing import Any

import requests

from nym_stats.http_client import request_json
from nym_stats.snapshot import NodeSnapshot

UNYM_PER_NYM = 1_000_000
# Large enough that the whole bonded set (about 1100 nodes in October 2026) fits in one page.
BONDED_PAGE_SIZE = 5000


class SnapshotError(Exception):
    """The API answered, but not with what this program expects."""


def fetch_node_snapshot(
    session: requests.Session, api_url: str, node_id: int, now: datetime
) -> NodeSnapshot:
    base = api_url.rstrip("/")
    bonded = request_json(
        session,
        "GET",
        f"{base}/v1/nym-nodes/bonded",
        label="nym-api bonded",
        params={"per_page": BONDED_PAGE_SIZE},
    )
    performance = request_json(
        session, "GET", f"{base}/v1/nym-nodes/performance/{node_id}", label="nym-api performance"
    )
    uptime = request_json(
        session, "GET", f"{base}/v1/nym-nodes/uptime-history/{node_id}", label="nym-api uptime"
    )
    return parse_snapshot(node_id, now, bonded, performance, uptime)


def parse_snapshot(
    node_id: int, now: datetime, bonded: dict, performance: dict, uptime: dict
) -> NodeSnapshot:
    node = _find_node(bonded, node_id)
    bond = _field(node, "bond_information")
    rewarding = _field(node, "rewarding_details")
    cost = _field(rewarding, "cost_params")
    uptime_percent, uptime_date = _latest_uptime(uptime)
    return NodeSnapshot(
        node_id=node_id,
        taken_at=now,
        operator_nym=_nym(_field(rewarding, "operator")),
        pledge_nym=_coin_nym(_field(bond, "original_pledge")),
        delegates_nym=_nym(_field(rewarding, "delegates")),
        profit_margin=float(_field(cost, "profit_margin_percent")),
        operating_cost_nym=_coin_nym(_field(cost, "interval_operating_cost")),
        performance=_performance(performance),
        uptime_percent=uptime_percent,
        uptime_date=uptime_date,
    )


def _find_node(bonded: dict, node_id: int) -> dict:
    nodes = _field(bonded, "data")
    for node in nodes:
        if _field(_field(node, "bond_information"), "node_id") == node_id:
            return node
    total = _field(_field(bonded, "pagination"), "total")
    if total > len(nodes):
        raise SnapshotError(
            f"node {node_id} not in the {len(nodes)} nodes returned out of {total}; "
            "the API capped the page size"
        )
    raise SnapshotError(f"node {node_id} is not bonded")


def _performance(body: dict) -> float | None:
    # The spec marks `performance` as optional and nullable, so absence is not an error.
    value = body.get("performance")
    if value is not None and not isinstance(value, int | float):
        raise SnapshotError(f"performance is not a number: {value!r}")
    return value


def _latest_uptime(body: dict) -> tuple[int | None, str | None]:
    entries = _field(_field(body, "history"), "data")
    if not entries:
        return None, None
    latest = max(entries, key=lambda entry: _field(entry, "date"))
    # The OpenAPI schema calls this field `performance`; the live API sends `uptime`.
    return int(_field(latest, "uptime")), _field(latest, "date")


def _coin_nym(coin: dict) -> float:
    denom = _field(coin, "denom")
    if denom != "unym":
        raise SnapshotError(f"unexpected denom {denom!r}")
    # The spec says integer; the live API sends a string. Both parse.
    return _nym(_field(coin, "amount"))


def _nym(unym: Any) -> float:
    try:
        return float(unym) / UNYM_PER_NYM
    except (TypeError, ValueError):
        raise SnapshotError(f"not an amount: {unym!r}") from None


def _field(obj: Any, key: str) -> Any:
    if not isinstance(obj, dict) or key not in obj:
        raise SnapshotError(f"field {key!r} missing from nym-api response")
    return obj[key]
