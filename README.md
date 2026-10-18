# Eastern Flank Monitor

A local early-warning research app. It reads public Russian-state coverage of Finland, Estonia, Latvia, Lithuania, and Poland. It does not collect allied force locations.

Live monitoring is off (`config/app.yaml`). The default showcase is the saved 2021–22 demo. That mode makes no API calls.

## Milestone status

| Milestone | Status |
|---|---|
| M0 Data reality check | Done. See `docs/sources.md`. |
| M1 Narrative pipeline | Done. See `docs/validation-report.md`. The GKG backfill finished on 2026-10-09. The service is disabled. Do not restart it. |
| M2 Scoring | I1 daily series recomputed without sea-only Baltic stems. Ukraine test series stored locally. Scoring engine not yet run. |
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

## How the reading works

The main screen replays stored weeks from January 2021 through February 2022. It is not live, and it does not rescore those weeks.

The stored sign is one region reading. Normal covers the calm and watchful stored levels. Tense is the elevated level. A proposed serious or critical level is shown as danger signs, unconfirmed. Country cards do not inherit that word. They list only a fact about that country.

Validation of the headline classifier is in `docs/validation-report.md`. On the adjudicated batch, both checked models agreed with the human label on 14 or 15 of 15 relevant headlines (93.3%, kappa 0.86). A later wording check on those same items scored 100%. That check is not independent: two rules were written from the same headlines. The hostile class in that audit is 4 headlines, so the bar is thin.

Limits:

- Western official lines are selected weeks, not full coverage. Russian official lines are from stored Russian state-media headlines.
- A Russian headline is shown only with an English line. The English line is first. The Russian original is smaller and grey.
- Per-country levels are not in the stored week table.
- The map uses public-domain Natural Earth outlines stored in this project. A dot stays for four weeks.
- The full backtest report has not been written. Do not treat this replay as that report.

Free collectors may keep running while paid calls stay off.

