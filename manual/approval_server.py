#!/usr/bin/env python3
"""Local approval page for backtest manual drafts.

Binds 127.0.0.1:8765 only. No model call. Each button appends one row
to the matching manual/*-approved.csv and flushes it before the page
moves on.
"""

from __future__ import annotations

import csv
import json
import os
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOST = "127.0.0.1"
PORT = 8765
ROOT = Path(__file__).resolve().parent
DECISIONS = ("Approve", "Reject", "Unsure")
FIELDS = [
    "input",
    "date",
    "region",
    "value",
    "note",
    "source_link",
    "source_date",
    "decision",
    "reviewer_note",
    "saved_at",
]

DRAFTS = [
    ("o2", "o2-us-commitment-draft.csv", "o2-us-commitment-approved.csv"),
    ("o1", "o1-ukraine-war-draft.csv", "o1-ukraine-war-approved.csv"),
    ("c2", "c2-force-posture-draft.csv", "c2-force-posture-approved.csv"),
]


def approved_path(name: str) -> Path:
    for key, _draft, approved in DRAFTS:
        if key == name:
            return ROOT / approved
    raise KeyError(name)


def ensure_approved() -> None:
    for _key, _draft, approved in DRAFTS:
        path = ROOT / approved
        if path.exists():
            continue
        with path.open("w", newline="") as handle:
            csv.DictWriter(handle, fieldnames=FIELDS).writeheader()


def load_entries() -> list[dict]:
    entries = []
    for key, draft_name, _approved in DRAFTS:
        path = ROOT / draft_name
        with path.open(newline="") as handle:
            for index, row in enumerate(csv.DictReader(handle)):
                entries.append(
                    {
                        "id": f"{key}:{index}",
                        "input": key,
                        "date": row.get("date", ""),
                        "region": row.get("region", ""),
                        "value": row.get("value", ""),
                        "note": row.get("note", ""),
                        "source_link": row.get("source_link", ""),
                        "source_date": row.get("source_date", ""),
                    }
                )
    return entries


def saved_ids() -> set[str]:
    found = set()
    entries = {item["id"]: item for item in load_entries()}
    by_key = {}
    for item in entries.values():
        by_key.setdefault(
            (item["input"], item["date"], item["region"], item["source_link"]),
            [],
        ).append(item["id"])
    for key, _draft, approved in DRAFTS:
        path = ROOT / approved
        if not path.exists():
            continue
        with path.open(newline="") as handle:
            for row in csv.DictReader(handle):
                match = (
                    row.get("input", ""),
                    row.get("date", ""),
                    row.get("region", ""),
                    row.get("source_link", ""),
                )
                for entry_id in by_key.get(match, []):
                    if entries[entry_id]["input"] == key:
                        found.add(entry_id)
    return found


