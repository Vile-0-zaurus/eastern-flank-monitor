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
        "base_url": "",
        "batch_size": 50,
        "price_per_million": {"input": 0.0, "output": 0.0},
        "hard_stop_usd": 1.0,
    }
    section = ""
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if line.strip() == "price_per_million:":
            section = "price"
            continue
        key, _, val = line.strip().partition(":")
        val = val.strip()
        if section == "price" and raw.startswith(" "):
            cfg["price_per_million"][key] = float(val)
            continue
        section = ""
        if key == "batch_size":
            cfg[key] = int(val)
        elif key == "hard_stop_usd":
            cfg[key] = float(val)
        else:
            cfg[key] = val
    return cfg


def title_hash(title: str) -> str:
    return hashlib.sha256(title.strip().encode("utf-8")).hexdigest()


def estimate_cost(input_tokens: int, output_tokens: int, cfg: dict | None = None) -> float:
    cfg = cfg or load_config()
    prices = cfg["price_per_million"]
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


def _api_key() -> str:
    key = os.environ.get("XAI_API_KEY", "")
    if not key:
        env = ROOT / ".env"
        if env.exists():
            for raw in env.read_text(encoding="utf-8").splitlines():
                if raw.startswith("XAI_API_KEY="):
                    key = raw.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    if not key:
        raise SystemExit("XAI_API_KEY is not set")
    return key


def complete(prompt: str, user: str, cfg: dict | None = None) -> tuple[str, int, int]:
    """One chat call. Caller must check estimate_cost and assert_under_cap first."""
    cfg = cfg or load_config()
    if cfg["provider"] != "xai":
        raise SystemExit(f"provider {cfg['provider']} is not implemented")
    body = json.dumps(
        {
            "model": cfg["model"],
            "temperature": 0,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": user},
            ],
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        cfg["base_url"].rstrip("/") + "/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {_api_key()}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    text = payload["choices"][0]["message"]["content"]
    usage = payload.get("usage") or {}
    return text, int(usage.get("prompt_tokens") or 0), int(usage.get("completion_tokens") or 0)
