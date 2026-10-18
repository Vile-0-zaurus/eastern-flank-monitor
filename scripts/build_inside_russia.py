#!/usr/bin/env python3
"""Count Inside Russia headline lines. Read-only. No model calls. No exchange."""

import json
import re
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GKG = ROOT / "data" / "backtest" / "gkg.sqlite"
ENGLISH = ROOT / "frontend" / "headline_en.json"
OUT = Path("/tmp/efm-inside-raw.json")

MOD = re.compile(
    r"шоигу|миноборон|министерств\w+ обороны|shoigu|defence ministry|defense ministry",
    re.IGNORECASE,
)
UKRAINE_MOD = re.compile(r"миноборон\w* украин|министерств\w+ обороны украин", re.IGNORECASE)
RUSSIAN_MOD = re.compile(r"шоигу|миноборон\w* (рф|россии)|shoigu", re.IGNORECASE)
PLANT = re.compile(
    r"уралвагон|алмаз-антей|оборонн\w+ завод|оборонн\w+ предприя|"
    r"камаз.{0,40}(завод|акци|выпуск|производ|контракт)|"
    r"сверхуроч\w*.{0,40}(завод|смен)",
    re.IGNORECASE,
)
CONSCRIPTION = re.compile(
    r"призывник|призывн|допризыв|мобилизац|резервист|военнообязан|"
    r"осенн\w+ призыв|весенн\w+ призыв|призыв в арм|call-up|call up|conscript",
    re.IGNORECASE,
)


def monday(day: str) -> str:
    date = datetime.strptime(day, "%Y%m%d").date()
    return (date - timedelta(days=date.weekday())).isoformat()


def russian_mod(title: str) -> bool:
    if UKRAINE_MOD.search(title) and not RUSSIAN_MOD.search(title):
        return False
    if re.search(r"шоигу|миноборон|shoigu", title, re.IGNORECASE):
        return True
    return bool(re.search(r"russian (defence|defense) ministry", title, re.IGNORECASE))


def better(current: dict | None, item: dict) -> dict:
    if current is None:
        return item
    if item["english"] and not current["english"]:
        return item
    return current


def main() -> None:
    stored = json.loads(ENGLISH.read_text(encoding="utf-8"))
    weeks: dict[str, dict] = {}
    con = sqlite3.connect(f"file:{GKG}?mode=ro", uri=True)
    con.execute("PRAGMA query_only=ON")
    query = """
        SELECT day, stream, page_title, article_url, domain
        FROM kept
        WHERE day >= '20210104' AND day <= '20220227' AND page_title != ''
    """
    for day, stream, title, url, domain in con.execute(query):
        week = monday(day)
        if week < "2021-01-04" or week > "2022-02-21":
            continue
        row = weeks.setdefault(week, {"mod": 0, "plant": 0, "call": 0, "mod_ex": None, "plant_ex": None, "call_ex": None})
        english = title if stream == "english" or not re.search(r"[А-Яа-яЁё]", title) else stored.get(title, "")
        item = {
            "title": title,
            "english": english,
            "url": url or "",
            "outlet": (domain or "Unknown outlet"),
            "date": f"{day[:4]}-{day[4:6]}-{day[6:8]}",
        }
        if russian_mod(title):
            row["mod"] += 1
            row["mod_ex"] = better(row["mod_ex"], item)
        if PLANT.search(title):
            row["plant"] += 1
            row["plant_ex"] = better(row["plant_ex"], item)
        if CONSCRIPTION.search(title):
            row["call"] += 1
            row["call_ex"] = better(row["call_ex"], item)
    OUT.write_text(json.dumps(weeks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("weeks", len(weeks))
    print("mod", sum(row["mod"] for row in weeks.values()))
    print("plant", sum(row["plant"] for row in weeks.values()))
    print("call", sum(row["call"] for row in weeks.values()))


if __name__ == "__main__":
    main()
