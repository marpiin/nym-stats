from dataclasses import dataclass

from nym_stats.snapshot import NodeSnapshot


@dataclass(frozen=True)
class AlertRule:
    min_performance: float  # 0 to 1
    consecutive: int  # how many readings or fetches in a row before alerting


def low_performance(readings: list[NodeSnapshot], rule: AlertRule) -> str | None:
    """`readings` newest first."""
    recent = readings[: rule.consecutive]
    if len(recent) < rule.consecutive:
        return None
    # No score at all is treated as a low score: either way the node is not being rated well.
    if all(r.performance is None or r.performance < rule.min_performance for r in recent):
        return f"Performance below {rule.min_performance:.2f} for the last {len(recent)} readings"
    return None


def failed_fetches(errors: list[str | None], rule: AlertRule) -> str | None:
    """`errors` newest first, None for a successful fetch."""
    failures = 0
    for error in errors:
        if error is None:
            break
        failures += 1
    if failures < rule.consecutive:
        return None
    return f"The last {failures} fetches failed. Latest error: {errors[0]}"
