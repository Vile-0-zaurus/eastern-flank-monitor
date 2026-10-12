"""Collapse approval clicks. Raw files are not rewritten."""
from __future__ import annotations

import csv
from pathlib import Path


def applied_level(row: dict) -> int | None:
    """Approve uses the draft value. A correction uses corrected_value. Empty is no data."""
    decision = (row.get("decision") or "").strip()
    if decision == "Value should be":
        return _level(row.get("corrected_value"))
    if decision == "Approve":
        return _level(row.get("value"))
    return None


def _level(value) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip()
    if not text.isdigit():
        return None
    number = int(text)
    if 0 <= number <= 4:
        return number
    return None


def load_decisions(paths) -> list[dict]:
    """One row per entry. The latest saved_at wins. Source files are only read."""
    rows = []
    for path in paths:
        with Path(path).open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                rows.append(dict(row))
    return collapse_latest(rows)


def collapse_latest(rows: list[dict]) -> list[dict]:
    kept: dict[tuple, dict] = {}
    order: list[tuple] = []
    for row in rows:
        key = (row.get("input", ""), row.get("date", ""), row.get("region", ""))
        previous = kept.get(key)
        if previous is None:
            kept[key] = row
            order.append(key)
            continue
        if (row.get("saved_at") or "") >= (previous.get("saved_at") or ""):
            kept[key] = row
    return [kept[key] for key in order]
