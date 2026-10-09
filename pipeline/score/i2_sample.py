"""I2 sample helpers. No model calls. Does not open gkg.sqlite."""
from __future__ import annotations

import html
import math
import random
import re
from datetime import date, timedelta

from pipeline.score.i1 import story_key, week_monday


def norm_title(title: str) -> str:
    text = html.unescape(title or "").lower()
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def collapse_stories(rows: list[dict]) -> list[dict]:
    """Same URL, or the same normalized title, is one story. Keep the earliest day."""
    parent = list(range(len(rows)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    by_url: dict[str, int] = {}
    by_title: dict[str, int] = {}
    for i, row in enumerate(rows):
        url = (row.get("url") or "").strip()
        title = norm_title(row.get("title") or "")
        if url:
            if url in by_url:
                union(i, by_url[url])
            else:
                by_url[url] = i
        if title:
            if title in by_title:
                union(i, by_title[title])
            else:
                by_title[title] = i
    groups: dict[int, dict] = {}
    for i, row in enumerate(rows):
        if not (row.get("url") or "").strip() and not norm_title(row.get("title") or ""):
            continue
        root = find(i)
        day = row["day"]
        kept = groups.get(root)
        if kept is None or day < kept["day"]:
            groups[root] = {
                "day": day,
                "url": (row.get("url") or "").strip(),
                "title": row.get("title") or "",
                "region": row["region"],
            }
        elif not groups[root]["url"] and (row.get("url") or "").strip():
            groups[root]["url"] = row["url"].strip()
    out = []
    for row in groups.values():
        monday = week_monday(date(int(row["day"][:4]), int(row["day"][4:6]), int(row["day"][6:8])))
        out.append({**row, "week": monday.isoformat()})
    out.sort(key=lambda item: (item["region"], item["week"], item["day"], item["url"], norm_title(item["title"])))
    return out


def draw_sample(stories: list[dict], seed: int, per_week: int) -> list[dict]:
    """One fixed seed, weeks in order. A short week keeps every story."""
    rng = random.Random(seed)
    by_key: dict[tuple[str, str], list[dict]] = {}
    for row in stories:
        by_key.setdefault((row["region"], row["week"]), []).append(row)
    picked = []
    for key in sorted(by_key):
        group = sorted(by_key[key], key=lambda item: (item["day"], item["url"], norm_title(item["title"])))
        chosen = group if len(group) <= per_week else rng.sample(group, per_week)
        chosen = sorted(chosen, key=lambda item: (item["day"], item["url"], norm_title(item["title"])))
        for item in chosen:
            picked.append({**item, "sampled": True})
    return picked


def wilson_interval(hostile: int, n: int, z: float = 1.96) -> tuple[float, float, float] | None:
    """Share and 95% Wilson interval. No classified rows is no data, not zero."""
    if n <= 0:
        return None
    phat = hostile / n
    denom = 1 + z * z / n
    center = (phat + z * z / (2 * n)) / denom
    margin = z * math.sqrt(phat * (1 - phat) / n + z * z / (4 * n * n)) / denom
    low = max(0.0, center - margin)
    high = min(1.0, center + margin)
    return phat, low, high


def hostile_yes(row: dict | None) -> bool | None:
    if not row or row.get("status") == "AI unavailable" or "hostile_framing" not in row:
        return None
    return str(row.get("hostile_framing") or "").strip().lower() == "yes"
