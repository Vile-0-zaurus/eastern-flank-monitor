"""Turn stored I2 answers into weekly shares. No model calls."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from pipeline.score.i1 import OUT
from pipeline.score.i2_run import ANSWERS
from pipeline.score.i2_sample import hostile_yes, wilson_interval

ROOT = Path(__file__).resolve().parents[2]


def load_answers(model: str) -> list[dict]:
    con = sqlite3.connect(f"file:{ANSWERS}?mode=ro", uri=True)
    con.execute("PRAGMA query_only=ON")
    rows = []
    for sample_id, region, week, status, blob in con.execute(
        "SELECT sample_id, region, week, status, result_json FROM answers WHERE model=? ORDER BY region, week",
        (model,),
    ):
        parsed = json.loads(blob)
        parsed["sample_id"] = sample_id
        parsed["region"] = region
        parsed["week"] = week
        parsed["status"] = status
        rows.append(parsed)
    con.close()
    return rows


def weekly(rows: list[dict]) -> list[dict]:
    buckets: dict[tuple[str, str], dict] = {}
    for row in rows:
        flag = hostile_yes(row)
        key = (row["region"], row["week"])
        bucket = buckets.setdefault(key, {"region": row["region"], "week": row["week"], "hostile": 0, "n": 0, "missing": 0})
        if flag is None:
            bucket["missing"] += 1
            continue
        bucket["n"] += 1
        if flag:
            bucket["hostile"] += 1
    out = []
    for key in sorted(buckets):
        bucket = buckets[key]
        interval = wilson_interval(bucket["hostile"], bucket["n"])
        if interval is None:
            bucket["value"] = None
            bucket["low"] = None
            bucket["high"] = None
        else:
            bucket["value"], bucket["low"], bucket["high"] = interval
        out.append(bucket)
    return out


def store(weeks: list[dict]) -> None:
    con = sqlite3.connect(OUT)
    cols = {row[1] for row in con.execute("PRAGMA table_info(indicators)")}
    if "ci_low" not in cols:
        con.execute("ALTER TABLE indicators ADD COLUMN ci_low REAL")
        con.execute("ALTER TABLE indicators ADD COLUMN ci_high REAL")
    ids = {"eastern_flank": "I2", "ukraine_test": "I2_ukraine_test"}
    for name in ids.values():
        con.execute("DELETE FROM indicators WHERE indicator=?", (name,))
    for row in weeks:
        con.execute(
            """
            INSERT INTO indicators
            (indicator, day, numerator, denominator, value, ci_low, ci_high)
            VALUES (?,?,?,?,?,?,?)
            """,
            (
                ids[row["region"]],
                row["week"],
                None if row["value"] is None else row["hostile"],
                None if row["value"] is None else row["n"],
                row["value"],
                row["low"],
                row["high"],
            ),
        )
    con.commit()
    con.close()


def precision(grok_rows: list[dict], sonnet_rows: list[dict]) -> dict:
    sonnet = {row["sample_id"]: row for row in sonnet_rows}
    judged = 0
    agree = 0
    missing = 0
    for row in grok_rows:
        if hostile_yes(row) is not True:
            continue
        other = sonnet.get(row["sample_id"])
        if other is None:
            continue
        flag = hostile_yes(other)
        if flag is None:
            missing += 1
            continue
        judged += 1
        if flag:
            agree += 1
    return {"judged": judged, "agree": agree, "missing": missing, "share": None if not judged else agree / judged}


def format_weeks(weeks: list[dict], region: str) -> str:
    lines = ["week        hostile  classified  share    low     high    missing"]
    for row in weeks:
        if row["region"] != region:
            continue
        if row["value"] is None:
            lines.append(f"{row['week']}  no data  missing {row['missing']}")
            continue
        lines.append(
            f"{row['week']}  {row['hostile']:>7}  {row['n']:>10}  {row['value']:.4f}  {row['low']:.4f}  {row['high']:.4f}  {row['missing']:>5}"
        )
    return "\n".join(lines)


def main() -> None:
    grok = load_answers("grok-build-0.1")
    weeks = weekly(grok)
    store(weeks)
    print(format_weeks(weeks, "eastern_flank"))
    print(format_weeks(weeks, "ukraine_test"))
    sonnet = load_answers("claude-sonnet-5-5")
    print("PRECISION", precision(grok, sonnet))


if __name__ == "__main__":
    main()
