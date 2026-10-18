#!/usr/bin/env python3
"""Build the committed economy file from saved Central Bank pages. No new fetch."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data/russia-probes"
OUT = ROOT / "manual/russia/economy.json"


def monday(iso: str) -> str:
    day = datetime.strptime(iso, "%Y-%m-%d").date()
    return (day - timedelta(days=day.weekday())).isoformat()


def main() -> None:
    xml_path = next(RAW.glob("econ-https-www-cbr-ru-scripts-xml*.body"))
    html_path = next(RAW.glob("econ-https-www-cbr-ru-hd-base-keyrate*.body"))
    root = ET.fromstring(xml_path.read_bytes().decode("windows-1251"))
    daily = {}
    for record in root.findall("Record"):
        day = datetime.strptime(record.attrib["Date"], "%d.%m.%Y").date().isoformat()
        value = record.findtext("Value") or ""
        nominal = record.findtext("Nominal") or "1"
        daily[day] = round(float(value.replace(",", ".")) / float(nominal.replace(",", ".")), 4)
    weekly = {}
    for day, value in daily.items():
        week = monday(day)
        if week < "2021-01-04" or week > "2022-02-21":
            continue
        previous = weekly.get(week)
        if previous is None or day > previous["date"]:
            weekly[week] = {"date": day, "rub_per_usd": value}
    html = html_path.read_text(encoding="utf-8", errors="replace")
    changes = []
    for row in re.findall(r"<tr>\s*<td>(\d{2}\.\d{2}\.\d{4})</td>\s*<td>([\d,]+)</td>", html):
        day = datetime.strptime(row[0], "%d.%m.%Y").date().isoformat()
        changes.append({"date": day, "key_rate_percent": float(row[1].replace(",", "."))})
    changes.sort(key=lambda item: item["date"])
    rate_weeks = {}
    cursor = 0
    week = datetime.strptime("2021-01-04", "%Y-%m-%d").date()
    end = datetime.strptime("2022-02-21", "%Y-%m-%d").date()
    while week <= end:
        while cursor + 1 < len(changes) and changes[cursor + 1]["date"] <= week.isoformat():
            cursor += 1
        if changes and changes[cursor]["date"] <= week.isoformat():
            rate_weeks[week.isoformat()] = changes[cursor]["key_rate_percent"]
        week += timedelta(days=7)
    payload = {
        "ruble": {
            "source": "Bank of Russia published USD rate file",
            "url": "https://www.cbr.ru/scripts/XML_dynamic.asp?date_req1=01/01/2021&date_req2=28/02/2022&VAL_NM_RQ=R01235",
            "unit": "rubles per 1 US dollar",
            "cadence": "weekly, last published rate in the week",
            "weeks": weekly,
        },
        "key_rate": {
            "source": "Bank of Russia key rate table",
            "url": "https://www.cbr.ru/hd_base/KeyRate/?UniDbQuery.Posted=True&UniDbQuery.From=01.01.2021&UniDbQuery.To=28.02.2022",
            "unit": "percent",
            "changes": changes,
            "weeks": rate_weeks,
        },
        "oil": {"status": "not collected in this file"},
        "inflation": {"status": "not collected in this file"},
        "note": "Published rates only. Not an exchange. Not trading. Not legal advice.",
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("ruble weeks", len(weekly), "key changes", len(changes), "key weeks", len(rate_weeks), "bytes", OUT.stat().st_size)


if __name__ == "__main__":
    main()
