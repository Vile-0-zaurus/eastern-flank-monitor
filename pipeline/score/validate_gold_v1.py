#!/usr/bin/env python3
"""Run prompt-v1 on the frozen gold set. Does not edit validation/gold.csv."""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))
from llm.client import complete, estimate_cost, load_config, log_usage  # noqa: E402

GOLD = ROOT / "validation" / "gold.csv"
PROMPT = ROOT / "prompts" / "classify_frames.md"
OUT = ROOT / "validation" / "gold-v1-results.json"
BUDGET = 0.10
FRAMES = ["F1", "F2", "F3", "F4", "F5", "F6"]


def human_relevant(v3: str) -> bool | None:
    if v3 in ("Ordinary news", "Hostile framing"):
        return True
    if v3 == "Not about region":
        return False
    return None


def ai_label(row: dict) -> str:
    rel = str(row.get("relevant", "")).lower()
    hostile = str(row.get("hostile_framing", "")).lower()
    if rel == "no":
        return "Not about region"
    if rel == "yes" and hostile == "yes":
        return "Hostile framing"
    if rel == "yes":
        return "Ordinary news"
    return "unparsed"


def parse_rows(text: str) -> list[dict]:
    raw = text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0]
    data = json.loads(raw)
    if isinstance(data, dict):
        data = data.get("results") or data.get("headlines") or data.get("items")
    if not isinstance(data, list):
        raise ValueError("response was not a JSON array")
    return data


def kappa(pairs: list[tuple[str, str]]) -> float | None:
    if not pairs:
        return None
    labels = sorted({a for a, _ in pairs} | {b for _, b in pairs})
    n = len(pairs)
    po = sum(a == b for a, b in pairs) / n
    pe = 0.0
    for lab in labels:
        pe += (sum(a == lab for a, _ in pairs) / n) * (sum(b == lab for _, b in pairs) / n)
    if pe == 1:
        return 1.0
    return (po - pe) / (1 - pe)


def main() -> None:
    cfg = load_config()
    prompt = PROMPT.read_text(encoding="utf-8")
    gold = list(csv.DictReader(GOLD.open(encoding="utf-8")))
    payload = json.dumps(
        [{"id": r["id"], "title": r["title"]} for r in gold],
        ensure_ascii=False,
    )
    # Rough token count: 4 characters per token, plus a JSON-output allowance.
    in_tokens = (len(prompt) + len(payload)) // 4 + 200
    out_tokens = 80 * len(gold)
    models = [cfg["model"], cfg["compare_model"]]
    est = sum(estimate_cost(in_tokens, out_tokens, cfg, m) for m in models)
    print(f"ESTIMATE usd={est:.4f} budget={BUDGET:.2f} input_tokens~{in_tokens} output_tokens~{out_tokens} models={models}")
    if est > BUDGET:
        raise SystemExit("hard stop: estimate exceeds the $0.10 task budget")

    spent = 0.0
    by_model = {}
    for model in models:
        extra: dict[str, object] = {"max_completion_tokens": 8000}
        if model == "grok-4.3":
            extra["reasoning_effort"] = "none"
        remaining = BUDGET - spent
        if estimate_cost(in_tokens, out_tokens, cfg, model) > remaining:
            raise SystemExit(f"hard stop before {model}: remaining ${remaining:.4f}")
        text, pin, pout = complete(prompt, payload, cfg, model=model, extra=extra, timeout=180)
        usd = estimate_cost(pin, pout, cfg, model)
        log_usage(model, pin, pout, usd)
        spent += usd
        print(f"USED model={model} input_tokens={pin} output_tokens={pout} usd={usd:.6f} spent={spent:.6f}")
        if spent > BUDGET:
            raise SystemExit("hard stop: actual spend exceeded $0.10")
        by_model[model] = {"text": text, "input_tokens": pin, "output_tokens": pout, "usd": usd}
    OUT.write_text(json.dumps({"estimate_usd": est, "spent_usd": spent, "models": by_model}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
