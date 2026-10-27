#!/usr/bin/env python3
"""Resumable GKG download for the last 12 full weeks.

English and translation streams. At most 2 downloads. Research user-agent only.
Zips are never written to disk. Network errors are retried and never final.
"""
from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
import threading
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "m0"))
sys.path.insert(0, str(ROOT / "pipeline" / "fetch"))

import gkg_backfill as bf  # noqa: E402
import gkg_filter_v2 as filt  # noqa: E402

NOW_DIR = ROOT / "data" / "now"
DB = NOW_DIR / "gkg-now.sqlite"
NOW_CONFIG = ROOT / "config" / "now.yaml"
WESTERN_PATH = ROOT / "config" / "western-outlets.yaml"
SIZE_CAP = NOW_DIR / "size-cap.txt"
INDEX_COUNT = NOW_DIR / "index-count.txt"
DAY_SIZE = NOW_DIR / "day-size.txt"
MAX_PARALLEL = 2
DISK_FLOOR = 10_000_000_000
DAY_CAP = 50_000_000
LISTS = {
    "english": "https://data.gdeltproject.org/gdeltv2/masterfilelist.txt",
    "translation": "https://data.gdeltproject.org/gdeltv2/masterfilelist-translation.txt",
}
CODE_SLOTS = {
    "FI", "EE", "LV", "LT", "PL", "BY", "RU", "UA",
    "EN", "LG", "LH", "BO", "RS", "UP",
}
REGION_RE = __import__("re").compile(
    r"finland|finnish|estonia|estonian|latvia|latvian|lithuania|lithuanian|"
    r"poland|polish|\bbaltic|belarus|kaliningrad|\brussia|\bukraine|\bnato\b|"
    r"финлянд|эстон|латви|литв|польш|прибалт|беларус|белорус|калинингр|росси|украин|"
    r"(?<![а-яё])нато(?![а-яё])",
    __import__("re").I,
)
PROBE_DOMAINS = (
    "lrt.lt", "err.ee", "lsm.lv", "yle.fi", "pap.pl",
    "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk",
)


def full_weeks(today: date, weeks: int = 12) -> tuple[str, str]:
    """Last N Monday-Sunday weeks that ended before today."""
    last_sunday = today - timedelta(days=today.weekday() + 1)
    start = last_sunday - timedelta(days=weeks * 7 - 1)
    return start.strftime("%Y%m%d"), last_sunday.strftime("%Y%m%d")


def configured_window(path: Path = NOW_CONFIG) -> tuple[str, str] | None:
    """Fixed dates from config. None when the file is missing or still rolling."""
    if not path.exists():
        return None
    rolling = True
    start = end = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = [part.strip() for part in line.split(":", 1)]
        if key == "rolling":
            rolling = value.lower() == "true"
        elif key == "window_start":
            start = value.replace("-", "")
        elif key == "window_end":
            end = value.replace("-", "")
    if rolling or len(start) != 8 or len(end) != 8:
        return None
    return start, end


def active_window(today: date | None = None) -> tuple[str, str]:
    frozen = configured_window()
    if frozen:
        return frozen
    return full_weeks(today or datetime.now(timezone.utc).date())


def disk_allows(free_bytes: int, floor: int = DISK_FLOOR) -> bool:
    return free_bytes >= floor


def day_exceeds(text_bytes: int, cap: int = DAY_CAP) -> bool:
    return text_bytes > cap


def location_codes(blob: str) -> set[str]:
    found = set()
    for rec in (blob or "").split(";"):
        parts = rec.split("#")
        if len(parts) >= 3 and parts[2].strip():
            found.add(parts[2].strip().upper())
    return found


def mentions_region(title: str, locations: str, v2locations: str) -> bool:
    if REGION_RE.search(title or ""):
        return True
    blob = f"{locations or ''}\n{v2locations or ''}"
    if REGION_RE.search(blob):
        return True
    codes = location_codes(locations) | location_codes(v2locations)
    return bool(codes & CODE_SLOTS)


def keep_row(domain: str, russian: set[str], western: set[str], title: str, locations: str, v2locations: str) -> bool:
    if domain in russian:
        return True
    if domain in western:
        return mentions_region(title, locations, v2locations)
    return False


def stream_file(name: str, stream: str) -> bool:
    if stream == "translation":
        return ".translation.gkg.csv.zip" in name
    return name.endswith(".gkg.csv.zip") and ".translation." not in name


def free_bytes() -> int:
    return shutil.disk_usage(ROOT).free


def wait_for_disk() -> None:
    while not disk_allows(free_bytes()):
        print(f"DISK_GUARD free_gb={free_bytes() / 1_000_000_000:.1f}", flush=True)
        time.sleep(bf.PAUSE_S)


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


def index_window(stream: str, list_url: str, start: str, end: str) -> list[tuple[str, str, str]]:
    files = []
    resp = filt.session().get(list_url, stream=True, timeout=600)
    resp.raise_for_status()
    for raw in resp.iter_lines(decode_unicode=True):
        if not raw:
            continue
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", "replace")
        parts = raw.split()
        if len(parts) < 3 or not stream_file(parts[2], stream):
            continue
        name = parts[2].rsplit("/", 1)[-1]
        stamp = name[:8]
        if not (start <= stamp <= end):
            continue
        url = parts[2]
        if url.startswith("http://"):
            url = "https://" + url[len("http://"):]
        files.append((stream, stamp, url))
    resp.close()
    return files


