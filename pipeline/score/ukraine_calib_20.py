"""ukraine-calib-20. Exactly 20 grok batches. No redraw. No Sonnet.

Ukraine subset is the lowest sha256(rowid+seed) 100 per week of the existing
sampled ukraine_test rows. Stories rows and rowids are not updated.
"""
from __future__ import annotations

import hashlib
import sqlite3

from pipeline.llm.client import load_config, require_explicit_ok
from pipeline.score.i2_collect import SAMPLE, load_i2_config
from pipeline.score.i2_run import (
    PROMPTS,
    _one_grok,
    chunks,
    estimate,
    open_answers,
    retry_spend_ceiling,
    spent,
    stored_status,
)

RUN_ID = "ukraine-calib-20"
CAP = 0.35
SEED = 20261009
BATCHES = 20
BATCH_SIZE = 50
N = BATCHES * BATCH_SIZE
MODEL = "grok-build-0.1"


def rank_key(rowid: int) -> str:
    return hashlib.sha256(f"{rowid}+{SEED}".encode()).hexdigest()


def stories_checksum(con: sqlite3.Connection) -> str:
    digest = hashlib.sha256()
    for row in con.execute(
        "SELECT rowid, region, week, day, url, title, sampled FROM stories ORDER BY rowid"
    ):
        digest.update(repr(row).encode())
    return digest.hexdigest()


def mark_subset() -> list[dict]:
    """Flag the 100/week subset. Does not update stories."""
    con = sqlite3.connect(SAMPLE)
    before = stories_checksum(con)
    flank = con.execute(
        "SELECT COALESCE(SUM(sampled), 0) FROM stories WHERE region='eastern_flank'"
    ).fetchone()[0]
    ukraine = con.execute(
        "SELECT COALESCE(SUM(sampled), 0) FROM stories WHERE region='ukraine_test'"
    ).fetchone()[0]
    by_week: dict[str, list[int]] = {}
    for rowid, week in con.execute(
        "SELECT rowid, week FROM stories WHERE region='ukraine_test' AND sampled=1"
    ):
        by_week.setdefault(week, []).append(int(rowid))
    picked: list[tuple[str, int]] = []
    for week in sorted(by_week):
        ranked = sorted(by_week[week], key=lambda rid: (rank_key(rid), rid))
        take = ranked if len(ranked) <= 100 else ranked[:100]
        picked.extend((week, rid) for rid in take)
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS ukraine_calib_flag (
          sample_id INTEGER PRIMARY KEY,
          week TEXT NOT NULL
        )
        """
    )
    con.execute("DELETE FROM ukraine_calib_flag")
    con.executemany(
        "INSERT INTO ukraine_calib_flag (sample_id, week) VALUES (?,?)",
        [(rid, week) for week, rid in picked],
    )
    con.execute("DROP VIEW IF EXISTS ukraine_calib_100")
    con.execute(
        """
        CREATE VIEW ukraine_calib_100 AS
        SELECT s.rowid AS sample_id, s.region, s.week, s.day, s.url, s.title
        FROM stories s
        JOIN ukraine_calib_flag f ON f.sample_id = s.rowid
        """
    )
    con.commit()
    after = stories_checksum(con)
    flank_after = con.execute(
        "SELECT COALESCE(SUM(sampled), 0) FROM stories WHERE region='eastern_flank'"
    ).fetchone()[0]
    ukraine_after = con.execute(
        "SELECT COALESCE(SUM(sampled), 0) FROM stories WHERE region='ukraine_test'"
    ).fetchone()[0]
    view_n = con.execute("SELECT COUNT(*) FROM ukraine_calib_100").fetchone()[0]
    if before != after or flank != flank_after or ukraine != ukraine_after:
        con.close()
        raise SystemExit("STOP stories rows changed. No call was made.")
    if view_n != len(picked) or flank_after != 11987:
        con.close()
        raise SystemExit(f"STOP subset mark view={view_n} flank={flank_after}. No call was made.")
    rows = [
        {
            "id": str(sample_id),
            "region": region,
            "week": week,
            "day": day,
            "url": url,
            "title": title,
        }
        for sample_id, region, week, day, url, title in con.execute(
            """
            SELECT sample_id, region, week, day, url, title
            FROM ukraine_calib_100
            ORDER BY week, sample_id
            LIMIT ?
            """,
            (N,),
        )
    ]
    con.close()
    print(
        f"MARKED subset={len(picked)} run_n={len(rows)} "
        f"weeks={rows[0]['week']}..{rows[-1]['week']} stories_unchanged=yes flank={flank_after}",
        flush=True,
    )
    return rows


def main() -> None:
    rows = mark_subset()
    if len(rows) != N:
        raise SystemExit(f"STOP run_n={len(rows)} expected {N}. No call was made.")
    est = estimate(N, BATCH_SIZE)
    higher = est["retry_gate"]
    print(
        f"ESTIMATE n={est['n']} batches={est['batches']} "
        f"grok_expected={est['grok_expected']:.6f} grok_cap={est['grok_cap']:.6f} "
        f"higher={higher:.6f} cap={CAP:.2f} run={RUN_ID}",
        flush=True,
    )
    if higher > CAP:
        raise SystemExit(f"STOP estimate ${higher:.2f} is above ${CAP:.2f}. No call was made.")
    require_explicit_ok(higher, run_id=RUN_ID)
    answers = open_answers()
    stored = stored_status(answers, MODEL)
    ok = [row for row in rows if stored.get(row["id"]) == "ok"]
    if ok:
        answers.close()
        raise SystemExit(f"STOP {len(ok)} already ok. No call was made.")
    i2_cfg = load_i2_config()
    hard = retry_spend_ceiling(spent(answers), CAP, i2_cfg["hard_stop_usd"])
    cfg = load_config()
    prompt = PROMPTS["ukraine_test"].read_text(encoding="utf-8")
    failures: list[bool] = []
    done = 0
    for batch in chunks(rows, BATCH_SIZE):
        if done >= BATCHES:
            break
        if spent(answers) >= hard:
            print(f"HARD STOP before batch spent={spent(answers):.4f}", flush=True)
            break
        _one_grok(answers, cfg, prompt, "ukraine_test", batch, hard, tries_left=2, failures=failures)
        done += 1
    print(f"GROK DONE batches={done} spent={spent(answers):.4f} run={RUN_ID}", flush=True)
    answers.close()


if __name__ == "__main__":
    main()
