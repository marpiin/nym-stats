import sqlite3
from dataclasses import dataclass
from html import escape

from nym_stats import alert_rule, store
from nym_stats.alert_rule import AlertRule
from nym_stats.snapshot import NodeSnapshot
from nym_stats.store import MonthlyRewards

MONTHS_SHOWN = 12


@dataclass(frozen=True)
class Summary:
    node_id: int
    latest: NodeSnapshot | None
    previous: NodeSnapshot | None
    months: list[MonthlyRewards]
    alerts: list[str]


def build_summary(conn: sqlite3.Connection, node_id: int, rule: AlertRule) -> Summary:
    readings = store.recent_readings(conn, node_id, max(rule.consecutive, 2))
    errors = store.recent_attempt_errors(conn, node_id, rule.consecutive)
    alerts = [
        alert
        for alert in (
            alert_rule.failed_fetches(errors, rule),
            alert_rule.low_performance(readings, rule),
        )
        if alert is not None
    ]
    return Summary(
        node_id=node_id,
        latest=readings[0] if readings else None,
        previous=readings[1] if len(readings) > 1 else None,
        months=store.monthly_rewards(conn, node_id)[-MONTHS_SHOWN:],
        alerts=alerts,
    )


def render_text(summary: Summary) -> str:
    lines = [_title(summary)]
    if summary.alerts:
        lines += ["", "Alerts", *summary.alerts]
    lines.append("")
    lines += [f"{label}: {value}" for label, value in _facts(summary)]
    if summary.months:
        lines += ["", "Rewards per month (NYM)", *_month_rows(summary)]
    return "\n".join(lines)


def render_html(summary: Summary) -> str:
    """Telegram HTML. Every value is escaped, including the API's and the error messages."""
    lines = [f"<b>{escape(_title(summary))}</b>"]
    if summary.alerts:
        lines += ["", "<b>Alerts</b>", *(escape(alert) for alert in summary.alerts)]
    lines.append("")
    lines += [f"{escape(label)}: {escape(value)}" for label, value in _facts(summary)]
    if summary.months:
        rows = "\n".join(escape(row) for row in _month_rows(summary))
        lines += ["", "Rewards per month (NYM)", f"<pre>{rows}</pre>"]
    return "\n".join(lines)


def _title(summary: Summary) -> str:
    if summary.latest is None:
        return f"Nym node {summary.node_id}: no readings yet"
    return f"Nym node {summary.node_id}, reading of {summary.latest.day} (UTC)"


def _facts(summary: Summary) -> list[tuple[str, str]]:
    latest = summary.latest
    if latest is None:
        return []
    facts = [
        ("Total stake", _nym(latest.total_stake_nym)),
        ("Operator pledge", _nym(latest.pledge_nym)),
        ("Operator rewards not yet withdrawn", _nym(latest.operator_rewards_nym)),
    ]
    if summary.previous is not None:
        change = latest.operator_rewards_nym - summary.previous.operator_rewards_nym
        facts.append((f"Change since {summary.previous.day}", _nym(change, signed=True)))
    facts += [
        ("Profit margin", f"{latest.profit_margin * 100:.1f} %"),
        ("Operating cost per interval", _nym(latest.operating_cost_nym)),
        ("Performance", "unknown" if latest.performance is None else f"{latest.performance:.4f}"),
    ]
    if latest.uptime_percent is not None:
        facts.append((f"Uptime on {latest.uptime_date}", f"{latest.uptime_percent} %"))
    return facts


def _month_rows(summary: Summary) -> list[str]:
    return [f"{m.month}  {m.earned_nym:>14,.6f}" for m in summary.months]


def _nym(amount: float, signed: bool = False) -> str:
    return f"{amount:+,.6f} NYM" if signed else f"{amount:,.6f} NYM"
