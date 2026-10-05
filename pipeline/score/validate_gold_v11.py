#!/usr/bin/env python3
"""Diagnostic run of prompt-v2 on gold-v1.1. Does not edit gold files or the prompt."""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))
from llm.client import complete, complete_anthropic, estimate_cost, load_config, log_usage  # noqa: E402
from score.escalate import assign_decisions, needs_human  # noqa: E402

GOLD = ROOT / "validation" / "gold-v1.1.csv"
PROMPT = (ROOT / "prompts" / "classify_frames.md").read_text(encoding="utf-8")
JUDGE_PROMPT = PROMPT + "\n\n" + (ROOT / "prompts" / "judge_option.md").read_text(encoding="utf-8")
OUT = ROOT / "validation" / "gold-v1.1-results.json"
DECISIONS = ROOT / "validation" / "gold-v1.1-decisions.csv"
BUDGET = 1.00
# Escalation compares the judge with the general classifier, not the cheap one.
CLASSIFIER = "grok-4.3"


def parse_rows(text: str) -> dict[str, dict]:
    raw = text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
    data = json.loads(raw)
    if isinstance(data, dict):
        data = data.get("results") or data.get("headlines") or data.get("items")
    if not isinstance(data, list):
        raise ValueError("response was not a JSON array")
    return {str(row["id"]): row for row in data}


def main() -> None:
    cfg = load_config()
    rows = [r for r in csv.DictReader(GOLD.open(encoding="utf-8")) if r["id"] != "175" and r.get("v3") != "Unsure"]
    payload = json.dumps([{"id": r["id"], "title": r["title"]} for r in rows], ensure_ascii=False)
    in_tokens = (len(PROMPT) + len(payload)) // 4 + 200
    out_tokens = 90 * len(rows)
    judge_out = 8000
    models = ["grok-4.3", "grok-build-0.1"]
    est = sum(estimate_cost(in_tokens, out_tokens, cfg, m) for m in models)
    est += estimate_cost(in_tokens, judge_out, cfg, "claude-opus-5-5")
    print(
        f"ESTIMATE usd={est:.4f} budget={BUDGET:.2f} headlines={len(rows)} "
        f"input_tokens~{in_tokens} classifier_output~{out_tokens} judge_output_cap={judge_out}"
    )
    if est > BUDGET:
        raise SystemExit("hard stop: estimate exceeds $1.00")

    spent = 0.0
    saved = {"estimate_usd": est, "models": {}, "judge_error": ""}
    for model in models:
        extra: dict[str, object] = {"max_completion_tokens": 8000}
        if model == "grok-4.3":
            extra["reasoning_effort"] = "none"
        if estimate_cost(in_tokens, out_tokens, cfg, model) + spent > BUDGET:
            raise SystemExit(f"hard stop before {model}")
        text, pin, pout = complete(PROMPT, payload, cfg, model=model, extra=extra, timeout=180)
        usd = estimate_cost(pin, pout, cfg, model)
        log_usage(model, pin, pout, usd)
        spent += usd
        print(f"USED model={model} input_tokens={pin} output_tokens={pout} usd={usd:.6f} spent={spent:.6f}")
        if spent > BUDGET:
            raise SystemExit("hard stop: spend exceeded $1.00")
        saved["models"][model] = {"text": text, "input_tokens": pin, "output_tokens": pout, "usd": usd}

    if estimate_cost(in_tokens, judge_out, cfg, "claude-opus-5-5") + spent > BUDGET:
        saved["judge_error"] = "skipped_budget"
        print("SKIP judge: remaining budget would not cover the output cap")
    else:
        try:
            text, pin, pout = complete_anthropic(JUDGE_PROMPT, payload, cfg["judge_model"], max_tokens=judge_out)
            usd = estimate_cost(pin, pout, cfg, "claude-opus-5-5")
            log_usage("claude-opus-5-5", pin, pout, usd)
            spent += usd
            print(f"USED model=claude-opus-5-5 input_tokens={pin} output_tokens={pout} usd={usd:.6f} spent={spent:.6f}")
            saved["models"]["claude-opus-5-5"] = {"text": text, "input_tokens": pin, "output_tokens": pout, "usd": usd}
        except SystemExit as exc:
            saved["judge_error"] = str(exc)
            print(f"SKIP judge: {exc}")
    saved["spent_usd"] = spent
    OUT.write_text(json.dumps(saved, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUT}")

    if "claude-opus-5-5" in saved["models"] and CLASSIFIER in saved["models"]:
        judge = parse_rows(saved["models"]["claude-opus-5-5"]["text"])
        clf = parse_rows(saved["models"][CLASSIFIER]["text"])
        queue = []
        for row in rows:
            j = judge.get(row["id"])
            c = clf.get(row["id"])
            if not j or not c:
                continue
            reason = needs_human(j, c)
            if reason:
                queue.append({"id": row["id"], "reason": reason, "date": "20210615", "title_en": row["title_en"]})
        decided = assign_decisions(queue)
        with DECISIONS.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, ["id", "reason", "date", "title_en", "queue_rank", "decided_by"])
            w.writeheader()
            w.writerows(decided)
        human = sum(1 for row in decided if row["decided_by"] == "human")
        print(f"escalations={len(decided)} shown_to_human={human} judge_no_human={len(decided) - human}")


if __name__ == "__main__":
    main()
