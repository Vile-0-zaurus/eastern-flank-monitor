#!/usr/bin/env python3
"""Parse one in-force Baltic NAVTEX page for Russian coastal warnings only.

Source fetched separately: Swedish Maritime Administration NAVTEX list
(Baltic Sea sub-area coordinator). Does not collect Finnish, Baltic,
Polish, or NATO force notices.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
SRC = DATA / "swe-navtex.html"
OUT = DATA / "navwarn-report.json"

RU_ORIGINS = ("PETERSBURG NAV WARN", "KALININGRAD NAV WARN")


def textify(html: str) -> str:
    html = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    html = re.sub(r"<style[\s\S]*?</style>", " ", html, flags=re.I)
    html = re.sub(r"<br\s*/?>", "\n", html, flags=re.I)
    html = re.sub(r"</(p|div|h\d|li|tr)>", "\n", html, flags=re.I)
    html = re.sub(r"<[^>]+>", " ", html)
    html = html.replace("&#xA;", "\n").replace("&#xD;", "\n").replace("&amp;", "&")
    html = re.sub(r"[ \t]+", " ", html)
    html = re.sub(r"\n\s*\n+", "\n", html)
    return html


def parse_entries(text: str) -> list[dict]:
    # Blocks look like: 231414 UTC SEP \n PETERSBURG NAV WARN \n 203/26 \n body...
    pattern = re.compile(
        r"(\d{6} UTC [A-Z]{3})\s+(PETERSBURG NAV WARN|KALININGRAD NAV WARN)\s+(\d+/\d+)\s+(.*?)(?=\d{6} UTC [A-Z]{3}\s+(?:PETERSBURG|KALININGRAD|ESTONIAN|FINNISH|POLISH|LATVIAN|SWEDISH|GERMAN|DANISH|BALTIC)|\Z)",
        re.S,
    )
    seen = set()
    rows = []
    for m in pattern.finditer(text):
        issued, origin, number, body = m.group(1), m.group(2), m.group(3), m.group(4)
        key = (origin, number)
        if key in seen:
            continue
        seen.add(key)
        body = re.sub(r"\s+", " ", body).strip()
        body = body[:500]
        coords = re.findall(r"\d{2}-\d{2}(?:\.\d+)?[NS]\s+\d{3}-\d{2}(?:\.\d+)?[EW]", body)
        rows.append({
            "origin": origin,
            "number": number,
            "issued": issued,
            "coords": coords[:6],
            "text": body,
        })
    return rows


def main() -> None:
    html = SRC.read_text(errors="replace")
    text = textify(html)
    rows = parse_entries(text)
    # also count update stamp if present
    updated = None
    m = re.search(r"20\d{2}-\d{2}-\d{2} \d{2}:\d{2}", text)
    if m:
        updated = m.group(0)
    report = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "official_ru_host": {
            "url": "https://mil.ru/navigation.htm",
            "result": "connection timeout from this host (FI). old.mil.ru also timed out.",
        },
        "sample_source": {
            "url": "https://navvarn.sjofartsverket.se/Navigationsvarningar/Navtex",
            "role": "Baltic Sea sub-area NAVTEX coordinator (Sweden). Republishes coastal warnings, including Russian Petersburg and Kaliningrad warnings, as HTML.",
            "robots": "https://www.sjofartsverket.se/robots.txt allows /",
            "page_updated_stamp": updated,
            "format": "HTML text, script-parseable",
            "history": "In-force list only. Not a 2021-2022 archive. UKHO reprints NAVAREA I texts in Admiralty Notices to Mariners weeks 1, 13, 26 and 39. Russian weekly Notices to Mariners are cited as living on mil.ru, which was unreachable.",
        },
        "n_russian_origin": len(rows),
        "entries": rows,
        "sample": rows[:3],
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"n": len(rows), "updated": updated, "sample": [
        {k: e[k] for k in ("origin", "number", "issued")} for e in rows[:3]
    ]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
