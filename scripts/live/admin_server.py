#!/usr/bin/env python3
"""Local admin server. Binds to 127.0.0.1 only. Never deployed."""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "live"))
from drafts import decide, published_incidents  # noqa: E402

DRAFTS = ROOT / "data" / "live" / "drafts.json"
INCIDENTS = ROOT / "data" / "live" / "incidents.json"
PAGE = ROOT / "frontend" / "admin" / "index.html"


def load(path: Path) -> list:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, rows: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")


def apply(body: dict) -> dict:
    rows = load(DRAFTS)
    found = next((row for row in rows if row.get("id") == body.get("id")), None)
    if not found:
        raise ValueError("draft not found")
    decided = decide(found, body.get("action") or "", body.get("note") or "")
    rows = [decided if row.get("id") == decided["id"] else row for row in rows]
    save(DRAFTS, rows)
    if decided["status"] in ("approved", "reported"):
        published = load(INCIDENTS)
        published = [row for row in published if row.get("id") != decided["id"]]
        published.append(decided)
        save(INCIDENTS, published)
    return {"ok": True, "published": len(published_incidents(load(INCIDENTS)))}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes, kind: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/drafts":
            self._send(200, json.dumps(load(DRAFTS)).encode("utf-8"), "application/json")
            return
        self._send(200, PAGE.read_bytes(), "text/html; charset=utf-8")

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/decide":
            self._send(404, b"not found", "text/plain")
            return
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length).decode("utf-8"))
        try:
            result = apply(body)
        except ValueError as err:
            self._send(400, str(err).encode("utf-8"), "text/plain")
            return
        self._send(200, json.dumps(result).encode("utf-8"), "application/json")

    def log_message(self, fmt: str, *args) -> None:
        return


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 8765), Handler)
    print("admin on http://127.0.0.1:8765")
    server.serve_forever()


if __name__ == "__main__":
    main()
