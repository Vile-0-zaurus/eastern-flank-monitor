#!/usr/bin/env python3
"""Read-only Now-tab counts. No API calls. Does not write the database."""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline" / "fetch"))

from now_download import configured_window  # noqa: E402
import gkg_backfill as bf  # noqa: E402

DB = ROOT / "data" / "now" / "gkg-now.sqlite"
VIEW = ROOT / "frontend" / "now-view.json"
HEADLINES = ROOT / "frontend" / "country-headlines.json"
COUNTRIES = ("FI", "EE", "LV", "LT", "PL")
STEMS = {
    "FI": re.compile(r"finland|finnish|финлянд", re.I),
    "EE": re.compile(r"estonia|estonian|эстон", re.I),
    "LV": re.compile(r"latvia|latvian|латви", re.I),
    "LT": re.compile(r"lithuania|lithuanian|литв", re.I),
    "PL": re.compile(r"poland|polish|польш", re.I),
}
ENGLISH = {
    "the", "a", "of", "and", "to", "in", "for", "on", "with", "from", "by",
    "is", "are", "was", "were", "that", "this", "as", "at", "an", "after",
}
HOSTILE = re.compile(
    r"(?i)(?<!\w)(?:"
    r"русофоб|нацист|фашист|неонаци|бандеров|агресси|милитаризац|"
    r"дискриминац|преследован|геноцид|реванш|оккупац|карател|"
    r"возмезд|русофоби|историческ\w*\s+земл|незаконн\w*\s+границ|"
    r"ответн\w*\s+удар|russophob|nazi|fascist|neonazi|aggress|"
    r"militariz|discriminat|persecut|genocide|revanch|retaliat"
    r")"
)


def monday_of(day: str) -> str:
    current = datetime.strptime(day, "%Y%m%d").date()
    return (current - timedelta(days=current.weekday())).isoformat()


def looks_english(title: str) -> bool:
    words = [word.strip(".,:;!?\"'").lower() for word in (title or "").split()]
    return sum(word in ENGLISH for word in words) >= 2


def main() -> None:
    window = configured_window()
    if not window:
        raise SystemExit("Now window is not frozen")
    start, end = window
    russian = set(bf.load_outlets())
    view = json.loads(VIEW.read_text(encoding="utf-8"))
    headlines = json.loads(HEADLINES.read_text(encoding="utf-8"))
    weeks = view["weeks"]
    stored = {week: {code: 0 for code in COUNTRIES} for week in weeks}
    unique = {week: {code: set() for code in COUNTRIES} for week in weeks}
    english = {week: {code: 0 for code in COUNTRIES} for week in weeks}
    hostile = {week: {code: 0 for code in COUNTRIES} for week in weeks}
    any_outlet = {week: {code: 0 for code in COUNTRIES} for week in weeks}
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=60)
    con.execute("PRAGMA query_only=ON")
    try:
        cur = con.execute("SELECT day, domain, article_url, page_title FROM kept")
        while True:
            chunk = cur.fetchmany(5000)
            if not chunk:
                break
            for day, domain, url, title in chunk:
                if day < start or day > end:
                    continue
                week = monday_of(day)
                if week not in stored:
                    continue
                named = [code for code, pattern in STEMS.items() if pattern.search(title or "")]
                if not named:
                    continue
                key = url or ((domain or "") + "|" + (title or ""))
                for code in named:
                    any_outlet[week][code] += 1
                    if domain in russian:
                        stored[week][code] += 1
                        unique[week][code].add(key)
                        if looks_english(title or ""):
                            english[week][code] += 1
                        if HOSTILE.search(title or ""):
                            hostile[week][code] += 1
    finally:
        con.close()

    yle = defaultdict(lambda: defaultdict(int))
    for story in view.get("news") or []:
        for code in story.get("countries") or []:
            if code in COUNTRIES:
                yle[story["week"]][code] += 1

    print("window", start, end)
    print("dossier_2026_weeks", sum(1 for key in headlines if str(key).startswith("2026")))
    print("chip_file_has_134", any(row.get("PL") == 134 for row in view["attention"].values()))
    print("week country stored unique relevant hostile_keyword with_english shown_dossier yle_bbc chip")
    for week in weeks:
        for code in COUNTRIES:
            chip = view["attention"][week][code]
            shown = len((headlines.get(week) or {}).get(code) or [])
            print(
                week, code,
                stored[week][code],
                len(unique[week][code]),
                stored[week][code],
                hostile[week][code],
                english[week][code],
                shown,
                yle[week][code],
                chip,
                "MATCH" if stored[week][code] == chip else "DIFF",
            )
        print(
            "any_outlet", week,
            " ".join(f"{code}={any_outlet[week][code]}" for code in COUNTRIES),
        )


if __name__ == "__main__":
    main()
