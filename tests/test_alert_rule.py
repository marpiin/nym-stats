from conftest import make_snapshot

from nym_stats.alert_rule import AlertRule, failed_fetches, low_performance

RULE = AlertRule(min_performance=0.8, consecutive=3)


def readings(*performances):
    """Newest first, one day apart."""
    return [make_snapshot(f"2026-01-{20 - i:02d}", 100.0, p) for i, p in enumerate(performances)]


def test_alerts_after_n_low_readings_in_a_row():
    assert low_performance(readings(0.5, 0.79, 0.1), RULE) is not None


def test_no_alert_if_one_recent_reading_is_good():
    assert low_performance(readings(0.5, 0.9, 0.1), RULE) is None


def test_threshold_itself_is_not_low():
    assert low_performance(readings(0.8, 0.8, 0.8), RULE) is None


def test_no_alert_with_fewer_readings_than_n():
    assert low_performance(readings(0.1, 0.1), RULE) is None


def test_missing_performance_counts_as_low():
    assert low_performance(readings(None, 0.1, None), RULE) is not None


def test_alerts_after_n_failed_fetches_in_a_row():
    alert = failed_fetches(["timeout", "HTTP 503", "HTTP 503"], RULE)
    assert alert == "The last 3 fetches failed. Latest error: timeout"


def test_success_resets_failure_count():
    assert failed_fetches(["timeout", None, "HTTP 503"], RULE) is None