def scan(content: bytes, russian: set[str], western: set[str]) -> tuple[dict[str, int], list[tuple]]:
    outlets = russian | western
    totals = {d: 0 for d in outlets}
    kept = []
    with zipfile.ZipFile(__import__("io").BytesIO(content)) as zf:
        with zf.open(zf.namelist()[0]) as raw:
            for line in raw:
                cols = line.decode("utf-8", "replace").rstrip("\n").split("\t")
                if len(cols) < 5:
                    continue
                dom = bf.match_domain(cols[3] if len(cols) > 3 else "", cols[4], outlets)
                if not dom:
                    continue
                totals[dom] = totals.get(dom, 0) + 1
                title = ""
                locations = cols[9] if len(cols) > 9 else ""
                v2locations = cols[10] if len(cols) > 10 else ""
                if len(cols) > 26:
                    title = __import__("html").unescape(filt.page_title(cols[26]))
                if not keep_row(dom, russian, western, title, locations, v2locations):
                    continue
                themes = ""
                tone = ""
                if len(cols) > 8:
                    themes = cols[8] or cols[7]
                if len(cols) > 15:
                    tone = cols[15]
                stored_locations = locations or v2locations
                kept.append((dom, cols[1], cols[4], title, stored_locations, themes, tone))
    return totals, kept


