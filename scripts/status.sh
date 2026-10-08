#!/usr/bin/env bash
# Read-only status for the eastern flank monitor. Does not stop or restart anything.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec python3 - "$ROOT" << 'PY'
import sqlite3
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

root = Path(sys.argv[1])
now = datetime.now().astimezone()
actions = []

def say(text):
    print(text)

def service_active():
    try:
        out = subprocess.check_output(
            ["systemctl", "--user", "is-active", "gkg-backfill.service"],
            text=True, stderr=subprocess.DEVNULL,
        ).strip()
    except subprocess.CalledProcessError as exc:
        return (exc.output or "").strip() or "inactive"
    return out

def journal_lines():
    try:
        out = subprocess.check_output(
            ["journalctl", "--user", "-u", "gkg-backfill", "--no-pager", "-o", "cat"],
            text=True, stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]

def parse_progress(lines):
    rows = []
    for line in lines:
        if not line.startswith("PROGRESS "):
            continue
        parts = line.split()
        if len(parts) < 3 or "/" not in parts[1]:
            continue
        done_s, total_s = parts[1].split("/", 1)
        try:
            when = datetime.fromisoformat(parts[2])
            done = int(done_s)
            total = int(total_s)
        except ValueError:
            continue
        rows.append((when, done, total))
    return rows

def latest_queue(lines):
    found = None
    for line in lines:
        if line.startswith("QUEUE "):
            found = line
    if not found:
        return None
    data = {}
    for bit in found.split()[1:]:
        if "=" in bit:
            key, val = bit.split("=", 1)
            try:
                data[key] = int(val)
            except ValueError:
                pass
    return data

def hours(minutes):
    if minutes < 90:
        return f"about {round(minutes)} minutes"
    h = minutes / 60
    if h < 48:
        return f"about {h:.0f} hours"
    return f"about {h / 24:.1f} days"

def translation_priority_state():
    """Read-only. Count files that were saved, not an assumed 96 files a day."""
    db = root / "data" / "backtest" / "gkg.sqlite"
    empty = {
        "known": False,
        "done": 0,
        "left": 0,
        "retry": 0,
        "failed": 0,
        "recorded": 0,
        "missing_days": 116,
        "finished": False,
    }
    if not db.exists():
        return empty
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=5)
    try:
        con.execute("PRAGMA query_only=ON")
        rows = con.execute(
            """
            SELECT status, COUNT(*)
            FROM files
            WHERE stream='translation' AND stamp>='20211101' AND stamp<='20220224'
            GROUP BY status
            """
        ).fetchall()
        day_rows = con.execute(
            """
            SELECT stamp,
                   SUM(CASE WHEN status='done' THEN 1 ELSE 0 END),
                   COUNT(*)
            FROM files
            WHERE stream='translation' AND stamp>='20211101' AND stamp<='20220224'
            GROUP BY stamp
            """
        ).fetchall()
    finally:
        con.close()
    saved_days = {stamp for stamp, done_n, total in day_rows if total and done_n == total}
    missing_days = 0
    day = datetime(2021, 11, 1, tzinfo=timezone.utc)
    end = datetime(2022, 2, 24, tzinfo=timezone.utc)
    while day <= end:
        if day.strftime("%Y%m%d") not in saved_days:
            missing_days += 1
        day += timedelta(days=1)
    counts = {status: n for status, n in rows}
    done = counts.get("done", 0)
    retry = counts.get("retry", 0)
    failed = counts.get("failed", 0)
    recorded = sum(counts.values())
    left = recorded - done
    return {
        "known": True,
        "done": done,
        "left": left,
        "retry": retry,
        "failed": failed,
        "recorded": recorded,
        "missing_days": missing_days,
        "finished": missing_days == 0 and left == 0 and done > 0,
    }


