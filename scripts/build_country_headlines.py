#!/usr/bin/env python3
"""Build country headline cards from gkg.sqlite. Read-only. No model calls."""

import json
import re
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data/backtest/gkg.sqlite"
OUT = ROOT / "frontend/country-headlines.json"
STEMS = {
    "FI": ("finland", "finnish", "финлянд", "финск"),
    "EE": ("estonia", "estonian", "эстон"),
    "LV": ("latvia", "latvian", "латви"),
    "LT": ("lithuania", "lithuanian", "литв"),
    "PL": ("poland", "polish", "польш"),
}
KALININGRAD = ("kaliningrad", "калининград")


def monday(day: str) -> str:
    parsed = datetime.strptime(day, "%Y%m%d").date()
    return (parsed - timedelta(days=parsed.weekday())).isoformat()


def load_english() -> dict[str, str]:
    found = {}
    headline_en = json.loads((ROOT / "frontend/headline_en.json").read_text(encoding="utf-8"))
    if isinstance(headline_en, dict):
        for title, english in headline_en.items():
            if isinstance(english, str) and english.strip():
                found[title] = english.strip()
    for item in json.loads((ROOT / "frontend/news.json").read_text(encoding="utf-8")):
        if item.get("english"):
            found[item["title"]] = item["english"]
    return found


def load_hostile() -> set[str]:
    return {
        item["url"]
        for item in json.loads((ROOT / "frontend/news.json").read_text(encoding="utf-8"))
        if item.get("hostile") and item.get("url")
    }


def names_country(title: str, code: str) -> bool:
    low = title.lower()
    return any(stem in low for stem in STEMS[code])


def kaliningrad_only(title: str) -> bool:
    low = title.lower()
    if not any(stem in low for stem in KALININGRAD):
        return False
    return not any(names_country(title, code) for code in STEMS)


def english_line(title: str, stream: str, stored: dict[str, str]) -> str:
    if stream == "english":
        return title
    return stored.get(title, "")


def main() -> None:
    stored = load_english()
    hostile = load_hostile()
    kept: dict[tuple[str, str], list[dict]] = {}
    seen: set[tuple[str, str, str]] = set()
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    con.execute("PRAGMA query_only=ON")
    query = """
        SELECT stream, day, domain, page_title, article_url
        FROM kept
        WHERE day >= '20210104' AND day <= '20220227'
          AND page_title IS NOT NULL AND page_title != ''
    """
    for stream, day, domain, title, url in con.execute(query):
        if kaliningrad_only(title):
            continue
        week = monday(day)
        if week < "2021-01-04" or week > "2022-02-21":
            continue
        english = english_line(title, stream, stored)
        if not english:
            continue
        for code in STEMS:
            if not names_country(title, code):
                continue
            key = (week, code, url or title)
            if key in seen:
                continue
            seen.add(key)
            bucket = kept.setdefault((week, code), [])
            bucket.append({
                "title": title,
                "english": english,
                "url": url or "",
                "outlet": domain or "",
                "date": f"{day[:4]}-{day[4:6]}-{day[6:8]}",
                "hostile": bool(url and url in hostile),
            })
    out: dict[str, dict[str, list[dict]]] = {}
    for (week, code), rows in kept.items():
        rows.sort(key=lambda item: (not item["hostile"], item["date"], item["title"]))
        # one story per title
        unique = []
        titles = set()
        for item in rows:
            norm = re.sub(r"\W+", " ", item["title"].lower()).strip()
            if norm in titles:
                continue
            titles.add(norm)
            unique.append(item)
            if len(unique) == 12:
                break
        out.setdefault(week, {})[code] = unique
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("weeks", len(out), "bytes", OUT.stat().st_size)


if __name__ == "__main__":
    main()
