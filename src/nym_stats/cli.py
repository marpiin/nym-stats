import argparse
import logging
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

from nym_stats import __version__, nym_api, report, store, telegram
from nym_stats.config import ConfigError, Settings, load_settings
from nym_stats.http_client import RequestFailed
from nym_stats.nym_api import SnapshotError

log = logging.getLogger("nym_stats")


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    # urllib3 logs request paths at DEBUG, and the Telegram path contains the token.
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    load_dotenv(Path.cwd() / ".env")
    try:
        settings = load_settings(os.environ)
        conn = store.connect(settings.db_path)
        try:
            return args.run(settings, conn, args)
        finally:
            conn.close()
    except (ConfigError, RequestFailed, SnapshotError, sqlite3.Error, OSError) as exc:
        log.error("%s failed: %s", args.command, exc)
        return 1


def fetch(settings: Settings, conn: sqlite3.Connection, args: argparse.Namespace) -> int:
    now = datetime.now(UTC)
    if store.has_reading_for_day(conn, settings.node_id, now.date().isoformat()):
        log.info("A reading for %s is already stored, nothing to fetch", now.date())
        return 0
    try:
        with requests.Session() as session:
            snapshot = nym_api.fetch_node_snapshot(session, settings.api_url, settings.node_id, now)
    except (RequestFailed, SnapshotError) as exc:
        store.record_attempt(conn, settings.node_id, now, str(exc))
        raise
    store.record_attempt(conn, settings.node_id, now, None)
    if store.save_reading(conn, snapshot):
        log.info("Stored reading for node %d on %s", settings.node_id, snapshot.day)
    else:
        log.info("A reading for %s was stored by another run, kept that one", snapshot.day)
    return 0


def print_report(settings: Settings, conn: sqlite3.Connection, args: argparse.Namespace) -> int:
    summary = report.build_summary(conn, settings.node_id, settings.alert_rule)
    print(report.render_text(summary))
    return 0


def notify(settings: Settings, conn: sqlite3.Connection, args: argparse.Namespace) -> int:
    if not settings.telegram_token or not settings.telegram_chat_id:
        raise ConfigError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set for notify")
    summary = report.build_summary(conn, settings.node_id, settings.alert_rule)
    with requests.Session() as session:
        telegram.send_message(
            session, settings.telegram_token, settings.telegram_chat_id, report.render_html(summary)
        )
    log.info("Sent summary to Telegram with %d alert(s)", len(summary.alerts))
    return 0


def export(settings: Settings, conn: sqlite3.Connection, args: argparse.Namespace) -> int:
    rows = store.export_csv(conn, settings.node_id, args.out, args.monthly)
    log.info("Wrote %d row(s) to %s", rows, args.out)
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nym-stats", description="Daily readings and Telegram alerts for a Nym node."
    )
    parser.add_argument("--version", action="version", version=f"nym-stats {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("fetch", help="read the node from nym-api and store it").set_defaults(
        run=fetch
    )
    commands.add_parser("report", help="print the summary").set_defaults(run=print_report)
    commands.add_parser("notify", help="send the summary to Telegram").set_defaults(run=notify)
    export_parser = commands.add_parser("export", help="write readings to CSV")
    export_parser.add_argument("--out", type=Path, default=Path("readings.csv"))
    export_parser.add_argument(
        "--monthly", action="store_true", help="write monthly reward totals instead"
    )
    export_parser.set_defaults(run=export)
    return parser
