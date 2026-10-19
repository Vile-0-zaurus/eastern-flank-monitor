#!/usr/bin/env python3
"""Build the Inside Russia cards for each stored week. No network. No model call."""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "frontend" / "inside-main.json"

EVENTS = {
    "event_buildup_apr": "A stored report says there was a buildup near Ukraine, and that those troops were ordered back by 1 May.",
    "event_zapad": "A stored report says Zapad-2021 was a large exercise in the western military district and Belarus.",
    "event_vehicles_dec": "A stored report says a base in Crimea was packed with armoured vehicles.",
    "event_arriving": "A stored report says Russian forces and hardware began arriving in Belarus for drills.",
    "event_logistics": "A stored report says the buildup near Ukraine included medical supplies.",
    "event_allied": "A stored report names Allied Resolve drills and Russian troops.",
    "event_warning": "A stored report says more than 100,000 troops were at the Ukrainian border.",
    "event_hospitals": "A stored report says field hospitals appeared near the Ukrainian border.",
    "event_mozyr": "A stored report says vehicles and shelters were at an airfield near Mozyr.",
    "event_belgorod": "A stored report says a field hospital was seen on the western edge of Belgorod.",
}


def monday(iso: str) -> str:
    day = datetime.strptime(iso[:10], "%Y-%m-%d").date()
    return (day - timedelta(days=day.weekday())).isoformat()


def weeks() -> list[str]:
    day = datetime.strptime("2021-01-04", "%Y-%m-%d").date()
    end = datetime.strptime("2022-02-21", "%Y-%m-%d").date()
    found = []
    while day <= end:
        found.append(day.isoformat())
        day += timedelta(days=7)
    return found


def arrow(value: float, usual: float) -> str:
    if value > usual:
        return "↑"
    if value < usual:
        return "↓"
    return "→"


def relation(value: float, usual: float) -> str:
    if value > usual:
        return "above"
    if value < usual:
        return "below"
    return "about"


def count_in(text: str) -> int:
    if re.search(r"No |no ", text):
        return 0
    match = re.search(r"(\d+)", text)
    return int(match.group(1)) if match else 0


def unfriendly_bars(result: str) -> list[dict]:
    section = result.split("Unfriendly:", 1)[1].split(".", 1)[0]
    found = {}
    for part in section.split(","):
        match = re.search(r"(\d+)\s+percent", part)
        if not match:
            continue
        name = part[: match.start()].strip()
        if name.lower().startswith("the "):
            name = name[4:]
        found[name] = int(match.group(1))
    order = (
        ("Lithuania", "Lithuania", False),
        ("Latvia", "Latvia", False),
        ("Estonia", "Estonia", False),
        ("Poland", "Poland", False),
        ("Finland", "Finland", False),
        ("United States", "USA", True),
        ("Ukraine", "Ukraine", True),
    )
    bars = []
    for source_name, label, reference in order:
        pct = found.get(source_name)
        bars.append({
            "name": label + (" (reference)" if reference else ""),
            "pct": pct,
            "reference": reference,
        })
    return bars


def mood_card(week: str, poll_items: list[dict]) -> dict:
    survey = next((item for item in poll_items if item.get("date") == "2021-06-15" and "Unfriendly:" in item.get("result", "")), None)
    if not survey or monday(survey["date"]) > week:
        return card("Public mood", "No new data this week", "", "", "", "")
    built = card(
        "Public mood",
        "In May 2021, Russians often named the Baltic states and Poland as unfriendly (Levada).",
        "",
        "",
        "",
        survey["url"],
    )
    built["poll_date"] = "May 2021"
    built["published"] = survey["date"]
    built["pollster"] = "Levada Center"
    built["caution"] = "Polls in Russia may not reflect honest opinion"
    built["axis"] = "% of Russians naming this country unfriendly"
    built["full"] = survey["question"] + " " + survey["result"]
    built["bars"] = unfriendly_bars(survey["result"])
    return built


def card(title: str, line: str, mark: str, english: str, russian: str, url: str) -> dict:
    return {
        "title": title,
        "line": line,
        "arrow": mark,
        "english": english,
        "russian": russian,
        "url": url,
    }


def best_post(posts: list[dict]) -> dict | None:
    if not posts:
        return None
    rank = ("Briefing", "Comment", "answered", "spoke", "met", "held a call", "Opening", "Press conference")
    def score(post: dict) -> tuple:
        text = post["english"]
        for index, word in enumerate(rank):
            if word in text:
                return (index, post["date"])
        return (len(rank), post["date"])
    return sorted(posts, key=score)[0]


