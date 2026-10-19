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
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
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


MAIN_SWEEP = r"""
(() => {
  const bad = [];
  const shown = [];
  const slider = document.getElementById('slider');
  const allowedSigns = new Set(['Normal', 'Tense', 'Danger signs, unconfirmed', 'No data']);
  const raw = /\b(FI|EE|LV|LT|PL|UA|BY|RU|KG|eastern_flank|ukraine_test)\b/;
  function textOf(id) {
    const node = document.getElementById(id);
    return node ? node.textContent.replace(/\s+/g, ' ').trim() : '';
  }
  function chromeText() {
    const bits = [textOf('week-label'), textOf('map-title'), textOf('news-title')];
    document.querySelectorAll('.country-card, .map-label').forEach((node) => bits.push(node.textContent));
    return bits.join(' ');
  }
  const max = Number(slider.max);
  for (let i = 0; i <= max; i += 1) {
    slider.value = String(i);
    slider.dispatchEvent(new Event('input', {bubbles: true}));
    const label = textOf('week-label');
    if (!/^Week of \d{1,2} [A-Z][a-z]+ \d{4}$/.test(label)) bad.push('main week ' + i + ' bad date ' + label);
    const face = chromeText();
    if (face.includes('undefined')) bad.push('main week ' + i + ' contains undefined');
    if (face.includes('NaN')) bad.push('main week ' + i + ' contains NaN');
    const code = face.match(raw);
    if (code) bad.push('main week ' + i + ' raw code ' + code[0]);
    if (document.documentElement.scrollWidth > document.documentElement.clientWidth + 8) {
      bad.push('main week ' + i + ' overflows');
    }
    const signs = [...document.querySelectorAll('.sign')].map((node) => node.textContent.trim());
    if (signs.length !== 5) bad.push('main week ' + i + ' sign count ' + signs.length);
    signs.forEach((sign) => {
      if (!allowedSigns.has(sign)) bad.push('main week ' + i + ' bad sign ' + sign);
    });
    const names = [...document.querySelectorAll('.country-name')].map((node) => node.textContent.trim());
    if (names.join('|') !== 'Finland|Estonia|Latvia|Lithuania|Poland|Russia') {
      bad.push('main week ' + i + ' names ' + names.join(','));
    }
    const dots = [...document.querySelectorAll('.event-dot')].map((dot) => ({
      place: dot.getAttribute('data-place'),
      date: dot.getAttribute('data-date'),
      cx: dot.getAttribute('cx'),
      cy: dot.getAttribute('cy'),
    }));
    dots.forEach((dot) => {
      if (!dot.place || !dot.date || dot.cx === 'NaN' || dot.cy === 'NaN') {
        bad.push('main week ' + i + ' bad dot');
      }
    });
    [...document.querySelectorAll('a')].forEach((link) => {
      const href = link.getAttribute('href') || '';
      if (!href || href === '#' || href.includes('undefined') || href.includes('NaN') || !/^https?:\/\//.test(href)) {
        if (link.id === 'how-link') return;
        bad.push('main week ' + i + ' bad link ' + href);
      }
    });
    document.getElementById('country-PL').click();
    const polandWhy = document.getElementById('why').innerText;
    if (polandWhy.includes('undefined') || polandWhy.includes('NaN')) bad.push('main week ' + i + ' poland why bad');
    const polandLinks = [...document.querySelectorAll('#why-official a, #why-events a, #why-media a')].map((link) => link.href);
    document.querySelector('[data-country="UA"]').dispatchEvent(new MouseEvent('click', {bubbles: true}));
    const ukraineLinks = [...document.querySelectorAll('#why-official a')].map((link) => link.href);
    document.getElementById('why-close').click();
    shown.push({i, week: label, dots, polandLinks, ukraineLinks, sign: signs[0] || ''});
  }
  return {
    bad,
    shown,
    lands: [...document.querySelectorAll('.land')].map((path) => path.getAttribute('data-country')),
  };
})()
"""


def utc_ms(iso: str) -> float:
    year, month, day = (int(part) for part in iso.split("-"))
    return datetime(year, month, day, tzinfo=timezone.utc).timestamp() * 1000


def active_dots(events: list[dict], week: str) -> list[tuple[str, str]]:
    found = []
    for event in events:
        places = event.get("places") or []
        if not places or event["date"] > week:
            continue
        age = (utc_ms(week) - utc_ms(event["date"])) / 86400000 / 7
        if age <= 4:
            found.extend((event["date"], place["name"]) for place in places)
    return sorted(found)


