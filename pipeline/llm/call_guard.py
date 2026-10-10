"""Decide what a failed provider call may do. Does not call the API."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

_KEY = re.compile(r"(?:xai-|sk-)[A-Za-z0-9_\-]{8,}")


def _safe(text: str) -> str:
    return _KEY.sub("[redacted]", text.replace("\n", " ")).strip()[:200]


def _message_from_body(raw: str) -> str:
    raw = raw.strip()
    if not raw:
        return ""
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return _safe(raw)
    err = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(err, dict):
        return _safe(str(err.get("message") or err.get("type") or raw))
    if isinstance(err, str):
        return _safe(err)
    return _safe(raw)


def error_record(exc: BaseException) -> dict:
    """Status code and a short message. A key in the body is not kept."""
    status = getattr(exc, "code", None)
    if not isinstance(status, int):
        status = None
    message = ""
    read = getattr(exc, "read", None)
    if callable(read):
        try:
            body = read()
            if isinstance(body, bytes):
                body = body.decode("utf-8", errors="replace")
            message = _message_from_body(str(body))
        except Exception:
            message = ""
    if not message:
        message = _safe(str(exc).strip() or type(exc).__name__)
    return {"status": status, "message": message}


def log_provider_error(record: dict, path: Path) -> str:
    status = record["status"] if record["status"] is not None else "none"
    line = (
        f"{datetime.now(timezone.utc).isoformat()} "
        f"status={status} message={record['message']}\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line)
    return line


MAX_ATTEMPTS = 3
WINDOW = 100
FAILURE_LIMIT = 0.10


def backoff_seconds(attempt: int) -> int:
    return 20 * (2 ** attempt)


_BALANCE = ("insufficient", "balance", "credit", "billing", "payment required")
_AUTH = ("unauthorized", "invalid api key", "invalid_api_key", "authentication", "forbidden")


def _is_stop(status: int | None, message: str) -> bool:
    if status == 429:
        return False
    text = message.lower()
    if status in (401, 402, 403):
        return True
    return any(word in text for word in _BALANCE) or any(word in text for word in _AUTH)


def _pause_report(failures: list[bool]) -> str:
    window = failures[-WINDOW:]
    if len(window) < WINDOW:
        return ""
    bad = sum(1 for item in window if item)
    if bad / WINDOW <= FAILURE_LIMIT:
        return ""
    return f"paused: {bad} failures in the last {WINDOW} calls. No rows were marked."


def note_success(failures: list[bool]) -> None:
    failures.append(False)
    if len(failures) > WINDOW:
        del failures[:-WINDOW]


def decide(exc: BaseException, attempt: int, failures: list[bool]) -> dict:
    """What to do after one failed call. Does not sleep and does not store a row."""
    record = error_record(exc)
    failures.append(True)
    if len(failures) > WINDOW:
        del failures[:-WINDOW]
    status = record["status"] if record["status"] is not None else "none"
    log = f"status={status} message={record['message']}"
    if _is_stop(record["status"], record["message"]):
        return {
            "action": "stop",
            "mark": False,
            "wait": 0,
            "log": log,
            "report": "stopped: auth or balance error. No rows were marked.",
        }
    paused = _pause_report(failures)
    if paused:
        return {"action": "pause", "mark": False, "wait": 0, "log": log, "report": paused}
    if attempt + 1 < MAX_ATTEMPTS:
        return {"action": "retry", "mark": False, "wait": backoff_seconds(attempt), "log": log, "report": ""}
    return {"action": "unavailable", "mark": True, "wait": 0, "log": log, "report": ""}
