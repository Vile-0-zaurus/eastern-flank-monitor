#!/usr/bin/env python3
"""Local labeling page. Binds to 127.0.0.1 only. Does not call a model."""
from __future__ import annotations

import csv
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "frontend" / "label" / "index.html"
GOLD = ROOT / "data" / "validation" / "gold.csv"
HOST = "127.0.0.1"
PORT = 8765
FIELDS = ["id", "bucket", "domain", "title", "title_en", "url", "relevant", "f1", "f2", "f3", "f4", "f5", "f6", "notes"]


def read_rows() -> list[dict]:
    if not GOLD.exists():
        raise SystemExit(f"missing {GOLD}; run pipeline/score/build_gold.py")
    with GOLD.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def write_rows(rows: list[dict]) -> None:
    GOLD.parent.mkdir(parents=True, exist_ok=True)
    with GOLD.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, FIELDS, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in FIELDS})


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
            # bucket is a sampling note, not a label. The page must not render it.
            items = [{k: r.get(k, "") for k in FIELDS if k != "bucket"} for r in read_rows()]
            self._send(200, json.dumps(items, ensure_ascii=False).encode("utf-8"), "application/json")
            return
        self._send(404, b"not found", "text/plain")

    def do_POST(self) -> None:
        if self.path != "/api/save":
            self._send(404, b"not found", "text/plain")
            return
        n = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(n).decode("utf-8"))
        rows = read_rows()
        found = False
        for row in rows:
            if str(row["id"]) != str(payload.get("id")):
                continue
            for key in ("relevant", "f1", "f2", "f3", "f4", "f5", "f6", "notes"):
                if key in payload:
                    row[key] = "" if payload[key] is None else str(payload[key])
            found = True
            break
        if not found:
            self._send(404, b"unknown id", "text/plain")
            return
        write_rows(rows)
        self._send(200, b"{\"ok\":true}", "application/json")


def main() -> None:
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"open http://{HOST}:{PORT}/")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
