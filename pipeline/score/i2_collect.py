"""Stream relevant titles for I2. Does not load gkg.sqlite. No model calls."""
from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

from pipeline.score.i1 import (
    OUT,
    SRC,
    WINDOW,
    format_weekly,
    iso_day,
    matchers,
    read_stored,
    require_memory,
    story_key,
    title_about_flank,
    week_monday,
    weekly_summary,
)
from pipeline.score.i2_sample import collapse_stories, draw_sample, norm_title

ROOT = Path(__file__).resolve().parents[2]
HITS = ROOT / "data" / "indicators" / "i2-stories.sqlite"
SAMPLE = ROOT / "data" / "indicators" / "i2-sample.sqlite"
CONFIG = ROOT / "config" / "i2.yaml"


def load_i2_config(path: Path = CONFIG) -> dict:
    cfg = {"seed": 20261009, "per_week": 200, "batch_size": 50, "estimate_cap_usd": 8.0, "hard_stop_usd": 10.0}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, _, val = line.partition(":")
        key, val = key.strip(), val.strip()
        if key in ("seed", "per_week", "batch_size"):
            cfg[key] = int(val)
        elif key in ("estimate_cap_usd", "hard_stop_usd"):
            cfg[key] = float(val)
        else:
            cfg[key] = val
    return cfg


def each_day(start: str, end: str):
    day = datetime.strptime(start, "%Y%m%d").date()
    last = datetime.strptime(end, "%Y%m%d").date()
    while day <= last:
        yield day
        day += timedelta(days=1)


def collect(start: str = WINDOW[0], end: str = WINDOW[1]) -> None:
    require_memory()
    if not SRC.exists():
        raise SystemExit(f"missing {SRC}")
    old = read_stored(OUT, "I1_ukraine_test")
    specs = matchers()
    HITS.parent.mkdir(parents=True, exist_ok=True)
    if HITS.exists():
        HITS.unlink()
    hits = sqlite3.connect(HITS)
    hits.execute("PRAGMA journal_mode=WAL")
    hits.execute("PRAGMA cache_size=-8000")
    hits.execute(
        """
        CREATE TABLE hits (
          region TEXT NOT NULL,
          day TEXT NOT NULL,
          story_key TEXT NOT NULL,
          url TEXT NOT NULL,
          title TEXT NOT NULL,
          norm_title TEXT NOT NULL
        )
        """
    )
    src = sqlite3.connect(f"file:{SRC}?mode=ro", uri=True)
    src.execute("PRAGMA query_only=ON")
    src.execute("PRAGMA cache_size=-8000")
    batch = []

    def flush() -> None:
        if not batch:
            return
        hits.executemany(
            "INSERT INTO hits (region, day, story_key, url, title, norm_title) VALUES (?,?,?,?,?,?)",
            batch,
        )
        hits.commit()
        batch.clear()

    seen = 0
    cur = src.execute(
        "SELECT day, domain, article_url, page_title FROM kept WHERE day>=? AND day<=?",
        (start, end),
    )
    for day, domain, url, title in cur:
        seen += 1
        key = story_key(domain or "", url or "", title or "")
        for spec in specs:
            if not title_about_flank(
                title, spec["stems"], spec["groups"], domain or "", spec["min_chars"], spec["pattern"]
            ):
                continue
            batch.append((spec["name"], day, key, (url or "").strip(), title or "", norm_title(title or "")))
        if len(batch) >= 5000:
            flush()
        if seen % 500000 == 0:
            print(f"streamed {seen}", flush=True)
            require_memory()
    flush()
    src.close()
    print(f"streamed {seen}", flush=True)
    hits.execute("CREATE INDEX hits_region_day ON hits(region, day)")
    hits.commit()
    hits.close()
    _replace_ukraine(old)
    _sample()


def _replace_ukraine(old: list[dict]) -> None:
    ind = sqlite3.connect(OUT)
    denom = {
        day: den
        for day, den in ind.execute(
            "SELECT day, denominator FROM indicators WHERE indicator='I1'"
        )
    }
    hits = sqlite3.connect(f"file:{HITS}?mode=ro", uri=True)
    hits.execute("PRAGMA query_only=ON")
    numer = {
        day: n
        for day, n in hits.execute(
            "SELECT day, COUNT(DISTINCT story_key) FROM hits WHERE region='ukraine_test' GROUP BY day"
        )
    }
    hits.close()
    ind.execute("DELETE FROM indicators WHERE indicator='I1_ukraine_test'")
    rows = []
    for day in each_day(WINDOW[0], WINDOW[1]):
        stamp = day.strftime("%Y%m%d")
        iso = iso_day(stamp)
        den = denom.get(iso)
        num = numer.get(stamp, 0) if den else None
        value = None if not den else num / den
        ind.execute(
            "INSERT INTO indicators (indicator, day, numerator, denominator, value) VALUES (?,?,?,?,?)",
            ("I1_ukraine_test", iso, num, den, value),
        )
        rows.append({"day": iso, "numerator": num, "denominator": den, "value": value})
    ind.commit()
    ind.close()
    print("## old_ukraine_test")
    print(format_weekly(weekly_summary(old)))
    print("## new_ukraine_test")
    print(format_weekly(weekly_summary(rows)))
    new_sum = sum(row["numerator"] or 0 for row in rows if row["denominator"])
    old_sum = sum(row["numerator"] or 0 for row in old if row["denominator"])
    print(f"ukraine relevant old {old_sum} new {new_sum}")


def _sample() -> None:
    require_memory()
    cfg = load_i2_config()
    hits = sqlite3.connect(f"file:{HITS}?mode=ro", uri=True)
    hits.execute("PRAGMA query_only=ON")
    rows = [
        {"region": region, "day": day, "url": url, "title": title}
        for region, day, url, title in hits.execute(
            "SELECT region, day, url, title FROM hits"
        )
    ]
    hits.close()
    print(f"hit rows {len(rows)}", flush=True)
    stories = collapse_stories(rows)
    del rows
    sample = draw_sample(stories, cfg["seed"], cfg["per_week"])
    if SAMPLE.exists():
        SAMPLE.unlink()
    out = sqlite3.connect(SAMPLE)
    out.execute(
        """
        CREATE TABLE stories (
          region TEXT NOT NULL,
          week TEXT NOT NULL,
          day TEXT NOT NULL,
          url TEXT NOT NULL,
          title TEXT NOT NULL,
          sampled INTEGER NOT NULL
        )
        """
    )
    sampled_keys = {(row["region"], row["week"], row["day"], row["url"], norm_title(row["title"])) for row in sample}
    out.executemany(
        "INSERT INTO stories (region, week, day, url, title, sampled) VALUES (?,?,?,?,?,?)",
        [
            (
                row["region"],
                row["week"],
                row["day"],
                row["url"],
                row["title"],
                1 if (row["region"], row["week"], row["day"], row["url"], norm_title(row["title"])) in sampled_keys else 0,
            )
            for row in stories
        ],
    )
    out.commit()
    counts = out.execute(
        "SELECT region, SUM(sampled), COUNT(*) FROM stories GROUP BY region"
    ).fetchall()
    out.close()
    print(f"unique stories and sample {counts} seed {cfg['seed']}")


if __name__ == "__main__":
    collect()
