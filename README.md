# Eastern Flank Monitor

A local early-warning research app. It reads public Russian-state coverage of Finland, Estonia, Latvia, Lithuania, and Poland. It does not collect allied force locations.

Live monitoring is off (`config/app.yaml`). The default showcase is the saved 2021–22 demo. That mode makes no API calls.

## Milestone status

| Milestone | Status |
|---|---|
| M0 Data reality check | Done. See `docs/sources.md`. |
| M1 Narrative pipeline | In progress. Outlet filter and gold sets exist. The GKG backfill is still running. Do not restart it. |
| M2 Scoring | Not started. |
| M3 Backtest report | Not started. Waiting on the backfill. |
| M4 Dashboard | Not started. Done only when demo mode is included. |
| M5 Admin page | Not started. |
| M6 Stage 2 prep | Not started. No paid hosting before then. |

## Restart in 10 minutes

1. `cd ~/Projects/eastern-flank-monitor`
2. `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`
3. Put keys in `.env` only if you will turn live monitoring on. Demo mode does not need them.
4. Leave `live_monitoring: off` in `config/app.yaml`. The app then shows "paused since <date> — showing demo" and makes no API calls.
5. Check the backfill without restarting it: `systemctl --user is-active gkg-backfill`
6. Label one headline: `.venv/bin/python pipeline/score/label_server.py --gold validation/label-175.csv` then open http://127.0.0.1:8765/

Free collectors may keep running while paid calls stay off.
