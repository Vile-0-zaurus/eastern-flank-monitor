#!/usr/bin/env python3
"""Provider-agnostic chat client. Switching provider is a config change.

Does not call the API unless complete() is used. Never prints the key.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "llm.yaml"
CACHE = ROOT / "data" / "llm" / "cache.sqlite"
USAGE = ROOT / "data" / "llm" / "usage.log"


def load_config(path: Path = CONFIG) -> dict:
    cfg = {
        "provider": "",
        "model": "",
        "compare_model": "",
        "base_url": "",
        "batch_size": 50,
        "hard_stop_usd": 1.0,
        "models": {},
        "price_per_million": {"input": 0.0, "output": 0.0},
    }
    section = ""
    current = ""
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        key, _, val = line.strip().partition(":")
        key, val = key.strip(), val.strip()
        if indent == 0 and key == "models":
            section = "models"
            continue
        if section == "models" and indent == 2 and not val:
            current = key
            cfg["models"][current] = {"role": "", "input": 0.0, "output": 0.0}
            continue
        if section == "models" and indent >= 4 and current:
            if key in ("input", "output"):
                cfg["models"][current][key] = float(val)
            else:
                cfg["models"][current][key] = val
            continue
        section = ""
        current = ""
        if key == "batch_size":
            cfg[key] = int(val)
        elif key == "hard_stop_usd":
            cfg[key] = float(val)
        else:
            cfg[key] = val
    chosen = cfg["models"].get(cfg["model"])
    if chosen:
        cfg["price_per_million"] = {"input": chosen["input"], "output": chosen["output"]}
    return cfg


def title_hash(title: str) -> str:
    return hashlib.sha256(title.strip().encode("utf-8")).hexdigest()


def estimate_cost(input_tokens: int, output_tokens: int, cfg: dict | None = None, model: str | None = None) -> float:
    cfg = cfg or load_config()
    name = model or cfg["model"]
    prices = cfg["models"].get(name) or cfg["price_per_million"]
    return (input_tokens * prices["input"] + output_tokens * prices["output"]) / 1_000_000


def assert_under_cap(usd: float, cfg: dict | None = None) -> None:
    cfg = cfg or load_config()
    if usd > cfg["hard_stop_usd"]:
        raise SystemExit(f"hard stop: estimated ${usd:.4f} exceeds ${cfg['hard_stop_usd']:.2f}")


def _cache() -> sqlite3.Connection:
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(CACHE)
    con.execute(
        "CREATE TABLE IF NOT EXISTS results (title_hash TEXT PRIMARY KEY, model TEXT, result_json TEXT, created_at TEXT)"
    )
    return con


def cached(title: str, model: str) -> dict | None:
    con = _cache()
    row = con.execute(
        "SELECT result_json FROM results WHERE title_hash=? AND model=?",
        (title_hash(title), model),
    ).fetchone()
    con.close()
    return json.loads(row[0]) if row else None


def store(title: str, model: str, result: dict) -> None:
    con = _cache()
    con.execute(
        "INSERT OR REPLACE INTO results (title_hash, model, result_json, created_at) VALUES (?,?,?,?)",
        (title_hash(title), model, json.dumps(result, ensure_ascii=False), datetime.now(timezone.utc).isoformat()),
    )
    con.commit()
    con.close()


def log_usage(model: str, input_tokens: int, output_tokens: int, usd: float) -> None:
    USAGE.parent.mkdir(parents=True, exist_ok=True)
    line = (
        f"{datetime.now(timezone.utc).isoformat()} model={model} "
        f"input_tokens={input_tokens} output_tokens={output_tokens} usd={usd:.6f}\n"
    )
    with USAGE.open("a", encoding="utf-8") as fh:
        fh.write(line)


def _api_key(name: str) -> str:
    key = os.environ.get(name, "")
    if not key:
        env = ROOT / ".env"
        if env.exists():
            for raw in env.read_text(encoding="utf-8").splitlines():
                if raw.startswith(name + "="):
                    key = raw.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    if not key:
        raise SystemExit(f"{name} is not set")
    return key


def complete(prompt: str, user: str, cfg: dict | None = None, model: str | None = None, extra: dict | None = None, timeout: int = 180) -> tuple[str, int, int]:
    """One chat call. Caller must check estimate_cost and assert_under_cap first."""
    cfg = cfg or load_config()
    if cfg["provider"] != "xai":
        raise SystemExit(f"provider {cfg['provider']} is not implemented")
    body = {
        "model": model or cfg["model"],
        "temperature": 0,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user},
        ],
    }
    if extra:
        body.update(extra)
    req = urllib.request.Request(
        cfg["base_url"].rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {_api_key('XAI_API_KEY')}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    text = payload["choices"][0]["message"]["content"]
    usage = payload.get("usage") or {}
    return text, int(usage.get("prompt_tokens") or 0), int(usage.get("completion_tokens") or 0)


def complete_anthropic(prompt: str, user: str, model: str, max_tokens: int = 8000, timeout: int = 300) -> tuple[str, int, int]:
    """One Anthropic message call. Never prints the key. Raises SystemExit with an error type only."""
    import urllib.error

    body = json.dumps(
        {
            "model": model,
            "max_tokens": max_tokens,
            "system": prompt,
            "messages": [{"role": "user", "content": user}],
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "x-api-key": _api_key("ANTHROPIC_API_KEY"),
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        kind = "http_error"
        try:
            err = json.loads(exc.read().decode("utf-8"))
            kind = str((err.get("error") or {}).get("type") or exc.code)
        except Exception:
            kind = str(exc.code)
        raise SystemExit(f"anthropic {kind}") from None
    parts = payload.get("content") or []
    text = "".join(part.get("text", "") for part in parts if part.get("type") == "text")
    usage = payload.get("usage") or {}
    return text, int(usage.get("input_tokens") or 0), int(usage.get("output_tokens") or 0)
