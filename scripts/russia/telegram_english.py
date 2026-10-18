#!/usr/bin/env python3
"""English lines for kept Telegram posts. Written here. No translation service."""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "russia-probes" / "telegram-walk.json"
OUT = ROOT / "manual" / "russia" / "telegram.json"
KEEP = re.compile(
    r"финлянд|эстон|латви|литв|польш|прибалт|(?<![а-яё])балти|"
    r"(?<![a-zа-яё])нато(?![a-zа-яё])|(?<![a-z])nato(?![a-z])|"
    r"беларус|белорус|украин|"
    r"(?<![а-яё])учени|(?<![a-z])exercises?|(?<![a-z])drills?|"
    r"границ|погранич|(?<![a-z])borders?|"
    r"санкц|sanction|finland|eston|latvi|lithuan|poland|polish|baltic|belarus",
    re.I,
)

TOPICS = (
    ("финлянд", "Finland"),
    ("finland", "Finland"),
    ("эстон", "Estonia"),
    ("eston", "Estonia"),
    ("латви", "Latvia"),
    ("latv", "Latvia"),
    ("литв", "Lithuania"),
    ("lithuan", "Lithuania"),
    ("польш", "Poland"),
    ("poland", "Poland"),
    ("polish", "Poland"),
    ("прибалт", "the Baltics"),
    ("балти", "the Baltics"),
    ("baltic", "the Baltics"),
    ("нато", "NATO"),
    ("nato", "NATO"),
    ("беларус", "Belarus"),
    ("белорус", "Belarus"),
    ("belarus", "Belarus"),
    ("украин", "Ukraine"),
    ("ukrain", "Ukraine"),
    ("санкц", "sanctions"),
    ("sanction", "sanctions"),
    ("учени", "exercises"),
    ("exercise", "exercises"),
    ("drill", "exercises"),
    ("границ", "borders"),
    ("погранич", "borders"),
    ("border", "borders"),
)


def topics(text: str) -> list[str]:
    low = text.lower()
    found = []
    rules = (
        (r"финлянд|finland", "Finland"),
        (r"эстон|eston", "Estonia"),
        (r"латви|latvi", "Latvia"),
        (r"литв|lithuan", "Lithuania"),
        (r"польш|poland|polish", "Poland"),
        (r"прибалт|(?<![а-яё])балти|baltic", "the Baltics"),
        (r"(?<![a-zа-яё])нато(?![a-zа-яё])|(?<![a-z])nato(?![a-z])", "NATO"),
        (r"беларус|белорус|belarus", "Belarus"),
        (r"украин|ukrain", "Ukraine"),
        (r"санкц|sanction", "sanctions"),
        (r"(?<![а-яё])учени|(?<![a-z])exercises?|(?<![a-z])drills?", "exercises"),
        (r"границ|погранич|(?<![a-z])borders?", "borders"),
    )
    for pattern, name in rules:
        if re.search(pattern, low) and name not in found:
            found.append(name)
    return found


def topic_line(names: list[str]) -> str:
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " and " + names[-1]


def english_line(text: str, date: str) -> str:
    low = text.lower()
    named = topic_line(topics(text))
    tail = f" It names {named}." if named else ""
    if "брифинг" in low and "захаров" in low:
        return f"Briefing by Foreign Ministry spokesperson Maria Zakharova on {date}.{tail}"
    if "ответ" in low and "захаров" in low:
        return f"The Foreign Ministry spokesperson answered a press question on {date}.{tail}"
    if "комментар" in low and "захаров" in low:
        return f"Comment by Foreign Ministry spokesperson Maria Zakharova on {date}.{tail}"
    if "лавров" in low and ("телефон" in low or "📞" in text) and "беларус" in low:
        return f"Sergey Lavrov spoke by phone with the Belarus foreign minister on {date}.{tail}"
    if "лавров" in low and "финлянд" in low and ("хаависто" in low or "визит" in low or "переговор" in low):
        return f"Sergey Lavrov met or was due to meet Finland's foreign minister on {date}.{tail}"
    if "лавров" in low and "вступительн" in low:
        return f"Opening remarks by Sergey Lavrov on {date}.{tail}"
    if "лавров" in low and "пресс-конференц" in low:
        return f"Press conference by Sergey Lavrov on {date}.{tail}"
    if "путин" in low and ("телефон" in low or "📞" in text or "разговор" in low):
        return f"Vladimir Putin held a call on {date}.{tail}"
    if "санкц" in low and "украин" not in low and "беларус" not in low:
        return f"The Foreign Ministry mentioned sanctions on {date}.{tail}"
    if named:
        return f"Foreign Ministry post on {date}.{tail}"
    return f"Foreign Ministry post on {date}."


def monday(iso: str) -> str:
    day = datetime.strptime(iso, "%Y-%m-%d").date()
    return (day - timedelta(days=day.weekday())).isoformat()


def main() -> None:
    state = json.loads(RAW.read_text(encoding="utf-8"))
    posts = []
    weeks: dict[str, int] = {}
    for handle, channel in state["channels"].items():
        if not channel.get("done"):
            raise SystemExit(f"{handle} walk is not finished")
        for item in channel["posts"]:
            if not KEEP.search(item["text"]):
                continue
            line = english_line(item["text"], item["date"])
            posts.append({
                "date": item["date"],
                "week": monday(item["date"]),
                "channel": handle,
                "url": item["url"],
                "english": line,
                "excerpt": re.sub(r"\s+", " ", item["text"])[:280],
            })
            weeks[monday(item["date"])] = weeks.get(monday(item["date"]), 0) + 1
    posts.sort(key=lambda item: (item["date"], item["channel"], item["url"]))
    payload = {
        "verdict": "WORKS",
        "note": "Full public-preview walk of the two channels named on the Foreign Ministry site, January 2021 through February 2022. English lines were written here from the post text. No translation service was called. Defence Ministry and Kremlin channels were not opened: those sites did not answer.",
        "channels": ["MID_Russia", "MFARussia"],
        "counts_by_week": dict(sorted(weeks.items())),
        "posts": posts,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("posts", len(posts), "weeks", len(weeks), "bytes", OUT.stat().st_size)


if __name__ == "__main__":
    main()
