#!/usr/bin/env python3
"""GKG filter check v2. Research UA only. At most 2 downloads at once.

Streams one day, filters, deletes each zip. Does not keep raw GKG.
"""
from __future__ import annotations

import json
import re
import threading
import time
import urllib.parse
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "gkg-filter"
OUT.mkdir(parents=True, exist_ok=True)
UA = "eastern-flank-monitor/0.1 (local research)"
DAY = "20210615"
WINDOW = ("20210101", "20220224")
MAX_PARALLEL = 2

STATE_DOMAINS = {
    "tass.ru", "tass.com", "ria.ru", "rt.com", "rg.ru", "iz.ru", "gazeta.ru",
    "sputniknews.com", "sputnikglobe.com", "tvzvezda.ru", "vesti.ru", "1tv.ru",
}
WATCH = ("tass.ru", "ria.ru", "rg.ru", "iz.ru", "gazeta.ru")
# ISO codes only. FIPS EN/LG/LH produced false hits in v1.
ISO = {"FI", "EE", "LV", "LT", "PL"}
COUNTRY_NAMES = ("finland", "estonia", "latvia", "lithuania", "poland")
TITLE_RE = re.compile(r"<PAGE_TITLE>(.*?)</PAGE_TITLE>", re.I | re.S)
# Stems cover adjective forms (Finnish, Estonian, Baltic, Suwałki, Польша, Прибалтика).
TITLE_KEYS = re.compile(
    r"финлянд|эстон|латви|литв|польш|прибалт|балти|нарв|калинингр|сувалк|"
    r"finland|finnish|estonia|estonian|latvia|latvian|lithuania|lithuanian|"
    r"poland|polish|baltic|narva|kaliningrad|suwalki|suwałki",
    re.I,
)


def session() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = UA
    return s


def domain_of(source_name: str, url: str) -> str:
    host = ""
    if url.startswith("http"):
        host = urllib.parse.urlparse(url).netloc.lower()
        if host.startswith("www."):
            host = host[4:]
    name = (source_name or "").lower().strip()
    for d in STATE_DOMAINS:
        if host == d or host.endswith("." + d) or name == d or name.endswith("." + d):
            return d
    return ""


def page_title(extras: str) -> str:
    m = TITLE_RE.search(extras or "")
    if not m:
        return ""
    return re.sub(r"\s+", " ", m.group(1)).strip()


def location_hit(locations: str, v2locations: str) -> bool:
    blob = f"{locations}\n{v2locations}"
    low = blob.lower()
    if any(n in low for n in COUNTRY_NAMES):
        return True
    for rec in blob.split(";"):
        parts = rec.split("#")
        if len(parts) >= 3 and parts[2] in ISO:
            return True
    return False


def region_hit(cols: list[str]) -> bool:
    title = page_title(cols[26] if len(cols) > 26 else "")
    if title and TITLE_KEYS.search(title):
        return True
    if len(cols) > 10 and location_hit(cols[9], cols[10]):
        return True
    return False


def index_day_and_window(list_url: str) -> tuple[list[tuple[int, str]], int, int]:
    day_files: list[tuple[int, str]] = []
    window_bytes = 0
    window_files = 0
    s = session()
    resp = s.get(list_url, stream=True, timeout=600)
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
        try:
            size = int(parts[0])
        except ValueError:
            continue
        url = parts[2]
        if url.startswith("http://"):
            url = "https://" + url[len("http://"):]
        if stamp == DAY:
            day_files.append((size, url))
        if WINDOW[0] <= stamp <= WINDOW[1]:
            window_bytes += size
            window_files += 1
    resp.close()
    day_files.sort(key=lambda x: x[1])
    return day_files, window_bytes, window_files


def scan_zip(content: bytes) -> dict:
    outlet_rows = {d: 0 for d in STATE_DOMAINS}
    watch_seen = {d: 0 for d in WATCH}
    kept = 0
    kept_by = {d: 0 for d in STATE_DOMAINS}
    examples: list[dict] = []
    rows = 0
    with zipfile.ZipFile(__import__("io").BytesIO(content)) as zf:
        with zf.open(zf.namelist()[0]) as raw:
            for line in raw:
                rows += 1
                cols = line.decode("utf-8", "replace").rstrip("\n").split("\t")
                if len(cols) < 5:
                    continue
                dom = domain_of(cols[3] if len(cols) > 3 else "", cols[4])
                if not dom:
                    continue
                outlet_rows[dom] = outlet_rows.get(dom, 0) + 1
                if dom in watch_seen:
                    watch_seen[dom] += 1
                if len(cols) < 27 or not region_hit(cols):
                    continue
                kept += 1
                kept_by[dom] = kept_by.get(dom, 0) + 1
                title = page_title(cols[26])
                if dom.endswith(".ru") and title and len(examples) < 8:
                    examples.append({"domain": dom, "title": title[:240]})
    return {
        "rows": rows,
        "outlet_rows": outlet_rows,
        "watch_seen": watch_seen,
        "kept": kept,
        "kept_by": kept_by,
        "examples": examples,
    }


