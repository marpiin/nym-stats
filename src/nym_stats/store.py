import csv
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from importlib import resources
from pathlib import Path

from nym_stats.snapshot import NodeSnapshot

READING_COLUMNS = (
    "node_id",
    "taken_at",
    "day",
    "operator_nym",
    "pledge_nym",
    "delegates_nym",
    "profit_margin",
    "operating_cost_nym",
    "performance",
    "uptime_percent",
    "uptime_date",
)

# Rewards earned between consecutive readings, summed by the month of the later
# reading. A negative step means rewards were withdrawn (or the pledge lowered),
# not that the node lost money, so it counts as zero.
MONTHLY_REWARDS_SQL = """
WITH step AS (
    SELECT
        day,
        (operator_nym - pledge_nym)
            - LAG(operator_nym - pledge_nym) OVER (ORDER BY day) AS earned
    FROM reading
    WHERE node_id = ?
)
SELECT substr(day, 1, 7) AS month, SUM(MAX(earned, 0)) AS earned_nym, COUNT(*) AS steps
FROM step
WHERE earned IS NOT NULL
GROUP BY month
ORDER BY month
"""


@dataclass(frozen=True)
class MonthlyRewards:
    month: str  # YYYY-MM
    earned_nym: float
    steps: int  # number of reading-to-reading differences behind the sum


def connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(resources.files("nym_stats").joinpath("schema.sql").read_text("utf-8"))
    return conn


def has_reading_for_day(conn: sqlite3.Connection, node_id: int, day: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM reading WHERE node_id = ? AND day = ?", (node_id, day)
    ).fetchone()
    return row is not None


def save_reading(conn: sqlite3.Connection, snapshot: NodeSnapshot) -> bool:
    """Store a reading. Returns False if that node already has one for that day."""
    values = (
        snapshot.node_id,
        snapshot.taken_at.isoformat(),
        snapshot.day,
        snapshot.operator_nym,
        snapshot.pledge_nym,
        snapshot.delegates_nym,
        snapshot.profit_margin,
        snapshot.operating_cost_nym,
        snapshot.performance,
        snapshot.uptime_percent,
        snapshot.uptime_date,
    )
    placeholders = ", ".join("?" for _ in READING_COLUMNS)
    with conn:
        cursor = conn.execute(
            f"INSERT INTO reading ({', '.join(READING_COLUMNS)}) VALUES ({placeholders}) "
            "ON CONFLICT (node_id, day) DO NOTHING",
            values,
        )
    return cursor.rowcount == 1


def record_attempt(
    conn: sqlite3.Connection, node_id: int, attempted_at: datetime, error: str | None
) -> None:
    with conn:
        conn.execute(
            "INSERT INTO fetch_attempt (node_id, attempted_at, error) VALUES (?, ?, ?)",
            (node_id, attempted_at.isoformat(), error),
        )


def recent_readings(conn: sqlite3.Connection, node_id: int, limit: int) -> list[NodeSnapshot]:
    """Newest first."""
    rows = conn.execute(
        "SELECT * FROM reading WHERE node_id = ? ORDER BY day DESC LIMIT ?", (node_id, limit)
    ).fetchall()
    return [_snapshot(row) for row in rows]


def recent_attempt_errors(conn: sqlite3.Connection, node_id: int, limit: int) -> list[str | None]:
    """Newest first; None for a successful attempt."""
    rows = conn.execute(
        "SELECT error FROM fetch_attempt WHERE node_id = ? ORDER BY id DESC LIMIT ?",
        (node_id, limit),
    ).fetchall()
    return [row["error"] for row in rows]


def monthly_rewards(conn: sqlite3.Connection, node_id: int) -> list[MonthlyRewards]:
    rows = conn.execute(MONTHLY_REWARDS_SQL, (node_id,)).fetchall()
    return [MonthlyRewards(row["month"], row["earned_nym"], row["steps"]) for row in rows]


def export_csv(conn: sqlite3.Connection, node_id: int, path: Path, monthly: bool) -> int:
    """Write readings (or monthly totals) to CSV. Returns the number of rows written."""
    if monthly:
        header = ("month", "earned_nym", "steps")
        rows = [(m.month, m.earned_nym, m.steps) for m in monthly_rewards(conn, node_id)]
    else:
        header = READING_COLUMNS
        rows = conn.execute(
            f"SELECT {', '.join(READING_COLUMNS)} FROM reading WHERE node_id = ? ORDER BY day",
            (node_id,),
        ).fetchall()
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
    return len(rows)


def _snapshot(row: sqlite3.Row) -> NodeSnapshot:
    return NodeSnapshot(
        node_id=row["node_id"],
        taken_at=datetime.fromisoformat(row["taken_at"]),
        operator_nym=row["operator_nym"],
        pledge_nym=row["pledge_nym"],
        delegates_nym=row["delegates_nym"],
        profit_margin=row["profit_margin"],
        operating_cost_nym=row["operating_cost_nym"],
        performance=row["performance"],
        uptime_percent=row["uptime_percent"],
        uptime_date=row["uptime_date"],
    )
