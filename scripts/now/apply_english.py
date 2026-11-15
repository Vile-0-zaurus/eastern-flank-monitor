#!/usr/bin/env python3
"""Write hand-made English lines into the Now headlines file. No API calls."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "frontend" / "now-headlines.json"
PARTS = [
    ROOT / "scripts" / "now" / "english_part1.json",
    ROOT / "scripts" / "now" / "english_part2.json",
    ROOT / "scripts" / "now" / "english_part3.json",
    ROOT / "scripts" / "now" / "english_part4.json",
]


def main() -> None:
    lines = {}
    for path in PARTS:
        lines.update(json.loads(path.read_text(encoding="utf-8")))
    data = json.loads(OUT.read_text(encoding="utf-8"))
    missing = []
    for week, countries in data["weeks"].items():
        for code, items in countries.items():
            for item in items:
                english = lines.get(item["title"])
                if not english:
                    missing.append(f"headline {week} {code} {item['title']}")
                    continue
                item["english"] = english
    for week, countries in data.get("officials", {}).items():
        for code, items in countries.items():
            for item in items:
                english = lines.get(item["title"])
                if not english:
                    missing.append(f"official {week} {code} {item['title']}")
                    continue
                item["english"] = english
    if missing:
        print("MISSING", len(missing))
        for row in missing:
            print(row)
        raise SystemExit(1)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("english_ok", len(lines))


if __name__ == "__main__":
    main()
