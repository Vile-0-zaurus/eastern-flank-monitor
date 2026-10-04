#!/usr/bin/env python3
"""Download one GDELT GKG day (2021-01-01) at <=1 req/s and scan for Russian outlets.

Sizes come from the already-fetched masterfilelist. Zips land in data/gkg/ (gitignored).
"""
from __future__ import annotations

import json
import time
import zipfile
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
GKG = DATA / "gkg"
GKG.mkdir(parents=True, exist_ok=True)
OUT = DATA / "gdelt-gkg-day.json"

DAY = "20210101"
NEEDLES = (
    b"tass.ru",
    b"ria.ru",
    b"interfax.ru",
    b"lenta.ru",
    b"kommersant.ru",
    b"iz.ru",
    b"rg.ru",
    b"rt.com",
    b"gazeta.ru",
    b"vedomosti.ru",
)

urls = []
with (DATA / "masterfilelist.txt").open() as fh:
    for line in fh:
        parts = line.split()
        if len(parts) < 3 or not parts[2].endswith(".gkg.csv.zip"):
            continue
        name = parts[2].rsplit("/", 1)[-1]
        if name.startswith(DAY):
            urls.append((int(parts[0]), "https://data.gdeltproject.org/gdeltv2/" + name))

print(f"files {len(urls)} index_bytes {sum(s for s,_ in urls)}", flush=True)
S = requests.Session()
S.headers["User-Agent"] = "m0-reality-check/0.1 (local research; dry-run; 1 req/s)"
downloaded = 0
failed = []
last = 0.0
for i, (size, url) in enumerate(urls, 1):
    dest = GKG / url.rsplit("/", 1)[-1]
    if dest.exists() and dest.stat().st_size == size:
        downloaded += dest.stat().st_size
        continue
    wait = 1.05 - (time.monotonic() - last)
    if wait > 0:
        time.sleep(wait)
    try:
        resp = S.get(url, timeout=120)
        last = time.monotonic()
    except Exception as exc:
        failed.append({"url": url, "error": str(exc)})
        print(f"ERR {i} {exc}", flush=True)
        continue
    if resp.status_code != 200:
        failed.append({"url": url, "status": resp.status_code})
        print(f"HTTP {resp.status_code} {i}", flush=True)
        continue
    dest.write_bytes(resp.content)
    downloaded += len(resp.content)
    if i % 16 == 0 or i == len(urls):
        print(f"progress {i}/{len(urls)} bytes {downloaded}", flush=True)

# scan up to 4 files spread across the day
hits = {n.decode(): 0 for n in NEEDLES}
scanned_files = []
scanned_rows = 0
sample_idxs = sorted(set([0, len(urls)//3, 2*len(urls)//3, len(urls)-1]))
for idx in sample_idxs:
    if not urls:
        break
    dest = GKG / urls[idx][1].rsplit("/", 1)[-1]
    if not dest.exists():
        continue
    try:
        zf = zipfile.ZipFile(dest)
    except zipfile.BadZipFile:
        failed.append({"url": str(dest), "error": "bad zip"})
        continue
    inner = zf.namelist()[0]
    file_hits = 0
    with zf.open(inner) as raw:
        for n, line in enumerate(raw):
            if n >= 8000:
                break
            scanned_rows += 1
            low = line.lower()
            for needle in NEEDLES:
                if needle in low:
                    hits[needle.decode()] += 1
                    file_hits += 1
                    break
    scanned_files.append({"file": dest.name, "rows_capped": min(8000, n + 1), "ru_token_rows": file_hits})
    zf.close()

report = {
    "day": DAY,
    "n_files_index": len(urls),
    "index_bytes": sum(s for s, _ in urls),
    "downloaded_bytes": downloaded,
    "n_failed": len(failed),
    "failed": failed[:8],
    "scanned_files": scanned_files,
    "rows_scanned": scanned_rows,
    "russian_source_token_hits": hits,
    "russian_sources_present": any(hits.values()),
}
OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps({k: report[k] for k in ("n_files_index", "index_bytes", "downloaded_bytes", "n_failed", "russian_sources_present", "russian_source_token_hits")}, indent=2))
