#!/usr/bin/env python3
"""Run prompt-v2 on the 80 batch-2 candidates. Does not edit the prompt or the gold file."""
from __future__ import annotations

import csv
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))
from llm.client import complete, complete_anthropic, estimate_cost, load_config, log_usage  # noqa: E402
from score.escalate import needs_human  # noqa: E402

CANDIDATES = ROOT / "validation" / "gold-b2-candidates.csv"
AUDIT = ROOT / "validation" / "gold-b2-audit.csv"
PROMPT = (ROOT / "prompts" / "classify_frames.md").read_text(encoding="utf-8")
JUDGE_PROMPT = PROMPT + "\n\n" + (ROOT / "prompts" / "judge_option.md").read_text(encoding="utf-8")
OUT = ROOT / "data" / "llm" / "gold-b2-results.json"
BUDGET = 1.50
CLASSIFIERS = ("grok-4.3", "grok-build-0.1")
JUDGES = ("claude-opus-5-5", "claude-sonnet-5-5")
PAGE_FIELDS = [
    "id", "domain", "date", "title", "title_en", "url",
    "v3", "f1", "f2", "f3", "f4", "f5", "f6", "f7", "notes",
]


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
    rows = list(csv.DictReader(CANDIDATES.open(encoding="utf-8")))
    payload = json.dumps(
        [{"id": row["id"], "title": row["title"]} for row in rows],
        ensure_ascii=False,
    )
    in_tokens = (len(PROMPT) + len(payload)) // 4 + 400
    out_tokens = 140 * len(rows)
    models = [*CLASSIFIERS, *JUDGES]
    est = sum(estimate_cost(in_tokens, out_tokens, cfg, model) for model in models)
    print(
        f"ESTIMATE usd={est:.4f} budget={BUDGET:.2f} headlines={len(rows)} "
        f"input_tokens~{in_tokens} output_tokens~{out_tokens} caching=anthropic"
    )
    if est > BUDGET:
        raise SystemExit("hard stop: estimate exceeds $1.50")

    spent = 0.0
    saved: dict = {"estimate_usd": est, "models": {}, "errors": {}}
    for model in CLASSIFIERS:
        extra: dict[str, object] = {"max_completion_tokens": out_tokens}
        if model == "grok-4.3":
            extra["reasoning_effort"] = "none"
        if estimate_cost(in_tokens, out_tokens, cfg, model) + spent > BUDGET:
            saved["errors"][model] = "skipped_budget"
            print(f"SKIP model={model} reason=skipped_budget")
            continue
        try:
            text, pin, pout = complete(PROMPT, payload, cfg, model=model, extra=extra, timeout=300)
        except SystemExit as exc:
            saved["errors"][model] = str(exc)
            print(f"SKIP model={model} error_type={exc}")
            continue
        usd = estimate_cost(pin, pout, cfg, model)
        log_usage(model, pin, pout, usd)
        spent += usd
        print(f"USED model={model} input_tokens={pin} output_tokens={pout} usd={usd:.6f} spent={spent:.6f}")
        if spent > BUDGET:
            raise SystemExit("hard stop: spend exceeded $1.50")
        saved["models"][model] = {"text": text, "input_tokens": pin, "output_tokens": pout, "usd": usd}

    judge_prompt_tokens = (len(JUDGE_PROMPT) + len(payload)) // 4 + 400
    for model in JUDGES:
        if estimate_cost(judge_prompt_tokens, out_tokens, cfg, model) + spent > BUDGET:
            saved["errors"][model] = "skipped_budget"
            print(f"SKIP model={model} reason=skipped_budget")
            continue
        try:
            text, pin, pout = complete_anthropic(JUDGE_PROMPT, payload, model, max_tokens=out_tokens, timeout=300)
        except SystemExit as exc:
            saved["errors"][model] = str(exc)
            print(f"SKIP model={model} error_type={exc}")
            continue
        usd = estimate_cost(pin, pout, cfg, model)
        log_usage(model, pin, pout, usd)
        spent += usd
        print(f"USED model={model} input_tokens={pin} output_tokens={pout} usd={usd:.6f} spent={spent:.6f}")
        if spent > BUDGET:
            raise SystemExit("hard stop: spend exceeded $1.50")
        saved["models"][model] = {"text": text, "input_tokens": pin, "output_tokens": pout, "usd": usd}

    saved["spent_usd"] = spent
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(saved, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUT}")
    write_audit(rows, saved)
    print(f"SPEND usd={spent:.6f}")


def disagrees(judge: dict, grok: dict | None) -> str:
    if str(judge.get("relevant") or "").lower() == "unsure" or str(judge.get("hostile_framing") or "").lower() == "unsure":
        return "unsure"
    if not grok:
        return ""
    reason = needs_human(judge, grok)
    if reason:
        return reason
    if str(judge.get("relevant") or "").lower() != str(grok.get("relevant") or "").lower():
        return "relevant_disagreement"
    return ""


def write_audit(rows: list[dict], saved: dict) -> None:
    parsed = {}
    for model, blob in saved["models"].items():
        try:
            parsed[model] = parse_rows(blob["text"])
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            saved["errors"][model] = f"unparsed:{type(exc).__name__}"
            print(f"UNPARSED model={model}")
    flagged = []
    clf = parsed.get("grok-4.3", {})
    for row in rows:
        reasons = []
        grok = clf.get(row["id"])
        for judge_name in JUDGES:
            judge = parsed.get(judge_name, {}).get(row["id"])
            if not judge:
                continue
            reason = disagrees(judge, grok)
            if reason:
                reasons.append(f"{judge_name}:{reason}")
        if reasons:
            flagged.append(row["id"])
    rng = random.Random(20220224)
    disagree = flagged[:10]
    rest = [row["id"] for row in rows if row["id"] not in set(disagree)]
    rng.shuffle(rest)
    chosen = disagree + rest[: 20 - len(disagree)]
    rng.shuffle(chosen)
    by_id = {row["id"]: row for row in rows}
    audit = []
    for item_id in chosen:
        src = by_id[item_id]
        audit.append({key: src.get(key, "") for key in PAGE_FIELDS})
    with AUDIT.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, PAGE_FIELDS)
        writer.writeheader()
        writer.writerows(audit)
    print(f"audit={len(audit)} flagged={len(flagged)} disagree_used={len(disagree)} wrote {AUDIT}")


if __name__ == "__main__":
    main()
