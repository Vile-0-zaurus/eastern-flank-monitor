"""Classify the I2 sample. Prints the estimate and stops if it is over $8.

Never prints API keys. Saves each answer before the next call.
"""
from __future__ import annotations

import json
import math
import sqlite3
import time
import urllib.error
import urllib.request
from pathlib import Path

from pipeline.llm.call_guard import decide, note_success
from pipeline.llm.client import (
    AI_UNAVAILABLE,
    _api_key,
    billed_usd,
    complete,
    estimate_cost,
    load_config,
    log_usage,
    usage_parts,
)
from pipeline.score.i2_collect import SAMPLE, load_i2_config
from pipeline.score.retry_grok_build import complete_objects, require_answers

ROOT = Path(__file__).resolve().parents[2]
ANSWERS = ROOT / "data" / "llm" / "i2-answers.sqlite"
ERROR_LOG = ROOT / "data" / "llm" / "i2-errors.log"
PROMPTS = {
    "eastern_flank": ROOT / "prompts" / "classify_frames.md",
    "ukraine_test": ROOT / "prompts" / "classify_frames_ukraine.md",
}
JUDGE = ROOT / "prompts" / "judge_option.md"
# Measured on the 80-headline prompt-v3 call, 2026-10-09.
MEASURED_IN = 3489 / 80
MEASURED_OUT = 6605 / 80
OUT_CAP = 6000
CONV = {
    "eastern_flank": "efm-i2-flank-20261009",
    "ukraine_test": "efm-i2-ukraine-20261009",
}


RETRY_CAP = 6.10
RETRY_RUN = "i2-unavailable-retry"


def assert_retry_allowed(usd: float) -> None:
    """This retry does not inherit the old $8 approval."""
    if usd > RETRY_CAP:
        raise SystemExit(
            f"STOP retry estimate ${usd:.2f} is above ${RETRY_CAP:.2f}. No call was made."
        )


def retry_spend_ceiling(already_spent: float, task_cap: float, config_hard: float) -> float:
    """New spend cannot pass the approved cap. Does not raise the config hard stop."""
    return min(config_hard, already_spent + task_cap)


def sample_rows() -> list[dict]:
    con = sqlite3.connect(f"file:{SAMPLE}?mode=ro", uri=True)
    con.execute("PRAGMA query_only=ON")
    rows = [
        {"id": str(rowid), "region": region, "week": week, "day": day, "url": url, "title": title}
        for rowid, region, week, day, url, title in con.execute(
            "SELECT rowid, region, week, day, url, title FROM stories WHERE sampled=1 ORDER BY region, week, rowid"
        )
    ]
    con.close()
    return rows


