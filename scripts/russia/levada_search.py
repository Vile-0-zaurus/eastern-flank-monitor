#!/usr/bin/env python3
"""One Levada search for the 2021 friends-and-enemies survey. Crawl-delay 10."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pace import get, save

QUERY = "дружественные и недружественные"
URL = "https://www.levada.ru/?s=" + quote(QUERY)


def main() -> None:
    record = get(URL, pause=10, timeout=25)
    text = record.get("body", b"").decode("utf-8", errors="replace")
    title = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
    record["title"] = re.sub(r"\s+", " ", title.group(1)).strip()[:180] if title else ""
    record["query"] = QUERY
    links = re.findall(r'href="(https://www\.levada\.ru/20[^"]+)"[^>]*>(.*?)</a>', text, re.I | re.S)
    found = []
    for href, inner in links:
        plain = re.sub(r"<[^>]+>", "", inner)
        plain = re.sub(r"\s+", " ", plain).strip()
        if plain and "/20" in href:
            found.append({"url": href, "title": plain[:180]})
    record["hits"] = found[:40]
    save("levada-search.json", record)
    print(record["status"], record["error"], "hits", len(found))
    for item in found[:25]:
        print(item["url"][:90], item["title"][:90])


if __name__ == "__main__":
    main()