def record(con, stream, stamp, url, attempts, totals, kept) -> None:
    day = stamp[:8]
    con.execute(
        """
        INSERT INTO files (url, stream, stamp, status, attempts, error, finished_at)
        VALUES (?, ?, ?, 'done', ?, NULL, ?)
        ON CONFLICT(url) DO UPDATE SET
          status='done', attempts=excluded.attempts, error=NULL, finished_at=excluded.finished_at
        """,
        (url, stream, stamp, attempts, bf.utcnow()),
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


def text_bytes(con: sqlite3.Connection, day: str) -> tuple[int, int]:
    row = con.execute(
        """
        SELECT COUNT(*),
               COALESCE(SUM(
                 COALESCE(LENGTH(page_title),0) + COALESCE(LENGTH(locations),0) +
                 COALESCE(LENGTH(themes),0) + COALESCE(LENGTH(tone),0) +
                 COALESCE(LENGTH(article_url),0) + COALESCE(LENGTH(domain),0) +
                 COALESCE(LENGTH(seendate),0) + COALESCE(LENGTH(stream),0) +
                 COALESCE(LENGTH(stamp),0) + COALESCE(LENGTH(day),0)
               ), 0)
        FROM kept WHERE day=?
        """,
        (day,),
    ).fetchone()
    return int(row[0]), int(row[1])


def write_day_size(day: str, rows: int, nbytes: int) -> None:
    DAY_SIZE.parent.mkdir(parents=True, exist_ok=True)
    with DAY_SIZE.open("a", encoding="utf-8") as fh:
        fh.write(f"{day} rows={rows} text_bytes={nbytes} text_mb={nbytes / 1_000_000:.2f}\n")


def stop_for_size(day: str, rows: int, nbytes: int) -> None:
    SIZE_CAP.parent.mkdir(parents=True, exist_ok=True)
    SIZE_CAP.write_text(
        f"day={day} rows={rows} text_mb={nbytes / 1_000_000:.2f}\n",
        encoding="utf-8",
    )
    print(f"SIZE_CAP day={day} rows={rows} text_mb={nbytes / 1_000_000:.2f}", flush=True)


def fetch_one(item, russian: set[str], western: set[str]):
    stream, stamp, url = item
    strikes = 0
    while True:
        bf.wait_for_network()
        wait_for_disk()
        try:
            content = bf.download(url)
            try:
                totals, kept = scan(content, russian, western)
            finally:
                del content
            return item, totals, kept, None
        except Exception as exc:
            if bf.is_network_error(exc) or not bf.network_up():
                print(f"NETWORK_RETRY {url} {str(exc)[:120]}", flush=True)
                time.sleep(bf.PAUSE_S)
                continue
            strikes += 1
            if strikes >= bf.MAX_TRIES:
                return item, None, None, str(exc)
            print(f"RETRY_PAUSE {url} {str(exc)[:120]}", flush=True)
            time.sleep(bf.PAUSE_S)


def run_days(con, todo, russian, western) -> None:
    lock = threading.Lock()
    done_n = 0
    days = sorted({stamp for _stream, stamp, _url in todo})
    by_day = {day: [item for item in todo if item[1] == day] for day in days}
    print(f"TODO {len(todo)} days={len(days)}", flush=True)
    for day in days:
        items = by_day[day]
        if not items:
            continue
        with ThreadPoolExecutor(max_workers=MAX_PARALLEL) as pool:
            futs = [pool.submit(fetch_one, item, russian, western) for item in items]
            for fut in as_completed(futs):
                (stream, stamp, url), totals, kept, err = fut.result()
                with lock:
                    if err:
                        bf.mark_fail(con, stream, stamp, url, err)
                        print(f"ERR {url} {err[:160]}", flush=True)
                    else:
                        prev = con.execute("SELECT attempts FROM files WHERE url=?", (url,)).fetchone()
                        attempts = (prev[0] if prev else 0) + 1
                        record(con, stream, stamp, url, attempts, totals, kept)
                        done_n += 1
                        print(f"PROGRESS {done_n}/{len(todo)} {bf.utcnow()}", flush=True)
        rows, nbytes = text_bytes(con, day)
        write_day_size(day, rows, nbytes)
        print(f"SIZE day={day} rows={rows} text_mb={nbytes / 1_000_000:.2f}", flush=True)
        if day_exceeds(nbytes):
            stop_for_size(day, rows, nbytes)
            return
    print(f"PASS_COMPLETE done={done_n} {bf.utcnow()}", flush=True)


def load_western(path: Path = WESTERN_PATH) -> list[str]:
    if not path.exists():
        raise SystemExit(f"no western outlet list at {path}")
    return bf.load_outlets(path)


def index_when_up(stream: str, list_url: str, start: str, end: str):
    while True:
        bf.wait_for_network()
        try:
            return index_window(stream, list_url, start, end)
        except Exception as exc:
            if not bf.is_network_error(exc):
                raise
            print(f"NETWORK_RETRY index {stream} {str(exc)[:120]}", flush=True)
            time.sleep(bf.PAUSE_S)


def run(today: date | None = None) -> None:
    if SIZE_CAP.exists():
        print("SIZE_CAP already set", SIZE_CAP.read_text(encoding="utf-8").strip(), flush=True)
        return
    today = today or datetime.now(timezone.utc).date()
    start, end = active_window(today)
    print(f"WINDOW {start} {end}", flush=True)
    russian = set(bf.load_outlets())
    western = set(load_western())
    overlap = sorted(russian & western)
    if overlap:
        raise SystemExit("outlet is in both lists: " + ",".join(overlap))
    print(f"OUTLETS russian={len(russian)} western={len(western)}", flush=True)
    con = connect(DB)
    reset_n = bf.clear_network_attempts(con)
    print(f"NETWORK_RETRY_RESET {reset_n}", flush=True)
    indexed = []
    counts = []
    for stream, list_url in LISTS.items():
        print(f"INDEX {stream}", flush=True)
        files = index_when_up(stream, list_url, start, end)
        print(f"INDEX {stream} files={len(files)}", flush=True)
        counts.append(f"{stream}={len(files)}")
        indexed.extend(files)
    INDEX_COUNT.write_text("\n".join(counts) + "\n", encoding="utf-8")
    todo = [item for item in indexed if not bf.skip(con, item[2])]
    todo.sort(key=lambda item: (item[1], item[0], item[2]))
    run_days(con, todo, russian, western)


def count_probe(content: bytes, domains: set[str]) -> dict[str, int]:
    found = {d: 0 for d in domains}
    with zipfile.ZipFile(__import__("io").BytesIO(content)) as zf:
        with zf.open(zf.namelist()[0]) as raw:
            for line in raw:
                cols = line.decode("utf-8", "replace").rstrip("\n").split("\t")
                if len(cols) < 5:
                    continue
                dom = bf.match_domain(cols[3] if len(cols) > 3 else "", cols[4], domains)
                if dom:
                    found[dom] = found.get(dom, 0) + 1
    return found


def probe(today: date | None = None) -> int:
    """Count example domains in a few files. Does not write the database."""
    today = today or datetime.now(timezone.utc).date()
    start, end = active_window(today)
    domains: set[str] = set(PROBE_DOMAINS)
    totals = {d: 0 for d in domains}
    sample_days = {end, start, "20260914"}
    picked = []
    for stream, list_url in LISTS.items():
        files = index_when_up(stream, list_url, start, end)
        by_day = {}
        for item in files:
            by_day.setdefault(item[1], []).append(item)
        for day in sorted(sample_days):
            rows = by_day.get(day) or []
            if not rows:
                continue
            step = max(1, len(rows) // 2)
            picked.append(rows[0])
            picked.append(rows[min(step, len(rows) - 1)])
    print(f"PROBE files={len(picked)}", flush=True)
    lock = threading.Lock()

    def one(item):
        _stream, _stamp, url = item
        bf.wait_for_network()
        content = bf.download(url)
        try:
            return count_probe(content, domains)
        finally:
            del content

    with ThreadPoolExecutor(max_workers=MAX_PARALLEL) as pool:
        for found in pool.map(one, picked):
            with lock:
                for dom, n in found.items():
                    totals[dom] += n
    for dom in PROBE_DOMAINS:
        print(f"{'SEEN' if totals[dom] else 'MISSING'} {dom} {totals[dom]}", flush=True)
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", action="store_true")
    args = parser.parse_args()
    if args.probe:
        raise SystemExit(probe())
    run()


if __name__ == "__main__":
    main()
