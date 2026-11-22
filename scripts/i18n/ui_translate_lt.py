#!/usr/bin/env python3
"""Run ui-translate-1: Lithuanian only. No other language. No extended thinking.

Hard cap is $0.15 of real usage tokens. A batch is not sent if its own
token ceiling would cross the cap. The key is never printed.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EN = ROOT / "frontend" / "i18n" / "en.json"
OUT = ROOT / "frontend" / "i18n" / "lt.json"
STORE = ROOT / "data" / "llm" / "ui-translate-1"
MODEL = "claude-sonnet-5-5"
RUN_ID = "ui-translate-1"
CAP = 0.15
INPUT_USD = 2.0
OUTPUT_USD = 10.0
CACHE_READ_USD = 0.20
CACHE_WRITE_USD = 2.50
BATCH = 40


def api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        env = ROOT / ".env"
        for raw in env.read_text(encoding="utf-8").splitlines():
            if raw.startswith("ANTHROPIC_API_KEY="):
                key = raw.split("=", 1)[1].strip().strip('"').strip("'")
                break
    if not key:
        raise SystemExit("ANTHROPIC_API_KEY is not set")
    return key


def cost(usage: dict) -> float:
    pin = int(usage.get("input_tokens") or 0)
    pout = int(usage.get("output_tokens") or 0)
    cread = int(usage.get("cache_read_input_tokens") or 0)
    cwrite = int(usage.get("cache_creation_input_tokens") or 0)
    return (
        pin * INPUT_USD
        + cread * CACHE_READ_USD
        + cwrite * CACHE_WRITE_USD
        + pout * OUTPUT_USD
    ) / 1_000_000


def call(user: str, max_tokens: int) -> tuple[str, dict]:
    body = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "thinking": {"type": "between_tools"},
        "output_config": {"effort": "low"},
        "system": (
            "Translate JSON values into Lithuanian. Return one JSON object and nothing else. "
            "Keep every placeholder such as {name} exactly. Do not translate GDELT, Yle, BBC, "
            "Zapad-2021, Allied Resolve, or Ryanair. Keep warning sentences exact in meaning."
        ),
        "messages": [{"role": "user", "content": user}],
    }
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "x-api-key": api_key(),
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        kind = str(exc.code)
        try:
            err = json.loads(exc.read().decode("utf-8"))
            kind = str((err.get("error") or {}).get("type") or kind)
        except Exception:
            pass
        raise SystemExit("anthropic " + kind) from None
    text = "".join(
        part.get("text", "") for part in payload.get("content") or [] if part.get("type") == "text"
    )
    return text, payload.get("usage") or {}


def parse_json(text: str) -> dict:
    raw = text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0]
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("not an object")
    return data


def main() -> int:
    english = json.loads(EN.read_text(encoding="utf-8"))
    keys = list(english)
    STORE.mkdir(parents=True, exist_ok=True)
    done: dict[str, str] = {}
    spent = 0.0
    rows = []
    batches = [keys[i : i + BATCH] for i in range(0, len(keys), BATCH)]
    print(f"run={RUN_ID} strings={len(keys)} batches={len(batches)} cap={CAP:.2f}")
    for index, batch in enumerate(batches, start=1):
        payload = {key: english[key] for key in batch}
        user = json.dumps(payload, ensure_ascii=False)
        est_in = max(800, len(user) // 2)
        room = CAP - spent
        input_cost = est_in * INPUT_USD / 1_000_000
        if input_cost >= room:
            print(f"STOP before batch {index}: input ceiling ${input_cost:.4f} leaves no room")
            break
        max_tokens = int((room - input_cost) * 1_000_000 / OUTPUT_USD)
        max_tokens = min(max_tokens, 4000)
        if max_tokens < 600:
            print(f"STOP before batch {index}: only {max_tokens} output tokens fit under the cap")
            break
        ceiling = input_cost + max_tokens * OUTPUT_USD / 1_000_000
        print(f"batch {index} strings={len(batch)} max_tokens={max_tokens} ceiling=${ceiling:.4f} spent=${spent:.4f}")
        text, usage = call(user, max_tokens)
        usd = cost(usage)
        spent += usd
        stamp = datetime.now(timezone.utc).isoformat()
        (STORE / f"batch-{index:02d}.json").write_text(
            json.dumps({"usage": usage, "usd": usd, "text": text}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        pin = int(usage.get("input_tokens") or 0)
        pout = int(usage.get("output_tokens") or 0)
        print(f"batch {index} input_tokens={pin} output_tokens={pout} usd={usd:.6f} spent={spent:.6f}")
        rows.append({"batch": index, "input_tokens": pin, "output_tokens": pout, "usd": usd, "at": stamp})
        try:
            parsed = parse_json(text)
        except Exception as exc:
            print(f"batch {index} parse failed: {type(exc).__name__}")
            if spent >= CAP:
                break
            continue
        for key in batch:
            value = parsed.get(key)
            if isinstance(value, str) and value.strip():
                done[key] = value
        if spent >= CAP:
            print("STOP: cap reached after this batch")
            break
    merged = dict(english)
    merged.update(done)
    OUT.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {
        "run_id": RUN_ID,
        "model": MODEL,
        "thinking": "between_tools",
        "effort": "low",
        "cap_usd": CAP,
        "spent_usd": round(spent, 6),
        "strings_done": len(done),
        "strings_total": len(keys),
        "batches": rows,
    }
    (STORE / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary))
    return 0 if len(done) == len(keys) and spent <= CAP else 2


if __name__ == "__main__":
    sys.exit(main())
