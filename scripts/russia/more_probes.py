#!/usr/bin/env python3
"""Probe oil, monthly inflation, non-exchange stock pages, polls, and regional pages."""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pace import get, save

URLS = (
    "https://www.eia.gov/robots.txt",
    "https://rosstat.gov.ru/robots.txt",
    "https://www.levada.ru/robots.txt",
    "https://wciom.ru/robots.txt",
    "https://fom.ru/robots.txt",
    "https://www.eia.gov/dnav/pet/hist/rbrteM.htm",
    "https://rosstat.gov.ru/",
    "https://www.cbr.ru/statistics/ddkp/infl/",
    "https://www.levada.ru/",
    "https://wciom.ru/",
    "https://fom.ru/",
    "https://kamaz.ru/robots.txt",
    "https://www.uacrussia.ru/robots.txt",
    "https://defmin.fi/robots.txt",
    "https://um.fi/robots.txt",
    "https://www.kaitseministeerium.ee/robots.txt",
    "https://vm.ee/robots.txt",
    "https://www.mod.gov.lv/robots.txt",
    "https://www.mfa.gov.lv/robots.txt",
    "https://kam.lt/robots.txt",
    "https://urm.lt/robots.txt",
    "https://www.gov.pl/robots.txt",
    "https://www.nato.int/robots.txt",
)


def main() -> None:
    for url in URLS:
        record = get(url, pause=1.0, timeout=18)
        text = record.get("body", b"").decode("utf-8", errors="replace")
        title = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
        record["title"] = re.sub(r"\s+", " ", title.group(1)).strip()[:160] if title else ""
        record["head"] = re.sub(r"\s+", " ", text)[:180]
        record["rejected"] = bool(re.search(r"Request Rejected|Please, wait|Just a moment|cf-browser-verification|Access Denied", text, re.I))
        name = "more-" + re.sub(r"[^a-z0-9]+", "-", url.lower()).strip("-")[:90] + ".json"
        save(name, record)
        print(record["status"] or record["error"], record["bytes"], record["title"][:70] or record["head"][:70])


if __name__ == "__main__":
    main()
