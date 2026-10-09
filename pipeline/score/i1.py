"""I1: title-relevant flank stories divided by outlet stories. No model calls.

Reads gkg.sqlite read-only. Writes data/indicators/indicators.sqlite only.
"""
from __future__ import annotations

import html
import re
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

from pipeline.score.region_filter import junk_title, load_keywords, title_pattern

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data" / "backtest" / "gkg.sqlite"
OUT = ROOT / "data" / "indicators" / "indicators.sqlite"
KEYWORDS = ROOT / "config" / "region_keywords.yaml"
REGIONS = ROOT / "config" / "regions.yaml"
WINDOW = ("20210101", "20220224")
KALININGRAD = {"калининград", "kaliningrad"}
MIN_FREE_KB = int(1.5 * 1024 * 1024)


def story_key(domain: str, url: str, title: str) -> str:
    cleaned = (url or "").strip()
    if cleaned:
        return "url:" + cleaned
    norm = re.sub(r"\s+", " ", html.unescape(title or "")).strip().lower()
    return "text:" + (domain or "").lower() + "|" + norm


def flank_terms(path: Path) -> tuple[list[str], list[str]]:
    _fips, _names, stems, groups, _min_chars = load_keywords(path)
    kept = [stem for stem in stems if stem.lower() not in KALININGRAD]
    return kept, groups


def title_about_flank(title, stems, groups, domain, min_chars, pattern=None) -> bool:
    text = html.unescape(title or "")
    if junk_title(text, domain or "", min_chars):
        return False
    if pattern is None:
        pattern = title_pattern(
            [stem for stem in stems if stem.lower() not in KALININGRAD],
            groups,
        )
    return bool(pattern.search(text))


def daily_counts(rows, stems, groups, min_chars) -> dict:
    pattern = title_pattern(
        [stem for stem in stems if stem.lower() not in KALININGRAD],
        groups,
    )
    all_keys: dict[str, set[str]] = {}
    hit_keys: dict[str, set[str]] = {}
    for day, domain, url, title in rows:
        key = story_key(domain, url, title)
        all_keys.setdefault(day, set()).add(key)
        if title_about_flank(title, stems, groups, domain, min_chars, pattern):
            hit_keys.setdefault(day, set()).add(key)
    out = {}
    for day, keys in all_keys.items():
        numer = len(hit_keys.get(day, set()))
        denom = len(keys)
        out[day] = {
            "numerator": numer,
            "denominator": denom,
            "value": None if denom == 0 else numer / denom,
        }
    return out


def iso_day(stamp: str) -> str:
    return f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:8]}"


def week_monday(day: date) -> date:
    return day - timedelta(days=day.weekday())


def each_day(start: str, end: str):
    day = datetime.strptime(start, "%Y%m%d").date()
    last = datetime.strptime(end, "%Y%m%d").date()
    while day <= last:
        yield day
        day += timedelta(days=1)


def available_kb() -> int:
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1])
    raise SystemExit("MemAvailable missing")


def require_memory() -> None:
    free = available_kb()
    if free < MIN_FREE_KB:
        raise SystemExit(f"available memory {free} kB is under 1.5 GB; stopped")


def load_regions(path: Path = REGIONS) -> dict:
    regions: dict[str, dict] = {}
    current = None
    section = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        stripped = line.strip()
        if indent == 0 and stripped.endswith(":"):
            current = stripped[:-1]
            regions[current] = {"indicator": current, "keywords": None, "stems": [], "groups": []}
            section = None
            continue
        if current is None:
            continue
        if stripped.startswith("- ") and section in ("title_stems", "title_groups"):
            key = "stems" if section == "title_stems" else "groups"
            regions[current][key].append(stripped[2:].strip())
            continue
        key, _, val = stripped.partition(":")
        key, val = key.strip(), val.strip()
        if not val:
            section = key
            continue
        section = None
        if key == "keywords":
            regions[current]["keywords"] = val
        elif key == "indicator":
            regions[current]["indicator"] = val
    return regions


def matchers(path: Path = REGIONS) -> list[dict]:
    out = []
    for name, spec in load_regions(path).items():
        if spec["keywords"]:
            keyword_path = ROOT / spec["keywords"]
            stems, groups = flank_terms(keyword_path)
            _fips, _names, _stems, _groups, min_chars = load_keywords(keyword_path)
        else:
            stems, groups, min_chars = spec["stems"], spec["groups"], 15
        if not stems and not groups:
            raise SystemExit(f"{name} has no title rules")
        out.append(
            {
                "name": name,
                "indicator": spec["indicator"],
                "stems": stems,
                "groups": groups,
                "min_chars": min_chars,
                "pattern": title_pattern(stems, groups),
            }
        )
    return out


def read_stored(dst: Path, indicator: str = "I1") -> list[dict]:
    if not dst.exists():
        return []
    con = sqlite3.connect(f"file:{dst}?mode=ro", uri=True)
    con.execute("PRAGMA query_only=ON")
    try:
        rows = con.execute(
            "SELECT day, numerator, denominator, value FROM indicators WHERE indicator=? ORDER BY day",
            (indicator,),
        ).fetchall()
    except sqlite3.OperationalError:
        rows = []
    con.close()
    return [
        {"day": day, "numerator": numer, "denominator": denom, "value": value}
        for day, numer, denom, value in rows
    ]