def say_translation(translation, rate):
    saved = translation["done"]
    left = translation["left"]
    missing = translation["missing_days"]
    if translation["finished"]:
        say(
            "The translation priority download, November 2021 through February 2022, "
            f"is finished. {saved:,} files are saved."
        )
    else:
        parts = [f"{saved:,} files are saved"]
        if left:
            extra = f", {hours(left / rate)}" if rate else ""
            parts.append(f"{left:,} files are not saved yet{extra}")
        if missing:
            parts.append(f"{missing} days in that window are not saved yet")
        say(
            "The translation priority download, November 2021 through February 2022, has "
            + ". ".join(parts)
            + "."
        )
    say(f"{translation['retry']:,} files are waiting to retry. {translation['failed']:,} files are failed.")
    recorded = translation["recorded"]
    if recorded and translation["failed"] / recorded > 0.01:
        actions.append(
            f"{translation['failed']:,} files are failed, more than 1 percent of the translation priority chunk"
        )

active = service_active()
priority_chunk_done = False
if active == "active":
    say("The backfill is running.")
else:
    say(f"The backfill is not running. Its status is {active}.")
    actions.append("the backfill service is not running")

lines = journal_lines()
progress = parse_progress(lines)
queue = latest_queue(lines)
index_total = None
for line in lines:
    if line.startswith("INDEX english files="):
        index_total = int(line.split("=", 1)[1])
    elif line.startswith("INDEX translation files=") and index_total:
        index_total += int(line.split("=", 1)[1])

if progress and queue and index_total:
    when, done_pass, todo = progress[-1]
    already = index_total - todo
    done_now = already + done_pass
    pct = 100 * done_now / index_total
    say(f"The backfill is {pct:.1f} percent done, {done_now:,} of {index_total:,} files.")
    translation = translation_priority_state()
    priority_chunk_done = translation["finished"]
    hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    recent = [(t, d, n) for t, d, n in progress if t >= hour_ago]
    rate = None
    if len(recent) >= 2:
        # A restart resets the counter. Sum each stretch instead of subtracting across it.
        gained = 0
        span = 0
        prev_t, prev_d, _prev_n = recent[0]
        for t, d, _n in recent[1:]:
            delta = (t - prev_t).total_seconds()
            if d >= prev_d and delta > 0:
                gained += d - prev_d
                span += delta
            prev_t, prev_d = t, d
        if span > 0 and gained > 0:
            rate = gained / (span / 60)
    if rate:
        say(f"Over the last hour it finished about {rate:.1f} files per minute.")
        everything_left = max(todo - done_pass, 0)
        say_translation(translation, rate)
        say(f"Everything still queued is about {everything_left:,} files, {hours(everything_left / rate)}.")
    else:
        say("There are not enough finished files in the last hour to estimate a speed or an arrival time.")
        say_translation(translation, None)
        actions.append("the backfill has no recent finished files, so its arrival time is unknown")
else:
    say("I cannot see a current backfill count in the service log.")
    actions.append("the backfill log has no current progress count")

try:
    df = subprocess.check_output(["df", "-B1", str(root)], text=True).splitlines()[-1].split()
    free_gb = int(df[3]) / 1_000_000_000
    say(f"The disk has {free_gb:.0f} GB free.")
    if free_gb < 15:
        actions.append(f"only {free_gb:.0f} GB of disk space is free")
except (subprocess.CalledProcessError, IndexError, ValueError):
    say("I could not read the free disk space.")
    actions.append("the free disk space could not be read")

sources = [
    ("tass-en.xml", "TASS English", "2026-10-04"),
    ("tass-ru.xml", "TASS Russian", "2026-10-05"),
    ("ria.xml", "RIA Novosti", "2026-10-04"),
    ("mfa.xml", "Russian foreign ministry", "2026-10-05"),
    ("navtex-ru", "Baltic navigation warnings", "2026-10-04"),
]
disabled = {}
collect_cfg = root / "config" / "collect.yaml"
if collect_cfg.exists():
    section = ""
    for raw in collect_cfg.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if not raw.startswith(" ") and line.strip() == "disabled:":
            section = "disabled"
            continue
        if section == "disabled" and ":" in line:
            key, val = line.strip().split(":", 1)
            disabled[key.strip()] = val.strip()
        elif not raw.startswith(" "):
            section = ""