def link_status(url: str) -> str:
    request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "eastern-flank-monitor/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            return str(response.status)
    except urllib.error.HTTPError as exc:
        if exc.code in (405, 501):
            get = urllib.request.Request(url, headers={"User-Agent": "eastern-flank-monitor/1.0"})
            try:
                with urllib.request.urlopen(get, timeout=12) as response:
                    return str(response.status)
            except urllib.error.HTTPError as again:
                return str(again.code)
            except Exception as again:
                return again.__class__.__name__
        return str(exc.code)
    except Exception as exc:
        return exc.__class__.__name__


def check_links(urls: list[str]) -> list[str]:
    problems = []
    unique = sorted(set(urls))
    with ThreadPoolExecutor(max_workers=6) as pool:
        for url, status in zip(unique, pool.map(link_status, unique)):
            if status in {"404", "410"} or status.endswith("Error") or status in {"URLError", "TimeoutError", "HTTPError"}:
                problems.append(f"link {status} {url}")
    return problems


def place_for_country(event: dict, code: str) -> bool:
    names = " ".join(place.get("name", "") for place in event.get("places") or []).lower()
    if "kaliningrad" in names and code in {"LT", "PL"}:
        return True
    if (event.get("tag") == "belarus" or any(word in names for word in ("belarus", "gomel", "zyabrovka", "mozyr"))) and code in {"LT", "LV", "PL"}:
        return True
    if any(word in names for word in ("northwest russia", "karelia", "pskov", "leningrad oblast")) and code in {"FI", "EE"}:
        return True
    return False


FACE_SWEEP = r"""
(() => {
  const bad = [];
  const shown = [];
  const banned = /\b(attack|attacks|invasion|invade|war|warfare|crisis|danger|dangerous|critical|urgent|imminent|panic|threat|threats|emergency|alarm|terror|terrorist|bomb|missile|kill|killed|death|deaths|blood|hostile|escalat\w*)\b/i;
  const raw = /\b(FI|EE|LV|LT|PL|UA|BY|RU|KG|eastern_flank|ukraine_test)\b/;
  const slider = document.getElementById('slider');
  function faceText() {
    const clone = document.getElementById('face').cloneNode(true);
    clone.querySelectorAll('details, [data-source]').forEach((node) => node.remove());
    return clone.innerText.replace(/\s+/g, ' ');
  }
  const max = Number(slider.max);
  for (let i = 0; i <= max; i += 1) {
    slider.value = String(i);
    slider.dispatchEvent(new Event('input', {bubbles: true}));
    const week = document.getElementById('week-label').textContent.trim();
    if (!/^Week of \d{1,2} [A-Z][a-z]+ \d{4}$/.test(week)) bad.push('bad date ' + week);
    document.getElementById('country-PL').click();
    const face = faceText();
    const hit = face.match(banned);
    if (hit) bad.push(week + ' alarm word ' + hit[0]);
    if (face.includes('undefined') || face.includes('NaN')) bad.push(week + ' bad token');
    const code = face.match(raw);
    if (code) bad.push(week + ' raw code ' + code[0]);
    const reading = document.getElementById('reading-line').textContent;
    if (!/headline/.test(reading)) bad.push(week + ' reading has no count');
    shown.push({
      week,
      reading,
      zones: document.querySelectorAll('#meter [data-zone]').length,
      dots: [...document.querySelectorAll('.event-dot')].map((dot) => ({
        place: dot.getAttribute('data-place'),
        date: dot.getAttribute('data-date'),
        cx: dot.getAttribute('cx'),
        cy: dot.getAttribute('cy'),
      })),
    });
    shown[shown.length - 1].dots.forEach((dot) => {
      if (dot.cx === 'NaN' || dot.cy === 'NaN') bad.push(week + ' bad dot');
    });
  }
  const links = [...document.querySelectorAll('#check-links a')].map((link) => link.href);
  if (!links.length) bad.push('no check-it-yourself links');
  links.forEach((href) => {
    if (!/^https:\/\//.test(href)) bad.push('bad check link ' + href);
  });
  return {
    bad,
    shown,
    links,
    lands: [...document.querySelectorAll('.land')].map((path) => path.getAttribute('data-country')),
  };
})()
"""


