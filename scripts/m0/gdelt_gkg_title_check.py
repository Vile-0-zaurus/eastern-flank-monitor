#!/usr/bin/env python3
"""Stream-filter one GDELT GKG day. Download, filter, delete each zip.

Keeps rows whose source is a Russian state outlet and whose Locations or
V2Locations mention Finland, Estonia, Latvia, Lithuania, or Poland.
Does not keep allied force data. Does not spoof a user-agent.
"""
from __future__ import annotations

import json
import re
import time
import urllib.parse
import zipfile
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
TMP = DATA / "gkg-tmp"
OUT = DATA / "gkg-filter"
TMP.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)

DAY = "20210615"
UA = "m0-reality-check/0.1 (local research; dry-run; 1 req/s)"
# User-listed outlets plus other clearly state outlets seen in GDELT.
STATE_DOMAINS = {
    "tass.ru",
    "tass.com",
    "ria.ru",
    "rt.com",
    "rg.ru",
    "iz.ru",
    "gazeta.ru",
    "sputniknews.com",
    "sputnikglobe.com",
    "tvzvezda.ru",
    "vesti.ru",
    "1tv.ru",
}
# Country name in the location fullname, or FIPS/ISO code in the country-code slot.
# EN/LG/LH are FIPS codes GDELT uses for Estonia/Latvia/Lithuania.
COUNTRY_NAMES = ("finland", "estonia", "latvia", "lithuania", "poland", "финляндия", "эстония", "латвия", "литва", "польша")
COUNTRY_CODES = {"FI", "EE", "LV", "LT", "PL", "EN", "LG", "LH"}
TITLE_RE = re.compile(r"<PAGE_TITLE>(.*?)</PAGE_TITLE>", re.I | re.S)

S = requests.Session()
S.headers["User-Agent"] = UA
_last = 0.0


def get(url: str, **kw):
    global _last
    wait = 1.05 - (time.monotonic() - _last)
    if wait > 0:
        time.sleep(wait)
    kw.setdefault("timeout", 180)
    resp = S.get(url, **kw)
    _last = time.monotonic()
    return resp


def domain_of(source_name: str, url: str) -> str:
    host = ""
    if url.startswith("http"):
        host = urllib.parse.urlparse(url).netloc.lower()
        if host.startswith("www."):
            host = host[4:]
    name = source_name.lower().strip()
    for d in STATE_DOMAINS:
        if host == d or host.endswith("." + d) or name == d or name.endswith("." + d):
            return d
    return ""


def location_hit(locations: str, v2locations: str) -> bool:
    blob = f"{locations}\n{v2locations}"
    low = blob.lower()
    if any(name in low for name in COUNTRY_NAMES):
        return True
    for rec in blob.split(";"):
        parts = rec.split("#")
        if len(parts) >= 3 and parts[2] in COUNTRY_CODES:
            return True
    return False


def page_title(extras: str) -> str:
    m = TITLE_RE.search(extras or "")
    if not m:
        return ""
    return re.sub(r"\s+", " ", m.group(1)).strip()


def urls_for_day() -> list[tuple[int, str]]:
    found = []
    resp = get("https://data.gdeltproject.org/gdeltv2/masterfilelist.txt", stream=True)
    resp.raise_for_status()
    for raw in resp.iter_lines(decode_unicode=True):
        if not raw:
            continue
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", "replace")
        parts = raw.split()
        if len(parts) < 3 or not parts[2].endswith(".gkg.csv.zip"):
            continue
        name = parts[2].rsplit("/", 1)[-1]
        if name.startswith(DAY):
            found.append((int(parts[0]), "https://data.gdeltproject.org/gdeltv2/" + name))
    resp.close()
    return found


def main() -> None:
    files = urls_for_day()
    print(f"index_files {len(files)} index_bytes {sum(s for s,_ in files)}", flush=True)
    kept_path = OUT / f"{DAY}-kept.tsv"
    kept_f = kept_path.open("w", encoding="utf-8")
    kept_f.write("source\tdomain\tseendate\ttitle\turl\n")
    n_rows = 0
    n_kept = 0
    n_title = 0
    examples = []
    domain_counts: dict[str, int] = {}
    downloaded = 0
    speed_bps = None
    failed = []
    for i, (size, url) in enumerate(files, 1):
        name = url.rsplit("/", 1)[-1]
        dest = TMP / name
        t0 = time.monotonic()
        try:
            resp = get(url)
        except Exception as exc:
            failed.append({"url": url, "error": str(exc)})
            print(f"ERR {i} {exc}", flush=True)
            continue
        elapsed = time.monotonic() - t0
        if resp.status_code != 200:
            failed.append({"url": url, "status": resp.status_code})
            print(f"HTTP {resp.status_code} {i}", flush=True)
            continue
        dest.write_bytes(resp.content)
        nbytes = len(resp.content)
        downloaded += nbytes
        if speed_bps is None and elapsed > 0:
            speed_bps = nbytes / elapsed
            print(f"speed_bps {speed_bps:.0f} file_bytes {nbytes} elapsed {elapsed:.2f}", flush=True)
        try:
            with zipfile.ZipFile(dest) as zf:
                inner = zf.namelist()[0]
                with zf.open(inner) as raw:
                    for line in raw:
                        n_rows += 1
                        try:
                            text = line.decode("utf-8", "replace")
                        except Exception:
                            continue
                        cols = text.rstrip("\n").split("\t")
                        if len(cols) < 27:
                            continue
                        dom = domain_of(cols[3], cols[4])
                        if not dom:
                            continue
                        if not location_hit(cols[9], cols[10]):
                            continue
                        title = page_title(cols[26])
                        n_kept += 1
                        domain_counts[dom] = domain_counts.get(dom, 0) + 1
                        if title:
                            n_title += 1
                            if len(examples) < 3:
                                examples.append({"title": title, "domain": dom, "url": cols[4][:180]})
                        kept_f.write(
                            "\t".join(
                                [
                                    cols[3].replace("\t", " "),
                                    dom,
                                    cols[1],
                                    title.replace("\t", " "),
                                    cols[4].replace("\t", " "),
                                ]
                            )
                            + "\n"
                        )
        finally:
            dest.unlink(missing_ok=True)
        if i % 16 == 0 or i == len(files):
            print(f"progress {i}/{len(files)} kept {n_kept} scanned {n_rows}", flush=True)
    kept_f.close()
    filtered_bytes = kept_path.stat().st_size
    report = {
        "day": DAY,
        "n_files": len(files),
        "index_bytes": sum(s for s, _ in files),
        "downloaded_bytes": downloaded,
        "rows_scanned": n_rows,
        "rows_kept": n_kept,
        "rows_with_title": n_title,
        "pct_with_title": round(100.0 * n_title / n_kept, 2) if n_kept else None,
        "examples": examples,
        "filtered_bytes": filtered_bytes,
        "filtered_mb": round(filtered_bytes / (1024 * 1024), 3),
        "domain_counts": domain_counts,
        "speed_bps": speed_bps,
        "n_failed": len(failed),
        "failed": failed[:5],
    }
    (OUT / f"{DAY}-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