collect = root / "data" / "collect"
window = [(now.date() - timedelta(days=n)) for n in range(6, -1, -1)]
attempts = defaultdict(list)
for log in collect.glob("*/collect.log"):
    for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
        for key, _label, _added in sources:
            if key in line and ("SUCCESS" in line or "FAILURE" in line or line.strip().startswith("OK ")):
                attempts[key].append((log.parent.name, "FAILURE" in line and "SUCCESS" not in line))
scheduled_fail = []
for key, label, added in sources:
    verb = "were" if key == "navtex-ru" else "was"
    pronoun = "They" if key == "navtex-ru" else "It"
    if key in disabled:
        say(f"{label} is disabled ({disabled[key]}).")
        continue
    seen = attempts.get(key, [])
    if not seen:
        say(f"{label} has not run yet (added {added}).")
        continue
    first = min(day for day, _fail in seen)
    ok_today = any(day == now.date().isoformat() and not fail for day, fail in seen)
    miss = 0
    for day in window:
        if day.isoformat() < first:
            continue
        if not any(d == day.isoformat() and not fail for d, fail in seen):
            miss += 1
    if ok_today:
        say(f"{label} {verb} collected today. {pronoun} missed {miss} days since {first}.")
    else:
        say(f"{label} {verb} not collected today. {pronoun} missed {miss} days since {first}.")
    today_rows = [fail for day, fail in seen if day == now.date().isoformat()]
    if today_rows and today_rows[-1]:
        scheduled_fail.append(label)
if scheduled_fail:
    actions.append("a scheduled collect failed for " + ", ".join(scheduled_fail))

if now.hour >= 8:
    today = now.date().isoformat()
    not_run = []
    ran_any = False
    for key, label, _added in sources:
        if key in disabled:
            continue
        seen = attempts.get(key, [])
        if any(day == today for day, _fail in seen):
            ran_any = True
        else:
            not_run.append(label)
    if not_run:
        if ran_any:
            reason = "the network, or that source did not answer"
        else:
            reason = "the machine was asleep or off, or the network was down"
        actions.append("not collected today: " + ", ".join(not_run) + ". Likely reason: " + reason)

spend = defaultdict(float)
usage = root / "data" / "llm" / "usage.log"
month = now.strftime("%Y-%m")
if usage.exists():
    for line in usage.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith(now.strftime("%Y-%m")):
            continue
        if "usd=" not in line or "model=" not in line:
            continue
        model = line.split("model=", 1)[1].split()[0]
        try:
            usd = float(line.split("usd=", 1)[1].split()[0])
        except ValueError:
            continue
        provider = "xAI" if model.startswith("grok") else "Anthropic" if model.startswith("claude") else model
        spend[provider] += usd
if spend:
    bits = [f"{name} ${amount:.2f}" for name, amount in sorted(spend.items())]
    say("API spend this month is " + ", ".join(bits) + ".")
else:
    say("There is no API spend recorded this month.")

candidates = root / "validation" / "gold-b2-candidates.csv"
if candidates.exists():
    say("Batch 2 is ready for your audit.")
    actions.append("batch 2 is ready for you to label")
elif priority_chunk_done:
    say("The translation priority download is finished. Batch 2 has not been built yet.")
else:
    say("Batch 2 is waiting. The translation priority download is not finished, so there is nothing for you to audit yet.")

if priority_chunk_done:
    if actions:
        say("ACTION NEEDED: " + "; ".join(actions) + ".")
    say("ACTION NEEDED: Priority download done. Tell Hermes: 'Continue the previous assignment from step 7 (batch 2).'")
elif actions:
    say("ACTION NEEDED: " + "; ".join(actions) + ".")
else:
    say("All good — nothing to do.")
PY
