#!/usr/bin/env python3
"""Open the one 2021 friends-and-enemies page named by the search. Crawl-delay 10."""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pace import get, save

URL = "https://www.levada.ru/2021/06/15/glavnye-druzhestvennye-i-nedruzhestvennye-strany/"


def main() -> None:
    time.sleep(10)
    record = get(URL, pause=1, timeout=25)
    text = record.get("body", b"").decode("utf-8", errors="replace")
    title = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
    record["title"] = re.sub(r"\s+", " ", title.group(1)).strip()[:180] if title else ""
    save("levada-friends-2021.json", record)
    print(record["status"], record["bytes"], record["title"][:80])


if __name__ == "__main__":
    main()
