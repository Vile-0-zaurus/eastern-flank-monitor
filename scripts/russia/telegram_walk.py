#!/usr/bin/env python3
"""Page the two verified Foreign Ministry Telegram previews. One request a second. No spoofing."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pace import get

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "russia-probes" / "telegram-walk.json"
START = {
    "MID_Russia": 23000,
    "MFARussia": 14000,
}
FLOOR = {"MID_Russia": 7000, "MFARussia": 7000}
WINDOW_START = "2021-01-01"
WINDOW_END = "2022-02-28"
KEEP = re.compile(
    r"финлянд|эстон|латви|литв|польш|прибалт|(?<![а-яё])балти|"
    r"(?<![a-zа-яё])нато(?![a-zа-яё])|(?<![a-z])nato(?![a-z])|"
    r"беларус|белорус|украин|"
    r"(?<![а-яё])учени|(?<![a-z])exercises?|(?<![a-z])drills?|"
    r"границ|погранич|(?<![a-z])borders?|"
    r"санкц|sanction",
    re.I,
)


def load() -> dict:
    if OUT.exists():
        return json.loads(OUT.read_text(encoding="utf-8"))
    return {"channels": {}}


def save(state: dict) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")


def plain(html: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("&nbsp;", " ").replace("&#39;", "'").replace("&amp;", "&")
    text = text.replace("&quot;", '"').replace("&#8212;", "—")
    return re.sub(r"[ \t]+", " ", text).strip()


def parse_page(html: str, handle: str) -> list[dict]:
    found = []
    for post_id, chunk in re.findall(
        rf'data-post="{handle}/(\d+)"([\s\S]*?)(?=data-post="{handle}/\d+"|$)',
        html,
    ):
        date_match = re.search(r'datetime="([^"]+)"', chunk)
        text_match = re.search(r'tgme_widget_message_text[^>]*>([\s\S]*?)</div>', chunk)
        if not date_match or not text_match:
            continue
        body = plain(text_match.group(1))
        if len(body) < 20:
            continue
        found.append({
            "id": int(post_id),
            "date": date_match.group(1)[:10],
            "text": body[:1200],
            "url": f"https://t.me/{handle}/{post_id}",
        })
    return found


def walk(handle: str, state: dict) -> None:
    channel = state["channels"].setdefault(handle, {"before": START[handle], "posts": [], "pages": 0, "done": False})
    if channel.get("done"):
        print(handle, "already done", len(channel["posts"]))
        return
    seen = {item["id"] for item in channel["posts"]}
    before = int(channel["before"])
    empty = 0
    while before > FLOOR[handle] and empty < 2 and channel["pages"] < 800:
        url = f"https://t.me/s/{handle}?before={before}"
        record = get(url, pause=1.0, timeout=25)
        html = record.get("body", b"").decode("utf-8", errors="replace")
        title = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
        title_text = re.sub(r"\s+", " ", title.group(1)).strip() if title else ""
        if record["status"] != 200 or "Just a moment" in title_text or not html:
            print(handle, "stop", record["status"], record["error"], title_text[:60])
            channel["error"] = record["error"] or title_text or str(record["status"])
            break
        posts = parse_page(html, handle)
        channel["pages"] += 1
        if not posts:
            empty += 1
            print(handle, "empty page", before)
            break
        empty = 0
        dates = [item["date"] for item in posts]
        kept = 0
        for item in posts:
            if item["id"] in seen:
                continue
            seen.add(item["id"])
            if WINDOW_START <= item["date"] <= WINDOW_END and KEEP.search(item["text"]):
                channel["posts"].append(item)
                kept += 1
        before = min(item["id"] for item in posts)
        channel["before"] = before
        channel["oldest"] = min(dates)
        channel["newest"] = max(dates)
        save(state)
        print(handle, "page", channel["pages"], "ids", before, "dates", min(dates), max(dates), "kept", kept, "total", len(channel["posts"]))
        if max(dates) < WINDOW_START:
            channel["done"] = True
            save(state)
            print(handle, "passed the start of the window")
            return
    channel["done"] = True
    save(state)


def main() -> None:
    state = load()
    for handle in ("MID_Russia", "MFARussia"):
        walk(handle, state)
    for handle, channel in state["channels"].items():
        weeks = {}
        for item in channel["posts"]:
            day = datetime.strptime(item["date"], "%Y-%m-%d").date()
            week = (day.toordinal() - day.weekday())
            from datetime import date
            label = date.fromordinal(week).isoformat()
            weeks[label] = weeks.get(label, 0) + 1
        print(handle, "posts", len(channel["posts"]), "weeks", len(weeks), "pages", channel["pages"])


if __name__ == "__main__":
    main()
