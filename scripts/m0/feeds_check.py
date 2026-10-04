#!/usr/bin/env python3
"""Probe Russian state-media and MFA feeds. One request per host, then 1/s."""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlparse

import feedparser
import requests

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "feeds-report.json"
OUT.parent.mkdir(exist_ok=True)

CANDIDATES = [
    ("tass_ru", ["https://tass.ru/rss/v2.xml", "http://tass.ru/rss/v2.xml", "https://tass.ru/rss/v2.xml"]),
    ("tass_en", ["https://tass.com/rss/v2.xml", "http://tass.com/rss/v2.xml"]),
    ("ria", ["https://ria.ru/export/rss2/archive/index.xml", "https://ria.ru/export/rss2/index.xml", "https://ria.ru/export/rss2/lenta.xml"]),
    ("mid", [
        "https://mid.ru/ru/rss/",
        "https://www.mid.ru/ru/rss/",
        "https://mid.ru/rss",
        "https://www.mid.ru/rss.xml",
        "https://mid.ru/en/rss/",
    ]),
]

S = requests.Session()
S.headers["User-Agent"] = "m0-reality-check/0.1 (local research; feed probe; 1 req/s)"
_last = {}


def get(url: str, **kw):
    host = urlparse(url).netloc
    now = time.monotonic()
    wait = 1.05 - (now - _last.get(host, 0.0))
    if wait > 0:
        time.sleep(wait)
    kw.setdefault("timeout", 40)
    kw.setdefault("allow_redirects", True)
    resp = S.get(url, **kw)
    _last[host] = time.monotonic()
    return resp


def robots(url: str) -> dict:
    host = urlparse(url).netloc
    scheme = urlparse(url).scheme
    rob = f"{scheme}://{host}/robots.txt"
    try:
        resp = get(rob)
        text = resp.text[:1500]
        disallow_all = "Disallow: /" in text and "Allow:" not in text.split("Disallow: /", 1)[0][-80:]
        return {"url": rob, "status": resp.status_code, "head": text[:400], "mentions_rss": "rss" in text.lower()}
    except Exception as exc:
        return {"url": rob, "error": str(exc)}


def summarize_feed(url: str, body: bytes, status: int, headers: dict) -> dict:
    parsed = feedparser.parse(body)
    entries = parsed.entries or []
    dates = []
    for e in entries:
        for key in ("published", "updated", "created"):
            if e.get(key):
                dates.append(e.get(key))
                break
    fields = set()
    if entries:
        e0 = entries[0]
        for k in ("title", "link", "published", "updated", "summary", "description", "content", "author"):
            if e0.get(k):
                fields.add(k)
        if e0.get("content"):
            fields.add("content")
        # full text heuristic
        summary = e0.get("summary") or ""
        content = ""
        if e0.get("content"):
            content = e0.content[0].get("value") or ""
        fields_note = {
            "title": bool(e0.get("title")),
            "date": bool(e0.get("published") or e0.get("updated")),
            "summary_len": len(summary),
            "content_len": len(content),
            "likely_full_text": len(content) > 800 or len(summary) > 800,
        }
    else:
        fields_note = {}
    bozo = getattr(parsed, "bozo", False)
    return {
        "url": url,
        "status": status,
        "content_type": headers.get("content-type"),
        "bytes": len(body),
        "bozo": bool(bozo),
        "bozo_exception": str(getattr(parsed, "bozo_exception", ""))[:200],
        "feed_title": (parsed.feed.get("title") if parsed.feed else None),
        "n_items": len(entries),
        "date_min": min(dates) if dates else None,
        "date_max": max(dates) if dates else None,
        "fields": fields_note,
        "sample_titles": [e.get("title") for e in entries[:3]],
        "body_head": body[:180].decode("utf-8", "replace") if not entries else None,
    }


def main() -> None:
    report = {"checked_at_utc": datetime.now(timezone.utc).isoformat(), "feeds": []}
    seen_robots = set()
    for name, urls in CANDIDATES:
        block = {"name": name, "attempts": []}
        # robots once per host of first url
        host = urlparse(urls[0]).netloc
        if host not in seen_robots:
            block["robots"] = robots(urls[0])
            seen_robots.add(host)
        worked = None
        for url in urls:
            try:
                resp = get(url)
            except Exception as exc:
                block["attempts"].append({"url": url, "error": str(exc)})
                print(name, url, "ERR", exc, flush=True)
                continue
            row = summarize_feed(url, resp.content, resp.status_code, resp.headers)
            # blocked/throttled heuristic
            row["blocked_or_throttled"] = resp.status_code in (401, 403, 429, 451) or (
                resp.status_code == 200 and row["n_items"] == 0 and b"captcha" in resp.content.lower()
            )
            block["attempts"].append({k: row[k] for k in ("url", "status", "n_items", "blocked_or_throttled", "content_type")})
            print(name, resp.status_code, row["n_items"], url, flush=True)
            if resp.status_code == 200 and row["n_items"] > 0:
                worked = row
                break
            if resp.status_code == 200 and worked is None:
                worked = row
        block["best"] = worked
        report["feeds"].append(block)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