def open_answers() -> sqlite3.Connection:
    ANSWERS.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(ANSWERS)
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS answers (
          sample_id TEXT NOT NULL,
          model TEXT NOT NULL,
          region TEXT NOT NULL,
          week TEXT NOT NULL,
          status TEXT NOT NULL,
          hostile TEXT,
          relevant TEXT,
          result_json TEXT NOT NULL,
          PRIMARY KEY (sample_id, model)
        )
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS spend (
          id INTEGER PRIMARY KEY,
          model TEXT NOT NULL,
          usd REAL NOT NULL,
          note TEXT NOT NULL
        )
        """
    )
    cols = {row[1] for row in con.execute("PRAGMA table_info(spend)")}
    if "ticks" not in cols:
        con.execute("ALTER TABLE spend ADD COLUMN ticks INTEGER")
    if "run_id" not in cols:
        con.execute("ALTER TABLE spend ADD COLUMN run_id TEXT")
    return con


def spent(con: sqlite3.Connection) -> float:
    row = con.execute("SELECT COALESCE(SUM(usd), 0) FROM spend").fetchone()
    return float(row[0])


def upfront_usd(expected: float, output_cap: float, factor: float) -> float:
    """Higher visible estimate, times the config calibration factor. No API call."""
    return max(expected, output_cap) * factor


def real_spend_usd(ticks: list) -> float | None:
    """Sum of cost_in_usd_ticks for this run. None if any call did not record ticks."""
    if any(item is None for item in ticks):
        return None
    return sum(int(item) for item in ticks) / 10_000_000_000


def real_cap_blocks(ticks: list, cap_usd: float) -> bool:
    """True when real spend has reached the cap, or ticks are missing so the cap cannot be checked."""
    spent_usd = real_spend_usd(ticks)
    if spent_usd is None:
        return True
    return spent_usd >= cap_usd


def run_ticks(con: sqlite3.Connection, after_id: int, run_id: str) -> list:
    return [
        row[0]
        for row in con.execute(
            "SELECT ticks FROM spend WHERE id > ? AND run_id = ? ORDER BY id",
            (after_id, run_id),
        )
    ]


def estimate(n: int, batch_size: int) -> dict:
    batches = math.ceil(n / batch_size) if n else 0
    prompt_tokens = 800
    title_tokens = 40
    in_tokens = batches * prompt_tokens + n * title_tokens
    extra_prompt = max(batches - math.ceil(n / 80), 0) * prompt_tokens
    cfg = load_config()
    grok_expected = estimate_cost(int(n * MEASURED_IN + extra_prompt), int(n * MEASURED_OUT), cfg, "grok-build-0.1")
    grok_cap = estimate_cost(int(in_tokens), int(batches * OUT_CAP), cfg, "grok-build-0.1")
    sonnet_list = estimate_cost(200 * (prompt_tokens + title_tokens), 200 * 160, cfg, "claude-sonnet-5-5")
    sonnet_batch = sonnet_list * 0.5
    return {
        "n": n,
        "batches": batches,
        "grok_expected": grok_expected,
        "grok_cap": grok_cap,
        "sonnet_batch": sonnet_batch,
        "gate": grok_cap + sonnet_batch,
        "retry_gate": max(grok_expected, grok_cap),
    }


def chunks(rows: list[dict], size: int):
    for i in range(0, len(rows), size):
        yield rows[i : i + size]


def store_rows(con: sqlite3.Connection, model: str, rows: list[dict], parsed: dict[str, dict]) -> None:
    for row in rows:
        item = parsed[row["id"]]
        status = item.get("status") or "ok"
        con.execute(
            """
            INSERT OR REPLACE INTO answers
            (sample_id, model, region, week, status, hostile, relevant, result_json)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            (
                row["id"],
                model,
                row["region"],
                row["week"],
                status,
                item.get("hostile_framing"),
                item.get("relevant"),
                json.dumps(item, ensure_ascii=False),
            ),
        )
    con.commit()


def already(con: sqlite3.Connection, model: str) -> set[str]:
    return {row[0] for row in con.execute("SELECT sample_id FROM answers WHERE model=?", (model,))}


def grok_pending(rows: list[dict], stored: dict[str, str]) -> list[dict]:
    """Real answers stay stored. A missing row or AI unavailable is called again."""
    return [row for row in rows if stored.get(row["id"]) in (None, AI_UNAVAILABLE)]


def stored_status(con: sqlite3.Connection, model: str) -> dict[str, str]:
    return {row[0]: row[1] for row in con.execute("SELECT sample_id, status FROM answers WHERE model=?", (model,))}


def run_grok(con: sqlite3.Connection, rows: list[dict], hard: float) -> None:
    cfg = load_config()
    done = stored_status(con, "grok-build-0.1")
    pending = grok_pending(rows, done)
    by_region: dict[str, list[dict]] = {}
    for row in pending:
        by_region.setdefault(row["region"], []).append(row)
    failures: list[bool] = []
    for region in ("eastern_flank", "ukraine_test"):
        prompt = PROMPTS[region].read_text(encoding="utf-8")
        for batch in chunks(by_region.get(region, []), 50):
            _one_grok(con, cfg, prompt, region, batch, hard, tries_left=2, failures=failures)


def _real_stop(con: sqlite3.Connection, spend_after: int, run_id: str, real_cap: float, where: str) -> bool:
    """True when this run must not make another call. Does not call the API."""
    if not run_id:
        print(f"REAL STOP {where} run_id missing", flush=True)
        return True
    ticks = run_ticks(con, spend_after, run_id)
    if not real_cap_blocks(ticks, real_cap):
        return False
    spent_usd = real_spend_usd(ticks)
    shown = "missing" if spent_usd is None else f"{spent_usd:.6f}"
    print(f"REAL STOP {where} usd={shown} cap={real_cap:.2f}", flush=True)
    return True