def download_one(url: str) -> tuple[int, float, bytes]:
    t0 = time.monotonic()
    resp = session().get(url, timeout=180)
    elapsed = time.monotonic() - t0
    resp.raise_for_status()
    return len(resp.content), elapsed, resp.content


def process_stream(name: str, list_url: str) -> dict:
    print(f"INDEX {name} {list_url}", flush=True)
    files, window_bytes, window_files = index_day_and_window(list_url)
    index_bytes = sum(s for s, _ in files)
    print(f"INDEX {name} files={len(files)} bytes={index_bytes} window_files={window_files} window_bytes={window_bytes}", flush=True)
    acc = {
        "stream": name,
        "n_files": len(files),
        "index_bytes": index_bytes,
        "downloaded_bytes": 0,
        "rows_scanned": 0,
        "rows_kept": 0,
        "outlet_totals": {d: 0 for d in sorted(STATE_DOMAINS)},
        "watch_any": {d: 0 for d in WATCH},
        "kept_by_domain": {},
        "examples": [],
        "window_files": window_files,
        "window_bytes": window_bytes,
        "failed": [],
    }
    lock = threading.Lock()

    def work(item: tuple[int, str]) -> None:
        _size, url = item
        content = b""
        try:
            nbytes, elapsed, content = download_one(url)
            scanned = scan_zip(content)
        except Exception as exc:
            with lock:
                acc["failed"].append({"url": url, "error": str(exc)[:200]})
            print(f"ERR {name} {url} {exc}", flush=True)
            return
        finally:
            # Never written to disk. Drop the bytes as soon as the scan returns.
            del content
        with lock:
            acc["downloaded_bytes"] += nbytes
            acc["rows_scanned"] += scanned["rows"]
            acc["rows_kept"] += scanned["kept"]
            for d, n in scanned["outlet_rows"].items():
                acc["outlet_totals"][d] = acc["outlet_totals"].get(d, 0) + n
            for d, n in scanned["watch_seen"].items():
                acc["watch_any"][d] = acc["watch_any"].get(d, 0) + n
            for d, n in scanned["kept_by"].items():
                if n:
                    acc["kept_by_domain"][d] = acc["kept_by_domain"].get(d, 0) + n
            for ex in scanned["examples"]:
                if len(acc["examples"]) < 8:
                    acc["examples"].append(ex)
            done = acc["downloaded_bytes"]
        print(f"FILE {name} {nbytes} {elapsed:.1f}s kept_so_far running bytes={done}", flush=True)

    with ThreadPoolExecutor(max_workers=MAX_PARALLEL) as pool:
        futs = [pool.submit(work, item) for item in files]
        for i, fut in enumerate(as_completed(futs), 1):
            fut.result()
            if i % 16 == 0 or i == len(files):
                print(f"PROGRESS {name} {i}/{len(files)} kept={acc['rows_kept']}", flush=True)
    path = OUT / f"{DAY}-{name}-v2.json"
    path.write_text(json.dumps(acc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"WROTE {path}", flush=True)
    return acc


def speed_test(urls: list[str]) -> dict:
    seq = urls[:4]
    par = urls[4:8]
    seq_rows = []
    t0 = time.monotonic()
    seq_bytes = 0
    for url in seq:
        n, elapsed, content = download_one(url)
        del content
        seq_bytes += n
        seq_rows.append({"bytes": n, "elapsed": round(elapsed, 2), "kbps": round(n / elapsed / 1024, 1)})
    seq_wall = time.monotonic() - t0
    t1 = time.monotonic()
    par_bytes = 0
    par_rows = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        futs = [pool.submit(download_one, u) for u in par]
        for fut in as_completed(futs):
            n, elapsed, content = fut.result()
            del content
            par_bytes += n
            par_rows.append({"bytes": n, "elapsed": round(elapsed, 2)})
    par_wall = time.monotonic() - t1
    report = {
        "sequential_4": {
            "bytes": seq_bytes,
            "wall_s": round(seq_wall, 2),
            "kbps": round(seq_bytes / seq_wall / 1024, 1),
            "files": seq_rows,
        },
        "parallel_2_of_4": {
            "bytes": par_bytes,
            "wall_s": round(par_wall, 2),
            "kbps": round(par_bytes / par_wall / 1024, 1) if par_wall else None,
            "files": par_rows,
        },
    }
    (OUT / f"{DAY}-speed.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)
    return report


def main() -> None:
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "both"
    if mode in ("translation", "both"):
        process_stream(
            "translation",
            "https://data.gdeltproject.org/gdeltv2/masterfilelist-translation.txt",
        )
    if mode in ("english", "both"):
        process_stream(
            "english",
            "https://data.gdeltproject.org/gdeltv2/masterfilelist.txt",
        )
    if mode == "speed":
        # Eight known files from the test day. Not run during a bulk pass.
        base = "https://data.gdeltproject.org/gdeltv2/"
        stamps = ["20210615000000", "20210615001500", "20210615003000", "20210615004500",
                  "20210615010000", "20210615011500", "20210615013000", "20210615014500"]
        urls = [base + s + ".gkg.csv.zip" for s in stamps]
        speed_test(urls)


if __name__ == "__main__":
    main()
