#!/usr/bin/env python3
"""Daily live job. Off unless live_monitoring is on. No paid calls in this file.

    python3 scripts/live/daily_run.py --dry-run --day 2026-11-21 --max-files 1
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "m0"))
sys.path.insert(0, str(ROOT / "scripts" / "live"))

from build_site import build_site  # noqa: E402
from gate import classify_allowed, monitoring_state, window_for  # noqa: E402


def load_yaml(path: Path) -> dict:
    config = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.split("#", 1)[0].strip()
        if not text or ":" not in text:
            continue
        key, value = text.split(":", 1)
        config[key.strip()] = value.strip().strip('"')
    return config


def snapshot_pack() -> dict:
    return json.loads((ROOT / "frontend" / "now-view.json").read_text(encoding="utf-8"))


def dry_run_day(day: str, max_files: int) -> dict:
    import gkg_filter_v2 as filt

    list_url = "https://data.gdeltproject.org/gdeltv2/masterfilelist.txt"
    stamp = day.replace("-", "")
    wanted = []
    session = filt.session()
    resp = session.get(list_url, stream=True, timeout=600)
    resp.raise_for_status()
    for raw in resp.iter_lines(decode_unicode=True):
        if not raw:
            continue
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", "replace")
        parts = raw.split()
        if len(parts) < 3 or ".gkg.csv.zip" not in parts[2]:
            continue
        name = parts[2].rsplit("/", 1)[-1]
        if not name.startswith(stamp):
            continue
        url = parts[2]
        if url.startswith("http://"):
            url = "https://" + url[len("http://"):]
        try:
            size = int(parts[0])
        except ValueError:
            size = 0
        wanted.append((size, url))
    resp.close()
    picked = wanted[:max_files]
    kept = 0
    downloaded = 0
    for _size, url in picked:
        nbytes, _elapsed, content = filt.download_one(url)
        downloaded += nbytes
        scanned = filt.scan_zip(content)
        kept += scanned["kept"]
        del content
    return {
        "day": stamp,
        "listed": len(wanted),
        "listed_bytes": sum(size for size, _url in wanted),
        "downloaded_files": len(picked),
        "downloaded_bytes": downloaded,
        "kept_rows": kept,
        "api_calls": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--day", default="")
    parser.add_argument("--max-files", type=int, default=1)
    parser.add_argument("--today", default="")
    args = parser.parse_args()
    config = load_yaml(ROOT / "config" / "app.yaml")
    budget = load_yaml(ROOT / "config" / "budget.yaml")
    today = date.fromisoformat(args.today) if args.today else date.today()
    state = monitoring_state(config, today)
    pack = snapshot_pack()
    window = window_for(config, today, pack)
    if window["mode"] == "snapshot" and (window["start"] != pack["window_start"] or window["end"] != pack["window_end"]):
        raise SystemExit("snapshot dates must not change")
    cap = float(budget.get("monthly_cap_usd") or 0)
    calls = classify_allowed(state["run"], 0.0, 0.01, cap)
    if args.dry_run:
        day = args.day or (today.strftime("%Y%m%d"))
        result = dry_run_day(day.replace("-", ""), args.max_files)
        result["classify"] = False
        result["window"] = window
        print(json.dumps(result))
        return 0
    if not state["run"]:
        print(state["message"])
        return 0
    if calls:
        raise SystemExit("classification is wired, but this run does not call an API")
    from drafts import mark_pending
    pending = mark_pending([{"title": "unread", "english": ""}])
    out = ROOT / "data" / "live" / "pending.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(pending), encoding="utf-8")
    print("live window " + window["start"] + " to " + window["end"] + "; classification skipped, cap is " + str(cap))
    build_site(ROOT / "frontend", ROOT / "site")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
