#!/usr/bin/env python3
"""Daily snapshot of sources that answer a normal research user-agent.

Stores gzip snapshots under data/collect/YYYY-MM-DD/. Does not spoof a
browser user-agent. Skips any source that blocks or rejects the request.
NAVTEX: keeps Russian-origin warnings only. The full Swedish page also
carries Finnish, Baltic, Polish and other allied notices, which this
project must not store.

Before any fetch, wait until DNS resolves and one test request succeeds,
for at most 60 minutes, then start the normal fetch anyway. If every
enabled source fails, exit 1. A later run the same day does nothing when
those feeds are already saved.
"""
from __future__ import annotations

import gzip
import re
import socket
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parents[2]
UA = "eastern-flank-monitor/0.1 (local research; 1 req/s)"
COLLECT_CONFIG = ROOT / "config" / "collect.yaml"
FEEDS = {
    "tass-en.xml": "https://tass.com/rss/v2.xml",
    "tass-ru.xml": "https://tass.ru/rss/v2.xml",
    "ria.xml": "https://ria.ru/export/rss2/archive/index.xml",
    "mfa.xml": "https://mid.ru/ru/rss/",
}
NAVTEX_URL = "https://navvarn.sjofartsverket.se/Navigationsvarningar/Navtex"
NAVTEX_NAME = "navtex-ru"
RU_MARK = re.compile(r"PETERSBURG NAV WARN|KALININGRAD NAV WARN", re.I)

S = requests.Session()
S.headers["User-Agent"] = UA
_last: dict[str, float] = {}
NETWORK_TRIES = 5
PAUSE_S = 60
CONNECT_WAIT_S = 60 * 60
CONNECT_POLL_S = 30
NETWORK_MARKERS = (
    "NameResolutionError",
    "Name or service not known",
    "Temporary failure in name resolution",
    "Network is unreachable",
    "timed out",
    "Timeout",
    "ConnectionError",
    "Connection reset",
    "Connection aborted",
    "IncompleteRead",
    "RemoteDisconnected",
    "Connection refused",
    "NewConnectionError",
    "Max retries exceeded",
)


def disabled_sources(path: Path = COLLECT_CONFIG) -> dict[str, str]:
    found: dict[str, str] = {}
    section = ""
    if not path.exists():
        return found
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if not raw.startswith(" ") and line.strip() == "disabled:":
            section = "disabled"
            continue
        if section == "disabled" and ":" in line:
            key, val = line.strip().split(":", 1)
            found[key.strip()] = val.strip()
        elif not raw.startswith(" "):
            section = ""
    return found


def enabled_sources(disabled: dict[str, str] | None = None) -> list[str]:
    """Enabled feed names, then navtex. Disabled sources are not requested."""
    skipped = disabled_sources() if disabled is None else disabled
    names = [name for name in FEEDS if name not in skipped]
    if NAVTEX_NAME not in skipped:
        names.append(NAVTEX_NAME)
    return names


def source_url(name: str) -> str:
    if name == NAVTEX_NAME:
        return NAVTEX_URL
    return FEEDS[name]


def saved_filename(name: str) -> str:
    if name == NAVTEX_NAME:
        return "navtex-ru.txt.gz"
    return f"{name}.gz"


