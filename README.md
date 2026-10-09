# Eastern Flank Monitor

A local early-warning research app. It reads public Russian-state coverage of Finland, Estonia, Latvia, Lithuania, and Poland. It does not collect allied force locations.

Live monitoring is off (`config/app.yaml`). The default showcase is the saved 2021–22 demo. That mode makes no API calls.

## Milestone status

| Milestone | Status |
|---|---|
| M0 Data reality check | Done. See `docs/sources.md`. |
| M1 Narrative pipeline | Done. See `docs/validation-report.md`. The GKG backfill finished on 2026-10-09. The service is disabled. Do not restart it. |
| M2 Scoring | Skeleton only. Not run on stored data. See `pipeline/score/engine.py`. |
| M3 Backtest report | Not started. The backfill is finished. |
| M4 Dashboard | Not started. Done only when demo mode is included. |
| M5 Admin page | Not started. |
| M6 Stage 2 prep | Not started. No paid hosting before then. |

## Restart in 10 minutes

1. `cd ~/Projects/eastern-flank-monitor`
2. `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`
3. Put keys in `.env` only if you will turn live monitoring on. Demo mode does not need them.
4. Leave `live_monitoring: off` in `config/app.yaml`. The app then shows "paused since <date> — showing demo" and makes no API calls.
5. Check status without touching the backfill: `efm-status`
6. The unlabeled headline was excluded. Do not open the old one-row labeling file.

Free collectors may keep running while paid calls stay off.
