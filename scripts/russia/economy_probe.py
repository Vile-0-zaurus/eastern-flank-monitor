#!/usr/bin/env python3
"""Probe free official or international economy series. No exchange. No API key."""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pace import get, save

URLS = (
    "https://www.cbr.ru/robots.txt",
    "https://api.worldbank.org/robots.txt",
    "https://fred.stlouisfed.org/robots.txt",
    "https://www.cbr.ru/scripts/XML_dynamic.asp?date_req1=01/01/2021&date_req2=28/02/2022&VAL_NM_RQ=R01235",
    "https://www.cbr.ru/hd_base/KeyRate/?UniDbQuery.Posted=True&UniDbQuery.From=01.01.2021&UniDbQuery.To=28.02.2022",
    "https://api.worldbank.org/v2/country/RUS/indicator/FP.CPI.TOTL.ZG?format=json&date=2021:2022",
    "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DCOILBRENTEU",
)


def main() -> None:
    for url in URLS:
        record = get(url, pause=1.0, timeout=25)
        text = record.get("body", b"").decode("utf-8", errors="replace")
        title = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
        record["title"] = re.sub(r"\s+", " ", title.group(1)).strip()[:160] if title else ""
        record["head"] = re.sub(r"\s+", " ", text)[:220]
        record["looks_rejected"] = bool(re.search(r"Request Rejected|Please, wait|Just a moment|cf-browser-verification", text, re.I))
        name = "econ-" + re.sub(r"[^a-z0-9]+", "-", url.lower()).strip("-")[:90] + ".json"
        save(name, record)
        print(record["status"], record["error"] or "", record["bytes"], record["title"][:60] or record["head"][:80])


if __name__ == "__main__":
    main()