PROTO_SWEEP = r"""
(() => {
  const bad = [];
  const shown = [];
  const slider = document.getElementById('slider');
  const allowed = new Set(['Normal', 'Tense', 'Danger signs, unconfirmed', 'No data']);
  function contrast(fg, bg) {
    const parse = (color) => {
      const match = String(color).match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
      return match ? [Number(match[1]), Number(match[2]), Number(match[3])] : [0, 0, 0];
    };
    const lin = (c) => {
      const x = c / 255;
      return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4);
    };
    const lum = (rgb) => 0.2126 * lin(rgb[0]) + 0.7152 * lin(rgb[1]) + 0.0722 * lin(rgb[2]);
    const hi = Math.max(lum(parse(fg)), lum(parse(bg)));
    const lo = Math.min(lum(parse(fg)), lum(parse(bg)));
    return (hi + 0.05) / (lo + 0.05);
  }
  const bodyStyle = getComputedStyle(document.body);
  const bodyContrast = contrast(bodyStyle.color, bodyStyle.backgroundColor);
  if (bodyContrast < 4.5) bad.push('body contrast ' + bodyContrast.toFixed(2));
  const max = Number(slider.max);
  for (let i = 0; i <= max; i += 1) {
    slider.value = String(i);
    slider.dispatchEvent(new Event('input', {bubbles: true}));
    const week = document.getElementById('week-label').textContent.trim();
    if (!/^Week of \d{1,2} [A-Z][a-z]+ \d{4}$/.test(week)) bad.push('bad date ' + week);
    const text = document.body.innerText;
    if (text.includes('No English line')) bad.push(week + ' missing-translation line');
    if (text.includes('undefined') || text.includes('NaN')) bad.push(week + ' bad token');
    if (document.documentElement.scrollWidth > document.documentElement.clientWidth + 8) bad.push(week + ' overflows');
    const region = document.getElementById('region-state').textContent.trim();
    const match = region.match(/^Region: (Normal|Tense|Danger signs, unconfirmed)/);
    if (!match) bad.push(week + ' region ' + region);
    if (!document.querySelector('.country-card .sign')) bad.push(week + ' chip missing state word');
        const cardText = document.getElementById('country-strip').innerText;
        if (!/→|↑|↓/.test(cardText)) bad.push(week + ' chip missing arrow');
        if (/stored headline|Cards list/.test(cardText)) bad.push(week + ' chip jargon');
    const names = [...document.querySelectorAll('.country-name')].map((node) => node.textContent.trim()).join('|');
    if (names !== 'Finland|Estonia|Latvia|Lithuania|Poland|Russia') bad.push(week + ' names ' + names);
    shown.push({
      week,
      sign: match ? match[1] : '',
      dots: [...document.querySelectorAll('.event-dot')].map((dot) => ({
        place: dot.getAttribute('data-place'),
        date: dot.getAttribute('data-date'),
        cx: dot.getAttribute('cx'),
        cy: dot.getAttribute('cy'),
      })),
    });
  }
  document.getElementById('country-PL').click();
  const why = document.getElementById('why');
  if (why.hidden) bad.push('why panel stayed closed');
  if (!document.getElementById('why-title').textContent.startsWith('This week in ')) bad.push('panel title ' + document.getElementById('why-title').textContent);
  document.getElementById('country-FI').click();
  if (/Mozyr|Zyabrovka|Gomel/.test(document.getElementById('why').innerText)) bad.push('Finland panel shows a Ukraine-facing Belarus event');
  if (!document.getElementById('map-legend')) bad.push('missing legend');
  return {
    bad,
    shown,
    lands: [...document.querySelectorAll('.land')].map((path) => path.getAttribute('data-country')),
    contrast: bodyContrast,
  };
})()
"""


