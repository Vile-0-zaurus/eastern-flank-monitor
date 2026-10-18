#!/usr/bin/env python3
"""Build frontend/news.json from the stored sample. No API calls.

English lines come only from frontend/headline_en.json. A headline with no
stored translation is kept in the original and marked not stored.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
ANSWERS = ROOT / "data" / "llm" / "i2-answers.sqlite"
SAMPLE = ROOT / "data" / "indicators" / "i2-sample.sqlite"
ENGLISH = ROOT / "frontend" / "headline_en.json"
OUT = ROOT / "frontend" / "news.json"
START = "2021-01-04"

OUTLETS = {
    "regnum.ru": "Regnum",
    "ria.ru": "RIA Novosti",
    "lenta.ru": "Lenta",
    "tass.ru": "TASS",
    "tass.com": "TASS",
    "pda.kp.ru": "Komsomolskaya Pravda",
    "pda.kaliningrad.kp.ru": "Komsomolskaya Pravda",
    "pda.donetsk.kp.ru": "Komsomolskaya Pravda",
    "iz.ru": "Izvestia",
    "russian.rt.com": "RT",
    "rt.com": "RT",
    "aif.ru": "Argumenty i Fakty",
    "gazeta.ru": "Gazeta.ru",
    "vesti.ru": "Vesti",
    "rg.ru": "Rossiyskaya Gazeta",
    "tvzvezda.ru": "Zvezda",
    "sputniknews.com": "Sputnik",
    "1tv.ru": "Channel One",
}

COUNTRIES = (
    ("FI", ("finland", "финлянд")),
    ("EE", ("estonia", "эстон")),
    ("LV", ("latvia", "латви")),
    ("LT", ("lithuania", "литв", "вильнюс")),
    ("PL", ("poland", "polish", "польш")),
    ("UA", ("ukraine", "украин")),
    ("BY", ("belarus", "беларус", "белорус")),
)


def outlet(url: str) -> str:
    host = urlparse(url or "").netloc.lower().removeprefix("www.")
    return OUTLETS.get(host, host or "Unknown outlet")


def normalize(title: str) -> str:
    text = title.replace("&quot;", '"').replace("&#x27;", "'").replace("&amp;", "&")
    cleaned = "".join(ch for ch in text.lower() if ch.isalnum() or ch.isspace())
    return " ".join(cleaned.split())


def countries_for(title: str, english: str | None) -> list[str]:
    blob = (title + " " + (english or "")).lower()
    return [code for code, stems in COUNTRIES if any(stem in blob for stem in stems)]


def main() -> None:
    english = json.loads(ENGLISH.read_text(encoding="utf-8"))
    answers = sqlite3.connect(f"file:{ANSWERS}?mode=ro", uri=True)
    answers.execute("PRAGMA query_only=ON")
    sample = sqlite3.connect(f"file:{SAMPLE}?mode=ro", uri=True)
    sample.execute("PRAGMA query_only=ON")
    hostile = {
        row[0]: row[1]
        for row in answers.execute(
            "SELECT sample_id, hostile FROM answers WHERE status = 'ok'"
        )
    }
    kept: dict[tuple[str, str], dict] = {}
    rows = sample.execute(
        """
        SELECT rowid, week, day, url, title
        FROM stories
        WHERE sampled = 1 AND week >= ? AND title != ''
        ORDER BY day, title
        """,
        (START,),
    )
    for rowid, week, day, url, title in rows:
        flag = hostile.get(str(rowid), "")
        matched = countries_for(title, english.get(title))
        if not matched and flag != "yes":
            continue
        key = (week, url or normalize(title))
        item = kept.get(key)
        translated = english.get(title)
        if item is None:
            kept[key] = {
                "week": week,
                "title": title,
                "english": translated,
                "outlet": outlet(url),
                "date": f"{day[:4]}-{day[4:6]}-{day[6:8]}",
                "url": url,
                "hostile": flag == "yes",
                "countries": matched,
            }
            continue
        if flag == "yes":
            item["hostile"] = True
        if item["english"] is None and translated:
            item["english"] = translated
            item["title"] = title
        for code in matched:
            if code not in item["countries"]:
                item["countries"].append(code)
    # Cap ordinary stories so the demo file stays a sample, not a dump.
    by_title: dict[tuple[str, str], dict] = {}
    for item in kept.values():
        key = (item["week"], normalize(item["title"]))
        prior = by_title.get(key)
        if prior is None:
            by_title[key] = item
            continue
        if item["hostile"]:
            prior["hostile"] = True
        if prior["english"] is None and item["english"]:
            prior["english"] = item["english"]
        for code in item["countries"]:
            if code not in prior["countries"]:
                prior["countries"].append(code)
    by_week: dict[str, list[dict]] = {}
    for item in by_title.values():
        by_week.setdefault(item["week"], []).append(item)
    chosen = []
    for week, items in by_week.items():
        flagged = [item for item in items if item["english"]]
        ordinary = [item for item in items if not item["hostile"] and not item["english"]]
        ordinary.sort(key=lambda item: (item["date"], item["title"]))
        chosen.extend(flagged)
        chosen.extend(ordinary[:6])
    chosen.sort(key=lambda item: (item["week"], item["date"], item["title"]))
    OUT.write_text(json.dumps(chosen, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(chosen)} stories across {len({item['week'] for item in chosen})} weeks")
    print(f"with english {sum(1 for item in chosen if item['english'])}")
    print(f"hostile {sum(1 for item in chosen if item['hostile'])}")


if __name__ == "__main__":
    main()