def write_indicators(src: Path, dst: Path, start: str = WINDOW[0], end: str = WINDOW[1]) -> dict[str, list[dict]]:
    """Stream kept rows. One story key per day per region. Does not load the source table."""
    require_memory()
    if not src.exists():
        raise SystemExit(f"missing {src}")
    specs = matchers()
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        dst.unlink()
    out = sqlite3.connect(dst)
    out.execute("PRAGMA journal_mode=WAL")
    out.execute("PRAGMA cache_size=-8000")
    out.executescript(
        """
        CREATE TABLE stories (
          day TEXT NOT NULL,
          story_key TEXT NOT NULL,
          region TEXT NOT NULL,
          relevant INTEGER NOT NULL,
          PRIMARY KEY (day, story_key, region)
        );
        CREATE TABLE indicators (
          indicator TEXT NOT NULL,
          day TEXT NOT NULL,
          numerator INTEGER,
          denominator INTEGER,
          value REAL,
          PRIMARY KEY (indicator, day)
        );
        """
    )
    src_con = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
    src_con.execute("PRAGMA query_only=ON")
    src_con.execute("PRAGMA cache_size=-8000")
    batch = []

    def flush() -> None:
        if not batch:
            return
        out.executemany(
            """
            INSERT INTO stories (day, story_key, region, relevant) VALUES (?,?,?,?)
            ON CONFLICT(day, story_key, region) DO UPDATE SET
              relevant = MAX(relevant, excluded.relevant)
            """,
            batch,
        )
        out.commit()
        batch.clear()

    cur = src_con.execute(
        """
        SELECT day, domain, article_url, page_title
        FROM kept
        WHERE day>=? AND day<=?
        """,
        (start, end),
    )
    seen = 0
    for day, domain, url, title in cur:
        seen += 1
        key = story_key(domain or "", url or "", title or "")
        for spec in specs:
            relevant = 1 if title_about_flank(
                title, spec["stems"], spec["groups"], domain or "", spec["min_chars"], spec["pattern"]
            ) else 0
            batch.append((day, key, spec["name"], relevant))
        if len(batch) >= 5000:
            flush()
        if seen % 500000 == 0:
            print(f"streamed {seen}", flush=True)
            require_memory()
    flush()
    src_con.close()
    print(f"streamed {seen}", flush=True)
    by_region: dict[str, dict[str, tuple]] = {spec["name"]: {} for spec in specs}
    for region, day, numer, denom in out.execute(
        "SELECT region, day, SUM(relevant), COUNT(*) FROM stories GROUP BY region, day"
    ):
        by_region[region][day] = (numer, denom)
    stored: dict[str, list[dict]] = {}
    for spec in specs:
        rows = []
        for day in each_day(start, end):
            stamp = day.strftime("%Y%m%d")
            numer, denom = by_region[spec["name"]].get(stamp, (None, None))
            value = None if not denom else numer / denom
            out.execute(
                "INSERT INTO indicators (indicator, day, numerator, denominator, value) VALUES (?,?,?,?,?)",
                (spec["indicator"], iso_day(stamp), numer, denom, value),
            )
            rows.append(
                {"day": iso_day(stamp), "numerator": numer, "denominator": denom, "value": value}
            )
        stored[spec["name"]] = rows
    out.execute("DROP TABLE stories")
    out.commit()
    require_memory()
    out.execute("VACUUM")
    out.close()
    return stored


def weekly_summary(rows: list[dict]) -> list[dict]:
    buckets: dict[date, dict] = {}
    for row in rows:
        if row["denominator"] is None:
            continue
        day = date.fromisoformat(row["day"])
        monday = week_monday(day)
        bucket = buckets.setdefault(
            monday, {"week": monday.isoformat(), "days": 0, "numerator": 0, "denominator": 0}
        )
        bucket["days"] += 1
        bucket["numerator"] += row["numerator"] or 0
        bucket["denominator"] += row["denominator"] or 0
    out = []
    for monday in sorted(buckets):
        bucket = buckets[monday]
        denom = bucket["denominator"]
        bucket["value"] = None if denom == 0 else bucket["numerator"] / denom
        bucket["partial"] = bucket["days"] != 7
        out.append(bucket)
    return out


def format_weekly(weeks: list[dict]) -> str:
    lines = ["week        days  relevant  outlet_stories  share    note"]
    for row in weeks:
        share = "no data" if row["value"] is None else f"{row['value']:.4f}"
        note = "partial" if row["partial"] else ""
        lines.append(
            f"{row['week']}  {row['days']:>4}  {row['numerator']:>8}  {row['denominator']:>14}  {share:>7}  {note}"
        )
    return "\n".join(lines)


def main() -> None:
    require_memory()
    old = read_stored(OUT, "I1")
    if old:
        print("## old_eastern_flank")
        print(format_weekly(weekly_summary(old)))
    stored = write_indicators(SRC, OUT)
    for name, rows in stored.items():
        print(f"## {name}")
        print(format_weekly(weekly_summary(rows)))
        numer = sum(row["numerator"] or 0 for row in rows if row["denominator"])
        denom = sum(row["denominator"] or 0 for row in rows if row["denominator"])
        share = "no data" if not denom else f"{numer / denom:.4f}"
        print(f"stored {len(rows)} daily rows  relevant {numer}  outlet {denom}  share {share}")


if __name__ == "__main__":
    main()