def _one_grok(con, cfg, prompt, region, batch, hard, tries_left: int, failures: list | None = None, *, real_cap: float | None = None, spend_after: int = 0, run_id: str = "") -> str:
    if failures is None:
        failures = []
    if not batch:
        return "ok"
    if real_cap is not None and _real_stop(con, spend_after, run_id, real_cap, "before batch"):
        return "stop"
    if spent(con) >= hard:
        parsed = require_answers([row["id"] for row in batch], {})
        store_rows(con, "grok-build-0.1", batch, parsed)
        print(f"HARD STOP before batch spent={spent(con):.4f}", flush=True)
        return "stop"
    payload = json.dumps([{"id": row["id"], "title": row["title"]} for row in batch], ensure_ascii=False)
    usage: list[dict] = []
    try:
        text, pin, pout = complete(
            prompt,
            payload,
            cfg,
            model="grok-build-0.1",
            extra={"max_completion_tokens": OUT_CAP},
            timeout=300,
            headers={"x-grok-conv-id": CONV[region]},
            usage_sink=usage,
        )
    except Exception as exc:
        attempt = max(0, 2 - tries_left)
        decision = decide(exc, attempt, failures)
        print(f"GROK ERROR {decision['log']}", flush=True)
        ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
        with ERROR_LOG.open("a", encoding="utf-8") as fh:
            fh.write(decision["log"] + "\n")
        if decision["action"] in ("stop", "pause"):
            print(decision["report"], flush=True)
            raise SystemExit(decision["report"])
        if decision["action"] == "retry":
            if real_cap is not None and _real_stop(con, spend_after, run_id, real_cap, "before retry"):
                return "stop"
            time.sleep(decision["wait"])
            return _one_grok(
                con, cfg, prompt, region, batch, hard, tries_left - 1, failures,
                real_cap=real_cap, spend_after=spend_after, run_id=run_id,
            )
        parsed = require_answers([row["id"] for row in batch], {})
        store_rows(con, "grok-build-0.1", batch, parsed)
        return "error"
    note_success(failures)
    raw = usage[0] if usage else {}
    parts = usage_parts(raw)
    usd = billed_usd(raw, cfg, "grok-build-0.1") if raw else estimate_cost(pin, pout, cfg, "grok-build-0.1")
    bill = "ticks" if parts["ticks"] is not None else "formula"
    log_usage(
        "grok-build-0.1",
        pin,
        pout,
        usd,
        extra={
            "cached_tokens": parts["cached"],
            "reasoning_tokens": parts["reasoning"],
            "reasoning_extra": parts["reasoning_extra"],
            "cost_ticks": parts["ticks"],
            "bill": bill,
        },
    )
    cols = {row[1] for row in con.execute("PRAGMA table_info(spend)")}
    if "ticks" not in cols:
        con.execute("ALTER TABLE spend ADD COLUMN ticks INTEGER")
    if "run_id" not in cols:
        con.execute("ALTER TABLE spend ADD COLUMN run_id TEXT")
    con.execute(
        "INSERT INTO spend (model, usd, note, ticks, run_id) VALUES (?,?,?,?,?)",
        ("grok-build-0.1", usd, region, parts["ticks"], run_id or None),
    )
    con.commit()
    parsed = require_answers([row["id"] for row in batch], complete_objects(text))
    missing = [row for row in batch if parsed[row["id"]].get("status") == AI_UNAVAILABLE]
    got = [row for row in batch if parsed[row["id"]].get("status") != AI_UNAVAILABLE]
    store_rows(con, "grok-build-0.1", got, parsed)
    print(
        f"USED grok region={region} n={len(batch)} in={pin} out={pout} cached={parts['cached']} "
        f"reasoning={parts['reasoning']} extra={parts['reasoning_extra']} ticks={parts['ticks'] or 0} "
        f"bill={bill} usd={usd:.6f} spent={spent(con):.4f} missing={len(missing)}",
        flush=True,
    )
    stopped = real_cap is not None and _real_stop(con, spend_after, run_id, real_cap, "after batch")
    if missing and tries_left > 0 and spent(con) < hard and not stopped:
        return _one_grok(
            con, cfg, prompt, region, missing, hard, tries_left - 1, failures,
            real_cap=real_cap, spend_after=spend_after, run_id=run_id,
        )
    if missing:
        store_rows(con, "grok-build-0.1", missing, parsed)
    return "stop" if stopped else "ok"


