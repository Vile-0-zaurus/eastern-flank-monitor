#!/usr/bin/env python3
"""No-regression run of prompt-v3. Does not edit the prompt or any gold file."""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))
from llm.client import (  # noqa: E402
    AI_UNAVAILABLE,
    complete,
    complete_anthropic,
    estimate_cost,
    load_config,
    log_usage,
)

CANDIDATES = ROOT / "validation" / "gold-b2-candidates.csv"
AUDIT = ROOT / "validation" / "gold-b2-audit.csv"
ADJ = ROOT / "validation" / "gold-b2-adjudicated.csv"
PROMPT_PATH = ROOT / "prompts" / "classify_frames.md"
JUDGE_NOTE = ROOT / "prompts" / "judge_option.md"
OUT = ROOT / "data" / "llm" / "gold-b2-prompt-v3.json"
BUDGET_LEFT = 0.1985
GROK_CAP = 8000
SONNET_CAP = 14000
HUMAN = {
    "Not about region": "not_about_region",
    "Ordinary news": "ordinary",
    "Hostile framing": "hostile",
    "Unsure": "unsure",
}


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


def four(row: dict | None) -> str:
    if not row or row.get("status") == AI_UNAVAILABLE:
        return "missing" if not row else "unavailable"
    rel = str(row.get("relevant") or "").strip().lower()
    hos = str(row.get("hostile_framing") or "").strip().lower()
    if rel == "unsure" or hos == "unsure":
        return "unsure"
    if rel == "no":
        return "not_about_region"
    if rel == "yes" and hos == "no":
        return "ordinary"
    if rel == "yes" and hos == "yes":
        return "hostile"
    return "other"


def require_answers(expected: list[str], parsed: dict[str, dict]) -> dict[str, dict]:
    out = {}
    missing = []
    for item_id in expected:
        row = parsed.get(item_id)
        if row and row.get("status") != AI_UNAVAILABLE and "relevant" in row:
            out[item_id] = row
            continue
        missing.append(item_id)
        out[item_id] = {"id": item_id, "status": AI_UNAVAILABLE}
    if missing:
        print("AI_UNAVAILABLE " + ",".join(missing))
    else:
        print(f"STORED {len(expected)}/{len(expected)}")
    return out


def kappa(pairs: list[tuple[bool, bool]]) -> float | None:
    n = len(pairs)
    if not n:
        return None
    po = sum(a == b for a, b in pairs) / n
    hy = sum(a for a, _ in pairs) / n
    my = sum(b for _, b in pairs) / n
    pe = hy * my + (1 - hy) * (1 - my)
    if math.isclose(pe, 1.0):
        return None
    return (po - pe) / (1 - pe)


def adjudicated_ref(item_id: str, human: str, opus: str, sonnet: str, decision: str) -> str | None:
    if decision == "Rule is unclear":
        return None
    if decision == "Judge applied the rule correctly":
        if opus == sonnet and opus not in ("missing", "other", "unavailable"):
            return opus
        return None
    if decision == "My label stands" or not decision:
        return human
    return None


def score(name: str, answers: dict[str, dict], audit: list[dict], adj: dict[str, dict], old_opus: dict, old_sonnet: dict) -> None:
    pairs = []
    for row in audit:
        item_id = row["id"]
        human = HUMAN.get((row.get("v3") or "").strip(), "blank")
        decision = (adj.get(item_id) or {}).get("decision", "")
        ref = adjudicated_ref(item_id, human, four(old_opus.get(item_id)), four(old_sonnet.get(item_id)), decision)
        if item_id not in adj and human not in ("unsure", "blank"):
            ref = human
        if ref not in ("ordinary", "hostile"):
            continue
        label = four(answers.get(item_id))
        if label not in ("ordinary", "hostile"):
            continue
        pairs.append((ref == "hostile", label == "hostile"))
    n = len(pairs)
    agree = sum(a == b for a, b in pairs)
    print(f"SCORE {name} {agree}/{n} {100 * agree / n if n else 0:.1f} kappa={kappa(pairs)}")


