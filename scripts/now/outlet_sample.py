#!/usr/bin/env python3
"""Scan 4 raw GKG files for flank outlet domains. In memory only. No zip on disk.

Research user-agent only. One file at a time. Does not touch the now-download database.
"""
from __future__ import annotations

import html
import json
import sys
import time
import zipfile
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "m0"))
sys.path.insert(0, str(ROOT / "pipeline" / "fetch"))

import gkg_filter_v2 as filt  # noqa: E402
from now_download import mentions_region  # noqa: E402

OUT = ROOT / "data" / "now" / "outlet-sample.json"
ROBOTS = "https://data.gdeltproject.org/robots.txt"
PAUSE_S = 1.0
FLANK_TLDS = (".fi", ".ee", ".lv", ".lt", ".pl")
# Longest first so news.err.ee is not also counted as err.ee.
NAMED = (
    "news.err.ee",
    "eng.lsm.lv",
    "delfi.lt",
    "delfi.ee",
    "delfi.lv",
    "lrt.lt",
    "err.ee",
    "lsm.lv",
    "pap.pl",
    "tvp.pl",
    "reuters.com",
    "apnews.com",
)
FILES = (
    ("english", "20260728", "https://data.gdeltproject.org/gdeltv2/20260728001500.gkg.csv.zip"),
    ("english", "20260915", "https://data.gdeltproject.org/gdeltv2/20260915001500.gkg.csv.zip"),
    ("translation", "20260818", "https://data.gdeltproject.org/gdeltv2/20260818000000.translation.gkg.csv.zip"),
    ("translation", "20261005", "https://data.gdeltproject.org/gdeltv2/20261005000000.translation.gkg.csv.zip"),
)


def host_of(url: str, source_name: str) -> str:
    raw = ""
    if url.startswith("http"):
        raw = urlparse(url).hostname or ""
    elif source_name and "." in source_name and " " not in source_name:
        raw = source_name
    host = raw.lower().strip(".")
    if host.startswith("www."):
        host = host[4:]
    return host


def named_domain(host: str) -> str:
    for domain in NAMED:
        if host == domain or host.endswith("." + domain):
            return domain
    return ""


def flank_domain(host: str) -> str:
    if not host or not host.endswith(FLANK_TLDS):
        return ""
    parts = host.split(".")
    if len(parts) < 2:
        return ""
    return ".".join(parts[-2:])


def scan(content: bytes) -> dict:
    named = {d: {"rows": 0, "relevant": 0, "examples": []} for d in NAMED}
    other: dict[str, dict] = {}
    rows = 0
    with zipfile.ZipFile(BytesIO(content)) as zf:
        with zf.open(zf.namelist()[0]) as raw:
            for line in raw:
                cols = line.decode("utf-8", "replace").rstrip("\n").split("\t")
                if len(cols) < 5:
                    continue
                rows += 1
                url = cols[4]
                source = cols[3] if len(cols) > 3 else ""
                host = host_of(url, source)
                if not host:
                    continue
                title = html.unescape(filt.page_title(cols[26])) if len(cols) > 26 else ""
                locations = cols[9] if len(cols) > 9 else ""
                v2locations = cols[10] if len(cols) > 10 else ""
                relevant = mentions_region(title, locations, v2locations)
                listed = named_domain(host)
                if listed:
                    named[listed]["rows"] += 1
                    if relevant:
                        named[listed]["relevant"] += 1
                        examples = named[listed]["examples"]
                        if len(examples) < 2 and title:
                            examples.append(title[:180])
                    continue
                domain = flank_domain(host)
                if not domain or not relevant:
                    continue
                slot = other.setdefault(domain, {"relevant": 0, "examples": []})
                slot["relevant"] += 1
                if len(slot["examples"]) < 2 and title:
                    slot["examples"].append(title[:180])
    other_kept = {k: v for k, v in other.items() if v["relevant"]}
    return {"rows": rows, "named": named, "other_relevant": other_kept}


def save(payload: dict) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    session = filt.session()
    robots = session.get(ROBOTS, timeout=30)
    payload = {
        "robots_status": robots.status_code,
        "robots_bytes": len(robots.content or b""),
        "files": [],
    }
    print(f"ROBOTS {robots.status_code} bytes={payload['robots_bytes']}", flush=True)
    save(payload)
    if robots.status_code == 200 and b"Disallow:" in (robots.content or b""):
        print("ROBOTS has Disallow rules; not parsed as a blanket allow", flush=True)
    for stream, day, url in FILES:
        time.sleep(PAUSE_S)
        started = time.monotonic()
        resp = session.get(url, timeout=180)
        resp.raise_for_status()
        content = resp.content
        nbytes = len(content)
        try:
            counted = scan(content)
        finally:
            del content
            del resp
        elapsed = time.monotonic() - started
        item = {
            "stream": stream,
            "day": day,
            "url": url,
            "zip_bytes": nbytes,
            "seconds": round(elapsed, 1),
            "deleted": True,
            **counted,
        }
        payload["files"].append(item)
        save(payload)
        print(
            f"SCANNED {stream} {day} zip_bytes={nbytes} rows={counted['rows']} seconds={elapsed:.1f} deleted=yes",
            flush=True,
        )
    print("WROTE", OUT, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
