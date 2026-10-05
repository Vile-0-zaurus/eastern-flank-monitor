#!/usr/bin/env python3
"""Resumable GKG backfill for 2021-01-01 .. 2022-02-24.

English + translation streams. v2 region filter. At most 2 downloads.
Research user-agent only. Zips are never written to disk.
Filtered rows and daily outlet totals go to SQLite under data/backtest/.
"""
from __future__ import annotations

import html
import sqlite3
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "m0"))
import gkg_filter_v2 as filt  # noqa: E402

DB = ROOT / "data" / "backtest" / "gkg.sqlite"
FAIL_LOG = ROOT / "data" / "backtest" / "failures.log"
WINDOW = ("20210101", "20220224")
LISTS = {
    "english": "https://data.gdeltproject.org/gdeltv2/masterfilelist.txt",
    "translation": "https://data.gdeltproject.org/gdeltv2/masterfilelist-translation.txt",
}
MAX_TRIES = 3
MAX_PARALLEL = 2


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_failure(url: str, attempts: int, error: str) -> None:
    FAIL_LOG.parent.mkdir(parents=True, exist_ok=True)
    with FAIL_LOG.open("a", encoding="utf-8") as fh:
        fh.write(f"{utcnow()} FAILED attempts={attempts} {url} {error}\n")


def connect() -> sqlite3.Connection:
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB, timeout=60)
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
          domain TEXT NOT NULL,
          seendate TEXT,
          title TEXT,
          article_url TEXT
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


def index_window(stream: str, list_url: str) -> list[tuple[str, str, str]]:
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
        if not (WINDOW[0] <= stamp <= WINDOW[1]):
            continue
        url = parts[2]
        if url.startswith("http://"):
            url = "https://" + url[len("http://"):]
        files.append((stream, stamp, url))
    resp.close()
    return files


def skip(con: sqlite3.Connection, url: str) -> bool:
    row = con.execute("SELECT status, attempts FROM files WHERE url=?", (url,)).fetchone()
    if not row:
        return False
    status, attempts = row
    if status == "done":
        return True
    if status == "failed" and attempts >= MAX_TRIES:
        return True
    return False


def scan(content: bytes) -> tuple[dict[str, int], list[tuple]]:
    totals = {d: 0 for d in filt.STATE_DOMAINS}
    kept = []
    import io
    import zipfile
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        with zf.open(zf.namelist()[0]) as raw:
            for line in raw:
                cols = line.decode("utf-8", "replace").rstrip("\n").split("\t")
                if len(cols) < 5:
                    continue
                dom = filt.domain_of(cols[3] if len(cols) > 3 else "", cols[4])
                if not dom:
                    continue
                totals[dom] = totals.get(dom, 0) + 1
                if len(cols) < 27 or not filt.region_hit(cols):
                    continue
                title = html.unescape(filt.page_title(cols[26]))
                kept.append((dom, cols[1], title, cols[4]))
    return totals, kept


def download(url: str) -> bytes:
    resp = filt.session().get(url, timeout=180)
    resp.raise_for_status()
    return resp.content


def record(con: sqlite3.Connection, stream: str, stamp: str, url: str, attempts: int,
           totals: dict[str, int], kept: list[tuple]) -> None:
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
    for dom, seendate, title, article_url in kept:
        con.execute(
            "INSERT INTO kept (stream, stamp, domain, seendate, title, article_url) VALUES (?,?,?,?,?,?)",
            (stream, stamp, dom, seendate, title, article_url),
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


def mark_fail(con: sqlite3.Connection, stream: str, stamp: str, url: str, error: str) -> None:
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


def main() -> None:
    con = connect()
    todo: list[tuple[str, str, str]] = []
    for stream, list_url in LISTS.items():
        print(f"INDEX {stream}", flush=True)
        files = index_window(stream, list_url)
        print(f"INDEX {stream} files={len(files)}", flush=True)
        for item in files:
            if not skip(con, item[2]):
                todo.append(item)
    print(f"TODO {len(todo)}", flush=True)
    lock = threading.Lock()
    done_n = 0

    def work(item: tuple[str, str, str]):
        stream, stamp, url = item
        try:
            content = download(url)
            try:
                totals, kept = scan(content)
            finally:
                del content
            return item, totals, kept, None
        except Exception as exc:
            return item, None, None, str(exc)

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
                    if done_n % 25 == 0:
                        print(f"PROGRESS done={done_n} todo={len(todo)} {utcnow()}", flush=True)
    print(f"PASS_COMPLETE done={done_n} {utcnow()}", flush=True)


if __name__ == "__main__":
    main()
