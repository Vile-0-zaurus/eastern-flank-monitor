#!/usr/bin/env python3
"""Sum GKG sizes from a masterfilelist on stdin. Does not keep the index."""
import json
import sys

day_b = day_n = win_b = win_n = 0
other = {s: [0, 0] for s in ("20210615", "20220201", "20220224")}
for line in sys.stdin:
    parts = line.split()
    if len(parts) < 3 or not parts[2].endswith(".gkg.csv.zip"):
        continue
    size = int(parts[0])
    stamp = parts[2].rsplit("/", 1)[-1][:8]
    if stamp == "20210101":
        day_b += size
        day_n += 1
    if "20210101" <= stamp <= "20220224":
        win_b += size
        win_n += 1
    if stamp in other:
        other[stamp][0] += size
        other[stamp][1] += 1
out = {
    "day_20210101_files": day_n,
    "day_20210101_bytes": day_b,
    "window_files": win_n,
    "window_bytes": win_b,
    "window_gib": round(win_b / 1024**3, 2),
    "comparison_days_mib": {
        s: {"files": n, "mib": round(b / 1024 / 1024, 1)} for s, (b, n) in other.items()
    },
}
json.dump(out, open("data/gdelt-window.json", "w"), indent=2)
print(json.dumps(out, indent=2))
