#!/usr/bin/env python3
"""Local labeling page for a later gold batch. Never writes validation/gold.csv."""
from __future__ import annotations

import csv
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "frontend" / "label" / "index.html"
FROZEN = ROOT / "validation" / "gold.csv"
GOLD = ROOT / "validation" / "gold-batch2.csv"
HOST = "127.0.0.1"
PORT = 8765
FIELDS = [
    "id",
    "domain",
    "date",
    "title",
    "title_en",
    "url",
    "v3",
    "f1",
    "f2",
    "f3",
    "f4",
    "f5",
    "f6",
    "f7",
    "notes",
]
LABEL_KEYS = ("v3", "f1", "f2", "f3", "f4", "f5", "f6", "f7", "notes")


def read_rows(path: Path | None = None) -> list[dict]:
    path = GOLD if path is None else path
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def write_rows(rows: list[dict], path: Path | None = None) -> None:
    path = GOLD if path is None else path
    if path.resolve() == FROZEN.resolve():
        raise SystemExit("refusing to write frozen validation/gold.csv")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, FIELDS, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in FIELDS})


def apply_save(rows: list[dict], payload: dict) -> bool:
    found = False
    for row in rows:
        if str(row.get("id")) != str(payload.get("id")):
            continue
        for key in LABEL_KEYS:
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
            items = [{k: r.get(k, "") for k in FIELDS} for r in read_rows()]
            self._send(200, json.dumps(items, ensure_ascii=False).encode("utf-8"), "application/json")
            return
        self._send(404, b"not found", "text/plain")

    def do_POST(self) -> None:
        if self.path != "/api/save":
            self._send(404, b"not found", "text/plain")
            return
        if GOLD.resolve() == FROZEN.resolve():
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
    global GOLD
    if len(sys.argv) == 3 and sys.argv[1] == "--gold":
        GOLD = Path(sys.argv[2])
        if GOLD.resolve() == FROZEN.resolve():
            raise SystemExit("refusing to open frozen validation/gold.csv for labeling")
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"open http://{HOST}:{PORT}/")
    print(f"writes {GOLD}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
