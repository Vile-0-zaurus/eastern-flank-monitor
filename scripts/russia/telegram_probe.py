#!/usr/bin/env python3
"""Probe official sites for a named Telegram handle. Research user-agent only."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pace import get, save

PAGES = (
    "https://mil.ru/robots.txt",
    "https://eng.mil.ru/robots.txt",
    "https://mid.ru/robots.txt",
    "https://kremlin.ru/robots.txt",
    "https://t.me/robots.txt",
    "https://mil.ru/",
    "https://eng.mil.ru/",
    "https://mid.ru/",
    "https://www.mid.ru/en/",
    "https://kremlin.ru/",
    "https://en.kremlin.ru/",
)


def main() -> None:
    found = []
    for url in PAGES:
        record = get(url, pause=1.0, timeout=20)
        body = record.get("body", b"")
        text = body.decode("utf-8", errors="replace")
        handles = sorted(set(re.findall(r"t\.me/(?:s/)?([A-Za-z0-9_]{3,})", text)))
        record["handles"] = handles
        record["title"] = ""
        match = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
        if match:
            record["title"] = re.sub(r"\s+", " ", match.group(1)).strip()[:180]
        record["snippet"] = re.sub(r"\s+", " ", text)[:240]
        name = "telegram-" + re.sub(r"[^a-z0-9]+", "-", url.lower()).strip("-")[:80] + ".json"
        save(name, record)
        print(record["status"], record["error"] or record["final_url"], "handles", handles, "title", record["title"][:80])
        found.extend(handles)
    print("ALL", sorted(set(found)))


if __name__ == "__main__":
    main()
