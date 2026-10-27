#!/usr/bin/env python3
"""Now-tab self-test. No API calls. Optionally records the 30-second video."""
from __future__ import annotations

import asyncio
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
CHROME = os.environ.get("CHROME", "/usr/bin/google-chrome")
VIEW = ROOT / "frontend" / "now-view.json"


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        return


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class Cdp:
    def __init__(self, ws):
        self.ws = ws
        self.next_id = 1
        self.pending = {}

    async def start(self):
        self.reader = asyncio.create_task(self._read())

    async def _read(self):
        async for raw in self.ws:
            msg = json.loads(raw)
            if "id" in msg and msg["id"] in self.pending:
                fut = self.pending.pop(msg["id"])
                if "error" in msg:
                    fut.set_exception(RuntimeError(str(msg["error"])))
                else:
                    fut.set_result(msg.get("result", {}))

    async def call(self, method, **params):
        call_id = self.next_id
        self.next_id += 1
        fut = asyncio.get_running_loop().create_future()
        self.pending[call_id] = fut
        await self.ws.send(json.dumps({"id": call_id, "method": method, "params": params}))
        return await fut

    async def js(self, expression):
        result = await self.call("Runtime.evaluate", expression=expression, returnByValue=True)
        return result.get("result", {}).get("value")


def check_file() -> list[str]:
    pack = json.loads(VIEW.read_text(encoding="utf-8"))
    bad = []
    if pack["window_start"] != "2026-08-03" or pack["window_end"] != "2026-10-25":
        bad.append("window is not frozen")
    if len(pack["weeks"]) != 12:
        bad.append(f"expected 12 weeks, got {len(pack['weeks'])}")
    if "full tension level not computed" not in pack["label"]:
        bad.append("level label missing")
    for item in pack["incidents"]:
        if not item.get("source") or not item.get("source_date") or not item.get("summary"):
            bad.append(f"incident missing source fields: {item.get('date')}")
        if item["date"] < pack["window_start"] or item["date"] > pack["window_end"]:
            bad.append(f"incident outside window: {item['date']}")
    return bad


async def run(record: bool) -> int:
    problems = check_file()
    port = free_port()
    os.chdir(ROOT)
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Quiet)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    debug = free_port()
    profile = Path("/tmp/efm-now-selftest")
    profile.mkdir(exist_ok=True)
    chrome = subprocess.Popen(
        [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage",
         f"--remote-debugging-port={debug}", f"--user-data-dir={profile}",
         "--window-size=1280,800", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(50):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{debug}/json/version", timeout=1).read()
                break
            except Exception:
                time.sleep(0.1)
        else:
            print("Chrome did not open.")
            return 1
        page = f"http://127.0.0.1:{port}/frontend/?mode=now"
        request = urllib.request.Request(f"http://127.0.0.1:{debug}/json/new?{page}", method="PUT")
        with urllib.request.urlopen(request, timeout=5) as response:
            target = json.loads(response.read().decode())
        async with websockets.connect(target["webSocketDebuggerUrl"], max_size=20_000_000) as ws:
            cdp = Cdp(ws)
            await cdp.start()
            await cdp.call("Runtime.enable")
            await cdp.call("Page.enable")
            ready = False
            for _ in range(40):
                ready = await cdp.js("document.getElementById('mode-now') && document.getElementById('mode-now').getAttribute('aria-pressed') === 'true' && document.getElementById('slider').max === '11'")
                if ready:
                    break
                await asyncio.sleep(0.15)
            if not ready:
                print("Now tab did not load.")
                return 1
            label = await cdp.js("document.getElementById('now-label').textContent")
            if "full tension level not computed" not in (label or ""):
                problems.append(f"label not shown: {label!r}")
            before = await cdp.js("window.scrollY")
            await cdp.js("document.getElementById('slider').value = '6'; document.getElementById('slider').dispatchEvent(new Event('input'))")
            await asyncio.sleep(0.2)
            after = await cdp.js("window.scrollY")
            if before != after:
                problems.append(f"week change jumped the page from {before} to {after}")
            missing = await cdp.js("""(() => {
              const pack = window.__now || null;
              return null;
            })()""")
            # Every incident link is in the served JSON the page loaded.
            linked = await cdp.js("""(() => {
              const bad = [];
              const items = (state.nowPack.incidents || []);
              items.forEach((item) => {
                if (!item.source || !item.source_date || !item.summary) bad.push(item.date || 'blank');
              });
              return bad;
            })()""")
            if linked:
                problems.append("incident missing a source: " + ", ".join(linked))
            tension = await cdp.js("document.getElementById('region-state').textContent")
            if tension and any(word in tension for word in ("Calm", "Tense", "Elevated", "Serious", "Critical")):
                problems.append(f"tension word on the Now strip: {tension}")
            scroll = await cdp.js("""(() => {
              const page = document.documentElement.scrollHeight - document.documentElement.clientHeight;
              const wide = document.documentElement.scrollWidth - document.documentElement.clientWidth;
              const bars = [];
              for (const el of document.querySelectorAll('body *')) {
                const style = getComputedStyle(el);
                if (style.display === 'none' || style.visibility === 'hidden') continue;
                const down = el.scrollHeight - el.clientHeight;
                const across = el.scrollWidth - el.clientWidth;
                const scrollsY = down > 1 && (style.overflowY === 'auto' || style.overflowY === 'scroll');
                const scrollsX = across > 1 && (style.overflowX === 'auto' || style.overflowX === 'scroll');
                if (scrollsY || scrollsX) bars.push((el.id || el.className || el.tagName) + ':' + down);
              }
              return {page, wide, bars, h: window.innerHeight, w: window.innerWidth};
            })()""")
            if not scroll or scroll.get("h") < 700:
                problems.append(f"viewport not 1280x800: {scroll}")
            elif scroll.get("page", 0) > 1 or scroll.get("wide", 0) > 1:
                problems.append(f"page scrollbar at 1280x800: {scroll}")
            elif len(scroll.get("bars") or []) > 1:
                problems.append(f"more than one scroller: {scroll}")
            if record and not problems:
                frames = Path("/tmp/efm-now-frames")
                frames.mkdir(exist_ok=True)
                for old in frames.glob("*.png"):
                    old.unlink()
                for index in range(60):
                    week = min(index // 5, 11)
                    await cdp.js(f"state.index = {week}; renderWeek();")
                    shot = await cdp.call("Page.captureScreenshot", format="png")
                    import base64
                    (frames / f"f{index:02d}.png").write_bytes(base64.b64decode(shot["data"]))
                dest = Path.home() / "Desktop" / "efm-now.mp4"
                subprocess.run(
                    ["ffmpeg", "-y", "-framerate", "2", "-i", str(frames / "f%02d.png"),
                     "-vf", "scale=1280:712", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                     "-t", "30", str(dest)],
                    check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                print(f"video {dest}")
    finally:
        chrome.terminate()
    if problems:
        print("FAIL")
        for item in problems:
            print("-", item)
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run("--record" in sys.argv)))
