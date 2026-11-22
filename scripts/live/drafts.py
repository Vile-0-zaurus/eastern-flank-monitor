"""Incident drafts. A draft is not a published incident. No network."""
from __future__ import annotations

import hashlib


OFFICIAL_MARKERS = ("raja.fi", "vsat.lrv.lt", "mod.gov.lv", "mil.ee", "strazgraniczna.pl", "gov.pl", "kam.lt")
STORED_MARKERS = ("yle.fi", "bbc.com", "bbc.co.uk")
ACTIONS = {"approve": "approved", "reject": "rejected", "reported": "reported"}


def _id(source: str, source_date: str) -> str:
    return hashlib.sha256((source + "|" + source_date).encode("utf-8")).hexdigest()[:16]


def draft_from_row(row: dict) -> dict | None:
    source = str(row.get("source") or row.get("url") or "")
    if not any(mark in source for mark in OFFICIAL_MARKERS + STORED_MARKERS):
        return None
    source_date = str(row.get("source_date") or row.get("date") or "")
    if not source or not source_date:
        return None
    return {
        "id": _id(source, source_date),
        "status": "draft",
        "source": source,
        "source_date": source_date,
        "summary": str(row.get("summary") or row.get("english") or row.get("title") or ""),
        "country": str(row.get("country") or ""),
        "note": "",
    }


def collect_drafts(rows: list[dict]) -> list[dict]:
    found = []
    seen = set()
    for row in rows:
        item = draft_from_row(row)
        if not item or item["id"] in seen:
            continue
        seen.add(item["id"])
        found.append(item)
    return found


def decide(draft: dict, action: str, note: str = "") -> dict:
    if action not in ACTIONS:
        raise ValueError("unknown action")
    if draft.get("status") != "draft":
        raise ValueError("only a draft can be decided")
    next_row = dict(draft)
    next_row["status"] = ACTIONS[action]
    next_row["note"] = note
    return next_row


def mark_pending(rows: list[dict]) -> list[dict]:
    marked = []
    for row in rows:
        item = dict(row)
        if not str(item.get("english") or "").strip():
            item["english"] = "translation pending"
        marked.append(item)
    return marked


def published_incidents(rows: list[dict]) -> list[dict]:
    return [row for row in rows if row.get("status") in ("approved", "reported")]
