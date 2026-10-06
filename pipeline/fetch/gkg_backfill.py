#!/usr/bin/env python3
"""Resumable GKG backfill. Outlet list only. No region filter.

English + translation streams, 2021-01-01 .. 2022-02-24.
At most 2 downloads. Research user-agent only.
Zips are never written to disk.
Kept columns: date, domain, URL, PAGE_TITLE, locations, themes, tone.
Daily totals per outlet are stored as well.

  python pipeline/fetch/gkg_backfill.py --day 20210615
      size test only; writes data/backtest/size-test.sqlite and prints stats
  python pipeline/fetch/gkg_backfill.py
      full window, resumable
"""
from __future__ import annotations

import html
import io
import socket
import sqlite3
import sys
import threading
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "m0"))
import gkg_filter_v2 as filt  # noqa: E402

OUTLETS_PATH = ROOT / "config" / "outlets.yaml"
DB = ROOT / "data" / "backtest" / "gkg.sqlite"
SIZE_DB = ROOT / "data" / "backtest" / "size-test.sqlite"
FAIL_LOG = ROOT / "data" / "backtest" / "failures.log"
WINDOW = ("20210101", "20220224")
PRIORITY = ("20211101", "20220224")
LISTS = {
    "english": "https://data.gdeltproject.org/gdeltv2/masterfilelist.txt",
    "translation": "https://data.gdeltproject.org/gdeltv2/masterfilelist-translation.txt",
}
MAX_TRIES = 3
MAX_PARALLEL = 2
PAUSE_S = 60
HOST = "data.gdeltproject.org"
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


def is_network_error(exc: BaseException) -> bool:
    text = str(exc)
    return any(marker in text for marker in NETWORK_MARKERS)


def network_up() -> bool:
    try:
        socket.getaddrinfo(HOST, 443)
        with socket.create_connection((HOST, 443), timeout=10):
            return True
    except OSError:
        return False


def wait_for_network() -> None:
    while not network_up():
        print("NETWORK_DOWN waiting 60s", flush=True)
        time.sleep(PAUSE_S)


def clear_network_attempts(con: sqlite3.Connection) -> int:
    """A DNS or connection error is not a final miss. Those rows are tried again."""
    clauses = " OR ".join("error LIKE ?" for _ in NETWORK_MARKERS)
    params = [f"%{marker}%" for marker in NETWORK_MARKERS]
    cur = con.execute(
        f"""
        UPDATE files
        SET attempts = 0, status = 'retry', error = NULL
        WHERE status IN ('retry', 'failed') AND ({clauses})
        """,
        params,
    )
    con.commit()
    return cur.rowcount


def load_outlets(path: Path = OUTLETS_PATH) -> list[str]:
    outlets = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line.startswith("- "):
            outlets.append(line[2:].strip())
    if not outlets:
        raise SystemExit(f"no outlets in {path}")
    return outlets


