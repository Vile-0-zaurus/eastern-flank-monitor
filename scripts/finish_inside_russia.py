#!/usr/bin/env python3
"""Turn the headline counts and published rates into the panel file. No exchange."""

import json
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]
RAW = Path("/tmp/efm-inside-raw.json")
RATES = Path("/tmp/efm-russia/cbr-usd.xml")
GDP = Path("/tmp/efm-russia/wb-gdp.json")
RES = Path("/tmp/efm-russia/wb-res.json")
ENGLISH = ROOT / "frontend" / "headline_en.json"
OUT = ROOT / "frontend" / "inside-russia.json"


def monday(iso: str) -> str:
    date = datetime.strptime(iso, "%Y-%m-%d").date()
    return (date - timedelta(days=date.weekday())).isoformat()


def arrow(count: int, usual: int) -> tuple[str, str]:
    if count > usual:
        return "above the usual", "↑"
    if count < usual:
        return "below the usual", "↓"
    return "about the usual", "→"


def count_line(label: str, count: int, usual: int, example: dict) -> str:
    relation, mark = arrow(count, usual)
    text = f"{label}: {count} stored headlines, {relation} {usual} {mark}."
    if example.get("english"):
        text += " " + example["english"]
    return text


def main() -> None:
    weeks = json.loads(RAW.read_text(encoding="utf-8"))
    stored = json.loads(ENGLISH.read_text(encoding="utf-8"))
    for row in weeks.values():
        for key in ("mod_ex", "plant_ex", "call_ex"):
            item = row.get(key) or {}
            if item and not item.get("english"):
                item["english"] = stored.get(item.get("title", ""), "")
    rates = {}
    for record in ET.parse(RATES).getroot().findall("Record"):
        day = datetime.strptime(record.attrib["Date"], "%d.%m.%Y").date().isoformat()
        value = record.find("Value")
        if value is None or not value.text:
            continue
        rates[day] = float(value.text.replace(",", "."))
    week_rate = {}
    for day, value in rates.items():
        week = monday(day)
        previous = week_rate.get(week)
        if previous is None or day > previous[0]:
            week_rate[week] = (day, value)
    usual = {
        "mod": int(median(row["mod"] for row in weeks.values())),
        "plant": int(median(row["plant"] for row in weeks.values())),
        "call": int(median(row["call"] for row in weeks.values())),
    }
    gdp = {row["date"]: row["value"] for row in json.loads(GDP.read_text())[1]}
    reserves = {row["date"]: row["value"] for row in json.loads(RES.read_text())[1]}
    background = {
        year: (
            f"Yearly GDP in {year} was about {gdp[year] / 1e12:.2f} trillion dollars. "
            f"Reserves including gold were about {reserves[year] / 1e9:.0f} billion dollars. World Bank."
        )
        for year in ("2021", "2022")
    }
    ordered = sorted(weeks)
    out_weeks = {}
    for week in ordered:
        row = weeks[week]
        mod_ex = row.get("mod_ex") or {}
        plant_ex = row.get("plant_ex") or {}
        call_ex = row.get("call_ex") or {}
        if row["plant"] == 0:
            plant_text = "Defense industry: No defense-plant headlines this week."
        else:
            plant_text = count_line("Defense industry", row["plant"], usual["plant"], plant_ex)
        if row["call"] == 0:
            call_text = "Conscription: No conscription news this week."
        else:
            call_text = count_line("Conscription", row["call"], usual["call"], call_ex)
        rate = week_rate.get(week)
        earlier = [item for item in ordered if item < week and item in week_rate]
        if not rate:
            ruble = "Ruble: no published Central Bank rate for this week."
            rate_date = ""
        else:
            if earlier:
                diff = rate[1] - week_rate[earlier[-1]][1]
                if abs(diff) < 0.005:
                    change = "about the same as last week →"
                elif diff > 0:
                    change = f"up {diff:.2f} from last week ↑"
                else:
                    change = f"down {abs(diff):.2f} from last week ↓"
            else:
                change = "no earlier week to compare →"
            ruble = f"Ruble: {rate[1]:.2f} per dollar on {rate[0]}, {change}."
            rate_date = rate[0]
        out_weeks[week] = {
            "lines": [
                {
                    "kind": "mod",
                    "text": count_line("Military talk", row["mod"], usual["mod"], mod_ex),
                    "english": mod_ex.get("english") or "",
                    "title": mod_ex.get("title") or "",
                    "url": mod_ex.get("url") or "",
                    "outlet": mod_ex.get("outlet") or "",
                    "date": mod_ex.get("date") or "",
                },
                {
                    "kind": "plant",
                    "text": plant_text,
                    "english": plant_ex.get("english") or "",
                    "title": plant_ex.get("title") or "",
                    "url": plant_ex.get("url") or "",
                    "outlet": plant_ex.get("outlet") or "",
                    "date": plant_ex.get("date") or "",
                },
                {
                    "kind": "call",
                    "text": call_text,
                    "english": call_ex.get("english") or "",
                    "title": call_ex.get("title") or "",
                    "url": call_ex.get("url") or "",
                    "outlet": call_ex.get("outlet") or "",
                    "date": call_ex.get("date") or "",
                },
                {
                    "kind": "ruble",
                    "text": ruble,
                    "english": ruble,
                    "title": "",
                    "url": "https://www.cbr.ru/currency_base/dynamics/",
                    "outlet": "Central Bank of Russia",
                    "date": rate_date,
                },
                {
                    "kind": "kamaz",
                    "text": "KAMAZ share price: no published price was collected. Context only. The exchange was not used.",
                    "english": "KAMAZ share price: no published price was collected. Context only. The exchange was not used.",
                    "title": "",
                    "url": "",
                    "outlet": "",
                    "date": "",
                },
            ],
            "background": background["2022" if week >= "2022-01-01" else "2021"],
        }
    display = {
        "note": "Inside Russia is display only. It does not affect the levels.",
        "sources": "Military talk, defense plants, and conscription are keyword counts in stored headlines. Counts measure news volume, not military preparation. The ruble is the Central Bank of Russia published dollar rate. GDP and reserves are World Bank yearly totals. No exchange was used.",
        "weeks": out_weeks,
    }
    OUT.write_text(json.dumps(display, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    empty = 0
    for week, block in out_weeks.items():
        if len(block["lines"]) != 5:
            empty += 1
        for line in block["lines"]:
            if not line["text"].strip():
                empty += 1
    print("weeks", len(out_weeks), "empty", empty, "bytes", OUT.stat().st_size)


if __name__ == "__main__":
    main()