def hostile_ids(con: sqlite3.Connection) -> list[dict]:
    return [
        {"id": sid, "region": region, "week": week, "title": title}
        for sid, region, week, title in con.execute(
            """
            SELECT a.sample_id, a.region, a.week, s.title
            FROM answers a
            JOIN stories s ON s.rowid = a.sample_id
            WHERE a.model='grok-build-0.1' AND lower(COALESCE(a.hostile, ''))='yes'
            ORDER BY a.sample_id
            """
        )
    ]


def pick_judge(rows: list[dict], seed: int) -> list[dict]:
    import random

    ordered = sorted(rows, key=lambda row: row["id"])
    if len(ordered) <= 200:
        return ordered
    rng = random.Random(seed)
    chosen = rng.sample(ordered, 200)
    return sorted(chosen, key=lambda row: row["id"])


def run_sonnet(con: sqlite3.Connection, rows: list[dict], hard: float) -> str | None:
    if not rows:
        print("SONNET no hostile flags; precision is no data", flush=True)
        return None
    if spent(con) >= hard:
        print(f"HARD STOP before sonnet spent={spent(con):.4f}", flush=True)
        return None
    prompt = (ROOT / "prompts" / "classify_frames.md").read_text(encoding="utf-8")
    # The judge re-checks the wording. Ukraine rows use the Ukraine prompt so the region sentence matches.
    # One batch, grouped by region, still one Batch API submission.
    requests = []
    for row in rows:
        rules = PROMPTS[row["region"]].read_text(encoding="utf-8") + "\n\n" + JUDGE.read_text(encoding="utf-8")
        requests.append(
            {
                "custom_id": f"j{row['id']}",
                "params": {
                    "model": "claude-sonnet-5-5",
                    "max_tokens": 800,
                    "system": [{"type": "text", "text": rules, "cache_control": {"type": "ephemeral"}}],
                    "messages": [{"role": "user", "content": json.dumps([{"id": row["id"], "title": row["title"]}], ensure_ascii=False)}],
                },
            }
        )
    body = json.dumps({"requests": requests}).encode("utf-8")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages/batches",
        data=body,
        headers={
            "x-api-key": _api_key("ANTHROPIC_API_KEY"),
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            created = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        kind = str(exc.code)
        print(f"SONNET BATCH ERROR {kind}", flush=True)
        return None
    batch_id = created.get("id")
    print(f"SONNET BATCH id={batch_id} n={len(requests)}", flush=True)
    return batch_id


def poll_sonnet(batch_id: str) -> None:
    """Caller polls. This module only submits; the poll is in main so a kill can resume."""
    raise NotImplementedError(batch_id)


def save_sonnet(con: sqlite3.Connection, batch_id: str, chosen: list[dict], hard: float) -> None:
    """Poll the Batch API and store each verdict. Error type only, never the key."""
    deadline = time.time() + 3 * 60 * 60
    status = "in_progress"
    while time.time() < deadline:
        req = urllib.request.Request(
            f"https://api.anthropic.com/v1/messages/batches/{batch_id}",
            headers={
                "x-api-key": _api_key("ANTHROPIC_API_KEY"),
                "anthropic-version": "2023-06-01",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            print(f"SONNET POLL ERROR {exc.code}", flush=True)
            time.sleep(30)
            continue
        status = payload.get("processing_status") or ""
        counts = payload.get("request_counts") or {}
        print(f"SONNET STATUS {status} {counts}", flush=True)
        if status == "ended":
            break
        time.sleep(30)
    if status != "ended":
        print("SONNET TIMEOUT", flush=True)
        return
    req = urllib.request.Request(
        f"https://api.anthropic.com/v1/messages/batches/{batch_id}/results",
        headers={
            "x-api-key": _api_key("ANTHROPIC_API_KEY"),
            "anthropic-version": "2023-06-01",
        },
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        body = resp.read().decode("utf-8")
    by_id = {row["id"]: row for row in chosen}
    cfg = load_config()
    for line in body.splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        custom = str(item.get("custom_id") or "")
        sample_id = custom[1:] if custom.startswith("j") else custom
        row = by_id.get(sample_id)
        if row is None:
            continue
        result = item.get("result") or {}
        if result.get("type") != "succeeded":
            parsed = {"id": sample_id, "status": AI_UNAVAILABLE}
            store_rows(con, "claude-sonnet-5-5", [row], {sample_id: parsed})
            continue
        message = result.get("message") or {}
        text = "".join(part.get("text", "") for part in message.get("content") or [] if part.get("type") == "text")
        usage = message.get("usage") or {}
        pin = int(usage.get("input_tokens") or 0)
        pout = int(usage.get("output_tokens") or 0)
        usd = estimate_cost(pin, pout, cfg, "claude-sonnet-5-5") * 0.5
        if spent(con) + usd > hard:
            parsed = {"id": sample_id, "status": AI_UNAVAILABLE}
            store_rows(con, "claude-sonnet-5-5", [row], {sample_id: parsed})
            print(f"HARD STOP during sonnet spent={spent(con):.4f}", flush=True)
            continue
        log_usage("claude-sonnet-5-5", pin, pout, usd)
        con.execute(
            "INSERT INTO spend (model, usd, note) VALUES (?,?,?)",
            ("claude-sonnet-5-5", usd, "batch"),
        )
        parsed = require_answers([sample_id], complete_objects(text))
        store_rows(con, "claude-sonnet-5-5", [row], parsed)
    con.commit()
    print(f"SONNET STORED spent={spent(con):.4f}", flush=True)


def main() -> None:
    cfg = load_i2_config()
    rows = sample_rows()
    con = open_answers()
    stored = stored_status(con, "grok-build-0.1")
    pending = grok_pending(rows, stored)
    retrying = any(stored.get(row["id"]) == AI_UNAVAILABLE for row in pending)
    if retrying:
        est = estimate(len(pending), cfg["batch_size"])
        print(
            f"RETRY ESTIMATE n={est['n']} batches={est['batches']} "
            f"grok_expected={est['grok_expected']:.2f} grok_cap={est['grok_cap']:.2f} "
            f"retry_gate={est['retry_gate']:.2f} cap={RETRY_CAP:.2f} run={RETRY_RUN}",
            flush=True,
        )
        assert_retry_allowed(est["retry_gate"])
        from pipeline.llm.client import require_explicit_ok
        require_explicit_ok(est["retry_gate"], run_id=RETRY_RUN)
        con.execute("ATTACH DATABASE ? AS sample", (str(SAMPLE),))
        run_grok(con, rows, retry_spend_ceiling(spent(con), RETRY_CAP, cfg["hard_stop_usd"]))
        print(f"GROK DONE spent={spent(con):.4f}", flush=True)
        print("SONNET already stored. No further spend.", flush=True)
        con.close()
        return
    est = estimate(len(rows), cfg["batch_size"])
    print(
        f"ESTIMATE n={est['n']} batches={est['batches']} grok_expected={est['grok_expected']:.2f} "
        f"grok_cap={est['grok_cap']:.2f} sonnet_batch={est['sonnet_batch']:.2f} gate={est['gate']:.2f} cap={cfg['estimate_cap_usd']:.2f}",
        flush=True,
    )
    if est["gate"] > cfg["estimate_cap_usd"]:
        raise SystemExit("STOP estimate over $8")
    from pipeline.llm.client import require_explicit_ok
    require_explicit_ok(est["gate"], run_id="i2-backtest-classification")
    con.execute("ATTACH DATABASE ? AS sample", (str(SAMPLE),))
    run_grok(con, rows, cfg["hard_stop_usd"])
    print(f"GROK DONE spent={spent(con):.4f}", flush=True)
    flagged = [
        {"id": sid, "region": region, "week": week, "title": title}
        for sid, region, week, title in con.execute(
            """
            SELECT a.sample_id, a.region, a.week, s.title
            FROM answers a
            JOIN sample.stories s ON s.rowid = CAST(a.sample_id AS INTEGER)
            WHERE a.model='grok-build-0.1' AND lower(COALESCE(a.hostile, ''))='yes'
            ORDER BY a.sample_id
            """
        )
    ]
    chosen = pick_judge(flagged, cfg["seed"])
    print(f"HOSTILE flagged={len(flagged)} judge_sample={len(chosen)}", flush=True)
    batch_id = run_sonnet(con, chosen, cfg["hard_stop_usd"])
    if batch_id:
        Path(ROOT / "data" / "llm" / "i2-sonnet-batch-id.txt").write_text(batch_id + "\n", encoding="utf-8")
        print(f"SONNET SUBMITTED {batch_id}", flush=True)
        save_sonnet(con, batch_id, chosen, cfg["hard_stop_usd"])
    con.close()


if __name__ == "__main__":
    main()
