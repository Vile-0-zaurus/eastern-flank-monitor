# Eastern Flank Monitor

Local research app. It reads public Russian coverage of Finland, Estonia, Latvia, Lithuania, and Poland, and shows a calm risk picture. It is not an official warning service. Stage 1 runs on this machine only.

## Stack

Python 3.11+, SQLite, and a static HTML/JS page. Rules and weights live in config/. Paid calls stay off while live_monitoring is off.

## Folders

- SPEC.md — what we build. Source of truth.
- config/ — weights, budgets, the frozen Now window.
- pipeline/ — fetch, score, and model calls.
- scripts/ — status, Now build, collectors.
- frontend/ — the local page. UI text is in frontend/i18n/en.json.
- manual/ — dated analyst inputs.
- tests/ — self-tests.
- docs/ — decisions, tasks, reports. data/ is gitignored.

## Rules

1. Russian side and aggregated incidents only. Never collect, display, or publish Finnish, Baltic, Polish, or NATO force locations or movements.
2. No data is not zero. Confirmed and reported stay separate. A row needs a fetched page with its own date.
3. Do not bypass blocks. No VPN, no DNS change, no user-agent spoof.
4. Secrets stay in .env. Never print or commit them.
5. live_monitoring stays off. Demo mode makes no API calls.
6. Every paid run needs an estimate, a hard cap on the REAL charge, a calibration run first, and approval. Hermes does not use the project key.
7. Do not restart the finished 2021–22 backfill. Do not roll or rescore data/backtest/gkg.sqlite. Open it read-only, and do not load it all into memory.
8. A closed written gate stays closed. Read STATE.md at session start. Update it before ending a work session.
9. Commit a small working step. Push only when the task or the user says so.

## Budget

The xAI top-up on 9 October 2026 is the final funding. It is not a monthly refill. Anthropic spend is separate and is not taken out of that top-up.

Every paid run needs an estimate, a hard cap on the real charge, a calibration run first, and approval. The agent's own key is not the project key.

When the project balance is gone, paid calls stop. Demo mode continues. Do not store a remaining balance in this file.

## How to run

1. cd ~/Projects/eastern-flank-monitor
2. bash scripts/status.sh
3. Leave live_monitoring off in config/app.yaml.
4. Demo page, only if you want to look: python3 -m http.server 8080 --bind 127.0.0.1
5. Open http://127.0.0.1:8080/frontend/
6. Do not start the WebUI, a paid run, or the disabled backfill from this file.
