#!/usr/bin/env python3
"""Check whether verified Telegram previews still show 2021 posts. A few pages only."""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pace import get, save

URLS = (
    "https://t.me/s/MID_Russia?before=500",
    "https://t.me/s/MID_Russia?before=8000",
    "https://t.me/s/MID_Russia?before=40000",
    "https://t.me/s/MFARussia?before=400",
    "https://t.me/s/MFARussia?before=4000",
    "https://t.me/s/MFARussia?before=15000",
)


def main() -> None:
    for url in URLS:
        record = get(url, pause=1.0, timeout=20)
        text = record.get("body", b"").decode("utf-8", errors="replace")
        dates = re.findall(r'datetime="([^"]+)"', text)
        ids = re.findall(r"/(?:MID_Russia|MFARussia)/(\d+)", text)
        record["dates"] = dates[:3] + dates[-3:]
        record["id_min"] = min(ids, default="")
        record["id_max"] = max(ids, default="")
        record["posts"] = len(dates)
        name = "tgold-" + re.sub(r"[^a-z0-9]+", "-", url.lower()).strip("-")[:90] + ".json"
        save(name, record)
        print(record["status"], url, "posts", len(dates), "ids", record["id_min"], record["id_max"], "dates", dates[:1], dates[-1:])


if __name__ == "__main__":
    main()
