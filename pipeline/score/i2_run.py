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

from pipeline.llm.client import (
    AI_UNAVAILABLE,
    _api_key,
    complete,
    estimate_cost,
    load_config,
    log_usage,
)
from pipeline.score.i2_collect import SAMPLE, load_i2_config
from pipeline.score.retry_grok_build import complete_objects, require_answers

ROOT = Path(__file__).resolve().parents[2]
ANSWERS = ROOT / "data" / "llm" / "i2-answers.sqlite"
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
    return con


def spent(con: sqlite3.Connection) -> float:
    row = con.execute("SELECT COALESCE(SUM(usd), 0) FROM spend").fetchone()
    return float(row[0])


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


def run_grok(con: sqlite3.Connection, rows: list[dict], hard: float) -> None:
    cfg = load_config()
    done = already(con, "grok-build-0.1")
    pending = [row for row in rows if row["id"] not in done]
    by_region: dict[str, list[dict]] = {}
    for row in pending:
        by_region.setdefault(row["region"], []).append(row)
    for region in ("eastern_flank", "ukraine_test"):
        prompt = PROMPTS[region].read_text(encoding="utf-8")
        for batch in chunks(by_region.get(region, []), 50):
            _one_grok(con, cfg, prompt, region, batch, hard, tries_left=2)


def _one_grok(con, cfg, prompt, region, batch, hard, tries_left: int) -> None:
    if not batch:
        return
    if spent(con) >= hard:
        parsed = require_answers([row["id"] for row in batch], {})
        store_rows(con, "grok-build-0.1", batch, parsed)
        print(f"HARD STOP before batch spent={spent(con):.4f}", flush=True)
        return
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
        kind = type(exc).__name__
        print(f"GROK ERROR {kind} tries_left={tries_left}", flush=True)
        if tries_left > 0:
            time.sleep(20)
            _one_grok(con, cfg, prompt, region, batch, hard, tries_left - 1)
            return
        parsed = require_answers([row["id"] for row in batch], {})
        store_rows(con, "grok-build-0.1", batch, parsed)
        return
    usd = estimate_cost(pin, pout, cfg, "grok-build-0.1")
    log_usage("grok-build-0.1", pin, pout, usd)
    con.execute("INSERT INTO spend (model, usd, note) VALUES (?,?,?)", ("grok-build-0.1", usd, region))
    con.commit()
    parsed = require_answers([row["id"] for row in batch], complete_objects(text))
    missing = [row for row in batch if parsed[row["id"]].get("status") == AI_UNAVAILABLE]
    got = [row for row in batch if parsed[row["id"]].get("status") != AI_UNAVAILABLE]
    store_rows(con, "grok-build-0.1", got, parsed)
    cached = 0
    if usage:
        details = usage[0].get("prompt_tokens_details") or {}
        cached = int(details.get("cached_tokens") or usage[0].get("cached_tokens") or 0)
    print(
        f"USED grok region={region} n={len(batch)} in={pin} out={pout} cached={cached} usd={usd:.6f} spent={spent(con):.4f} missing={len(missing)}",
        flush=True,
    )
    if missing and tries_left > 0 and spent(con) < hard:
        _one_grok(con, cfg, prompt, region, missing, hard, tries_left - 1)
    elif missing:
        store_rows(con, "grok-build-0.1", missing, parsed)


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
    est = estimate(len(rows), cfg["batch_size"])
    print(
        f"ESTIMATE n={est['n']} batches={est['batches']} grok_expected={est['grok_expected']:.2f} "
        f"grok_cap={est['grok_cap']:.2f} sonnet_batch={est['sonnet_batch']:.2f} gate={est['gate']:.2f} cap={cfg['estimate_cap_usd']:.2f}",
        flush=True,
    )
    if est["gate"] > cfg["estimate_cap_usd"]:
        raise SystemExit("STOP estimate over $8")
    con = open_answers()
    # stories table is in the sample db; the join in hostile_ids needs it attached.
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
