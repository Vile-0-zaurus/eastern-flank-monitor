#!/usr/bin/env python3
"""Headless UI self-test. No API calls.

Re-run from anywhere:

    python3 tests/ui_selftest.py
"""

from __future__ import annotations

import asyncio
import csv
import json
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import websockets

ROOT = Path(__file__).resolve().parents[1]
WEEKS = ROOT / "docs" / "reports" / "2026-10-12-backtest-weeks.csv"
INTENT = ROOT / "docs" / "reports" / "2026-10-11-i2-weeks.csv"
EVENTS = ROOT / "frontend" / "events.json"
MANUAL = ROOT / "manual" / "c2-force-posture-approved.csv"
CHROME = os.environ.get("CHROME", "/usr/bin/google-chrome")
START = "2021-01-04"
MONTHS = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)
LEVELS = ["Calm", "Watchful", "Elevated", "Serious", "Critical"]
LAYERS = {
    "Signals of intent": "intent",
    "Military readiness": "capability",
    "Window of opportunity": "opportunity",
    "Grey-zone activity": "hybrid",
}
BASE = {
    "eastern_flank": {"i1": 0.0086, "i2": 0.12},
    "ukraine_test": {"i1": 0.0271, "i2": 0.29},
}


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        return


def start_server(port: int) -> None:
    os.chdir(ROOT)
    httpd = ThreadingHTTPServer(("127.0.0.1", port), QuietHandler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()


def week_label(iso: str) -> str:
    year, month, day = (int(part) for part in iso.split("-"))
    return f"Week of {day} {MONTHS[month - 1]} {year}"


def expected_badge(row: dict) -> str:
    if "proposed" in row["shown_label"]:
        return "Elevated. Serious is proposed, not confirmed."
    if row["shown"] == "":
        return "No data"
    return LEVELS[int(float(row["shown"]))]


def load_weeks() -> dict[str, list[dict]]:
    found: dict[str, list[dict]] = {}
    with WEEKS.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["week"] >= START:
                found.setdefault(row["region"], []).append(row)
    return found


def load_intent() -> dict[tuple[str, str], dict]:
    found = {}
    with INTENT.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            found[(row["region"], row["week"])] = row
    return found


def manual_notes() -> dict[tuple[str, str], str]:
    found = {}
    with MANUAL.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            found[(row["date"], row["region"])] = row["note"]
    return found


class Cdp:
    def __init__(self, ws):
        self.ws = ws
        self.next_id = 1
        self.pending: dict[int, asyncio.Future] = {}
        self.console: list[str] = []
        self.reader: asyncio.Task | None = None

    async def start(self) -> None:
        self.reader = asyncio.create_task(self._read())

    async def _read(self) -> None:
        async for raw in self.ws:
            msg = json.loads(raw)
            if "id" in msg and msg["id"] in self.pending:
                fut = self.pending.pop(msg["id"])
                if "error" in msg:
                    fut.set_exception(RuntimeError(str(msg["error"])))
                else:
                    fut.set_result(msg.get("result", {}))
                continue
            method = msg.get("method", "")
            params = msg.get("params", {})
            if method == "Runtime.exceptionThrown":
                text = params.get("exceptionDetails", {}).get("text", "exception")
                self.console.append(text)
            elif method == "Runtime.consoleAPICalled" and params.get("type") == "error":
                bits = [str(arg.get("value", arg.get("description", ""))) for arg in params.get("args", [])]
                self.console.append("console: " + " ".join(bits))

    async def call(self, method: str, **params):
        call_id = self.next_id
        self.next_id += 1
        fut = asyncio.get_running_loop().create_future()
        self.pending[call_id] = fut
        await self.ws.send(json.dumps({"id": call_id, "method": method, "params": params}))
        return await fut

    async def js(self, expression: str):
        result = await self.call(
            "Runtime.evaluate",
            expression=expression,
            returnByValue=True,
            awaitPromise=True,
        )
        details = result.get("exceptionDetails")
        if details:
            raise RuntimeError(details.get("text", "js error"))
        return result.get("result", {}).get("value")


SWEEP = r"""
(() => {
  const bad = [];
  const shown = [];
  const slider = document.getElementById('slider');
  const region = document.getElementById('region');
  const depths = [...document.querySelectorAll('[data-depth]')];
  function textOf(id) {
    const node = document.getElementById(id);
    return node ? node.textContent.replace(/\s+/g, ' ').trim() : '';
  }
  function check(tag) {
    const text = document.body.innerText;
    if (text.includes('undefined')) bad.push(tag + ' contains undefined');
    if (text.includes('NaN')) bad.push(tag + ' contains NaN');
    if (document.documentElement.scrollWidth > document.documentElement.clientWidth + 8) {
      bad.push(tag + ' overflows');
    }
  }
  for (const option of [...region.options]) {
    region.value = option.value;
    region.dispatchEvent(new Event('change', {bubbles: true}));
    const max = Number(slider.max);
    for (let i = 0; i <= max; i++) {
      slider.value = String(i);
      slider.dispatchEvent(new Event('input', {bubbles: true}));
      document.querySelector('[data-depth="1"]').click();
      const label = textOf('week-label');
      if (!/^Week of \d{1,2} [A-Z][a-z]+ \d{4}$/.test(label)) bad.push(option.value + ' i' + i + ' bad date ' + label);
      if (!textOf('level-badge')) bad.push(option.value + ' i' + i + ' empty badge');
      if (!textOf('why-level')) bad.push(option.value + ' i' + i + ' empty why');
      if (!textOf('versus-normal')) bad.push(option.value + ' i' + i + ' empty versus');
      if (!textOf('headlines')) bad.push(option.value + ' i' + i + ' empty headlines');
      const cards = [...document.querySelectorAll('.card')].map((card) => ({
        title: card.querySelector('h3').textContent.trim(),
        trend: card.querySelector('.arrow') ? card.querySelector('.arrow').className : ''
      }));
      document.querySelector('[data-depth="2"]').click();
      const layerCards = [...document.querySelectorAll('.card')].map((card) => ({
        title: card.querySelector('h3').textContent.trim(),
        trend: card.querySelector('.arrow') ? card.querySelector('.arrow').className : ''
      }));
      shown.push({
        region: option.value,
        i,
        week: label,
        badge: textOf('level-badge'),
        why: textOf('why-level'),
        versus: textOf('versus-normal'),
        headlines: textOf('headlines'),
        events: textOf('week-events'),
        links: [...document.querySelectorAll('#week-events a')].map((link) => link.href),
        cards: layerCards
      });
      for (const depth of depths) {
        depth.click();
        check(option.value + ' i' + i + ' d' + depth.dataset.depth);
      }
    }
  }
  return {bad, shown};
})()
"""


def compare_rows(shown: list[dict], weeks: dict[str, list[dict]], intent: dict, events: list[dict], notes: dict) -> list[str]:
    problems = []
    by_region: dict[str, list[dict]] = {}
    for row in shown:
        by_region.setdefault(row["region"], []).append(row)
    for region, rows in weeks.items():
        got_rows = by_region.get(region, [])
        if len(got_rows) != len(rows):
            problems.append(f"{region} showed {len(got_rows)} weeks, file has {len(rows)}")
            continue
        for index, (src, got) in enumerate(zip(rows, got_rows)):
            label = week_label(src["week"])
            if got["week"] != label:
                problems.append(f"{region} {src['week']} date shows {got['week']!r}")
            badge = expected_badge(src)
            if got["badge"] != badge:
                problems.append(f"{region} {src['week']} level shows {got['badge']!r}, file says {badge!r}")
            if "proposed" in src["shown_label"] and "proposed" not in got["why"]:
                problems.append(f"{region} {src['week']} why sentence misses the proposal")
            if "because" not in got["why"] and "not enough data" not in got["why"]:
                problems.append(f"{region} {src['week']} why sentence does not explain the level")
            extra = intent.get((region, src["week"]), {})
            hostile = extra.get("value", "")
            if hostile == "":
                if "Hostile tone is not available." not in got["versus"]:
                    problems.append(f"{region} {src['week']} missing hostile unavailable line")
            else:
                pct = str(int(float(hostile) * 100 + 0.5))
                normal = str(round(BASE[region]["i2"] * 100))
                expected = f"Hostile tone: {pct}% of headlines (usual about {normal}%)."
                if expected not in got["versus"]:
                    problems.append(f"{region} {src['week']} hostile line shows {got['versus']!r}")
            share = extra.get("i1", "")
            if share == "":
                if "Attention this week is not available." not in got["versus"]:
                    problems.append(f"{region} {src['week']} missing attention unavailable line")
            else:
                ratio = float(share) / BASE[region]["i1"]
                if ratio >= 1.25 and "the usual amount" not in got["versus"]:
                    problems.append(f"{region} {src['week']} attention ratio {ratio:.2f} not described")
                if ratio <= 0.8 and "less about the region" not in got["versus"]:
                    problems.append(f"{region} {src['week']} low attention not described")
            if "No hostile headlines in the sample." not in got["headlines"] and "English:" not in got["headlines"]:
                problems.append(f"{region} {src['week']} headlines have no English line")
            if "Original:" in got["headlines"] and "English:" not in got["headlines"]:
                problems.append(f"{region} {src['week']} original without English")
            expected_events = [
                event for event in events
                if event["date"] == src["week"] and region in event["regions"]
            ]
            if not expected_events:
                if "No events reported in our sources." not in got["events"]:
                    problems.append(f"{region} {src['week']} empty week does not say no events")
            else:
                for event in expected_events:
                    if event["note"] not in got["events"]:
                        problems.append(f"{region} {src['week']} missing note for {event['tag']}")
                    if event["source"] not in got["links"]:
                        problems.append(f"{region} {src['week']} missing source link for {event['tag']}")
                    manual = notes.get((event["date"], event["tag"]))
                    if manual != event["note"]:
                        problems.append(f"events.json note drifted for {event['date']} {event['tag']}")
            previous = rows[index - 1] if index else None
            for card in got["cards"]:
                key = LAYERS.get(card["title"])
                if not key:
                    problems.append(f"{region} {src['week']} unknown card {card['title']}")
                    continue
                now = src[key]
                before = previous[key] if previous else ""
                if now == "" or before == "":
                    expect = ""
                else:
                    left, right = int(float(now)), int(float(before))
                    expect = "up" if left > right else "down" if left < right else "same"
                got_kind = ""
                if "arrow up" in card["trend"]:
                    got_kind = "up"
                elif "arrow down" in card["trend"]:
                    got_kind = "down"
                elif "arrow same" in card["trend"]:
                    got_kind = "same"
                if expect != got_kind:
                    problems.append(f"{region} {src['week']} {key} trend {got_kind!r}, file says {expect!r}")
    return problems


async def run() -> int:
    weeks = load_weeks()
    intent = load_intent()
    events = json.loads(EVENTS.read_text(encoding="utf-8"))
    notes = manual_notes()
    port = free_port()
    start_server(port)
    debug = free_port()
    profile = Path("/tmp/efm-ui-selftest")
    profile.mkdir(exist_ok=True)
    chrome = subprocess.Popen(
        [
            CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
            "--disable-dev-shm-usage", f"--remote-debugging-port={debug}",
            f"--user-data-dir={profile}", "--window-size=1280,900", "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    problems: list[str] = []
    try:
        version_url = f"http://127.0.0.1:{debug}/json/version"
        for _ in range(50):
            try:
                urllib.request.urlopen(version_url, timeout=1).read()
                break
            except Exception:
                time.sleep(0.1)
        else:
            print("Chrome did not open a debug port.")
            return 1
        page_url = f"http://127.0.0.1:{port}/frontend/"
        request = urllib.request.Request(f"http://127.0.0.1:{debug}/json/new?{page_url}", method="PUT")
        with urllib.request.urlopen(request, timeout=5) as response:
            target = json.loads(response.read().decode())
        async with websockets.connect(target["webSocketDebuggerUrl"], max_size=20_000_000) as ws:
            cdp = Cdp(ws)
            await cdp.start()
            await cdp.call("Runtime.enable")
            for _ in range(40):
                ready = await cdp.js("!!document.getElementById('slider') && document.getElementById('slider').max !== ''")
                if ready:
                    break
                await asyncio.sleep(0.15)
            else:
                print("Page did not finish loading.")
                return 1
            result = await cdp.js(SWEEP)
            problems.extend(result["bad"])
            problems.extend(compare_rows(result["shown"], weeks, intent, events, notes))
            await cdp.js("document.getElementById('region').value = 'eastern_flank'; document.getElementById('region').dispatchEvent(new Event('change', {bubbles:true}))")
            await cdp.js("document.getElementById('slider').value = '10'; document.getElementById('slider').dispatchEvent(new Event('input', {bubbles:true}))")
            before = await cdp.js("document.getElementById('week-label').textContent")
            await cdp.js("document.getElementById('play').click()")
            await asyncio.sleep(1.4)
            during = await cdp.js("document.getElementById('week-label').textContent")
            if during == before:
                problems.append("play did not advance the week")
            await cdp.js("document.getElementById('pause').click()")
            paused = await cdp.js("document.getElementById('week-label').textContent")
            await asyncio.sleep(1.4)
            after = await cdp.js("document.getElementById('week-label').textContent")
            if after != paused:
                problems.append("pause did not stop the replay")
            await cdp.js("const slider = document.getElementById('slider'); slider.value = '20'; slider.dispatchEvent(new Event('input', {bubbles:true}));")
            moved = await cdp.js("document.getElementById('week-label').textContent")
            if moved != week_label(weeks["eastern_flank"][20]["week"]):
                problems.append(f"slider did not move to week 20, got {moved!r}")
            await cdp.js("document.getElementById('compare-toggle').click()")
            compare = await cdp.js("document.getElementById('compare').innerText")
            if "Eastern flank" not in compare or "Ukraine test" not in compare:
                problems.append("compare view does not show both regions")
            if "because" not in compare and "not enough data" not in compare:
                problems.append("compare view has no reason line")
            if "undefined" in compare or "NaN" in compare:
                problems.append("compare view contains undefined or NaN")
            await cdp.call("Emulation.setDeviceMetricsOverride", width=390, height=800, deviceScaleFactor=1, mobile=True)
            narrow = await cdp.js(
                "document.documentElement.scrollWidth > document.documentElement.clientWidth + 8"
            )
            if narrow:
                problems.append("narrow compare view overflows")
            await cdp.js("document.getElementById('compare-toggle').click(); document.querySelector('[data-depth=\"1\"]').click()")
            narrow_summary = await cdp.js(
                "document.documentElement.scrollWidth > document.documentElement.clientWidth + 8"
            )
            if narrow_summary:
                problems.append("narrow summary overflows")
            problems.extend(f"browser: {line}" for line in cdp.console)
    finally:
        chrome.terminate()
        try:
            chrome.wait(timeout=5)
        except subprocess.TimeoutExpired:
            chrome.kill()
    if problems:
        print(f"FAIL {len(problems)}")
        for line in problems[:40]:
            print(line)
        if len(problems) > 40:
            print(f"... {len(problems) - 40} more")
        return 1
    print("PASS every week, both regions, all tabs, play, pause, slider, compare")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))
