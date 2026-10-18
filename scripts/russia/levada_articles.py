#!/usr/bin/env python3
"""Fetch two Levada articles named on the opened month pages. Crawl-delay 10."""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pace import get, save

URLS = (
    "https://www.levada.ru/2022/02/24/ukraina-i-donbass-2/",
    "https://www.levada.ru/2022/02/09/levada-tsentr-chem-molozhe-i-obrazovannee-rossiyane-tem-luchshe-oni-dumayut-ob-estonii/",
)


def main() -> None:
    for url in URLS:
        record = get(url, pause=10, timeout=20)
        text = record.get("body", b"").decode("utf-8", errors="replace")
        title = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
        record["title"] = re.sub(r"\s+", " ", title.group(1)).strip()[:180] if title else ""
        name = "poll-" + re.sub(r"[^a-z0-9]+", "-", url.lower()).strip("-")[:90] + ".json"
        save(name, record)
        print(record["status"], record["bytes"], record["title"][:80])


if __name__ == "__main__":
    main()
