#!/usr/bin/env python3
"""Fail if a UI string is missing from a language file. No API calls."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCALES = ("en", "fi", "et", "lv", "lt", "pl")
ALLOW_SAME = {
    "sub_line",
    "marker_ryanair",
    "marker_zapad",
    "marker_allied",
    "country_LV",
    "country_EE",
    "country_KG",
    "region",
    "fact_ru_rostec",
    "fact_ru_almaz",
    "fact_ru_uac",
}
DENY = (
    '"Nothing this week."',
    '"Bottom line"',
    '"What happened"',
    '"What officials said"',
    '"What Russian media says"',
    '"Not an official warning service."',
    '"Source"',
)


def main() -> int:
    packs = {
        code: json.loads((ROOT / "frontend/i18n" / f"{code}.json").read_text(encoding="utf-8"))
        for code in LOCALES
    }
    english = packs["en"]
    problems = []
    for code, data in packs.items():
        if set(data) != set(english):
            problems.append(f"{code} keys differ")
        for key, value in data.items():
            if not str(value).strip():
                problems.append(f"{code} {key} is empty")
        if code == "en":
            continue
        for key, value in data.items():
            if key in ALLOW_SAME:
                continue
            if value == english[key]:
                problems.append(f"{code} {key} is still English")
    html = (ROOT / "frontend/index.html").read_text(encoding="utf-8")
    js = (ROOT / "frontend/app.js").read_text(encoding="utf-8")
    used = set(re.findall(r'data-i18n="([^"]+)"', html))
    used.update(re.findall(r'\bt\("([^"]+)"\)', js))
    used.update(re.findall(r'\bfill\("([^"]+)"', js))
    for key in sorted(used):
        if key not in english:
            problems.append("used key missing from en.json: " + key)
    for phrase in DENY:
        if phrase in js:
            problems.append("hard-coded UI string in app.js: " + phrase)
    if problems:
        print("FAIL")
        for row in problems:
            print("-", row)
        return 1
    print(f"PASS languages={len(LOCALES)} keys={len(english)} used={len(used)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
