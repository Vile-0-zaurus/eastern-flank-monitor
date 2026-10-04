#!/usr/bin/env python3
"""DOC 2.0 artlist probes only. Saves data/gdelt-doc.json immediately."""
from __future__ import annotations

import json
import time
import urllib.parse
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
OUT = DATA / "gdelt-doc.json"

S = requests.Session()
S.headers["User-Agent"] = "m0-reality-check/0.1 (local research; dry-run)"
_last = 0.0


def get(url: str) -> requests.Response:
    global _last
    wait = 1.05 - (time.monotonic() - _last)
    if wait > 0:
        time.sleep(wait)
    resp = S.get(url, timeout=90)
    _last = time.monotonic()
    return resp


def probe(label: str, query: str, extra: dict | None = None) -> dict:
    params = {"query": query, "mode": "artlist", "format": "json", "maxrecords": "250"}
    if extra:
        params.update(extra)
    url = "https://api.gdeltproject.org/api/v2/doc/doc?" + urllib.parse.urlencode(params)
    row = {"label": label, "query": query, "extra": extra or {}}
    resp = get(url)
    row["status"] = resp.status_code
    row["bytes"] = len(resp.content)
    text = resp.text
    try:
        payload = resp.json()
    except Exception:
        payload = None
        row["body_head"] = text[:600]
    if isinstance(payload, dict):
        arts = payload.get("articles") or []
        row["n_articles"] = len(arts)
        dates = sorted(a.get("seendate") or "" for a in arts if a.get("seendate"))
        row["seendate_min"] = dates[0] if dates else None
        row["seendate_max"] = dates[-1] if dates else None
        row["top_domains"] = Counter(a.get("domain") or "" for a in arts).most_common(8)
        row["languages"] = Counter(a.get("language") or "" for a in arts).most_common(5)
        row["samples"] = [
            {"title": a.get("title"), "domain": a.get("domain"), "seendate": a.get("seendate"), "lang": a.get("language")}
            for a in arts[:3]
        ]
        if not arts:
            row["payload_keys"] = list(payload.keys())
            row["body_head"] = text[:600]
    else:
        row["n_articles"] = None
        row["body_head"] = text[:600]
    print(label, row.get("status"), row.get("n_articles"), row.get("seendate_min"), row.get("seendate_max"), flush=True)
    return row


def main() -> None:
    countries = (
        "(Финляндия OR Finland OR Эстония OR Estonia OR Латвия OR Latvia "
        "OR Литва OR Lithuania OR Польша OR Poland)"
    )
    q_ru = f"{countries} sourcelang:russian"
    q_dom = f"{countries} (domain:tass.ru OR domain:ria.ru)"
    q_both = f"{countries} sourcelang:russian (domain:tass.ru OR domain:ria.ru)"
    rows = [
        probe("ru_default", q_ru),
        probe("ru_3m", q_ru, {"timespan": "3m"}),
        probe("ru_1y", q_ru, {"timespan": "1y"}),
        probe("ru_2021_window", q_ru, {"startdatetime": "20210101000000", "enddatetime": "20220224000000"}),
        probe("domains_default", q_dom),
        probe("ru_and_domains_3m", q_both, {"timespan": "3m"}),
    ]
    doc = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "rows": rows,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
