#!/usr/bin/env python3
"""Weekly defense-contractor counts from stored headlines. Read-only. No network."""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "data/backtest/gkg.sqlite"
ENGLISH = ROOT / "frontend/headline_en.json"
OUT = ROOT / "manual/russia/contractors.json"

COMPANIES = (
    ("Rostec", r"(?<![a-zа-яё])(?:rostec|ростех)(?![a-zа-яё])"),
    ("Almaz-Antey", r"almaz[-\s]?antey|алмаз[-\s]?антей"),
    ("Uralvagonzavod", r"uralvagonzavod|уралвагонзавод"),
    ("Kalashnikov", r"(?<![a-zа-яё])(?:kalashnikov|калашников\w*)(?![a-zа-яё])"),
    ("UAC", r"united aircraft|авиастроительн\w*|объедин[её]нн\w* авиастроительн\w*|(?<![a-zа-яё])оак(?![a-zа-яё])"),
    ("Tactical Missiles", r"tactical missiles|(?<![a-zа-яё])ктрв(?![a-zа-яё])|тактическ\w* ракетн\w*"),
    ("KAMAZ", r"(?<![a-zа-яё])(?:kamaz|камаз)(?![a-zа-яё])"),
)
RELEVANT = re.compile(
    r"производ|сверхуроч|дополнительн\w* смен|в три смен|найм|набор персонал|ваканс|"
    r"контракт|гособоронзаказ|госзаказ|государственн\w* заказ|"
    r"production|extra shift|three shift|hiring|vacanc|contract|state order",
    re.I,
)


def monday(day: str) -> str:
    parsed = datetime.strptime(day, "%Y%m%d").date()
    return (parsed - timedelta(days=parsed.weekday())).isoformat()


def company_of(title: str) -> str:
    low = title.lower()
    for name, pattern in COMPANIES:
        if re.search(pattern, low):
            return name
    return ""


def main() -> None:
    english = {}
    if ENGLISH.exists():
        loaded = json.loads(ENGLISH.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            english = {key: value for key, value in loaded.items() if isinstance(value, str)}
    sql_stems = (
        "rostec", "ростех", "almaz", "antey", "алмаз", "антей",
        "uralvagonzavod", "уралвагонзавод", "kalashnikov", "калашников",
        "united aircraft", "авиастроительн", "оак", "tactical missiles",
        "ктрв", "ракетн", "kamaz", "камаз",
    )
    clauses = []
    params: list[str] = []
    for stem in sql_stems:
            clauses.append("LOWER(page_title) LIKE ?")
            params.append(f"%{stem}%")
    query = f"""
        SELECT day, domain, page_title, article_url, stream
        FROM kept
        WHERE day >= '20210104' AND day <= '20220227'
          AND page_title IS NOT NULL AND page_title != ''
          AND ({' OR '.join(clauses)})
    """
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    con.execute("PRAGMA query_only=ON")
    by_company: dict[str, int] = {}
    weeks: dict[str, dict] = {}
    seen: set[tuple[str, str]] = set()
    for day, domain, title, url, stream in con.execute(query, params):
        name = company_of(title)
        if not name:
            continue
        week = monday(day)
        if week < "2021-01-04" or week > "2022-02-21":
            continue
        key = (week, url or title)
        if key in seen:
            continue
        seen.add(key)
        bucket = weeks.setdefault(week, {"count": 0, "relevant": 0, "example": None})
        bucket["count"] += 1
        by_company[name] = by_company.get(name, 0) + 1
        relevant = bool(RELEVANT.search(title))
        if relevant:
            bucket["relevant"] += 1
        if relevant and bucket["example"] is None:
            line = english.get(title, "")
            if stream == "english" and not line:
                line = title
            bucket["example"] = {
                "company": name,
                "title": title,
                "english": line,
                "url": url or "",
                "outlet": domain or "",
                "date": f"{day[:4]}-{day[4:6]}-{day[6:8]}",
            }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": "Stored headlines already in this project. No new fetch.",
        "window": "2021-01-04 to 2022-02-21",
        "companies": [name for name, _pattern in COMPANIES],
        "by_company": by_company,
        "note": "Count is headlines that name a listed company. The example is the first title that week about production, shifts, hiring, contracts, or a state order. No such title means count only.",
        "weeks": weeks,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    named = sum(row["count"] for row in weeks.values())
    with_example = sum(1 for row in weeks.values() if row["example"])
    print("weeks", len(weeks), "headlines", named, "weeks_with_example", with_example, "bytes", OUT.stat().st_size)


if __name__ == "__main__":
    main()