def queue_rank(item: tuple[str, str, str]) -> tuple:
    """Translation Nov 2021–Feb 2022, then English for those dates, then the rest."""
    stream, stamp, url = item
    if PRIORITY[0] <= stamp <= PRIORITY[1] and stream == "translation":
        return (0, stamp, url)
    if PRIORITY[0] <= stamp <= PRIORITY[1] and stream == "english":
        return (1, stamp, url)
    return (2, 0 if stream == "english" else 1, stamp, url)


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_failure(url: str, attempts: int, error: str) -> None:
    FAIL_LOG.parent.mkdir(parents=True, exist_ok=True)
    with FAIL_LOG.open("a", encoding="utf-8") as fh:
        fh.write(f"{utcnow()} FAILED attempts={attempts} {url} {error}\n")


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=60)
    con.execute("PRAGMA journal_mode=WAL")
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS files (
          url TEXT PRIMARY KEY,
          stream TEXT NOT NULL,
          stamp TEXT NOT NULL,
          status TEXT NOT NULL,
          attempts INTEGER NOT NULL DEFAULT 0,
          error TEXT,
          finished_at TEXT
        );
        CREATE TABLE IF NOT EXISTS kept (
          id INTEGER PRIMARY KEY,
          stream TEXT NOT NULL,
          stamp TEXT NOT NULL,
          day TEXT NOT NULL,
          domain TEXT NOT NULL,
          seendate TEXT,
          article_url TEXT,
          page_title TEXT,
          locations TEXT,
          themes TEXT,
          tone TEXT
        );
        CREATE TABLE IF NOT EXISTS daily_totals (
          day TEXT NOT NULL,
          stream TEXT NOT NULL,
          domain TEXT NOT NULL,
          n INTEGER NOT NULL,
          PRIMARY KEY (day, stream, domain)
        );
        """
    )
    return con


def index_window(stream: str, list_url: str, day: str | None) -> list[tuple[str, str, str]]:
    files = []
    resp = filt.session().get(list_url, stream=True, timeout=600)
    resp.raise_for_status()
    for raw in resp.iter_lines(decode_unicode=True):
        if not raw:
            continue
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", "replace")
        parts = raw.split()
        if len(parts) < 3 or ".gkg.csv.zip" not in parts[2]:
            continue
        name = parts[2].rsplit("/", 1)[-1]
        stamp = name[:8]
        if day:
            if stamp != day:
                continue
        elif not (WINDOW[0] <= stamp <= WINDOW[1]):
            continue
        url = parts[2]
        if url.startswith("http://"):
            url = "https://" + url[len("http://"):]
        files.append((stream, stamp, url))
    resp.close()
    return files


def match_domain(source_name: str, url: str, outlets: set[str]) -> str:
    host = ""
    if url.startswith("http"):
        host = url.split("/")[2].lower()
        if host.startswith("www."):
            host = host[4:]
    name = (source_name or "").lower().strip()
    for d in outlets:
        if host == d or host.endswith("." + d) or name == d or name.endswith("." + d):
            return d
    return ""


def scan(content: bytes, outlets: set[str]) -> tuple[dict[str, int], list[tuple]]:
    totals = {d: 0 for d in outlets}
    kept = []
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        with zf.open(zf.namelist()[0]) as raw:
            for line in raw:
                cols = line.decode("utf-8", "replace").rstrip("\n").split("\t")
                if len(cols) < 5:
                    continue
                dom = match_domain(cols[3] if len(cols) > 3 else "", cols[4], outlets)
                if not dom:
                    continue
                totals[dom] = totals.get(dom, 0) + 1
                title = html.unescape(filt.page_title(cols[26])) if len(cols) > 26 else ""
                locations = ""
                themes = ""
                tone = ""
                if len(cols) > 10:
                    locations = cols[9] or cols[10]
                if len(cols) > 8:
                    themes = cols[8] or cols[7]
                if len(cols) > 15:
                    tone = cols[15]
                kept.append((dom, cols[1], cols[4], title, locations, themes, tone))
    return totals, kept


def download(url: str) -> bytes:
    resp = filt.session().get(url, timeout=180)
    resp.raise_for_status()
    return resp.content


def skip(con: sqlite3.Connection, url: str) -> bool:
    row = con.execute("SELECT status, attempts FROM files WHERE url=?", (url,)).fetchone()
    if not row:
        return False
    status, attempts = row
    if status == "done":
        return True
    return status == "failed" and attempts >= MAX_TRIES


def record(con, stream, stamp, url, attempts, totals, kept) -> None:
    day = stamp[:8]
    con.execute(
        """
        INSERT INTO files (url, stream, stamp, status, attempts, error, finished_at)
        VALUES (?, ?, ?, 'done', ?, NULL, ?)
        ON CONFLICT(url) DO UPDATE SET
          status='done', attempts=excluded.attempts, error=NULL, finished_at=excluded.finished_at
        """,
        (url, stream, stamp, attempts, utcnow()),
    )
    con.executemany(
        """
        INSERT INTO kept (
          stream, stamp, day, domain, seendate, article_url, page_title, locations, themes, tone
        ) VALUES (?,?,?,?,?,?,?,?,?,?)
        """,
        [
            (stream, stamp, day, dom, seendate, article_url, title, locations, themes, tone)
            for dom, seendate, article_url, title, locations, themes, tone in kept
        ],
    )
    for dom, n in totals.items():
        if not n:
            continue
        con.execute(
            """
            INSERT INTO daily_totals (day, stream, domain, n) VALUES (?,?,?,?)
            ON CONFLICT(day, stream, domain) DO UPDATE SET n = n + excluded.n
            """,
            (day, stream, dom, n),
        )
    con.commit()


def mark_fail(con, stream, stamp, url, error) -> None:
    row = con.execute("SELECT attempts FROM files WHERE url=?", (url,)).fetchone()
    attempts = (row[0] if row else 0) + 1
    status = "failed" if attempts >= MAX_TRIES else "retry"
    con.execute(
        """
        INSERT INTO files (url, stream, stamp, status, attempts, error, finished_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(url) DO UPDATE SET
          status=excluded.status, attempts=excluded.attempts,
          error=excluded.error, finished_at=excluded.finished_at
        """,
        (url, stream, stamp, status, attempts, error[:500], utcnow()),
    )
    con.commit()
    if attempts >= MAX_TRIES:
        log_failure(url, attempts, error[:500])
        print(f"GAVE_UP {url} attempts={attempts}", flush=True)


def index_when_up(stream: str, list_url: str, day: str | None) -> list[tuple[str, str, str]]:
    while True:
        wait_for_network()
        try:
            return index_window(stream, list_url, day)
        except Exception as exc:
            if not is_network_error(exc):
                raise
            print(f"NETWORK_RETRY index {stream} {str(exc)[:120]}", flush=True)
            time.sleep(PAUSE_S)


def run(day: str | None, db_path: Path) -> None:
    outlets = load_outlets()
    outlet_set = set(outlets)
    con = connect(db_path)
    reset_n = clear_network_attempts(con)
    print(f"NETWORK_RETRY_RESET {reset_n}", flush=True)
    todo = []
    for stream, list_url in LISTS.items():
        print(f"INDEX {stream}", flush=True)
        files = index_when_up(stream, list_url, day)
        print(f"INDEX {stream} files={len(files)}", flush=True)
        for item in files:
            if not skip(con, item[2]):
                todo.append(item)
    todo.sort(key=queue_rank)
    n0 = sum(1 for item in todo if queue_rank(item)[0] == 0)
    n1 = sum(1 for item in todo if queue_rank(item)[0] == 1)
    print(f"QUEUE translation_priority={n0} english_priority={n1} rest={len(todo) - n0 - n1}", flush=True)
    print(f"TODO {len(todo)}", flush=True)
    lock = threading.Lock()
    done_n = 0

    def work(item):
        _stream, _stamp, url = item
        strikes = 0
        while True:
            wait_for_network()
            try:
                content = download(url)
                try:
                    totals, kept = scan(content, outlet_set)
                finally:
                    del content
                return item, totals, kept, None
            except Exception as exc:
                if not is_network_error(exc) or not network_up():
                    if is_network_error(exc):
                        print(f"NETWORK_DOWN during {url}", flush=True)
                        continue
                    return item, None, None, str(exc)
                strikes += 1
                if strikes >= MAX_TRIES:
                    return item, None, None, str(exc)
                print(f"RETRY_PAUSE {url} {str(exc)[:120]}", flush=True)
                time.sleep(PAUSE_S)

    with ThreadPoolExecutor(max_workers=MAX_PARALLEL) as pool:
        futs = [pool.submit(work, item) for item in todo]
        for fut in as_completed(futs):
            (stream, stamp, url), totals, kept, err = fut.result()
            with lock:
                if err:
                    mark_fail(con, stream, stamp, url, err)
                    print(f"ERR {url} {err[:160]}", flush=True)
                else:
                    assert totals is not None and kept is not None
                    prev = con.execute("SELECT attempts FROM files WHERE url=?", (url,)).fetchone()
                    attempts = (prev[0] if prev else 0) + 1
                    record(con, stream, stamp, url, attempts, totals, kept)
                    done_n += 1
                    if done_n % 16 == 0:
                        print(f"PROGRESS {done_n}/{len(todo)} {utcnow()}", flush=True)
    print(f"PASS_COMPLETE done={done_n} {utcnow()}", flush=True)
    if day:
        print_size(con, db_path)


def print_size(con: sqlite3.Connection, db_path: Path) -> None:
    con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    rows = con.execute("SELECT COUNT(*) FROM kept").fetchone()[0]
    by = dict(con.execute("SELECT domain, COUNT(*) FROM kept GROUP BY domain").fetchall())
    present = sorted(d for d, n in by.items() if n)
    missing = sorted(set(load_outlets()) - set(present))
    db_bytes = db_path.stat().st_size
    for suffix in ("-wal", "-shm"):
        extra = Path(str(db_path) + suffix)
        if extra.exists():
            db_bytes += extra.stat().st_size
    print("SIZE_TEST", flush=True)
    print(f"kept_rows={rows} sqlite_bytes={db_bytes} sqlite_mb={db_bytes / 1024 / 1024:.2f}", flush=True)
    print("present=" + ",".join(present), flush=True)
    print("missing=" + ",".join(missing), flush=True)
    for dom, n in sorted(by.items(), key=lambda kv: -kv[1]):
        print(f"outlet {dom} {n}", flush=True)


def main() -> None:
    if len(sys.argv) >= 3 and sys.argv[1] == "--day":
        day = sys.argv[2]
        if SIZE_DB.exists():
            SIZE_DB.unlink()
        for suffix in ("-wal", "-shm"):
            extra = Path(str(SIZE_DB) + suffix)
            if extra.exists():
                extra.unlink()
        run(day, SIZE_DB)
        return
    run(None, DB)


if __name__ == "__main__":
    main()
