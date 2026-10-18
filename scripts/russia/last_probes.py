#!/usr/bin/env python3
"""Last allowed pages: poll indexes, one RSS, one NATO archive page, Telegram date brackets."""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pace import get, save

URLS = (
    ("https://www.levada.ru/2021/01/", 10),
    ("https://www.levada.ru/2021/06/", 10),
    ("https://www.levada.ru/2022/01/", 10),
    ("https://www.levada.ru/2022/02/", 10),
    ("https://bd.wciom.ru/baza_rezultatov_oprosa_s_1992_goda/", 1),
    ("https://www.mfa.gov.lv/en/rss", 1),
    ("https://www.nato.int/en/about-us/official-texts-and-resources/NATO-archives", 1),
    ("https://t.me/s/MID_Russia?before=17500", 1),
    ("https://t.me/s/MFARussia?before=10500", 1),
)


def main() -> None:
    for url, pause in URLS:
        record = get(url, pause=pause, timeout=20)
        text = record.get("body", b"").decode("utf-8", errors="replace")
        title = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
        record["title"] = re.sub(r"\s+", " ", title.group(1)).strip()[:160] if title else ""
        record["dates"] = re.findall(r'datetime="([^"]+)"', text)[:2] + re.findall(r'datetime="([^"]+)"', text)[-2:]
        record["head"] = re.sub(r"\s+", " ", text)[:140]
        name = "last-" + re.sub(r"[^a-z0-9]+", "-", url.lower()).strip("-")[:90] + ".json"
        save(name, record)
        print(record["status"], record["error"][:50] if record["error"] else "", record["bytes"], record["title"][:60], record["dates"][:2])


if __name__ == "__main__":
    main()