def main() -> None:
    telegram = json.loads((ROOT / "manual/russia/telegram.json").read_text(encoding="utf-8"))
    economy = json.loads((ROOT / "manual/russia/economy.json").read_text(encoding="utf-8"))
    contractors = json.loads((ROOT / "manual/russia/contractors.json").read_text(encoding="utf-8"))
    polls = json.loads((ROOT / "manual/russia/polls.json").read_text(encoding="utf-8"))
    inside = json.loads((ROOT / "frontend/inside-russia.json").read_text(encoding="utf-8"))
    events = json.loads((ROOT / "frontend/events.json").read_text(encoding="utf-8"))
    by_week: dict[str, list] = {}
    for post in telegram["posts"]:
        by_week.setdefault(post["week"], []).append(post)
    mod = {}
    call = {}
    for week, block in inside["weeks"].items():
        for line in block["lines"]:
            if line["kind"] == "mod":
                mod[week] = count_in(line["text"])
            elif line["kind"] == "call":
                call[week] = count_in(line["text"])
    order = weeks()
    usual_posts = median([len(by_week.get(week, [])) for week in order])
    usual_mod = median([mod.get(week, 0) for week in order])
    usual_call = median([call.get(week, 0) for week in order])
    usual_firm = median([contractors["weeks"].get(week, {}).get("count", 0) for week in order])
    ruble_values = [row["rub_per_usd"] for row in economy["ruble"]["weeks"].values()]
    usual_ruble = median(ruble_values)
    poll_items = []
    for item in polls["levada"]["items"]:
        if item.get("date"):
            poll_items.append(item)
    poll_items.sort(key=lambda item: item["date"])
    built = {}
    for week in order:
        posts = by_week.get(week, [])
        post = best_post(posts)
        if post:
            russian = post["excerpt"] if re.search(r"[А-Яа-яЁё]", post["excerpt"]) else ""
            officials = card(
                "Officials say",
                f"{len(posts)} Foreign Ministry posts this week, {relation(len(posts), usual_posts)} the usual {int(usual_posts)}.",
                arrow(len(posts), usual_posts),
                post["english"],
                russian,
                post["url"],
            )
        else:
            officials = card("Officials say", "No new data this week", "", "", "", "")
        firm = contractors["weeks"].get(week, {})
        firm_count = firm.get("count", 0)
        mod_count = mod.get(week, 0)
        week_events = []
        seen = set()
        for event in events:
            if monday(event["date"]) != week or event["textKey"] in seen:
                continue
            seen.add(event["textKey"])
            week_events.append(event)
        military_line = (
            f"Defence ministry headlines: {mod_count}, {relation(mod_count, usual_mod)} the usual {int(usual_mod)}. "
            f"Contractor headlines: {firm_count}, {relation(firm_count, usual_firm)} the usual {int(usual_firm)}. "
            f"Events this week: {len(week_events)}."
        )
        example = firm.get("example") or {}
        if example:
            military = card(
                "Military and industry",
                military_line,
                arrow(mod_count, usual_mod),
                example.get("english") or example.get("title") or "",
                example.get("title") if re.search(r"[А-Яа-яЁё]", example.get("title") or "") else "",
                example.get("url") or "",
            )
        elif week_events:
            event = week_events[0]
            military = card(
                "Military and industry",
                military_line,
                arrow(mod_count, usual_mod),
                EVENTS.get(event["textKey"], "A stored report names an event this week."),
                "",
                event.get("source") or "",
            )
        elif mod_count or firm_count:
            military = card("Military and industry", military_line, arrow(mod_count, usual_mod), "", "", "")
        else:
            military = card("Military and industry", "No new data this week", "", "", "", "")
        call_count = call.get(week, 0)
        if call_count:
            conscription = card(
                "Conscription",
                f"{call_count} conscription headlines, {relation(call_count, usual_call)} the usual {int(usual_call)}.",
                arrow(call_count, usual_call),
                "",
                "",
                "",
            )
        else:
            conscription = card("Conscription", "No new data this week", "", "", "", "")
        rate = economy["ruble"]["weeks"].get(week)
        key = economy["key_rate"]["weeks"].get(week)
        month = week[:7]
        brent = next((row for row in economy["oil"]["months"] if row["month"] == month), None)
        bits = []
        if rate:
            bits.append(f"Ruble: {rate['rub_per_usd']:.2f} per dollar, {relation(rate['rub_per_usd'], usual_ruble)} the usual {usual_ruble:.2f}.")
        if key is not None:
            bits.append(f"Key rate: {key:g} percent.")
        if brent:
            bits.append(f"Brent, month average: {brent['brent']:.2f} dollars.")
        if bits:
            economy_card = card(
                "Economy",
                " ".join(bits),
                arrow(rate["rub_per_usd"], usual_ruble) if rate else "→",
                "",
                "",
                "https://www.cbr.ru/hd_base/KeyRate/",
            )
        else:
            economy_card = card("Economy", "No new data this week", "", "", "", "")
        mood = mood_card(week, poll_items)
        built[week] = {
            "cards": [officials, military, conscription, economy_card, mood],
        }
    payload = {
        "note": "Inside Russia informs; it does not change the tension levels.",
        "coverage": "Telegram coverage: 1 January 2021 through 28 February 2022.",
        "volume_note": "Counts measure news volume, not military preparation. No exchange was used.",
        "weeks": built,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("weeks", len(built), "bytes", OUT.stat().st_size)


if __name__ == "__main__":
    main()
