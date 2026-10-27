import requests

from nym_stats.http_client import RequestFailed, request_json


def send_message(session: requests.Session, token: str, chat_id: str, html_text: str) -> None:
    # A retried POST can, rarely, deliver the message twice. A duplicate summary
    # is a smaller problem than a missing alert.
    body = request_json(
        session,
        "POST",
        f"https://api.telegram.org/bot{token}/sendMessage",
        label="telegram sendMessage",
        json={"chat_id": chat_id, "text": html_text, "parse_mode": "HTML"},
    )
    if body.get("ok") is not True:
        raise RequestFailed("telegram sendMessage: response did not have ok=true")