async def check_main(cdp, weeks: dict[str, list[dict]], events: list[dict]) -> list[str]:
    problems = []
    result = await cdp.js(PROTO_SWEEP)
    problems.extend(result["bad"])
    lands = set(result["lands"])
    for code in ("FI", "EE", "LV", "LT", "PL", "BY", "UA", "RU", "KG"):
        if code not in lands:
            problems.append(f"map missing {code}")
    flank = weeks["eastern_flank"]
    shown = result["shown"]
    if len(shown) != len(flank):
        problems.append(f"main screen showed {len(shown)} weeks, file has {len(flank)}")
    else:
        for src, got in zip(flank, shown):
            if got["week"] != week_label(src["week"]):
                problems.append(f"main {src['week']} date shows {got['week']!r}")
            if src["shown"] == "1" and got["sign"] != "Normal":
                problems.append(f"main {src['week']} Watchful shows {got['sign']!r}")
            expected = active_dots(events, src["week"])
            got_dots = sorted((dot["date"], dot["place"]) for dot in got["dots"])
            if got_dots != expected:
                problems.append(f"main {src['week']} dots {got_dots} file says {expected}")
    await cdp.call("Emulation.setEmulatedMedia", features=[{"name": "prefers-color-scheme", "value": "dark"}])
    dark = await cdp.js("""(() => {
      const style = getComputedStyle(document.body);
      const parse = (color) => {
        const match = String(color).match(/rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)/);
        return match ? [Number(match[1]), Number(match[2]), Number(match[3])] : [0, 0, 0];
      };
      const lin = (c) => { const x = c / 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); };
      const lum = (rgb) => 0.2126 * lin(rgb[0]) + 0.7152 * lin(rgb[1]) + 0.0722 * lin(rgb[2]);
      const a = lum(parse(style.color));
      const b = lum(parse(style.backgroundColor));
      const hi = Math.max(a, b), lo = Math.min(a, b);
      return (hi + 0.05) / (lo + 0.05);
    })()""")
    if dark < 4.5:
        problems.append(f"dark body contrast {dark}")
    await cdp.call("Emulation.setEmulatedMedia", features=[{"name": "prefers-color-scheme", "value": "light"}])
    await cdp.js("document.getElementById('slider').value = '0'; document.getElementById('slider').dispatchEvent(new Event('input', {bubbles:true}))")
    before = await cdp.js("document.getElementById('week-label').textContent")
    await cdp.js("window.scrollTo(0, 180)")
    scroll_before = await cdp.js("window.scrollY")
    await cdp.js("document.getElementById('play').click()")
    await asyncio.sleep(1.2)
    during = await cdp.js("document.getElementById('week-label').textContent")
    if during == before:
        problems.append("play did not advance the week")
    if await cdp.js("document.getElementById('play').textContent") != "Pause":
        problems.append("toggle did not show Pause while playing")
    await cdp.js("document.getElementById('play').click()")
    if await cdp.js("document.getElementById('play').textContent") != "Play":
        problems.append("toggle did not show Play after pause")
    paused = await cdp.js("document.getElementById('week-label').textContent")
    await asyncio.sleep(1.6)
    after = await cdp.js("document.getElementById('week-label').textContent")
    if after != paused:
        problems.append("pause did not stop the replay")
    scroll_after = await cdp.js("window.scrollY")
    if abs(scroll_after - scroll_before) > 2:
        problems.append(f"scroll moved during playback {scroll_before} -> {scroll_after}")
    await cdp.js("document.getElementById('play').click()")
    await asyncio.sleep(0.3)
    await cdp.js("const slider = document.getElementById('slider'); slider.value = '4'; slider.dispatchEvent(new Event('input', {bubbles:true}))")
    held = await cdp.js("document.getElementById('week-label').textContent")
    await asyncio.sleep(1.6)
    if await cdp.js("document.getElementById('week-label').textContent") != held:
        problems.append("slider click did not stop playback")
    if abs(await cdp.js("window.scrollY") - scroll_after) > 2:
        problems.append("scroll moved when the week changed")
    await cdp.call("Emulation.setDeviceMetricsOverride", width=390, height=800, deviceScaleFactor=1, mobile=True)
    narrow = await cdp.js("document.documentElement.scrollWidth > document.documentElement.clientWidth + 8")
    if narrow:
        problems.append("narrow main screen overflows")
    await cdp.call("Emulation.clearDeviceMetricsOverride")
    return problems


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
            problems.extend(await check_main(cdp, weeks, events))
            order = await cdp.js("""(() => {
              const bad = [];
              if (document.getElementById('how-link') || document.body.innerHTML.includes('how-it-works.html')) bad.push('How it works link still present');
              document.querySelectorAll('.story').forEach((story) => {
                const en = story.querySelector('.headline-en');
                const ru = story.querySelector('.headline-ru');
                if (!en || !en.textContent.trim()) bad.push('story missing English');
                if (ru && en && en.compareDocumentPosition(ru) !== Node.DOCUMENT_POSITION_FOLLOWING) bad.push('Russian is not after English');
              });
              const note = document.getElementById('officials') ? document.getElementById('officials').innerText : '';
              if (!note.includes('Russian officials: full coverage from Russian state media. Western officials: selected weeks.')) bad.push('officials note missing');
              const square = document.getElementById('russia-square');
              const poland = document.getElementById('country-PL');
              if (!square) bad.push('russia square missing');
              if (square && poland && poland.compareDocumentPosition(square) !== Node.DOCUMENT_POSITION_FOLLOWING) bad.push('Russia square is not after Poland');
              if (square) {
                const box = square.getBoundingClientRect();
                const all = document.getElementById('show-all').getBoundingClientRect();
                if (box.left < 0 || box.right > window.innerWidth + 1 || box.width < 40) bad.push('russia square clipped');
                if (all.right > window.innerWidth + 1) bad.push('show all clipped');
                if (getComputedStyle(square).borderTopColor === getComputedStyle(poland).borderTopColor) bad.push('Russia square border is not distinct');
                square.click();
              }
              if (document.getElementById('inside-main').hidden) bad.push('russia square did not open');
              const slider = document.getElementById('slider');
              const max = Number(slider.max);
              for (let i = 0; i <= max; i += 1) {
                slider.value = String(i);
                slider.dispatchEvent(new Event('input', {bubbles: true}));
                const cards = [...document.querySelectorAll('#inside-cards .russia-card')];
                if (cards.length !== 5) bad.push('inside cards ' + cards.length);
                cards.forEach((card) => {
                  const en = card.querySelector('.headline-en');
                  const ru = card.querySelector('.headline-ru');
                  if (ru && en && !(en.compareDocumentPosition(ru) & Node.DOCUMENT_POSITION_FOLLOWING)) bad.push('inside Russian before English');
                });
                if (document.getElementById('inside-main').hidden) bad.push('week ' + i + ' Russia closed while moving weeks');
                const mainPanel = document.getElementById('inside-main').innerText;
                if (!mainPanel.includes('Inside Russia informs; it does not change the tension levels.')) bad.push('inside note missing');
                if (!mainPanel.includes('Telegram coverage: 1 January 2021 through 28 February 2022.')) bad.push('coverage missing');
                if (/imminent|war is coming|alarming|shocking/i.test(mainPanel)) bad.push('scare wording');
                const foreignLetters = /[ãõçñ¿¡ğşıİıіїєґјљњћђџ]/;
                function storyText(story) {
                  return [...story.children].map((node) => node.textContent).join(' ');
                }
                function hasNato(text) {
                  return /(^|[^A-Za-z])nato([^A-Za-z]|$)/i.test(text);
                }
                const regionWord = /finland|finnish|estonia|estonian|latvia|latvian|lithuania|lithuanian|poland|polish|baltic|belarus|kaliningrad|ukraine|ukrainian|border|military|troop|army|exercise|drill|sanction|deploy|финлянд|финск|эстон|латви|литв|польш|прибалт|балтий|беларус|белорус|калининград|украин|границ|погранич|военн|войск|арми|учен|санкц|разв|нато/i;
                const ruSpeaker = /путин|кремл|песков|лавров|захаров|шоигу|миноборон|госдум|совфед|совет федерации|сенатор|putin|kremlin|peskov|lavrov|zakharova|shoigu|state duma|federation council|russian senator|russian diplomat|senator/i;
                const westSpeaker = /столтенберг|stoltenberg|north atlantic council|biden|байден|blinken|блинкен|psaki|псаки|white house|state department|department of state|pentagon|госдеп|european commission|еврокомисс|евросоюз|european council|borrell|боррел|президент|премьер|мид |prime minister|president|ministry of|government of|finnish|estonian|latvian|lithuanian|polish|finland|estonia|latvia|lithuania|poland|niinist|kallas|karis|nauseda|duda|morawiecki|us senator|american senator|нато/i;
                const russianOffice = /federation council|совфед|совет федерации|сенатор|russian senator|russian diplomat|state duma|госдум/i;
                document.querySelectorAll('#news .story, #country-news .story, #officials .story').forEach((story) => {
                  const text = storyText(story);
                  const original = story.querySelector('.headline-ru');
                  if (original && (foreignLetters.test(original.textContent) || !/[А-Яа-яЁё]/.test(original.textContent))) bad.push('week ' + i + ' non-Russian original');
                  if (!original && foreignLetters.test(text)) bad.push('week ' + i + ' foreign-language item');
                  if (!hasNato(text) && !regionWord.test(text)) bad.push('week ' + i + ' item fails relevance: ' + text.replace(/\s+/g, ' ').trim().slice(0, 90));
                });
                document.querySelectorAll('#officials-ru .story').forEach((story) => {
                  if (!ruSpeaker.test(story.textContent)) bad.push('week ' + i + ' Russian column speaker');
                });
                document.querySelectorAll('#officials-west .story').forEach((story) => {
                  const text = storyText(story);
                  if (!hasNato(text) && !westSpeaker.test(text)) bad.push('week ' + i + ' Western column speaker: ' + text.replace(/\s+/g, ' ').trim().slice(0, 90));
                  if (russianOffice.test(text) || (/(^|[^A-Za-z])senator([^A-Za-z]|$)/i.test(text) && !/(us|u\.s\.|american|french|dutch|german|british)\s+senators?/i.test(text))) bad.push('week ' + i + ' Russian speaker in western column');
                });
                if (i === 0 && document.getElementById('drawer').textContent.includes('Assange')) bad.push('Assange item was not dropped');
                const regionStories = document.querySelectorAll('#region-news .story').length;
                if (regionStories > 3) bad.push('week ' + i + ' region news over 3');
                if (!mainPanel.includes('Counts measure news volume, not military preparation.')) bad.push('volume note missing');
              }
              document.getElementById('show-all').click();
              if (document.querySelector('.picked')) bad.push('focus remained after show all');
              if (!document.getElementById('country-news').hidden) bad.push('country news stayed open');
              document.getElementById('country-PL').click();
              const card = document.getElementById('country-PL');
              const shape = document.querySelector('.land[data-country="PL"]');
              const section = document.getElementById('country-news');
              if (!card.classList.contains('picked') || !shape.classList.contains('picked') || !section.classList.contains('picked')) bad.push('selection did not highlight card, map, and news together');
              if (document.querySelectorAll('.country-card.dimmed').length !== 4) bad.push('other cards were not dimmed');
              const title = document.getElementById('country-news-title').textContent;
              if (title !== 'Russian media about Poland') bad.push('country news title ' + title);
              const stories = [...section.querySelectorAll('.story')];
              const foreign = stories.filter((story) => !(story.dataset.countries || '').split(',').includes('PL'));
              if (foreign.length) bad.push('country news included another country');
              if (!stories.length && !section.innerText.includes('No news about Poland this week.')) bad.push('empty country news has no sentence');
              const scrollers = [...document.querySelectorAll('*')].filter((el) => {
                const style = getComputedStyle(el);
                return (style.overflowY === 'auto' || style.overflowY === 'scroll') && el.scrollHeight > el.clientHeight + 2;
              });
              if (scrollers.some((el) => !el.classList.contains('drawer'))) bad.push('scrollers ' + scrollers.map((el) => el.id || el.className).join(','));
              if (document.documentElement.scrollHeight > document.documentElement.clientHeight + 4) bad.push('page scrolls');
              const quiet = document.getElementById('why-quiet');
              if (quiet && !quiet.hidden && stories.length) bad.push('quiet while news exists');
              const playBox = document.getElementById('play').getBoundingClientRect();
              const foot = document.querySelector('.rail-foot').getBoundingClientRect();
              if (playBox.bottom > foot.top + 2) bad.push('footer overlaps play');
              document.getElementById('country-PL').click();
              if (!document.getElementById('country-news').hidden) bad.push('second click did not clear the country');
              const countryStories = document.querySelectorAll('#country-news .story').length;
              if (countryStories > 3) bad.push('country news over 3');
              function goWeek(label) {
                const slider = document.getElementById('slider');
                const max = Number(slider.max);
                for (let i = 0; i <= max; i += 1) {
                  slider.value = String(i);
                  slider.dispatchEvent(new Event('input', {bubbles: true}));
                  if (document.getElementById('week-label').textContent === label) return true;
                }
                return false;
              }
              document.getElementById('russia-square').click();
              if (!goWeek('Week of 7 June 2021')) bad.push('missing week before the poll');
              const before = document.getElementById('inside-main').innerText;
              if (!before.includes('No new data this week')) bad.push('poll shown before publication');
              if (before.includes('In May 2021, Russians often named')) bad.push('mood sentence before publication');
              if (!goWeek('Week of 14 June 2021')) bad.push('missing poll week');
              if (document.getElementById('inside-main').hidden) bad.push('Russia closed while moving to the poll week');
              const mood = [...document.querySelectorAll('#inside-cards .russia-card')].find((card) => card.querySelector('h3') && card.querySelector('h3').textContent === 'Public mood');
              const moodText = mood ? mood.innerText : '';
              if (!moodText.includes('In May 2021, Russians often named the Baltic states and Poland as unfriendly (Levada).')) bad.push('mood sentence missing');
              if (!moodText.includes('% of Russians naming this country unfriendly')) bad.push('mood axis missing');
              const names = mood ? [...mood.querySelectorAll('.mood-name')].map((node) => node.textContent) : [];
              if (names.join('|') !== 'Lithuania|Latvia|Estonia|Poland|Finland|USA (reference)|Ukraine (reference)') bad.push('mood bars ' + names.join('|'));
              const finland = mood ? mood.querySelectorAll('.mood-value')[4] : null;
              if (!finland || finland.textContent !== 'not listed') bad.push('Finland number was invented');
              if (!moodText.includes('Polls in Russia may not reflect honest opinion')) bad.push('mood caution missing');
              if (!moodText.includes('Levada Center')) bad.push('pollster missing');
              const full = mood ? mood.querySelector('.full-poll') : null;
              if (!full || full.open) bad.push('full poll is not behind a toggle');
              if (moodText.includes('83 percent said Russia has enemies')) bad.push('full poll is visible without the toggle');
              const conscription = [...document.querySelectorAll('#inside-cards .russia-card')].find((card) => card.querySelector('h3') && card.querySelector('h3').textContent === 'Conscription');
              if (!conscription || conscription.querySelector('.mood-chart')) bad.push('conscription card changed');
              document.querySelector('.land[data-country="RU"]').dispatchEvent(new MouseEvent('click', {bubbles: true}));
              if (!document.getElementById('inside-main').hidden) bad.push('map click did not close Russia');
              document.querySelector('.land[data-country="RU"]').dispatchEvent(new MouseEvent('click', {bubbles: true}));
              if (document.getElementById('inside-main').hidden) bad.push('map click did not open Russia');
              document.getElementById('drawer-close').click();
              if (!document.getElementById('inside-main').hidden || document.getElementById('region-overview').hidden) bad.push('Close did not return to the region');
              const left = document.getElementById('russia-square').getBoundingClientRect().x;
              document.getElementById('slider').dispatchEvent(new Event('input', {bubbles: true}));
              if (Math.abs(document.getElementById('russia-square').getBoundingClientRect().x - left) > 1) bad.push('Russia square jumped');
              return bad;
            })()""")
            problems.extend(order or [])
            reach = await cdp.js("""(() => {
              const play = document.getElementById('play');
              const box = play.getBoundingClientRect();
              play.click();
              const again = play.getBoundingClientRect();
              return box.width > 20 && box.top >= 0 && box.bottom <= window.innerHeight && again.width > 20;
            })()""")
            if not reach:
                problems.append("play control is not reachable")
            await cdp.call("Emulation.setEmulatedMedia", features=[{"name": "prefers-reduced-motion", "value": "reduce"}])
            await cdp.js("sessionStorage.removeItem('efm-doors'); location.reload()")
            for _ in range(40):
                ready = await cdp.js("!!document.getElementById('slider') && document.getElementById('slider').max !== ''")
                if ready:
                    break
                await asyncio.sleep(0.15)
            else:
                problems.append("reduced-motion page did not load")
            reduced = await cdp.js("""(() => {
              const doors = document.getElementById('doors');
              if (!doors) return true;
              return getComputedStyle(doors).display === 'none' || doors.hidden;
            })()""")
            if not reduced:
                problems.append("reduced-motion still shows the entrance")
            problems.extend(await layout_round(cdp))
            for height in (768, 1080):
                await cdp.call(
                    "Emulation.setDeviceMetricsOverride",
                    width=1280,
                    height=height,
                    deviceScaleFactor=1,
                    mobile=False,
                )
                await asyncio.sleep(0.25)
                problems.extend(await cdp.js(
                    """(() => {
                      const bad = [];
                      const viewHeight = window.innerHeight;
                      const viewWidth = window.innerWidth;
                      if (viewHeight < %d - 30) bad.push('viewport height ' + viewHeight);
                      ['play', 'week-label', 'slider'].forEach((id) => {
                        const box = document.getElementById(id).getBoundingClientRect();
                        if (box.top < -1 || box.left < -1 || box.bottom > viewHeight + 1 || box.right > viewWidth + 1 || box.height < 8 || box.width < 8) {
                          bad.push('%d ' + id + ' cut ' + Math.round(box.top) + ',' + Math.round(box.bottom) + ' of ' + viewHeight);
                        }
                      });
                      const foot = document.querySelector('.rail-foot').getBoundingClientRect();
                      if (foot.top < -1 || foot.bottom > viewHeight + 1 || foot.height < 8 || foot.right > viewWidth + 1) {
                        bad.push('%d disclaimer cut ' + Math.round(foot.top) + ',' + Math.round(foot.bottom));
                      }
                      const rail = document.querySelector('.rail').getBoundingClientRect();
                      if (rail.height + 1 < 9.5 * 16) bad.push('%d controls min-height ' + Math.round(rail.height));
                      if (document.documentElement.scrollHeight > document.documentElement.clientHeight + 4) bad.push('%d page scrolls');
                      const scrollers = [...document.querySelectorAll('*')].filter((el) => {
                        const style = getComputedStyle(el);
                        return (style.overflowY === 'auto' || style.overflowY === 'scroll') && el.scrollHeight > el.clientHeight + 2;
                      });
                      if (scrollers.some((el) => !el.classList.contains('drawer'))) bad.push('%d extra scroll');
                      return bad;
                    })()""" % (height, height, height, height, height, height)
                ) or [])
            await cdp.call("Emulation.clearDeviceMetricsOverride")
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
    print("PASS main screen: every week, map dots, links, play, pause, English first, no How it works")
    return 0


