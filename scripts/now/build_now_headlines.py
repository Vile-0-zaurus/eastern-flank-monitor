#!/usr/bin/env python3
"""Pick the Now headlines the dossier will show. Read-only. No API calls."""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline" / "fetch"))

from now_download import configured_window  # noqa: E402
import gkg_backfill as bf  # noqa: E402

DB = ROOT / "data" / "now" / "gkg-now.sqlite"
VIEW = ROOT / "frontend" / "now-view.json"
OUT = ROOT / "frontend" / "now-headlines.json"
COUNTRIES = ("FI", "EE", "LV", "LT", "PL")
STEMS = {
    "FI": re.compile(r"finland|finnish|финлянд", re.I),
    "EE": re.compile(r"estonia|estonian|эстон", re.I),
    "LV": re.compile(r"latvia|latvian|латви", re.I),
    "LT": re.compile(r"lithuania|lithuanian|литв", re.I),
    "PL": re.compile(r"poland|polish|польш", re.I),
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
SPECIFIC = re.compile(
    r"границ|погранич|беспилот|дрон|бпла|учен|военн|нато|санкц|"
    r"border|drone|nato|sanction|military|exercise|airspace",
    re.I,
)
OFFICIAL = re.compile(
    r"путин|кремл|песков|лавров|захаров|шоигу|миноборон|госдум|"
    r"putin|kremlin|peskov|lavrov|zakharova|shoigu|defence ministry|defense ministry|state duma",
    re.I,
)


def monday_of(day: str) -> str:
    current = datetime.strptime(day, "%Y%m%d").date()
    return (current - timedelta(days=current.weekday())).isoformat()


def iso_day(day: str) -> str:
    return f"{day[:4]}-{day[4:6]}-{day[6:8]}"


def key_of(url: str, domain: str, title: str) -> str:
    text = (title or "").lower()
    text = re.sub(r"[^0-9a-zа-яё]+", " ", text, flags=re.I)
    return url or (domain + "|" + " ".join(text.split()[:12]))


def false_country(title: str, code: str) -> bool:
    text = title or ""
    if code == "LT" and re.search(r"литвиненко|литвинов|молитв", text, re.I):
        return True
    return False


def score(title: str, code: str) -> tuple:
    named = [item for item, pattern in STEMS.items() if pattern.search(title or "")]
    hostile = 1 if HOSTILE.search(title or "") else 0
    exclusive = 1 if named == [code] else 0
    specific = 1 if SPECIFIC.search(title or "") else 0
    return (hostile, exclusive, specific, -len(named))


def main() -> None:
    window = configured_window()
    if not window:
        raise SystemExit("Now window is not frozen")
    start, end = window
    view = json.loads(VIEW.read_text(encoding="utf-8"))
    weeks = view["weeks"]
    russian = set(bf.load_outlets())
    buckets = {week: {code: [] for code in COUNTRIES} for week in weeks}
    seen = {week: {code: set() for code in COUNTRIES} for week in weeks}
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=60)
    con.execute("PRAGMA query_only=ON")
    try:
        cur = con.execute(
            "SELECT day, domain, article_url, page_title FROM kept WHERE day>=? AND day<=?",
            (start, end),
        )
        while True:
            chunk = cur.fetchmany(5000)
            if not chunk:
                break
            for day, domain, url, title in chunk:
                if domain not in russian or not title:
                    continue
                week = monday_of(day)
                if week not in buckets:
                    continue
                named = [code for code, pattern in STEMS.items() if pattern.search(title)]
                named = [code for code in named if not false_country(title, code)]
                if not named:
                    continue
                for code in named:
                    identity = key_of(url or "", domain, title)
                    if identity in seen[week][code]:
                        continue
                    seen[week][code].add(identity)
                    buckets[week][code].append({
                        "title": title,
                        "url": url or "",
                        "outlet": domain,
                        "date": iso_day(day),
                        "hostile": bool(HOSTILE.search(title)),
                        "official": bool(OFFICIAL.search(title)),
                        "rank": score(title, code),
                    })
    finally:
        con.close()

    picked = {}
    officials = {}
    for week in weeks:
        picked[week] = {}
        officials[week] = {}
        for code in COUNTRIES:
            rows = sorted(buckets[week][code], key=lambda row: (row["rank"], row["date"]), reverse=True)
            chosen = []
            for row in rows:
                if len(chosen) >= 5:
                    break
                item = {key: row[key] for key in ("title", "url", "outlet", "date", "hostile")}
                item["english"] = ""
                chosen.append(item)
            picked[week][code] = chosen
            named = [row for row in rows if row["official"]][:3]
            officials[week][code] = [
                {key: row[key] for key in ("title", "url", "outlet", "date")}
                for row in named
            ]
    payload = {
        "source": "data/now/gkg-now.sqlite",
        "window_start": view["window_start"],
        "window_end": view["window_end"],
        "rule": "Top 5 Russian-outlet titles per country per week. Hostile keyword first, then a title that names only that country, then a border, drone, military, NATO, or sanctions word. English lines are written by hand. No model call.",
        "weeks": picked,
        "officials": officials,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    missing = 0
    for week in weeks:
        for code in COUNTRIES:
            chip = view["attention"][week][code]
            got = len(picked[week][code])
            expect = min(5, chip)
            if got != expect:
                print("COUNT", week, code, "chip", chip, "got", got, "expect", expect)
            missing += sum(1 for item in picked[week][code] if not item["english"])
    print("weeks", len(weeks), "missing_english", missing, "out", OUT)


if __name__ == "__main__":
    main()
