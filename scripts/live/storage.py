"""What a live day may store. No network."""
from __future__ import annotations

import gzip
from pathlib import Path


def load_outlets(path: Path) -> set[str]:
    found = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.split("#", 1)[0].strip()
        if text.startswith("- "):
            found.add(text[2:].strip())
    return found


def row_fate(domain: str, russian: set[str], western: set[str], region: bool) -> str:
    """Russian outlets are kept in full. Other outlets are kept only on a region hit."""
    if domain in russian:
        return "keep_all"
    if domain in western and region:
        return "keep_region"
    return "drop"


def tally(rows: list[dict], russian: set[str], western: set[str]) -> dict:
    result = {
        "russian_rows": 0,
        "western_region_rows": 0,
        "dropped": 0,
        "daily_totals": {},
    }
    for row in rows:
        domain = row["domain"]
        fate = row_fate(domain, russian, western, bool(row.get("region")))
        if fate == "keep_all":
            result["russian_rows"] += 1
            result["daily_totals"][domain] = result["daily_totals"].get(domain, 0) + 1
        elif fate == "keep_region":
            result["western_region_rows"] += 1
        else:
            result["dropped"] += 1
    return result


def tass_supplement(day_dir: Path, live_on: bool) -> dict:
    """Read saved collector files. Do not fetch. Off means the files are not included."""
    if not live_on:
        return {"included": False, "reason": "live_monitoring is off", "files": {}}
    files = {}
    for name, domain in (("tass-ru.xml.gz", "tass.ru"), ("tass-en.xml.gz", "tass.com")):
        path = day_dir / name
        if not path.is_file() or path.stat().st_size <= 0:
            files[domain] = {"present": False, "items": 0}
            continue
        text = gzip.open(path, "rt", encoding="utf-8", errors="replace").read()
        files[domain] = {"present": True, "items": text.count("<item")}
    return {"included": True, "reason": "", "files": files}
