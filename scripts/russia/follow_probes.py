#!/usr/bin/env python3
"""Follow-up pages that robots allow. Does not touch a disallowed path."""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pace import get, save

# um.fi crawl-delay is 20. levada crawl-delay is 10. Others use 1.
URLS = (
    ("https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s=RBRTE&f=M", 1),
    ("https://www.levada.ru/tag/ukraina/", 10),
    ("https://bd.wciom.ru/robots.txt", 1),
    ("https://fom.ru/Politika", 1),
    ("https://um.fi/", 20),
    ("https://www.mfa.gov.lv/en", 1),
    ("https://www.gov.pl/web/national-defence", 1),
    ("https://www.gov.pl/web/diplomacy", 1),
    ("https://www.nato.int/cps/en/natohq/press_releases.htm", 1),
)


def main() -> None:
    for url, pause in URLS:
        record = get(url, pause=pause, timeout=20)
        text = record.get("body", b"").decode("utf-8", errors="replace")
        title = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
        record["title"] = re.sub(r"\s+", " ", title.group(1)).strip()[:160] if title else ""
        record["rejected"] = bool(re.search(r"Request Rejected|Just a moment|Access Denied|Bloķēts", text, re.I))
        record["has_2021"] = "2021" in text
        record["has_2022"] = "2022" in text
        record["head"] = re.sub(r"\s+", " ", text)[:160]
        name = "follow-" + re.sub(r"[^a-z0-9]+", "-", url.lower()).strip("-")[:90] + ".json"
        save(name, record)
        print(record["status"], record["error"][:60] if record["error"] else "", record["bytes"], record["rejected"], record["has_2021"], record["title"][:70])


if __name__ == "__main__":
    main()
