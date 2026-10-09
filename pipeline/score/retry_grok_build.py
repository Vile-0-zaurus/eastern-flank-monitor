#!/usr/bin/env python3
"""Retry missing classifier answers and keep the full text."""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))
from llm.client import AI_UNAVAILABLE, complete, estimate_cost, load_config, log_usage  # noqa: E402

CANDIDATES = ROOT / "validation" / "gold-b2-candidates.csv"
PROMPT = ROOT / "prompts" / "classify_frames.md"
OUT = ROOT / "data" / "llm" / "gold-b2-grok-build-retry.json"
MODEL = "grok-build-0.1"
IDS = ("675348", "161699", "331834")
BUDGET = 0.20
OUT_CAP = 800
MAX_TRIES = 3  # first call plus 2 retries


def complete_objects(text: str) -> dict[str, dict]:
    raw = text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
    rows = []
    depth = 0
    start = None
    in_str = False
    esc = False
    for i, ch in enumerate(raw):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
            continue
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                try:
                    rows.append(json.loads(raw[start : i + 1]))
                except json.JSONDecodeError:
                    pass
                start = None
    return {str(row["id"]): row for row in rows if "id" in row}


def require_answers(expected: list[str], parsed: dict[str, dict]) -> dict[str, dict]:
    """Every headline gets a stored answer. Missing is AI unavailable, never silent."""
    out = {}
    missing = []
    for item_id in expected:
        row = parsed.get(item_id)
        if row and str(row.get("status") or "") != AI_UNAVAILABLE and "relevant" in row:
            out[item_id] = row
            continue
        missing.append(item_id)
        out[item_id] = {"id": item_id, "status": AI_UNAVAILABLE}
    if missing:
        print("AI_UNAVAILABLE " + ",".join(missing))
    else:
        print(f"STORED {len(expected)}/{len(expected)}")
    return out


def main() -> None:
    cfg = load_config()
    prompt = PROMPT.read_text(encoding="utf-8")
    cand = {row["id"]: row for row in csv.DictReader(CANDIDATES.open(encoding="utf-8"))}
    still = list(IDS)
    spent = 0.0
    attempts = []
    parsed: dict[str, dict] = {}
    for attempt in range(1, MAX_TRIES + 1):
        if not still:
            break
        payload = json.dumps(
            [{"id": item_id, "title": cand[item_id]["title"]} for item_id in still],
            ensure_ascii=False,
        )
        in_tokens = (len(prompt) + len(payload)) // 4 + 200
        est = estimate_cost(in_tokens, OUT_CAP, cfg, MODEL)
        print(f"ESTIMATE attempt={attempt} usd={est:.4f} budget={BUDGET:.2f} headlines={len(still)} output_cap={OUT_CAP}")
        if est + spent > BUDGET:
            print("SKIP reason=budget")
            break
        try:
            text, pin, pout = complete(
                prompt,
                payload,
                cfg,
                model=MODEL,
                extra={"max_completion_tokens": OUT_CAP},
                timeout=180,
            )
        except Exception as exc:
            kind = type(exc).__name__
            print(f"SKIP attempt={attempt} error_type={kind}")
            attempts.append({"attempt": attempt, "ids": list(still), "text": "", "error_type": kind})
            continue
        usd = estimate_cost(pin, pout, cfg, MODEL)
        log_usage(MODEL, pin, pout, usd)
        spent += usd
        got = complete_objects(text)
        parsed.update(got)
        attempts.append(
            {
                "attempt": attempt,
                "ids": list(still),
                "text": text,
                "parsed": got,
                "input_tokens": pin,
                "output_tokens": pout,
                "usd": usd,
            }
        )
        still = [item_id for item_id in still if item_id not in got]
        print(f"USED attempt={attempt} input_tokens={pin} output_tokens={pout} usd={usd:.6f} spent={spent:.6f} still={still}")
        if spent > BUDGET:
            raise SystemExit("hard stop: spend exceeded $0.20")
    answers = require_answers(list(IDS), parsed)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(
            {"model": MODEL, "spent_usd": spent, "attempts": attempts, "answers": answers},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