def latest_levels(log_text: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for line in log_text.splitlines():
        parts = line.split()
        if len(parts) < 3 or parts[1] not in ("SUCCESS", "FAILURE", "SKIP"):
            continue
        found[parts[2]] = parts[1]
    return found


def feeds_already_saved(dest: Path, names: list[str]) -> bool:
    """True only when every enabled source has a saved file and a latest SUCCESS."""
    if not names:
        return True
    log_path = dest / "collect.log"
    text = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
    levels = latest_levels(text)
    for name in names:
        path = dest / saved_filename(name)
        if not path.is_file() or path.stat().st_size <= 0:
            return False
        if levels.get(name) != "SUCCESS":
            return False
    return True


def collect_exit_code(names: list[str], outcomes: dict[str, str]) -> int:
    """Exit 1 only when every enabled source failed. A partial save is 0."""
    if not names:
        return 0
    if all(outcomes.get(name) != "SUCCESS" for name in names):
        return 1
    return 0


def dns_resolves(host: str, timeout: float = 10) -> bool:
    old = socket.getdefaulttimeout()
    socket.setdefaulttimeout(timeout)
    try:
        socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        return True
    except OSError:
        return False
    finally:
        socket.setdefaulttimeout(old)


def request_succeeds(url: str) -> bool:
    """One completed HTTP response. A connection error is not success."""
    try:
        get(url)
        return True
    except Exception:
        return False


def wait_for_connectivity(
    urls: list[str],
    note,
    resolve=dns_resolves,
    request=request_succeeds,
    sleep=time.sleep,
    monotonic=time.monotonic,
    deadline_s: float = CONNECT_WAIT_S,
    poll_s: float = CONNECT_POLL_S,
) -> bool:
    """Wait until one host resolves and one test request succeeds, or 60 minutes."""
    if not urls:
        return True
    start = monotonic()
    while True:
        for url in urls:
            host = urlparse(url).netloc
            if resolve(host) and request(url):
                note("OK", "connectivity", "dns and test request succeeded")
                return True
        elapsed = monotonic() - start
        if elapsed >= deadline_s:
            note("FAILURE", "connectivity", "waited 60 minutes; starting fetch")
            return False
        note("RETRY", "connectivity", f"elapsed={int(elapsed)}s")
        remaining = deadline_s - elapsed
        sleep(min(poll_s, remaining) if remaining > 0 else 0)
    return False


def get(url: str) -> requests.Response:
    host = urlparse(url).netloc
    wait = 1.05 - (time.monotonic() - _last.get(host, 0.0))
    if wait > 0:
        time.sleep(wait)
    resp = S.get(url, timeout=60, allow_redirects=True)
    _last[host] = time.monotonic()
    return resp


def is_network_error(exc: BaseException) -> bool:
    text = str(exc)
    return any(marker in text for marker in NETWORK_MARKERS)


def get_with_retry(url: str, source: str, note) -> requests.Response:
    """Network and DNS errors pause and try again. Other errors are not retried."""
    last: BaseException | None = None
    tries = NETWORK_TRIES + 1
    for attempt in range(1, tries + 1):
        try:
            return get(url)
        except Exception as exc:
            last = exc
            if not is_network_error(exc) or attempt == tries:
                raise
            note("RETRY", source, f"attempt={attempt} pause={PAUSE_S}s error={exc}")
            time.sleep(PAUSE_S)
    assert last is not None
    raise last


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

    def flush() -> None:
        with (dest / "collect.log").open("a", encoding="utf-8") as fh:
            fh.write("\n".join(log) + "\n")

    skipped = disabled_sources()
    names = enabled_sources(skipped)
    if feeds_already_saved(dest, names):
        note("SKIP", "collect", "today's feeds are already saved")
        flush()
        return
    wait_for_connectivity([source_url(name) for name in names], note)
    outcomes: dict[str, str] = {}
    for name, url in FEEDS.items():
        if name in skipped:
            note("SKIP", name, "disabled")
            continue
        try:
            resp = get_with_retry(url, name, note)
        except Exception as exc:
            note("FAILURE", name, f"error={type(exc).__name__}")
            outcomes[name] = "FAILURE"
            continue
        why = blocked(resp)
        looks_like_feed = b"<rss" in resp.content[:800].lower() or b"<feed" in resp.content[:800].lower()
        if why or resp.status_code != 200 or not looks_like_feed:
            note("FAILURE", name, f"HTTP {resp.status_code} {why or 'not a feed'}")
            outcomes[name] = "FAILURE"
            continue
        write_gz(dest / saved_filename(name), resp.content)
        note("SUCCESS", name, f"HTTP {resp.status_code} bytes={len(resp.content)}")
        outcomes[name] = "SUCCESS"
    if NAVTEX_NAME not in skipped:
        try:
            resp = get_with_retry(NAVTEX_URL, NAVTEX_NAME, note)
        except Exception as exc:
            note("FAILURE", NAVTEX_NAME, f"error={type(exc).__name__}")
            outcomes[NAVTEX_NAME] = "FAILURE"
            resp = None
        if resp is not None:
            why = blocked(resp)
            if why or resp.status_code != 200:
                note("FAILURE", NAVTEX_NAME, f"HTTP {resp.status_code} {why}")
                outcomes[NAVTEX_NAME] = "FAILURE"
            else:
                text = russian_navtex(resp.text)
                n = text.count("NAV WARN")
                write_gz(dest / saved_filename(NAVTEX_NAME), text.encode("utf-8"))
                note("SUCCESS", NAVTEX_NAME, f"HTTP {resp.status_code} warnings={n} bytes={len(text.encode())}")
                outcomes[NAVTEX_NAME] = "SUCCESS"
    code = collect_exit_code(names, outcomes)
    if code:
        note("FAILURE", "collect", "all enabled sources failed")
    flush()
    if code:
        raise SystemExit(code)


if __name__ == "__main__":
    main()
