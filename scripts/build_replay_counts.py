#!/usr/bin/env python3
"""Count stored headlines that name each flank country. Read-only. No model calls.

The count uses the same title stems as I1, per country. It is not the English sample.
"""
import hashlib
import json
import re
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "backtest" / "gkg.sqlite"
OUT = ROOT / "frontend" / "replay-counts.json"
STEMS = {
    "FI": ("finland", "finnish", "хельсинк", "helsinki", "финлянд", "финск", "финн"),
    "EE": ("estonia", "estonian", "таллин", "tallinn", "нарв", "narva", "эстон"),
    "LV": ("latvia", "latvian", "рижск", "латви", "латыш"),
    "LT": ("lithuania", "lithuanian", "вильнюс", "vilnius", "литв", "литов"),
    "PL": ("poland", "polish", "варшав", "warsaw", "сувалк", "suwalki", "suwałki", "польш", "польск", "поляк"),
}
RIGA = re.compile(r"риг(а|и|е|у|ой)(?![а-яё])", re.IGNORECASE)
KALININGRAD = ("kaliningrad", "калининград")


def monday(day: str) -> str:
    parsed = datetime.strptime(day, "%Y%m%d").date()
    return (parsed - timedelta(days=parsed.weekday())).isoformat()


def names(title: str, code: str) -> bool:
    low = title.lower()
    if any(stem in low for stem in STEMS[code]):
        return True
    return code == "LV" and bool(RIGA.search(title))


def main() -> None:
    counts: dict[str, dict[str, int]] = {}
    seen: set[tuple[str, str, str]] = set()
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    con.execute("PRAGMA query_only=ON")
    query = """
        SELECT day, page_title, article_url
        FROM kept
        WHERE day >= '20210104' AND day <= '20220227'
          AND page_title IS NOT NULL AND page_title != ''
    """
    for day, title, url in con.execute(query):
        week = monday(day)
        if week < "2021-01-04" or week > "2022-02-21":
            continue
        low = title.lower()
        if any(stem in low for stem in KALININGRAD) and not any(names(title, code) for code in STEMS):
            continue
        key = url or title
        for code in STEMS:
            if not names(title, code):
                continue
            mark = (week, code, hashlib.sha1(key.encode("utf-8", "replace")).hexdigest())
            if mark in seen:
                continue
            seen.add(mark)
            bucket = counts.setdefault(week, {})
            bucket[code] = bucket.get(code, 0) + 1
    OUT.write_text(
        json.dumps(
            {
                "note": "Unique stored headlines naming the country. I1 stems. Not the English sample.",
                "weeks": counts,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    zeros = 0
    for week, row in counts.items():
        for code in STEMS:
            if row.get(code, 0) == 0:
                zeros += 1
    print("weeks", len(counts), "zero_cells", zeros, "bytes", OUT.stat().st_size)


if __name__ == "__main__":
    main()
