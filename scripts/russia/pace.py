#!/usr/bin/env python3
"""Paced research fetch. Research user-agent only. No spoofing, no proxy."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data/russia-probes"
UA = "eastern-flank-monitor/0.1 (local research; source probe; 1 req/s)"
LAST: dict[str, float] = {}


def host_of(url: str) -> str:
    return urllib.parse.urlparse(url).netloc.lower()


def wait(url: str, pause: float) -> None:
    host = host_of(url)
    elapsed = time.monotonic() - LAST.get(host, 0.0)
    if elapsed < pause:
        time.sleep(pause - elapsed)
    LAST[host] = time.monotonic()


def get(url: str, pause: float = 1.0, timeout: int = 25) -> dict:
    wait(url, pause)
    request = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read(1_500_000)
            return {
                "url": url,
                "final_url": response.geturl(),
                "status": response.status,
                "content_type": response.headers.get("Content-Type", ""),
                "bytes": len(body),
                "elapsed_s": round(time.monotonic() - started, 2),
                "body": body,
                "error": "",
            }
    except urllib.error.HTTPError as exc:
        body = exc.read(200_000)
        return {
            "url": url,
            "final_url": exc.geturl(),
            "status": exc.code,
            "content_type": exc.headers.get("Content-Type", "") if exc.headers else "",
            "bytes": len(body),
            "elapsed_s": round(time.monotonic() - started, 2),
            "body": body,
            "error": "",
        }
    except Exception as exc:
        return {
            "url": url,
            "final_url": "",
            "status": 0,
            "content_type": "",
            "bytes": 0,
            "elapsed_s": round(time.monotonic() - started, 2),
            "body": b"",
            "error": type(exc).__name__ + ": " + str(exc)[:240],
        }


def save(name: str, record: dict) -> Path:
    RAW.mkdir(parents=True, exist_ok=True)
    path = RAW / name
    body = record.pop("body", b"")
    text_path = RAW / (Path(name).stem + ".body")
    if body:
        text_path.write_bytes(body[:1_500_000])
        record["body_file"] = str(text_path)
    else:
        record["body_file"] = ""
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
