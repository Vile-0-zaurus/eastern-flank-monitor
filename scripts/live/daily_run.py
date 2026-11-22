#!/usr/bin/env python3
"""Daily live job. Off unless live_monitoring is on. No paid calls in this file.

    python3 scripts/live/daily_run.py --dry-run --day 2026-11-21 --max-files 0
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "m0"))
sys.path.insert(0, str(ROOT / "scripts" / "live"))

from build_site import build_site  # noqa: E402
from gate import classify_allowed, monitoring_state, window_for  # noqa: E402
from storage import load_outlets, row_fate, tass_supplement  # noqa: E402


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


def stream_name(url: str) -> str:
    name = url.rsplit("/", 1)[-1]
    if ".translation." in name:
        return "translation"
    return "english"


def empty_stream() -> dict:
    return {
        "files": 0,
        "bytes": 0,
        "region_rows": 0,
        "russian_rows_total": 0,
        "daily_totals": {},
        "russian_kept_region": {},
    }


def add_counts(target: dict, scanned: dict) -> None:
    for domain, count in scanned["outlet_rows"].items():
        if count:
            target["russian_rows"][domain] = target["russian_rows"].get(domain, 0) + count
    for domain, count in scanned["kept_by"].items():
        if count:
            target["russian_kept"][domain] = target["russian_kept"].get(domain, 0) + count


def download_zip(session, url: str, dest: Path) -> int:
    with session.get(url, stream=True, timeout=180) as resp:
        resp.raise_for_status()
        with dest.open("wb") as handle:
            for chunk in resp.iter_content(chunk_size=256 * 1024):
                if chunk:
                    handle.write(chunk)
    return dest.stat().st_size


def dry_run_day(day: str, max_files: int) -> dict:
    import gkg_filter_v2 as filt

    started = time.monotonic()
    lists = (
        ("english", "https://data.gdeltproject.org/gdeltv2/masterfilelist.txt"),
        ("translation", "https://data.gdeltproject.org/gdeltv2/masterfilelist-translation.txt"),
    )
    stamp = day.replace("-", "")
    wanted = []
    session = filt.session()
    for stream, list_url in lists:
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
            wanted.append((size, url, stream))
        resp.close()
        print("listed " + stream + " " + str(sum(1 for item in wanted if item[2] == stream)), flush=True)
    picked = wanted if max_files <= 0 else wanted[:max_files]
    streams = {"english": empty_stream(), "translation": empty_stream()}
    russian = load_outlets(ROOT / "config" / "outlets.yaml")
    western = load_outlets(ROOT / "config" / "western-outlets.yaml")
    disk_start = shutil.disk_usage("/").used
    peak_used = disk_start
    largest_zip = 0
    with tempfile.TemporaryDirectory(prefix="efm-dry-") as tmp:
        dest = Path(tmp) / "one.zip"
        for index, (_size, url, stream) in enumerate(picked, start=1):
            nbytes = download_zip(session, url, dest)
            peak_used = max(peak_used, shutil.disk_usage("/").used)
            largest_zip = max(largest_zip, nbytes)
            scanned = filt.scan_zip(dest)
            bucket = streams[stream]
            bucket["files"] += 1
            bucket["bytes"] += nbytes
            bucket["region_rows"] += scanned["kept"]
            for domain, count in scanned["outlet_rows"].items():
                if not count:
                    continue
                if row_fate(domain, russian, western, False) == "keep_all":
                    bucket["russian_rows_total"] += count
                    bucket["daily_totals"][domain] = bucket["daily_totals"].get(domain, 0) + count
            for domain, count in scanned["kept_by"].items():
                if count:
                    bucket["russian_kept_region"][domain] = bucket["russian_kept_region"].get(domain, 0) + count
            dest.unlink(missing_ok=True)
            if index % 20 == 0 or index == len(picked):
                print("filtered " + str(index) + "/" + str(len(picked)), flush=True)
    return {
        "day": stamp,
        "listed": len(wanted),
        "listed_by_stream": {
            stream: {
                "files": sum(1 for item in wanted if item[2] == stream),
                "bytes": sum(item[0] for item in wanted if item[2] == stream),
            }
            for stream in ("english", "translation")
        },
        "downloaded_files": len(picked),
        "streams": streams,
        "runtime_seconds": round(time.monotonic() - started, 1),
        "peak_disk_bytes": peak_used - disk_start,
        "largest_zip_bytes": largest_zip,
        "api_calls": 0,
        "zips_kept": 0,
        "kept_meaning": "russian_rows_total is every Russian-outlet row. region_rows is the old region filter and is not the store rule.",
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
        day = args.day or today.strftime("%Y%m%d")
        result = dry_run_day(day.replace("-", ""), args.max_files)
        result["classify"] = False
        result["window"] = window
        print(json.dumps(result))
        return 0
    if not state["run"]:
        print(state["message"])
        return 0
    supplement = tass_supplement(ROOT / "data" / "collect" / today.isoformat(), True)
    out_dir = ROOT / "data" / "live"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "tass-supplement.json").write_text(json.dumps(supplement), encoding="utf-8")
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
