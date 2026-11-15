#!/usr/bin/env python3
"""Compare Now chip counts with the dossier headlines. No API calls."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEW = ROOT / "frontend" / "now-view.json"
HEAD = ROOT / "frontend" / "now-headlines.json"
COUNTRIES = ("FI", "EE", "LV", "LT", "PL")


def main() -> int:
    view = json.loads(VIEW.read_text(encoding="utf-8"))
    headlines = json.loads(HEAD.read_text(encoding="utf-8"))
    problems = []
    for week in view["weeks"]:
        for code in COUNTRIES:
            chip = view["attention"][week][code]
            items = ((headlines.get("weeks") or {}).get(week) or {}).get(code) or []
            if chip > 0 and not items:
                problems.append(f"{week} {code} chip {chip} but dossier is empty")
            if len(items) > min(5, chip):
                problems.append(f"{week} {code} dossier {len(items)} exceeds chip {chip}")
            if chip == 0 and items:
                problems.append(f"{week} {code} chip 0 but dossier has {len(items)}")
            for item in items:
                if not item.get("english"):
                    problems.append(f"{week} {code} missing English")
                if item.get("title") and "Литвиненко" in item["title"]:
                    problems.append(f"{week} {code} false Lithuania match")
    if problems:
        print("FAIL")
        for row in problems:
            print("-", row)
        return 1
    print(f"PASS weeks={len(view['weeks'])} countries={len(COUNTRIES)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
