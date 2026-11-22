"""Live monitoring gates. No network. No API calls."""
from __future__ import annotations

from datetime import date, timedelta


def monitoring_state(config: dict, today: date) -> dict:
    mode = str(config.get("live_monitoring") or "off").strip()
    end_text = str(config.get("live_end_date") or "").strip()
    if mode == "on" and not end_text:
        raise ValueError("live_end_date is required when live_monitoring is on")
    ended = False
    if end_text:
        ended = today.isoformat() >= end_text
    if ended:
        return {
            "run": False,
            "snapshot": True,
            "ended": True,
            "message": "Live monitoring ended " + end_text,
        }
    if mode != "on":
        return {
            "run": False,
            "snapshot": True,
            "ended": False,
            "message": "live_monitoring is off; snapshot dates stay fixed",
        }
    return {"run": True, "snapshot": False, "ended": False, "message": ""}


def rolling_weeks(end: date, weeks: int = 12) -> tuple[str, str]:
    start = end - timedelta(days=weeks * 7 - 1)
    return start.isoformat(), end.isoformat()


def window_for(config: dict, today: date, snapshot: dict) -> dict:
    state = monitoring_state(config, today)
    if state["snapshot"]:
        return {
            "mode": "snapshot",
            "start": snapshot["window_start"],
            "end": snapshot["window_end"],
            "changed": False,
        }
    start, end = rolling_weeks(today)
    return {"mode": "live", "start": start, "end": end, "changed": True}


def classify_allowed(live_on: bool, spent_usd: float, batch_usd: float, cap_usd: float) -> bool:
    if not live_on:
        return False
    if cap_usd <= 0:
        return False
    return spent_usd + batch_usd <= cap_usd
