#!/usr/bin/env python3
"""One-page probe of verified MFA Telegram previews and the spokesperson page."""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pace import get, save

URLS = (
    "https://mid.ru/ru/press_service/spokesman/",
    "https://t.me/s/MID_Russia",
    "https://t.me/s/MFARussia",
)


def main() -> None:
    for url in URLS:
        record = get(url, pause=1.0, timeout=20)
        body = record.get("body", b"")
        text = body.decode("utf-8", errors="replace")
        record["handles"] = sorted(set(re.findall(r"t\.me/(?:s/)?([A-Za-z0-9_]{3,})", text)))
        record["dates"] = re.findall(r'datetime="([^"]+)"', text)[:8]
        record["message_ids"] = re.findall(r"MID_Russia/(\d+)|MFARussia/(\d+)", text)[:5]
        ids = [item for pair in re.findall(r"/(?:MID_Russia|MFARussia)/(\d+)", text) for item in [pair]]
        record["ids"] = ids[:12]
        title = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
        record["title"] = re.sub(r"\s+", " ", title.group(1)).strip()[:160] if title else ""
        record["has_before"] = "before=" in text or "?before" in text
        name = "tg2-" + re.sub(r"[^a-z0-9]+", "-", url.lower()).strip("-")[:80] + ".json"
        save(name, record)
        print(record["status"], record["error"] or record["final_url"])
        print(" title", record["title"])
        print(" handles", record["handles"])
        print(" dates", record["dates"][:4], "ids", record["ids"][:6], "before", record["has_before"])


if __name__ == "__main__":
    main()
