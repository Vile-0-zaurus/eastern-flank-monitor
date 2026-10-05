#!/usr/bin/env bash
# Read-only status for the eastern flank monitor. Does not stop or restart anything.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec python3 - "$ROOT" << 'PY'
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

active = service_active()
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
    priority_total = queue.get("translation_priority", 0)
    priority_done = min(done_pass, priority_total)
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
        priority_left = max(priority_total - priority_done, 0)
        everything_left = max(todo - done_pass, 0)
        if priority_left == 0:
            say("The priority chunk, Russian-language files from November 2021 through February 2022, is finished.")
        else:
            say(f"The priority chunk has about {priority_left:,} files left, {hours(priority_left / rate)}.")
        say(f"Everything still queued is about {everything_left:,} files, {hours(everything_left / rate)}.")
    else:
        say("There are not enough finished files in the last hour to estimate a speed or an arrival time.")
        actions.append("the backfill has no recent finished files, so its arrival time is unknown")
else:
    say("I cannot see a current backfill count in the service log.")
    actions.append("the backfill log has no current progress count")

try:
    df = subprocess.check_output(["df", "-B1", str(root)], text=True).splitlines()[-1].split()
    free_gb = int(df[3]) / 1_000_000_000
    say(f"The disk has {free_gb:.0f} GB free.")
    if free_gb < 10:
        actions.append(f"only {free_gb:.0f} GB of disk space is free")
except (subprocess.CalledProcessError, IndexError, ValueError):
    say("I could not read the free disk space.")
    actions.append("the free disk space could not be read")

sources = [
    ("tass-en.xml", "TASS English"),
    ("tass-ru.xml", "TASS Russian"),
    ("ria.xml", "RIA Novosti"),
    ("mfa.xml", "Russian foreign ministry"),
    ("navtex-ru", "Baltic navigation warnings"),
]
collect = root / "data" / "collect"
days = [(now.date() - timedelta(days=n)) for n in range(6, -1, -1)]
missed = []
for key, label in sources:
    ok_today = False
    miss = 0
    for day in days:
        log = collect / day.isoformat() / "collect.log"
        text = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
        success = False
        for line in text.splitlines():
            if key in line and ("SUCCESS" in line or line.strip().startswith("OK ")):
                success = True
                break
        if day == now.date():
            ok_today = success
        if not success:
            miss += 1
    verb = "were" if key == "navtex-ru" else "was"
    pronoun = "They" if key == "navtex-ru" else "It"
    if ok_today:
        say(f"{label} {verb} collected today. {pronoun} missed {miss} of the last 7 days.")
    else:
        say(f"{label} {verb} not collected today. {pronoun} missed {miss} of the last 7 days.")
        missed.append(label)
if missed:
    if len(missed) == 1:
        actions.append(f"{missed[0]} was not collected today")
    else:
        actions.append("these feeds were not collected today: " + ", ".join(missed))

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
else:
    say("Batch 2 is waiting. The priority download is not finished, so there is nothing for you to audit yet.")

if actions:
    say("ACTION NEEDED: " + "; ".join(actions) + ".")
else:
    say("All good — nothing to do.")
PY
