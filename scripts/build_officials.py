#!/usr/bin/env python3
"""Build the officials layer from stored headlines. Read-only. No model calls."""

import json
import re
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GKG = ROOT / "data" / "backtest" / "gkg.sqlite"
ENGLISH = ROOT / "frontend" / "headline_en.json"
OFFICIAL = ROOT / "frontend" / "official.json"
OUT = ROOT / "frontend" / "officials.json"
MISSING = Path("/tmp/efm-officials-missing.json")

STEMS = {
    "FI": ("finland", "finnish", "финлянд", "финск"),
    "EE": ("estonia", "estonian", "эстон"),
    "LV": ("latvia", "latvian", "латви"),
    "LT": ("lithuania", "lithuanian", "литв"),
    "PL": ("poland", "polish", "польш"),
}
RU_NAME = re.compile(
    r"путин|кремл|песков|лавров|захаров|шоигу|госдум|совфед|совет федерации|"
    r"мид рф|мид россии|миноборон|"
    r"putin|kremlin|peskov|lavrov|zakharova|shoigu|state duma|federation council",
    re.IGNORECASE,
)
WEST_NAME = re.compile(
    r"nato|столтенберг|stoltenberg|biden|байден|blinken|блинкен|"
    r"president of (finland|estonia|latvia|lithuania|poland)|"
    r"prime minister of (finland|estonia|latvia|lithuania|poland)|"
    r"(finnish|estonian|latvian|lithuanian|polish) (president|prime minister|minister)|"
    r"президент\w* (финлянд|эстон|латви|литв|польш)|"
    r"премьер\w*.{0,40}(финлянд|эстон|латви|литв|польш)|"
    r"niinist|kallas|karins|nauseda|duda|morawiecki|psaki|псаки",
    re.IGNORECASE,
)
KALININGRAD = re.compile(r"калининград|kaliningrad", re.IGNORECASE)


def monday(day: str) -> str:
    date = datetime.strptime(day, "%Y%m%d").date()
    return (date - timedelta(days=date.weekday())).isoformat()


def named(title: str) -> list[str]:
    low = title.lower()
    return [code for code, stems in STEMS.items() if any(stem in low for stem in stems)]


def keep_title(title: str) -> bool:
    if KALININGRAD.search(title) and not named(title):
        return False
    return True


def english_line(title: str, stream: str, stored: dict) -> str:
    if stream == "english" or not re.search(r"[А-Яа-яЁё]", title):
        return title
    return stored.get(title, "")


def add(bucket: dict, week: str, code: str, item: dict) -> None:
    rows = bucket.setdefault(week, {}).setdefault(code, [])
    if any(row["url"] == item["url"] for row in rows):
        return
    rows.append(item)
    if len(rows) > 40:
        rows.sort(key=prefer)
        del rows[24:]


def prefer(row: dict) -> tuple:
    return (0 if row.get("english") else 1, 0 if row.get("kind") == "official" else 1, row["date"], row["title"])


def main() -> None:
    stored = json.loads(ENGLISH.read_text(encoding="utf-8"))
    official = json.loads(OFFICIAL.read_text(encoding="utf-8"))
    russian: dict = {}
    western: dict = {}
    con = sqlite3.connect(f"file:{GKG}?mode=ro", uri=True)
    con.execute("PRAGMA query_only=ON")
    query = """
        SELECT day, stream, page_title, article_url, domain
        FROM kept
        WHERE day >= '20210104' AND day <= '20220227' AND page_title != ''
    """
    for day, stream, title, url, domain in con.execute(query):
        if not title or not keep_title(title):
            continue
        week = monday(day)
        if week < "2021-01-04" or week > "2022-02-21":
            continue
        host = (domain or "").lower()
        codes = named(title)
        if RU_NAME.search(title):
            line = english_line(title, stream, stored)
            item = {
                "title": title,
                "english": line,
                "url": url or "",
                "outlet": host or "Unknown outlet",
                "date": f"{day[:4]}-{day[4:6]}-{day[6:8]}",
                "countries": codes,
            }
            for code in codes:
                add(russian, week, code, item)
            add(russian, week, "REGION", item)
        if "tass." in host and WEST_NAME.search(title) and stream == "english":
            item = {
                "title": title,
                "english": title,
                "url": url or "",
                "outlet": "TASS",
                "date": f"{day[:4]}-{day[4:6]}-{day[6:8]}",
                "countries": codes,
                "kind": "tass",
            }
            for code in codes:
                add(western, week, code, item)
            add(western, week, "REGION", item)
    for week, rows in official.items():
        for row in rows:
            item = {
                "title": row.get("who", "Official"),
                "english": row.get("summary", ""),
                "url": row.get("url", ""),
                "outlet": row.get("who", "Official"),
                "date": row.get("date", week),
                "countries": row.get("countries", []),
                "kind": "official",
            }
            if not item["english"]:
                continue
            for code in item["countries"]:
                if code in STEMS:
                    add(western, week, code, item)
            add(western, week, "REGION", item)
    for week in list(russian):
        for code, rows in russian[week].items():
            rows.sort(key=prefer)
            del rows[3:]
    for week in list(western):
        for code, rows in western[week].items():
            rows.sort(key=prefer)
            del rows[3:]
    weeks = sorted(set(russian) | set(western))
    out = {
        week: {"russian": russian.get(week, {}), "western": western.get(week, {})}
        for week in weeks
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    shown_missing = sorted({
        item["title"]
        for week in russian
        for rows in russian[week].values()
        for item in rows
        if not item.get("english")
    })
    MISSING.write_text(json.dumps(shown_missing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"weeks {len(out)} missing {len(shown_missing)}")


if __name__ == "__main__":
    main()
