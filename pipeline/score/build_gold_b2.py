#!/usr/bin/env python3
"""Pick the batch-2 candidate headlines. Read-only on gkg.sqlite. No model calls."""
from __future__ import annotations

import csv
import html
import json
import random
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))
from score.region_filter import junk_title, load_keywords, title_pattern  # noqa: E402

DB = ROOT / "data" / "backtest" / "gkg.sqlite"
OUT = ROOT / "validation" / "gold-b2-candidates.csv"
PICK = ROOT / "validation" / "gold-b2-pick.json"
FIELDS = ["id", "domain", "date", "title", "title_en", "url", "bucket", "month"]
HOSTILE = re.compile(
    r"(?i)(?<!\w)(?:"
    r"русофоб|нацист|фашист|неонаци|бандеров|агресси|милитаризац|"
    r"дискриминац|преследован|геноцид|реванш|оккупац|карател|"
    r"возмезд|русофоби|историческ\w*\s+земл|незаконн\w*\s+границ|"
    r"ответн\w*\s+удар|russophob|nazi|fascist|neonazi|aggress|"
    r"militariz|discriminat|persecut|genocide|revanch|retaliat"
    r")"
)
KALININGRAD = re.compile(r"(?i)(?<!\w)(?:калининград\w*|kaliningrad\w*)")
EXTRA_REGION = re.compile(
    r"(?i)(?<!\w)(?:нато|nato|границ|border|военн|military|арми|"
    r"финлянд|финск|финн|эстон|латви|латыш|литв|литов|польш|польск|поляк|"
    r"прибалт|балтий|балтик|сувалк|варшав|вильнюс|таллин|хельсинк|"
    r"finland|finnish|estonia|estonian|latvia|latvian|lithuania|lithuanian|"
    r"poland|polish|baltic|warsaw|vilnius|tallinn|helsinki|suwalki|suwałki)"
)


def story_key(title: str) -> str:
    text = html.unescape(title).lower()
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    words = [word for word in text.split() if len(word) > 2]
    return " ".join(words[:12])


def date_of(day: str, seen: str) -> str:
    raw = (seen or day or "").strip()
    digits = re.sub(r"\D", "", raw)
    if len(digits) >= 8:
        return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"
    return raw


def title_ok(title: str, pattern: re.Pattern[str]) -> bool:
    if not pattern.search(title):
        return False
    if KALININGRAD.search(title) and not EXTRA_REGION.search(title):
        return False
    return True


def main() -> None:
    if OUT.exists() and "--force" not in sys.argv:
        raise SystemExit(f"refusing to rebuild existing {OUT.name}; pass --force")
    fips, _names, stems, groups, min_chars = load_keywords(ROOT / "config" / "region_keywords.yaml")
    del fips
    pattern = title_pattern(stems, groups)
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=30)
    con.execute("PRAGMA query_only=ON")
    seen_stories: set[str] = set()
    rows = []
    scanned = 0
    for source_id, domain, seen, url, title, day in con.execute(
        """
        SELECT id, domain, seendate, article_url, page_title, day
        FROM kept
        WHERE day >= '20211101' AND day <= '20220224'
        """
    ):
        scanned += 1
        text = html.unescape(title or "")
        if junk_title(text, domain or "", min_chars) or not title_ok(text, pattern):
            continue
        key = story_key(text)
        if not key or key in seen_stories:
            continue
        seen_stories.add(key)
        when = date_of(day or "", seen or "")
        rows.append(
            {
                "id": str(source_id),
                "domain": domain or "",
                "date": when,
                "title": re.sub(r"\s+", " ", text).strip(),
                "title_en": "",
                "url": url or "",
                "month": when[:7],
            }
        )
    con.close()
    hostile = [row for row in rows if HOSTILE.search(row["title"])]
    ordinary = [row for row in rows if row not in hostile]
    rng = random.Random(20211101)
    rng.shuffle(hostile)
    rng.shuffle(ordinary)
    picked_h = _mix(hostile, 40, rng)
    picked_r = _mix(ordinary, 40, rng)
    for row in picked_h:
        row["bucket"] = "hostile_keyword"
    for row in picked_r:
        row["bucket"] = "random"
    picked = picked_h + picked_r
    print(f"scanned={scanned} title_stories={len(rows)} hostile_pool={len(hostile)} random_pool={len(ordinary)} picked={len(picked)}")
    print("months", sorted({row["month"] for row in picked}))
    print("outlets", sorted({row["domain"] for row in picked}))
    PICK.write_text(json.dumps(picked, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {PICK}")


def _mix(rows: list[dict], n: int, rng: random.Random) -> list[dict]:
    by_month: dict[str, list[dict]] = {}
    for row in rows:
        by_month.setdefault(row["month"], []).append(row)
    months = sorted(by_month)
    out: list[dict] = []
    while len(out) < n and any(by_month.values()):
        for month in months:
            pool = by_month.get(month) or []
            if not pool or len(out) >= n:
                continue
            out.append(pool.pop(rng.randrange(len(pool))))
    return out


if __name__ == "__main__":
    main()
