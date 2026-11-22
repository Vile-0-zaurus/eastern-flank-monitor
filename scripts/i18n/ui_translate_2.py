#!/usr/bin/env python3
"""Run ui-translate-2: Finnish, Estonian, Latvian, Polish. Not Lithuanian.

Same settings as ui-translate-1: claude-sonnet-5-5, thinking between_tools,
effort low. Hard cap is $0.45 of usage tokens times published rates, shared
across every batch. A batch is not sent if its token ceiling would cross the
cap. A stored batch is not called again. The key is never printed.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EN_PATH = ROOT / "frontend" / "i18n" / "en.json"
STORE = ROOT / "data" / "llm" / "ui-translate-2"
MODEL = "claude-sonnet-5-5"
RUN_ID = "ui-translate-2"
CAP = 0.45
MEASURED_PER_LANG = 0.087150
INPUT_USD = 2.0
OUTPUT_USD = 10.0
CACHE_READ_USD = 0.20
CACHE_WRITE_USD = 2.50
BATCH = 40
LANGS = (
    ("fi", "Finnish"),
    ("et", "Estonian"),
    ("lv", "Latvian"),
    ("pl", "Polish"),
)
ALLOW_SAME = {
    "sub_line",
    "marker_ryanair",
    "marker_zapad",
    "marker_allied",
    "country_LV",
    "country_EE",
    "country_KG",
    "region",
}
PLACEHOLDER = re.compile(r"\{[A-Za-z0-9_]+\}")


def api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        for raw in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
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


def thinking_tokens(usage: dict) -> int:
    details = usage.get("output_tokens_details") or {}
    return int(details.get("thinking_tokens") or 0)


def call(language: str, user: str, max_tokens: int) -> tuple[str, dict, str]:
    body = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "thinking": {"type": "between_tools"},
        "output_config": {"effort": "low"},
        "system": (
            f"Translate JSON values into {language}. Return one JSON object and nothing else. "
            "Keep every placeholder such as {name} exactly. Do not translate GDELT, Yle, BBC, "
            "Zapad-2021, Allied Resolve, or Ryanair. Keep warning sentences exact in meaning. "
            "Translate every value. Leave a value unchanged only for a proper noun or a code."
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
        part.get("text", "")
        for part in payload.get("content") or []
        if part.get("type") == "text"
    )
    return text, payload.get("usage") or {}, str(payload.get("stop_reason") or "")


def parse_json(text: str) -> dict:
    raw = text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0]
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("not an object")
    return data


def accepted(key: str, english: str, value: object) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    if set(PLACEHOLDER.findall(english)) != set(PLACEHOLDER.findall(value)):
        return False
    if key not in ALLOW_SAME and value == english:
        return False
    return True


def take(batch: list[str], english: dict, parsed: dict, done: dict) -> list[str]:
    missing = []
    for key in batch:
        value = parsed.get(key)
        if accepted(key, english[key], value):
            done[key] = value
        else:
            missing.append(key)
    return missing


def room_for(spent: float, user: str) -> tuple[int, float] | None:
    est_in = max(800, len(user) // 2)
    room = CAP - spent
    input_cost = est_in * INPUT_USD / 1_000_000
    if input_cost >= room:
        print(f"STOP before call: input ceiling ${input_cost:.4f} leaves no room")
        return None
    max_tokens = int((room - input_cost) * 1_000_000 / OUTPUT_USD)
    max_tokens = min(max_tokens, 4000)
    if max_tokens < 600:
        print(f"STOP before call: only {max_tokens} output tokens fit under the cap")
        return None
    ceiling = input_cost + max_tokens * OUTPUT_USD / 1_000_000
    return max_tokens, ceiling


def write_review(code: str, language: str, english: dict, done: dict, rows: list[dict]) -> None:
    pin = sum(row["input_tokens"] for row in rows)
    pout = sum(row["output_tokens"] for row in rows)
    think = sum(row["thinking_tokens"] for row in rows)
    usd = sum(row["usd"] for row in rows)
    same = [key for key in done if done[key] == english[key]]
    lines = [
        f"# {language} review — {RUN_ID}",
        "",
        f"Date: 22 November 2026. Model: {MODEL}. {language} only. Thinking tokens: {think}.",
        "",
        (
            f"Real cost from the API usage fields: {pin:,} input tokens and {pout:,} output tokens. "
            f"At $2 and $10 per million, that is ${usd:.6f}. "
            "The measured rate from Lithuanian was $0.087150. "
            f"Cache tokens are in the batch files under data/llm/{RUN_ID}/{code}/."
        ),
        "",
    ]
    if same:
        lines.append("Same as English, on purpose or as a proper noun: " + ", ".join(same) + ".")
        lines.append("")
    week = done.get("week_of", "")
    if week and week != english.get("week_of") and "{year}" in week:
        lines.append(
            "One note: week_of still has {year}, {month}, and {day}. "
            "The page fills them by name, so the week line still works."
        )
        lines.append("")
    for key in english:
        lines.append(f"## {key}")
        lines.append("")
        lines.append("English: " + english[key])
        lines.append("")
        lines.append(f"{language}: " + done[key])
        lines.append("")
    path = ROOT / "docs" / f"i18n-review-{code}.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"review {path}")


def run_language(code: str, language: str, english: dict, spent: float, dry: bool) -> tuple[float, dict, bool]:
    keys = list(english)
    folder = STORE / code
    folder.mkdir(parents=True, exist_ok=True)
    done: dict[str, str] = {}
    rows = []
    batches = [keys[i : i + BATCH] for i in range(0, len(keys), BATCH)]
    print(f"language={code} strings={len(keys)} batches={len(batches)} spent=${spent:.6f}")
    stopped = False
    for index, batch in enumerate(batches, start=1):
        path = folder / f"batch-{index:02d}.json"
        if path.exists() and not dry:
            stored = json.loads(path.read_text(encoding="utf-8"))
            usage = stored.get("usage") or {}
            usd = float(stored.get("usd") or cost(usage))
            spent += usd
            parsed = stored.get("parsed") or {}
            missing = take(batch, english, parsed, done)
            rows.append(
                {
                    "batch": index,
                    "input_tokens": int(usage.get("input_tokens") or 0),
                    "output_tokens": int(usage.get("output_tokens") or 0),
                    "thinking_tokens": thinking_tokens(usage),
                    "usd": usd,
                    "at": stored.get("at") or "",
                }
            )
            retry_path = folder / f"batch-{index:02d}-retry.json"
            if retry_path.exists():
                retry_stored = json.loads(retry_path.read_text(encoding="utf-8"))
                retry_usage = retry_stored.get("usage") or {}
                retry_usd = float(retry_stored.get("usd") or cost(retry_usage))
                spent += retry_usd
                # The retry file does not store accepted values. Re-parse its text.
                try:
                    retry_parsed = parse_json(retry_stored.get("text") or "")
                except Exception:
                    retry_parsed = {}
                missing = take(missing, english, retry_parsed, done)
                rows.append(
                    {
                        "batch": index,
                        "retry": True,
                        "input_tokens": int(retry_usage.get("input_tokens") or 0),
                        "output_tokens": int(retry_usage.get("output_tokens") or 0),
                        "thinking_tokens": thinking_tokens(retry_usage),
                        "usd": retry_usd,
                        "at": "",
                    }
                )
            print(
                f"batch {code}-{index} reused usd={usd:.6f} spent={spent:.6f} missing={len(missing)}"
            )
            if missing and not retry_path.exists():
                print(f"batch {code}-{index} stored incomplete; one retry if the cap allows")
            elif missing:
                print(f"STOP {code}: stored batch {index} is still incomplete")
                stopped = True
                break
            elif spent >= CAP:
                print("STOP: cap reached on a stored batch")
                stopped = True
                break
            else:
                continue
            # Fall through to the retry block only. The first call is already stored.
            user = json.dumps({key: english[key] for key in missing}, ensure_ascii=False)
            retry_fit = room_for(spent, user)
            if retry_fit is None:
                stopped = True
                break
            retry_max, retry_ceiling = retry_fit
            print(
                f"retry {code}-{index} strings={len(missing)} max_tokens={retry_max} "
                f"ceiling=${retry_ceiling:.4f} spent=${spent:.6f}"
            )
            text, usage, stop_reason = call(language, user, retry_max)
            usd = cost(usage)
            spent += usd
            think = thinking_tokens(usage)
            try:
                parsed = parse_json(text)
            except Exception as exc:
                parsed = {}
                print(f"retry {code}-{index} parse failed: {type(exc).__name__}")
            still = take(missing, english, parsed, done)
            (folder / f"batch-{index:02d}-retry.json").write_text(
                json.dumps(
                    {
                        "usage": usage,
                        "usd": usd,
                        "stop_reason": stop_reason,
                        "text": text,
                        "missing": still,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            pin = int(usage.get("input_tokens") or 0)
            pout = int(usage.get("output_tokens") or 0)
            print(
                f"retry {code}-{index} input_tokens={pin} output_tokens={pout} "
                f"thinking_tokens={think} usd={usd:.6f} spent={spent:.6f} still={len(still)}"
            )
            rows.append(
                {
                    "batch": index,
                    "retry": True,
                    "input_tokens": pin,
                    "output_tokens": pout,
                    "thinking_tokens": think,
                    "usd": usd,
                    "at": datetime.now(timezone.utc).isoformat(),
                }
            )
            if think > 0 or still or spent >= CAP:
                print(f"STOP {code}: stored-batch retry did not finish")
                stopped = True
                break
            continue
        payload = {key: english[key] for key in batch}
        user = json.dumps(payload, ensure_ascii=False)
        fit = room_for(spent, user)
        if fit is None:
            stopped = True
            break
        max_tokens, ceiling = fit
        print(
            f"batch {code}-{index} strings={len(batch)} max_tokens={max_tokens} "
            f"ceiling=${ceiling:.4f} spent=${spent:.6f}"
        )
        if dry:
            continue
        text, usage, stop_reason = call(language, user, max_tokens)
        usd = cost(usage)
        spent += usd
        think = thinking_tokens(usage)
        try:
            parsed = parse_json(text)
        except Exception as exc:
            parsed = {}
            print(f"batch {code}-{index} parse failed: {type(exc).__name__}")
        missing = take(batch, english, parsed, done)
        if missing and stop_reason != "max_tokens":
            print(f"batch {code}-{index} rejected={len(missing)}")
        stamp = datetime.now(timezone.utc).isoformat()
        path.write_text(
            json.dumps(
                {
                    "usage": usage,
                    "usd": usd,
                    "stop_reason": stop_reason,
                    "text": text,
                    "parsed": {key: done[key] for key in batch if key in done},
                    "missing": missing,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        pin = int(usage.get("input_tokens") or 0)
        pout = int(usage.get("output_tokens") or 0)
        print(
            f"batch {code}-{index} input_tokens={pin} output_tokens={pout} "
            f"thinking_tokens={think} usd={usd:.6f} spent={spent:.6f}"
        )
        rows.append(
            {
                "batch": index,
                "input_tokens": pin,
                "output_tokens": pout,
                "thinking_tokens": think,
                "usd": usd,
                "at": stamp,
            }
        )
        if think > 0:
            print("STOP: thinking tokens were billed; no thinking was approved")
            stopped = True
            break
        if missing:
            retry_payload = {key: english[key] for key in missing}
            retry_user = json.dumps(retry_payload, ensure_ascii=False)
            retry_fit = room_for(spent, retry_user)
            if retry_fit is None:
                stopped = True
                break
            retry_max, retry_ceiling = retry_fit
            print(
                f"retry {code}-{index} strings={len(missing)} max_tokens={retry_max} "
                f"ceiling=${retry_ceiling:.4f} spent=${spent:.6f}"
            )
            text, usage, stop_reason = call(language, retry_user, retry_max)
            usd = cost(usage)
            spent += usd
            think = thinking_tokens(usage)
            try:
                parsed = parse_json(text)
            except Exception as exc:
                parsed = {}
                print(f"retry {code}-{index} parse failed: {type(exc).__name__}")
            still = take(missing, english, parsed, done)
            (folder / f"batch-{index:02d}-retry.json").write_text(
                json.dumps(
                    {
                        "usage": usage,
                        "usd": usd,
                        "stop_reason": stop_reason,
                        "text": text,
                        "missing": still,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            pin = int(usage.get("input_tokens") or 0)
            pout = int(usage.get("output_tokens") or 0)
            print(
                f"retry {code}-{index} input_tokens={pin} output_tokens={pout} "
                f"thinking_tokens={think} usd={usd:.6f} spent={spent:.6f} still={len(still)}"
            )
            rows.append(
                {
                    "batch": index,
                    "retry": True,
                    "input_tokens": pin,
                    "output_tokens": pout,
                    "thinking_tokens": think,
                    "usd": usd,
                    "at": datetime.now(timezone.utc).isoformat(),
                }
            )
            if think > 0 or still:
                print(f"STOP {code}: retry did not finish batch {index}")
                stopped = True
                break
        if spent >= CAP:
            print("STOP: cap reached after this batch")
            stopped = True
            break
    complete = len(done) == len(keys)
    if complete and not dry:
        out = ROOT / "frontend" / "i18n" / f"{code}.json"
        out.write_text(json.dumps(done, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        # Keep English key order.
        ordered = {key: done[key] for key in keys}
        out.write_text(json.dumps(ordered, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        write_review(code, language, english, ordered, rows)
        print(f"wrote {code} strings={len(ordered)}")
    elif not dry:
        print(f"NOT written {code}: strings_done={len(done)} of {len(keys)}")
    summary = {
        "code": code,
        "language": language,
        "strings_done": len(done),
        "strings_total": len(keys),
        "complete": complete,
        "batches": rows,
    }
    if not dry:
        (folder / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return spent, summary, stopped


def main() -> int:
    dry = "--dry-run" in sys.argv
    english = json.loads(EN_PATH.read_text(encoding="utf-8"))
    expected = MEASURED_PER_LANG * len(LANGS)
    print(
        f"run={RUN_ID} strings={len(english)} languages={len(LANGS)} "
        f"expected=${expected:.6f} cap=${CAP:.2f} dry={dry}"
    )
    if expected > CAP:
        print("STOP before first call: measured estimate is over the cap")
        return 2
    STORE.mkdir(parents=True, exist_ok=True)
    spent = 0.0
    summaries = []
    for code, language in LANGS:
        spent, summary, stopped = run_language(code, language, english, spent, dry)
        summaries.append(summary)
        if stopped:
            break
    result = {
        "run_id": RUN_ID,
        "model": MODEL,
        "thinking": "between_tools",
        "effort": "low",
        "cap_usd": CAP,
        "expected_usd": round(expected, 6),
        "spent_usd": round(spent, 6),
        "languages": summaries,
    }
    if not dry:
        (STORE / "summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
    if dry:
        return 0
    finished = all(row.get("complete") for row in summaries) and len(summaries) == len(LANGS)
    return 0 if finished and spent <= CAP else 2


if __name__ == "__main__":
    sys.exit(main())
