"""ukraine-100-finish. No redraw. No Sonnet. No call unless the calibrated price is at or under the cap.

Ukraine pending rows are the existing 100/week subset that are not already ok.
Eastern flank pending rows are the existing 200/week sample that are not already ok.
"""
from __future__ import annotations

import sqlite3

from pipeline.llm.client import load_budget, require_explicit_ok
from pipeline.score.i2_collect import SAMPLE
from pipeline.score.i2_run import (
    ANSWERS,
    PROMPTS,
    _one_grok,
    chunks,
    estimate,
    open_answers,
    retry_spend_ceiling,
    spent,
    upfront_usd,
)

RUN_ID = "ukraine-100-finish"
CAP = 4.70
MODEL = "grok-build-0.1"


def pending_counts() -> dict:
    """Read-only counts. Does not update stories or answers."""
    sample = sqlite3.connect(f"file:{SAMPLE}?mode=ro", uri=True)
    sample.execute("PRAGMA query_only=ON")
    answers = sqlite3.connect(f"file:{ANSWERS}?mode=ro", uri=True)
    answers.execute("PRAGMA query_only=ON")
    ok = {
        row[0]
        for row in answers.execute(
            "SELECT sample_id FROM answers WHERE model=? AND status='ok'",
            (MODEL,),
        )
    }
    subset = [str(row[0]) for row in sample.execute("SELECT sample_id FROM ukraine_calib_100")]
    flank = [
        str(row[0])
        for row in sample.execute(
            "SELECT rowid FROM stories WHERE region='eastern_flank' AND sampled=1"
        )
    ]
    answers.close()
    sample.close()
    ukraine_pending = sum(1 for item in subset if item not in ok)
    flank_pending = sum(1 for item in flank if item not in ok)
    return {
        "subset": len(subset),
        "subset_ok": len(subset) - ukraine_pending,
        "ukraine_pending": ukraine_pending,
        "flank": len(flank),
        "flank_ok": len(flank) - flank_pending,
        "flank_pending": flank_pending,
        "n": ukraine_pending + flank_pending,
    }


def priced(n: int) -> dict:
    budget = load_budget()
    if not budget["calibration_factor_set"]:
        raise SystemExit("STOP calibration_factor is not in config. No call was made.")
    est = estimate(n, 50)
    factor = budget["calibration_factor"]
    price = upfront_usd(est["grok_expected"], est["grok_cap"], factor)
    measured = est["grok_expected"] * factor
    return {
        "n": n,
        "batches": est["batches"],
        "grok_expected": est["grok_expected"],
        "grok_cap": est["grok_cap"],
        "factor": factor,
        "upfront": price,
        "measured": measured,
    }


def pending_rows() -> list[dict]:
    sample = sqlite3.connect(f"file:{SAMPLE}?mode=ro", uri=True)
    sample.execute("PRAGMA query_only=ON")
    answers = sqlite3.connect(f"file:{ANSWERS}?mode=ro", uri=True)
    answers.execute("PRAGMA query_only=ON")
    ok = {
        row[0]
        for row in answers.execute(
            "SELECT sample_id FROM answers WHERE model=? AND status='ok'",
            (MODEL,),
        )
    }
    rows = []
    for sample_id, region, week, day, url, title in sample.execute(
        """
        SELECT sample_id, region, week, day, url, title
        FROM ukraine_calib_100
        ORDER BY week, sample_id
        """
    ):
        if str(sample_id) not in ok:
            rows.append(
                {
                    "id": str(sample_id),
                    "region": region,
                    "week": week,
                    "day": day,
                    "url": url,
                    "title": title,
                }
            )
    for rowid, region, week, day, url, title in sample.execute(
        """
        SELECT rowid, region, week, day, url, title
        FROM stories
        WHERE region='eastern_flank' AND sampled=1
        ORDER BY week, rowid
        """
    ):
        if str(rowid) not in ok:
            rows.append(
                {
                    "id": str(rowid),
                    "region": region,
                    "week": week,
                    "day": day,
                    "url": url,
                    "title": title,
                }
            )
    answers.close()
    sample.close()
    return rows


def main() -> None:
    counts = pending_counts()
    quote = priced(counts["n"])
    print(
        f"ESTIMATE run={RUN_ID} ukraine_pending={counts['ukraine_pending']} "
        f"flank_pending={counts['flank_pending']} n={quote['n']} batches={quote['batches']} "
        f"visible_expected={quote['grok_expected']:.6f} visible_cap={quote['grok_cap']:.6f} "
        f"factor={quote['factor']} measured={quote['measured']:.6f} "
        f"higher={quote['upfront']:.6f} gate=measured cap={CAP:.2f}",
        flush=True,
    )
    print(
        "NOTE xAI balance before any start: user stated $14.29. This process has not called.",
        flush=True,
    )
    if quote["measured"] > CAP:
        raise SystemExit(
            f"STOP measured ${quote['measured']:.2f} is above ${CAP:.2f}. No call was made."
        )
    require_explicit_ok(quote["measured"], run_id=RUN_ID)
    from pipeline.score.i2_run import load_i2_config

    answers = open_answers()
    before = answers.execute("SELECT COALESCE(MAX(id), 0) FROM spend").fetchone()[0]
    hard = retry_spend_ceiling(spent(answers), CAP, load_i2_config()["hard_stop_usd"])
    from pipeline.llm.client import load_config

    cfg = load_config()
    prompts = {name: path.read_text(encoding="utf-8") for name, path in PROMPTS.items()}
    failures: list[bool] = []
    for region in ("ukraine_test", "eastern_flank"):
        region_rows = [row for row in pending_rows() if row["region"] == region]
        for batch in chunks(region_rows, 50):
            result = _one_grok(
                answers,
                cfg,
                prompts[region],
                region,
                batch,
                hard,
                tries_left=2,
                failures=failures,
                real_cap=CAP,
                spend_after=int(before),
                run_id=RUN_ID,
            )
            if result == "stop":
                print(f"REAL STOP run={RUN_ID}", flush=True)
                answers.close()
                return
    print(f"GROK DONE run={RUN_ID}", flush=True)
    answers.close()


if __name__ == "__main__":
    main()
