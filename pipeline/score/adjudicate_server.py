#!/usr/bin/env python3
"""Adjudication page. Writes gold-b2-adjudicated.csv only. Never the tagged audit."""
from __future__ import annotations

import csv
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "frontend" / "adjudicate" / "index.html"
OUT = ROOT / "validation" / "gold-b2-adjudicated.csv"
FROZEN = {
    (ROOT / "validation" / "gold.csv").resolve(),
    (ROOT / "validation" / "gold-b2-audit.csv").resolve(),
    (ROOT / "validation" / "gold-b2-candidates.csv").resolve(),
}
HOST = "127.0.0.1"
PORT = 8766
FIELDS = [
    "id",
    "title",
    "title_en",
    "my_label",
    "opus_label",
    "opus_reason",
    "sonnet_label",
    "sonnet_reason",
    "rule",
    "decision",
    "note",
]
SAVE_KEYS = ("decision", "note")


def target_path() -> Path:
    return OUT


def read_rows(path: Path | None = None) -> list[dict]:
    path = target_path() if path is None else path
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def write_rows(rows: list[dict], path: Path | None = None) -> None:
    path = target_path() if path is None else path
    if path.resolve() in FROZEN:
        raise SystemExit(f"refusing to write frozen file {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in FIELDS})


def apply_save(rows: list[dict], payload: dict) -> bool:
    found = False
    for row in rows:
        if str(row.get("id")) != str(payload.get("id")):
            continue
        for key in SAVE_KEYS:
            if key in payload:
                row[key] = "" if payload[key] is None else str(payload[key])
        found = True
        break
    return found


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        return

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            self._send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
            return
        if self.path == "/api/items":
            items = [{key: row.get(key, "") for key in FIELDS} for row in read_rows()]
            self._send(200, json.dumps(items, ensure_ascii=False).encode("utf-8"), "application/json")
            return
        self._send(404, b"not found", "text/plain")

    def do_POST(self) -> None:
        if self.path != "/api/save":
            self._send(404, b"not found", "text/plain")
            return
        if target_path().resolve() in FROZEN:
            self._send(403, b"frozen", "text/plain")
            return
        n = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(n).decode("utf-8"))
        rows = read_rows()
        if not apply_save(rows, payload):
            self._send(404, b"unknown id", "text/plain")
            return
        write_rows(rows)
        self._send(200, b'{"ok":true}', "application/json")


def main() -> None:
    if target_path().resolve() in FROZEN:
        raise SystemExit("refusing to serve a frozen gold file")
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"open http://{HOST}:{PORT}/")
    print(f"writes {target_path()}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
