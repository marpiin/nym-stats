import csv

import pytest
from conftest import NODE_ID, make_snapshot

from nym_stats import store


def test_second_reading_on_same_day_is_rejected(conn):
    assert store.save_reading(conn, make_snapshot("2026-01-15", 110.0))
    assert not store.save_reading(conn, make_snapshot("2026-01-15", 999.0))
    readings = store.recent_readings(conn, NODE_ID, 10)
    assert [r.operator_nym for r in readings] == [110.0]


def test_monthly_rewards_come_from_differences_between_readings(conn):
    # Rewards (operator - pledge): 10, 12, 15 | 16, then withdrawn to 0, then 2.
    for day, operator in [
        ("2026-01-29", 110.0),
        ("2026-01-30", 112.0),
        ("2026-01-31", 115.0),
        ("2026-02-01", 116.0),
        ("2026-02-02", 100.0),
        ("2026-02-03", 102.0),
    ]:
        store.save_reading(conn, make_snapshot(day, operator))

    months = store.monthly_rewards(conn, NODE_ID)

    assert [m.month for m in months] == ["2026-01", "2026-02"]
    assert months[0].earned_nym == pytest.approx(5.0)
    assert months[0].steps == 2
    # 1 earned, the withdrawal counts as 0, then 2 earned.
    assert months[1].earned_nym == pytest.approx(3.0)
    assert months[1].steps == 3


def test_rerunning_a_day_does_not_change_monthly_totals(conn):
    store.save_reading(conn, make_snapshot("2026-01-01", 100.0))
    store.save_reading(conn, make_snapshot("2026-01-02", 101.0))
    before = store.monthly_rewards(conn, NODE_ID)
    store.save_reading(conn, make_snapshot("2026-01-02", 101.0))
    assert store.monthly_rewards(conn, NODE_ID) == before


def test_export_writes_readings_and_monthly_csv(conn, tmp_path):
    store.save_reading(conn, make_snapshot("2026-01-01", 100.0))
    store.save_reading(conn, make_snapshot("2026-01-02", 101.5))

    readings_csv = tmp_path / "readings.csv"
    assert store.export_csv(conn, NODE_ID, readings_csv, monthly=False) == 2
    rows = list(csv.DictReader(readings_csv.open(encoding="utf-8")))
    assert [row["day"] for row in rows] == ["2026-01-01", "2026-01-02"]

    monthly_csv = tmp_path / "monthly.csv"
    assert store.export_csv(conn, NODE_ID, monthly_csv, monthly=True) == 1
    (row,) = csv.DictReader(monthly_csv.open(encoding="utf-8"))
    assert float(row["earned_nym"]) == pytest.approx(1.5)


def test_attempt_errors_are_newest_first(conn):
    reading = make_snapshot("2026-01-01", 100.0)
    store.record_attempt(conn, NODE_ID, reading.taken_at, None)
    store.record_attempt(conn, NODE_ID, reading.taken_at, "first failure")
    store.record_attempt(conn, NODE_ID, reading.taken_at, "second failure")
    assert store.recent_attempt_errors(conn, NODE_ID, 5) == [
        "second failure",
        "first failure",
        None,
    ]
