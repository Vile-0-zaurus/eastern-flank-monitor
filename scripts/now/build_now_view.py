#!/usr/bin/env python3
"""Build the Now-tab JSON from the frozen window. Read-only. No model calls.

Rows outside config/now.yaml stay in the database and are not written here.
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline" / "fetch"))

from now_download import configured_window  # noqa: E402
import gkg_backfill as bf  # noqa: E402

DB = ROOT / "data" / "now" / "gkg-now.sqlite"
OUT = ROOT / "frontend" / "now-view.json"
COUNTRIES = ("FI", "EE", "LV", "LT", "PL")
ENGLISH = {
    "the", "a", "of", "and", "to", "in", "for", "on", "with", "from", "by",
    "is", "are", "was", "were", "that", "this", "as", "at", "an", "after",
}
TITLE_STEMS = {
    "FI": re.compile(r"finland|finnish|финлянд", re.I),
    "EE": re.compile(r"estonia|estonian|эстон", re.I),
    "LV": re.compile(r"latvia|latvian|латви", re.I),
    "LT": re.compile(r"lithuania|lithuanian|литв", re.I),
    "PL": re.compile(r"poland|polish|польш", re.I),
}


def monday_of(day: str) -> str:
    current = datetime.strptime(day, "%Y%m%d").date()
    start = current - timedelta(days=current.weekday())
    return start.isoformat()


def weeks_in(start: str, end: str) -> list[str]:
    first = datetime.strptime(start, "%Y%m%d").date()
    last = datetime.strptime(end, "%Y%m%d").date()
    found = []
    cursor = first - timedelta(days=first.weekday())
    while cursor <= last:
        found.append(cursor.isoformat())
        cursor += timedelta(days=7)
    return found


def countries_named(title: str) -> list[str]:
    return [code for code, pattern in TITLE_STEMS.items() if pattern.search(title or "")]


def looks_english(title: str) -> bool:
    words = [word.strip(".,:;!?\"'").lower() for word in (title or "").split()]
    return sum(word in ENGLISH for word in words) >= 2


# Each row was checked against a fetched page, or against a stored Yle/BBC row
# whose title is already English. Dates below are the incident date, not the
# week Monday. source_date is the date printed on the page, or the stored
# GKG day when the live page did not print a calendar date.
INCIDENTS = [
    {
        "date": "2026-08-14",
        "type": "drone",
        "country": "FI",
        "place": "Eastern Gulf of Finland",
        "lat": 59.8737,
        "lon": 26.3230,
        "summary": "Finland closed the eastern Gulf of Finland airspace overnight and reopened it that morning.",
        "source": "https://yle.fi/a/74-20241014",
        "source_date": "2026-08-14",
        "source_note": "Stored Yle row. The page prints 14.8.",
    },
    {
        "date": "2026-08-20",
        "type": "drone",
        "country": "FI",
        "place": "South of Utö",
        "lat": 59.7806,
        "lon": 21.3741,
        "summary": "A Russian IL-20 is suspected of entering Finnish airspace south of Utö for about three minutes.",
        "source": "https://yle.fi/a/74-20242226",
        "source_date": "2026-08-21",
        "source_note": "Stored Yle row. The page prints 21.8 and says Thursday afternoon.",
    },
    {
        "date": "2026-09-01",
        "type": "drone",
        "country": "FI",
        "place": "Pellinge, Porvoo",
        "lat": 60.2139,
        "lon": 25.8526,
        "summary": "A surveying drone was found on the Pellinge coast. The Border Guard opened a border-violation investigation.",
        "source": "https://raja.fi/en/-/border-guard-starts-investigating-the-discovered-drone-as-a-border-violation",
        "source_date": "2026-09-04",
        "source_note": "Finnish Border Guard page, publication date 4.9.2026. The find is dated 1 September.",
    },
    {
        "date": "2026-08-15",
        "type": "sabotage",
        "country": "EE",
        "place": "Tallinn",
        "lat": 59.4372,
        "lon": 24.7573,
        "summary": "Estonia's foreign minister said the 14–15 August arson at Milrem Robotics was sabotage ordered by Russian special services. The city is named in a stored Yle headline, not on the ministry page.",
        "source": "https://www.vm.ee/en/news/foreign-minister-tsahkna-estonia-challenging-target-russias-hybrid-attacks",
        "source_date": "2026-09-29",
        "source_note": "Estonian Foreign Ministry page prints 29.09.2026.",
    },
    {
        "date": "2026-09-15",
        "type": "drone",
        "country": "LT",
        "place": "Near Kaunas",
        "lat": 54.8982,
        "lon": 23.9045,
        "summary": "NATO jets shot down a drone that entered Lithuanian airspace near Kaunas shortly after midnight.",
        "source": "https://www.bbc.co.uk/news/articles/cjx2zgk7edlzo",
        "source_date": "2026-09-15",
        "source_note": "Stored BBC row. The live page did not print a calendar date.",
    },
    {
        "date": "2026-09-23",
        "type": "drone",
        "country": "PL",
        "place": "North of Braniewo",
        "lat": 54.3791,
        "lon": 19.8222,
        "summary": "Poland said a Russian Mi-8 crossed from Kaliningrad about 300 metres into Polish airspace for 42 seconds.",
        "source": "https://www.bbc.co.uk/news/articles/c699d2dn9z0mo",
        "source_date": "2026-09-23",
        "source_note": "Stored BBC row. The live page did not print a calendar date.",
    },
    {
        "date": "2026-09-27",
        "type": "border",
        "country": "LT",
        "place": "Tausiūnai and Eišiškės",
        "lat": 54.1524,
        "lon": 25.0582,
        "summary": "Border guards brought down two cigarette drones that entered from Belarus near Tausiūnai and Eišiškės.",
        "source": "https://vsat.lrv.lt/lt/naujienos/per-kelias-valandas-purvenu-pasienieciai-nukove-du-is-baltarusijos-skridusius-dronus-su-cigareciu-kroviniu-foto-xjM/",
        "source_date": "2026-09-28",
        "source_note": "Lithuanian State Border Guard page prints 2026-09-28. English line written from that page, not a full translation.",
    },
    {
        "date": "2026-08-14",
        "type": "drone",
        "country": "LV",
        "place": "Balvi Municipality",
        "lat": 57.073622,
        "lon": 27.464738,
        "status": "Officially confirmed",
        "summary": "Officially confirmed. NATO jets shot down a foreign drone in Balvi Municipality after it entered Latvian airspace. The ministry said Russian electronic warfare was the cause.",
        "source": "https://www.mod.gov.lv/en/news/foreign-drone-shot-down-allied-fighter-jets-latvian-airspace",
        "source_date": "2026-08-14",
        "source_note": "Latvian defence ministry page prints 14.08.2026. Map pin is the discovery page's approximate marker for Balvi Municipality, not a surveyed point.",
    },
    {
        "date": "2026-09-01",
        "type": "drone",
        "country": "LV",
        "place": "Alūksne Municipality",
        "lat": 57.383077,
        "lon": 27.188973,
        "status": "Officially confirmed",
        "summary": "Officially confirmed. Latvia declared an airspace threat in Alūksne Municipality at 03:37 and activated NATO fighters. The ministry page does not say an object entered Estonia.",
        "source": "https://www.mod.gov.lv/lv/zinas/izsludinats-apdraudejums-latvijas-gaisa-telpa-aluksnes-novada",
        "source_date": "2026-09-01",
        "source_note": "Latvian defence ministry page prints 01.09.2026. English line written from that page. Map pin is the discovery page's approximate marker.",
    },
    {
        "date": "2026-10-18",
        "type": "drone",
        "country": "LT",
        "place": "Juodžionys, Pasvalys",
        "lat": 56.153141,
        "lon": 24.537617,
        "status": "Reported",
        "summary": "Reported. A discovery page says a drone exploded near Juodžionys. Lithuania's defence ministry confirms only that NATO jets scrambled that day for an unidentified target and could not identify it.",
        "source": "https://www.globalmilitary.net/conflicts/european-airspace/incidents/202610-167/",
        "source_date": "2026-10-18",
        "source_note": "Place and explosion are on the discovery page, which prints 18 Oct 2026. Ministry page dated 2026-10-19 confirms the scramble only. Pin is the discovery page's approximate marker.",
    },
    {
        "date": "2026-10-18",
        "type": "drone",
        "country": "LV",
        "place": "Liepna Parish",
        "lat": 57.327340,
        "lon": 27.530341,
        "status": "Reported",
        "summary": "Reported. A discovery page places a crashed foreign drone in Liepna Parish on 18 October. No official page naming that place was fetched.",
        "source": "https://www.globalmilitary.net/conflicts/european-airspace/incidents/202610-169/",
        "source_date": "2026-10-18",
        "source_note": "Discovery page prints 18 Oct 2026. No defence-ministry page naming Liepna was fetched. Pin is that page's approximate marker.",
    },
]


def main() -> None:
    window = configured_window()
    if not window:
        raise SystemExit("Now window is not frozen")
    start, end = window
    week_list = weeks_in(start, end)
    russian = set(bf.load_outlets())
    counts: dict[str, dict[str, int]] = {week: {code: 0 for code in COUNTRIES} for week in week_list}
    news = []
    outside = 0
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=60)
    con.execute("PRAGMA query_only=ON")
    try:
        outside = con.execute(
            "SELECT COUNT(*) FROM kept WHERE day < ? OR day > ?",
            (start, end),
        ).fetchone()[0]
        cur = con.execute(
            "SELECT day, domain, seendate, article_url, page_title, locations FROM kept"
        )
        while True:
            chunk = cur.fetchmany(5000)
            if not chunk:
                break
            for day, domain, seen, url, title, locations in chunk:
                if day < start or day > end:
                    continue
                week = monday_of(day)
                if week not in counts:
                    continue
                found = countries_named(title or "")
                if domain in russian:
                    for code in found:
                        counts[week][code] += 1
                if domain in {"yle.fi", "bbc.com", "bbc.co.uk"} and looks_english(title) and found and url:
                    news.append({
                        "week": week,
                        "date": f"{day[:4]}-{day[4:6]}-{day[6:8]}",
                        "title": title,
                        "english": title,
                        "url": url,
                        "outlet": domain,
                        "countries": sorted(found),
                    })
    finally:
        con.close()
    usual = {}
    for code in COUNTRIES:
        series = [counts[week][code] for week in week_list]
        usual[code] = int(median(series))
    inside_weeks = {}
    for week in week_list:
        total = sum(counts[week].values())
        base = sum(usual.values())
        arrow = "↑" if total > base else "↓" if total < base else "→"
        inside_weeks[week] = {
            "cards": [{
                "title": "Russian media",
                "line": f"{total} flank stories, usual {base}",
                "arrow": arrow,
            }]
        }
    payload = {
        "window_start": "2026-08-03",
        "window_end": "2026-10-25",
        "label": "Now: attention and incidents only; full tension level not computed",
        "weeks": week_list,
        "usual": usual,
        "attention": counts,
        "outside_rows_excluded": outside,
        "gaps": [
            "No dated GPS-jamming incident in this window had an official page or a stored Yle/BBC row that named a specific event.",
            "No new cable or pipeline damage in this window. The Eagle S court item is about an earlier case.",
            "No Vilnius airport closure caused by Belarus balloons in this window had a fetched page dated 2026. Airport notices that describe a closure are dated 2025. A border-guard page dated 2026-10-08 reports a cigarette seizure in Vilnius with balloon remnants; that is not an airport closure and was not mapped.",
        ],
        "incidents": INCIDENTS,
        "news": news,
        "inside": {
            "note": "Inside Russia informs; it does not change the tension levels. Counts measure news volume, not military preparation.",
            "coverage": "Now window only, 3 August through 25 October 2026. Older stored rows are excluded.",
            "volume_note": "Usual is the median weekly count inside this frozen window. It is not the registered scoring baseline.",
            "weeks": inside_weeks,
        },
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"weeks={len(week_list)} news={len(news)} incidents={len(INCIDENTS)} outside={outside}")
    print("usual", usual)


if __name__ == "__main__":
    main()
