#!/usr/bin/env python3
"""Build frontend/headlines.json from the stored sample. No API calls.

Hostile is a yes or no in the stored answers. There is no separate hostility
score. Up to three headlines a week are kept, preferring the ones with more
hostile frames marked, then the earlier day, then the title.
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
OUT = ROOT / "frontend" / "headlines.json"

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
    "mundo.sputniknews.com": "Sputnik",
    "pl.sputniknews.com": "Sputnik",
    "br.sputniknews.com": "Sputnik",
    "fr.sputniknews.com": "Sputnik",
    "rs.sputniknews.com": "Sputnik",
    "vn.sputniknews.com": "Sputnik",
    "1tv.ru": "Channel One",
}
FRAMES = ("F1", "F2", "F3", "F4", "F5", "F6")


def iso_week(day: str) -> str:
    from datetime import date, timedelta
    parsed = date(int(day[:4]), int(day[4:6]), int(day[6:8]))
    return (parsed - timedelta(days=parsed.weekday())).isoformat()


def outlet(url: str) -> str:
    host = urlparse(url).netloc.lower().removeprefix("www.")
    return OUTLETS.get(host, host)


def hostile_yes(raw: str) -> bool:
    try:
        value = json.loads(raw).get("hostile_framing")
    except json.JSONDecodeError:
        return False
    return str(value).strip().lower() in {"yes", "true", "1"}


def frame_count(raw: str) -> int:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return 0
    count = 0
    for key in FRAMES:
        value = data.get(key)
        if value in {1, "1", "yes", "true", True}:
            count += 1
    return count


def main() -> None:
    english = json.loads(ENGLISH.read_text(encoding="utf-8"))
    answers = sqlite3.connect(f"file:{ANSWERS}?mode=ro", uri=True)
    sample = sqlite3.connect(f"file:{SAMPLE}?mode=ro", uri=True)
    rows = answers.execute(
        """
        SELECT region, sample_id, result_json
        FROM answers
        WHERE status = 'ok'
        """
    ).fetchall()
    picked: dict[tuple[str, str], list] = {}
    for region, sample_id, raw in rows:
        if not hostile_yes(raw):
            continue
        story = sample.execute(
            "SELECT day, url, title FROM stories WHERE rowid = ?",
            (sample_id,),
        ).fetchone()
        if story is None or not story[2]:
            continue
        day, url, title = story
        week = iso_week(day)
        if week < "2021-01-04":
            continue
        picked.setdefault((region, week), []).append({
            "title": title,
            "outlet": outlet(url),
            "date": f"{day[:4]}-{day[4:6]}-{day[6:8]}",
            "url": url,
            "frames": frame_count(raw),
            "day": day,
        })
    out = {}
    missing = []
    for key, items in picked.items():
        items.sort(key=lambda item: (-item["frames"], item["day"], item["title"]))
        seen = set()
        chosen = []
        for item in items:
            if item["title"] in seen:
                continue
            seen.add(item["title"])
            translation = english.get(item["title"])
            if not translation:
                missing.append(item["title"])
                continue
            chosen.append({
                "title": item["title"],
                "english": translation,
                "outlet": item["outlet"],
                "date": item["date"],
                "url": item["url"],
            })
            if len(chosen) == 3:
                break
        out[key[0] + "|" + key[1]] = chosen
    if missing:
        raise SystemExit(f"{len(set(missing))} selected titles have no English line")
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(out)} week keys, {sum(len(v) for v in out.values())} headlines")


if __name__ == "__main__":
    main()
