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
WINDOW = ("20210101", "20220224")
KALININGRAD = {"калининград", "kaliningrad"}


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


def write_indicators(src: Path, dst: Path, start: str = WINDOW[0], end: str = WINDOW[1]) -> list[dict]:
    if not src.exists():
        raise SystemExit(f"missing {src}")
    stems, groups = flank_terms(KEYWORDS)
    _fips, _names, _stems, _groups, min_chars = load_keywords(KEYWORDS)
    pattern = title_pattern(stems, groups)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        dst.unlink()
    out = sqlite3.connect(dst)
    out.execute("PRAGMA journal_mode=WAL")
    out.executescript(
        """
        CREATE TABLE stories (
          day TEXT NOT NULL,
          story_key TEXT NOT NULL,
          relevant INTEGER NOT NULL,
          PRIMARY KEY (day, story_key)
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
    batch = []

    def flush() -> None:
        if not batch:
            return
        out.executemany(
            """
            INSERT INTO stories (day, story_key, relevant) VALUES (?,?,?)
            ON CONFLICT(day, story_key) DO UPDATE SET
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
    for day, domain, url, title in cur:
        key = story_key(domain or "", url or "", title or "")
        relevant = 1 if title_about_flank(title, stems, groups, domain or "", min_chars, pattern) else 0
        batch.append((day, key, relevant))
        if len(batch) >= 5000:
            flush()
    flush()
    src_con.close()
    by_day = {
        day: (numer, denom)
        for day, numer, denom in out.execute(
            "SELECT day, SUM(relevant), COUNT(*) FROM stories GROUP BY day"
        )
    }
    rows = []
    for day in each_day(start, end):
        stamp = day.strftime("%Y%m%d")
        numer, denom = by_day.get(stamp, (None, None))
        value = None if not denom else numer / denom
        out.execute(
            "INSERT INTO indicators (indicator, day, numerator, denominator, value) VALUES ('I1',?,?,?,?)",
            (iso_day(stamp), numer, denom, value),
        )
        rows.append(
            {
                "day": iso_day(stamp),
                "numerator": numer,
                "denominator": denom,
                "value": value,
            }
        )
    out.execute("DROP TABLE stories")
    out.commit()
    out.close()
    return rows


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
    rows = write_indicators(SRC, OUT)
    weeks = weekly_summary(rows)
    text = format_weekly(weeks)
    print(text)
    print(f"stored {len(rows)} daily rows in {OUT}")


if __name__ == "__main__":
    main()
