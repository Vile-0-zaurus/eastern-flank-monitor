#!/usr/bin/env python3
"""Confirm gpsjam.org daily CSV is fetchable. Does not download history.

Writes data/gpsjam-report.json. One manifest fetch + a HEAD of the latest CSV.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "gpsjam-report.json"
S = requests.Session()
S.headers["User-Agent"] = "m0-reality-check/0.1 (local research; dry-run)"


def main() -> None:
    rob = S.get("https://gpsjam.org/robots.txt", timeout=30)
    time.sleep(1.1)
    man = S.get("https://gpsjam.org/data/manifest.csv", timeout=40)
    text = man.content
    # server gzip; requests decompresses when it sees content-encoding
    body = man.text
    lines = [ln for ln in body.splitlines() if ln.strip()]
    header = lines[0] if lines else ""
    first = lines[1] if len(lines) > 1 else ""
    last = lines[-1] if len(lines) > 1 else ""
    time.sleep(1.1)
    latest_date = last.split(",")[0] if last else ""
    csv_url = f"https://gpsjam.org/data/{latest_date}-h3_4.csv" if latest_date else ""
    head = S.head(csv_url, timeout=30, allow_redirects=True) if csv_url else None
    report = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "robots_status": rob.status_code,
        "manifest_status": man.status_code,
        "manifest_rows": max(0, len(lines) - 1),
        "manifest_header": header,
        "first_date": first.split(",")[0] if first else None,
        "last_date": latest_date or None,
        "latest_csv_url": csv_url,
        "latest_csv_head_status": None if head is None else head.status_code,
        "latest_csv_content_type": None if head is None else head.headers.get("content-type"),
        "known_columns": "hex,count_good_aircraft,count_bad_aircraft",
        "history_note": "Manifest starts 2022-02-14. No rows before that. Does not cover 2021-01-01.",
        "terms_note": "No robots.txt (404 SPA). About page does not state a license. Treat bulk reuse as not cleared.",
    }
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
