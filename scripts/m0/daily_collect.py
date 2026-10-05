#!/usr/bin/env python3
"""Daily snapshot of sources that answer a normal research user-agent.

Stores gzip snapshots under data/collect/YYYY-MM-DD/. Does not spoof a
browser user-agent. Skips any source that blocks or rejects the request.
NAVTEX: keeps Russian-origin warnings only. The full Swedish page also
carries Finnish, Baltic, Polish and other allied notices, which this
project must not store.
"""
from __future__ import annotations

import gzip
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parents[2]
UA = "eastern-flank-monitor/0.1 (local research; 1 req/s)"
FEEDS = {
    "tass-en.xml": "https://tass.com/rss/v2.xml",
    "tass-ru.xml": "https://tass.ru/rss/v2.xml",
    "ria.xml": "https://ria.ru/export/rss2/archive/index.xml",
    "mfa.xml": "https://mid.ru/ru/rss/",
}
NAVTEX_URL = "https://navvarn.sjofartsverket.se/Navigationsvarningar/Navtex"
RU_MARK = re.compile(r"PETERSBURG NAV WARN|KALININGRAD NAV WARN", re.I)

S = requests.Session()
S.headers["User-Agent"] = UA
_last: dict[str, float] = {}


def get(url: str) -> requests.Response:
    host = urlparse(url).netloc
    wait = 1.05 - (time.monotonic() - _last.get(host, 0.0))
    if wait > 0:
        time.sleep(wait)
    resp = S.get(url, timeout=60, allow_redirects=True)
    _last[host] = time.monotonic()
    return resp


def blocked(resp: requests.Response) -> str:
    if resp.status_code in (401, 403, 429, 451):
        return f"HTTP {resp.status_code}"
    body = resp.text[:400].lower()
    if "request rejected" in body or "access denied" in body:
        return "rejected page"
    return ""


def russian_navtex(html: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</(p|div|h\d|li|tr)>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("&#xA;", "\n").replace("&#xD;", "\n").replace("&amp;", "&")
    text = re.sub(r"[ \t]+", " ", text)
    # Split on warning stamps. Keep a block only if it is a Russian coastal warning
    # and does not also carry an allied warning label.
    # Split only on a new Russian warning header. Internal times like
    # "302100 UTC SEP" must stay inside the warning body.
    chunks = re.split(r"(?=\d{6} UTC [A-Z]{3}\s+(?:PETERSBURG|KALININGRAD) NAV WARN)", text)
    kept = []
    for chunk in chunks:
        if not RU_MARK.search(chunk):
            continue
        if re.search(r"ESTONIAN NAV|FINNISH NAV|POLISH NAV|LATVIAN NAV|LITHUANIAN NAV|SWEDISH NAV|GERMAN NAV|DANISH NAV|NATO", chunk, re.I):
            continue
        kept.append(re.sub(r"\n\s*\n+", "\n", chunk).strip())
    header = f"# Russian-origin warnings only\n# source: {NAVTEX_URL}\n# fetched: {datetime.now(timezone.utc).isoformat()}\n\n"
    return header + "\n\n".join(kept) + ("\n" if kept else "")


def write_gz(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wb") as fh:
        fh.write(data)


def main() -> None:
    day = datetime.now().astimezone().strftime("%Y-%m-%d")
    dest = ROOT / "data" / "collect" / day
    dest.mkdir(parents=True, exist_ok=True)
    log = []

    def note(level: str, source: str, detail: str) -> None:
        line = f"{datetime.now(timezone.utc).isoformat()} {level} {source} {detail}"
        log.append(line)
        print(line, flush=True)

    for name, url in FEEDS.items():
        try:
            resp = get(url)
        except Exception as exc:
            note("FAILURE", name, f"error={exc}")
            continue
        why = blocked(resp)
        looks_like_feed = b"<rss" in resp.content[:800].lower() or b"<feed" in resp.content[:800].lower()
        if why or resp.status_code != 200 or not looks_like_feed:
            note("FAILURE", name, f"HTTP {resp.status_code} {why or 'not a feed'}")
            continue
        write_gz(dest / f"{name}.gz", resp.content)
        note("SUCCESS", name, f"HTTP {resp.status_code} bytes={len(resp.content)}")
    try:
        resp = get(NAVTEX_URL)
    except Exception as exc:
        note("FAILURE", "navtex-ru", f"error={exc}")
        resp = None
    if resp is not None:
        why = blocked(resp)
        if why or resp.status_code != 200:
            note("FAILURE", "navtex-ru", f"HTTP {resp.status_code} {why}")
        else:
            text = russian_navtex(resp.text)
            n = text.count("NAV WARN")
            write_gz(dest / "navtex-ru.txt.gz", text.encode("utf-8"))
            note("SUCCESS", "navtex-ru", f"HTTP {resp.status_code} warnings={n} bytes={len(text.encode())}")
    summary = "\n".join(log) + "\n"
    with (dest / "collect.log").open("a", encoding="utf-8") as fh:
        fh.write(summary)


if __name__ == "__main__":
    main()
