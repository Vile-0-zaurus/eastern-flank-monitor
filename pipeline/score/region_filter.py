#!/usr/bin/env python3
"""Re-runnable region filter. Reads size-test.sqlite only. Does not touch gkg.sqlite.

Writes data/validation/region_matches.sqlite. Safe to run again; it rebuilds that file.
"""
from __future__ import annotations

import html
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data" / "backtest" / "size-test.sqlite"
OUT = ROOT / "data" / "validation" / "region_matches.sqlite"
KEYWORDS = ROOT / "config" / "region_keywords.yaml"

# FIPS country-code slot only. EN is Estonia in GDELT, not a substring match.
# Codes are loaded from config/region_keywords.yaml.


def load_keywords(path: Path) -> tuple[set[str], list[str], list[str], list[str], int]:
    fips: set[str] = set()
    loc_names: list[str] = []
    stems: list[str] = []
    groups: list[str] = []
    min_chars = 15
    section = ""
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        key = line.split(":")[0].strip()
        if not raw.startswith(" ") and line.endswith(":") and not line.strip().startswith("-"):
            section = key
            continue
        if section == "junk" and key == "min_title_chars":
            min_chars = int(line.split(":", 1)[1].strip())
            continue
        if line.strip().startswith("- "):
            item = line.strip()[2:].strip()
            if section == "location_fips":
                fips.add(item)
            elif section == "location_names":
                loc_names.append(item)
            elif section == "title_stems":
                stems.append(item)
            elif section == "title_groups":
                groups.append(item)
    return fips, loc_names, stems, groups, min_chars


def title_pattern(stems: list[str], groups: list[str]) -> re.Pattern[str]:
    parts = [re.escape(s) for s in stems]
    parts.extend(groups)
    body = "|".join(parts)
    return re.compile(rf"(?i)(?<!\w)(?:{body})")


def location_hit(locations: str, fips: set[str], loc_names: list[str]) -> bool:
    if not locations:
        return False
    for name in loc_names:
        if re.search(rf"(?i)(?<!\w){re.escape(name)}", locations):
            return True
    for rec in locations.split(";"):
        parts = rec.split("#")
        if len(parts) >= 3 and parts[2] in fips:
            return True
    return False


def junk_title(title: str, domain: str, min_chars: int) -> bool:
    t = re.sub(r"\s+", " ", (title or "")).strip()
    if len(t) < min_chars:
        return True
    low = t.lower()
    dom = domain.lower()
    outlet_names = {dom, dom.split(".")[0], "тасс", "риа новости", "риа", "rt", "sputnik"}
    return low in outlet_names


def main() -> None:
    if not SRC.exists():
        raise SystemExit(f"missing {SRC}")
    fips, loc_names, stems, groups, min_chars = load_keywords(KEYWORDS)
    pat = title_pattern(stems, groups)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if OUT.exists():
        OUT.unlink()
    src = sqlite3.connect(f"file:{SRC}?mode=ro", uri=True)
    dst = sqlite3.connect(OUT)
    dst.execute(
        """
        CREATE TABLE matches (
          id INTEGER PRIMARY KEY,
          source_id INTEGER,
          domain TEXT,
          seendate TEXT,
          article_url TEXT,
          page_title TEXT,
          locations TEXT,
          matched_by TEXT
        )
        """
    )
    n = 0
    for row in src.execute(
        "SELECT id, domain, seendate, article_url, page_title, locations FROM kept"
    ):
        title = html.unescape(row[4] or "")
        if junk_title(title, row[1], min_chars):
            continue
        loc = location_hit(row[5] or "", fips, loc_names)
        tit = bool(pat.search(title))
        if not loc and not tit:
            continue
        how = "both" if loc and tit else "location" if loc else "title"
        dst.execute(
            "INSERT INTO matches (source_id, domain, seendate, article_url, page_title, locations, matched_by) VALUES (?,?,?,?,?,?,?)",
            (row[0], row[1], row[2], row[3], title, row[5], how),
        )
        n += 1
    dst.commit()
    print(f"matched {n}")
    print("by", dict(dst.execute("SELECT matched_by, COUNT(*) FROM matches GROUP BY matched_by")))
    print("domains", dst.execute("SELECT domain, COUNT(*) FROM matches GROUP BY domain ORDER BY 2 DESC").fetchall())
    src.close()
    dst.close()


if __name__ == "__main__":
    main()
