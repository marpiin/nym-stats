from conftest import NODE_ID, make_snapshot

from nym_stats import report, store
from nym_stats.alert_rule import AlertRule
from nym_stats.report import Summary

RULE = AlertRule(min_performance=0.8, consecutive=2)


def test_html_escapes_every_external_value():
    summary = Summary(
        node_id=NODE_ID,
        latest=make_snapshot("2026-01-15", 112.5),
        previous=None,
        months=[],
        alerts=['nym-api bonded: HTTP 502 <html><script>alert("x")</script> & more'],
    )
    html = report.render_html(summary)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "&amp; more" in html
    # The only tags left are the ones the report adds itself.
    assert html.startswith("<b>Nym node")


def test_text_report_from_stored_readings(conn):
    store.save_reading(conn, make_snapshot("2026-01-14", 110.0, performance=0.5))
    store.save_reading(conn, make_snapshot("2026-01-15", 112.5, performance=0.4))
    store.record_attempt(conn, NODE_ID, make_snapshot("2026-01-15", 0).taken_at, None)

    text = report.render_text(report.build_summary(conn, NODE_ID, RULE))

    assert f"Nym node {NODE_ID}, reading of 2026-01-15 (UTC)" in text
    assert "Operator rewards not yet withdrawn: 12.500000 NYM" in text
    assert "Change since 2026-01-14: +2.500000 NYM" in text
    assert "2026-01        2.500000" in text
    assert "Performance below 0.80 for the last 2 readings" in text


def test_summary_without_readings(conn):
    text = report.render_text(report.build_summary(conn, NODE_ID, RULE))
    assert text.startswith(f"Nym node {NODE_ID}: no readings yet")