def append_decision(entry: dict, decision: str, reviewer_note: str) -> None:
    path = approved_path(entry["input"])
    ensure_approved()
    row = {
        "input": entry["input"],
        "date": entry["date"],
        "region": entry["region"],
        "value": entry["value"],
        "note": entry["note"],
        "source_link": entry["source_link"],
        "source_date": entry["source_date"],
        "decision": decision,
        "reviewer_note": reviewer_note,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
    }
    with path.open("a", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writerow(row)
        handle.flush()
        os.fsync(handle.fileno())


PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Backtest manual approval</title>
<style>
body { font-family: sans-serif; max-width: 42rem; margin: 2rem auto; line-height: 1.4; }
button { font-size: 1rem; margin-right: 0.5rem; padding: 0.4rem 0.8rem; }
textarea { width: 100%; min-height: 4rem; }
a { word-break: break-all; }
.muted { color: #444; }
#status { min-height: 1.2rem; }
</style>
</head>
<body>
<p id="progress">0 / 0</p>
<h1 id="title"></h1>
<p id="value"></p>
<p id="note"></p>
<p>Source date: <span id="source-date"></span></p>
<p id="link"></p>
<label>Optional note<br><textarea id="reviewer"></textarea></label>
<p>
<button id="approve" type="button">Approve</button>
<button id="reject" type="button">Reject</button>
<button id="unsure" type="button">Unsure</button>
</p>
<p id="status" class="muted"></p>
<p><button id="prev" type="button">Previous</button> <button id="next" type="button">Next</button></p>
<script>
let entries = [];
let saved = [];
let index = 0;

function unsavedIndex() {
  const ids = new Set(saved);
  const found = entries.findIndex((item) => !ids.has(item.id));
  return found === -1 ? 0 : found;
}

function show() {
  const item = entries[index];
  document.getElementById("progress").textContent = saved.length + " / " + entries.length;
  if (!item) {
    document.getElementById("title").textContent = "No drafts.";
    return;
  }
  const region = item.region ? " / " + item.region : "";
  document.getElementById("title").textContent = item.input.toUpperCase() + " " + item.date + region;
  document.getElementById("value").textContent = item.value === "" ? "Value: no data. Not calm, and not zero." : "Value: " + item.value;
  document.getElementById("note").textContent = item.note;
  document.getElementById("source-date").textContent = item.source_date || "none";
  const link = document.getElementById("link");
  link.replaceChildren();
  if (item.source_link) {
    const anchor = document.createElement("a");
    anchor.href = item.source_link;
    anchor.target = "_blank";
    anchor.rel = "noopener";
    anchor.textContent = item.source_link;
    link.appendChild(anchor);
  } else {
    link.textContent = "No source link.";
  }
  document.getElementById("reviewer").value = "";
  document.getElementById("status").textContent = saved.includes(item.id) ? "Already saved. A new click appends another row." : "";
}

async function load() {
  const response = await fetch("/api/queue");
  const data = await response.json();
  entries = data.entries;
  saved = data.saved;
  index = unsavedIndex();
  show();
}

async function save(decision) {
  const item = entries[index];
  document.getElementById("status").textContent = "Saving...";
  const response = await fetch("/api/save", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      id: item.id,
      decision: decision,
      reviewer_note: document.getElementById("reviewer").value
    })
  });
  if (!response.ok) {
    document.getElementById("status").textContent = "Not saved.";
    return;
  }
  const data = await response.json();
  saved = data.saved;
  document.getElementById("status").textContent = "Saved.";
  const next = entries.findIndex((row, i) => i > index && !saved.includes(row.id));
  index = next === -1 ? unsavedIndex() : next;
  show();
}

document.getElementById("approve").onclick = () => save("Approve");
document.getElementById("reject").onclick = () => save("Reject");
document.getElementById("unsure").onclick = () => save("Unsure");
document.getElementById("prev").onclick = () => { if (index > 0) { index -= 1; show(); } };
document.getElementById("next").onclick = () => { if (index + 1 < entries.length) { index += 1; show(); } };
load();
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/":
            body = PAGE.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/api/queue":
            entries = load_entries()
            saved = sorted(saved_ids())
            body = json.dumps({"entries": entries, "saved": saved}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(404)

    def do_POST(self) -> None:
        if self.path != "/api/save":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        if length > 4000:
            self.send_error(400)
            return
        try:
            payload = json.loads(self.rfile.read(length).decode())
        except json.JSONDecodeError:
            self.send_error(400)
            return
        decision = payload.get("decision")
        note = str(payload.get("reviewer_note") or "")[:500]
        entry = next((item for item in load_entries() if item["id"] == payload.get("id")), None)
        if decision not in DECISIONS or entry is None:
            self.send_error(400)
            return
        append_decision(entry, decision, note)
        body = json.dumps({"ok": True, "saved": sorted(saved_ids())}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:
        return


def main() -> None:
    ensure_approved()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Approval page: http://{HOST}:{PORT}/")
    server.serve_forever()


if __name__ == "__main__":
    main()