async def layout_round(cdp: Cdp) -> list[str]:
    """Round 2: stable strip, open dossier, controls inside 768 and 1080."""
    return await cdp.js(r"""(async () => {
      const bad = [];
      const doors = document.getElementById('doors');
      if (doors) doors.remove();
      if (document.fonts && document.fonts.ready) await document.fonts.ready;
      document.getElementById('show-all').click();
      const overview = document.getElementById('region-overview');
      if (!overview || overview.hidden) bad.push('region overview hidden');
      if (!overview.innerText.includes('Region overview')) bad.push('region overview missing');
      const drawer = document.getElementById('drawer');
      const map = document.getElementById('map-panel').getBoundingClientRect();
      const dossier = drawer.getBoundingClientRect();
      const width = window.innerWidth;
      const mapShare = map.width / width;
      const dossierShare = dossier.width / width;
      if (mapShare < 0.35 || mapShare > 0.40) bad.push('map width ' + mapShare.toFixed(3));
      if (dossierShare < 0.58 || dossierShare > 0.66) bad.push('dossier width ' + dossierShare.toFixed(3));
      if (dossier.width < 200 || dossier.right > width + 2) bad.push('dossier not open');
      const rail = document.querySelector('.rail');
      if (rail.getBoundingClientRect().height + 1 < 9.5 * 16) bad.push('controls min-height ' + rail.getBoundingClientRect().height);
      function boxes() {
        const found = {};
        ['region-state', 'country-FI', 'country-EE', 'country-LV', 'country-LT', 'country-PL', 'show-all', 'play', 'week-label', 'slider'].forEach((id) => {
          const node = document.getElementById(id);
          const box = node.getBoundingClientRect();
          found[id] = [Math.round(box.x), Math.round(box.y), Math.round(box.width), Math.round(box.height)];
        });
        document.querySelectorAll('.state-word, .trend-arrow, .country-card .sign, .chip-arrow').forEach((node, index) => {
          const box = node.getBoundingClientRect();
          found['slot' + index] = [Math.round(box.x), Math.round(box.y), Math.round(box.width), Math.round(box.height)];
        });
        return found;
      }
      const slider = document.getElementById('slider');
      const max = Number(slider.max);
      const words = [];
      for (let i = 0; i <= max; i += 1) {
        slider.value = String(i);
        slider.dispatchEvent(new Event('input', {bubbles: true}));
        words.push(document.querySelector('.state-word').textContent);
      }
      let start = 0;
      for (let i = 0; i + 9 <= max; i += 1) {
        if (new Set(words.slice(i, i + 10)).size > 1) {
          start = i;
          break;
        }
      }
      slider.value = String(start);
      slider.dispatchEvent(new Event('input', {bubbles: true}));
      const first = boxes();
      const seen = new Set([words[start]]);
      for (let step = 1; step <= 10; step += 1) {
        slider.value = String(start + step);
        slider.dispatchEvent(new Event('input', {bubbles: true}));
        seen.add(words[start + step]);
        const now = boxes();
        Object.keys(first).forEach((key) => {
          const left = first[key];
          const right = now[key];
          if (!right || left.some((value, index) => Math.abs(value - right[index]) > 1)) {
            bad.push('moved ' + key + ' week ' + step + ' ' + left.join(',') + ' -> ' + (right ? right.join(',') : 'missing'));
          }
        });
      }
      if (seen.size < 2) bad.push('10 weeks did not change the state word');
      function cutOff(tag) {
        const height = window.innerHeight;
        const viewWidth = window.innerWidth;
        ['play', 'week-label', 'slider'].forEach((id) => {
          const box = document.getElementById(id).getBoundingClientRect();
          if (box.top < -1 || box.left < -1 || box.bottom > height + 1 || box.right > viewWidth + 1 || box.height < 8 || box.width < 8) {
            bad.push(tag + ' ' + id + ' cut ' + Math.round(box.top) + ',' + Math.round(box.bottom) + ' of ' + height);
          }
        });
        const foot = document.querySelector('.rail-foot').getBoundingClientRect();
        if (foot.top < -1 || foot.bottom > height + 1 || foot.height < 8) bad.push(tag + ' disclaimer cut');
        if (document.documentElement.scrollHeight > document.documentElement.clientHeight + 4) bad.push(tag + ' page scrolls');
      }
      cutOff('900');
      return bad;
    })()""")


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))