def main() -> None:
    cfg = load_config()
    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    judge_prompt = prompt + "\n\n" + JUDGE_NOTE.read_text(encoding="utf-8")
    rows = list(csv.DictReader(CANDIDATES.open(encoding="utf-8")))
    ids = [row["id"] for row in rows]
    payload = json.dumps([{"id": row["id"], "title": row["title"]} for row in rows], ensure_ascii=False)
    in_g = (len(prompt) + len(payload)) // 4 + 400
    in_s = (len(judge_prompt) + len(payload)) // 4 + 400
    est_g = estimate_cost(in_g, GROK_CAP, cfg, "grok-build-0.1")
    est_s = estimate_cost(in_s, SONNET_CAP, cfg, "claude-sonnet-5-5")
    print(f"ESTIMATE grok-build-0.1 usd={est_g:.4f} in~{in_g} out_cap={GROK_CAP}")
    print(f"ESTIMATE claude-sonnet-5-5 usd={est_s:.4f} in~{in_s} out_cap={SONNET_CAP}")
    print(f"ESTIMATE total usd={est_g + est_s:.4f} budget_left={BUDGET_LEFT:.4f}")
    if est_g + est_s > BUDGET_LEFT:
        raise SystemExit("hard stop: estimate exceeds remaining $0.20 budget")

    spent = 0.0
    saved: dict = {"prompt_tag": "prompt-v3", "models": {}, "errors": {}}
    text, pin, pout = complete(
        prompt,
        payload,
        cfg,
        model="grok-build-0.1",
        extra={"max_completion_tokens": GROK_CAP},
        timeout=300,
    )
    usd = estimate_cost(pin, pout, cfg, "grok-build-0.1")
    log_usage("grok-build-0.1", pin, pout, usd)
    spent += usd
    print(f"USED model=grok-build-0.1 input_tokens={pin} output_tokens={pout} usd={usd:.6f} spent={spent:.6f}")
    saved["models"]["grok-build-0.1"] = {"text": text, "input_tokens": pin, "output_tokens": pout, "usd": usd}
    if spent > BUDGET_LEFT:
        raise SystemExit("hard stop: spend exceeded remaining budget")

    text, pin, pout = complete_anthropic(judge_prompt, payload, "claude-sonnet-5-5", max_tokens=SONNET_CAP, timeout=300)
    usd = estimate_cost(pin, pout, cfg, "claude-sonnet-5-5")
    log_usage("claude-sonnet-5-5", pin, pout, usd)
    spent += usd
    print(f"USED model=claude-sonnet-5-5 input_tokens={pin} output_tokens={pout} usd={usd:.6f} spent={spent:.6f}")
    saved["models"]["claude-sonnet-5-5"] = {"text": text, "input_tokens": pin, "output_tokens": pout, "usd": usd}
    saved["spent_usd"] = spent
    answers = {
        name: require_answers(ids, complete_objects(blob["text"]))
        for name, blob in saved["models"].items()
    }
    saved["answers"] = answers
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(saved, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUT}")

    old = json.loads((ROOT / "data/llm/gold-b2-results.json").read_text(encoding="utf-8"))
    old_opus = complete_objects(old["models"]["claude-opus-5-5"]["text"])
    old_sonnet = complete_objects(old["models"]["claude-sonnet-5-5"]["text"])
    extra = json.loads((ROOT / "data/llm/gold-b2-sonnet-614574.json").read_text(encoding="utf-8"))
    old_sonnet.update(complete_objects(extra["text"]))
    audit = list(csv.DictReader(AUDIT.open(encoding="utf-8")))
    adj = {row["id"]: row for row in csv.DictReader(ADJ.open(encoding="utf-8"))}
    print("prompt-v2 raw Opus 78.6 Sonnet 73.3; adjudicated both 93.3")
    score("prompt-v3 grok-build-0.1", answers["grok-build-0.1"], audit, adj, old_opus, old_sonnet)
    score("prompt-v3 claude-sonnet-5-5", answers["claude-sonnet-5-5"], audit, adj, old_opus, old_sonnet)


if __name__ == "__main__":
    main()
