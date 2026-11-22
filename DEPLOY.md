# Deploy notes

This is not a public site. Live monitoring stays off until you turn it on. The disclaimer has not had a legal review. Do not publish the site until that review is done.

## Service path

The user service files need an absolute path. systemd does not expand a tilde. `%h` means the home directory of the user who runs the service.

`systemd/user/daily-collect.service` and `systemd/user/efm-now-download.service` set:

`EFM_ROOT=%h/Projects/eastern-flank-monitor`

That is the default checkout. If the repo lives somewhere else, override the variable and reload:

1. `systemctl --user edit daily-collect.service`
2. Add `Environment=EFM_ROOT=/path/to/eastern-flank-monitor` under `[Service]`.
3. `systemctl --user daemon-reload`

The installed copies under the user systemd folder are separate from these repo files. Copy the unit again after a change if you want the running unit to match.

## Same job on a small Linux server

GitHub Actions can run a one-file dry-run. A full day is safer on a small server you control. The job is `scripts/live/daily_run.py`. It does not call a model while `live_monitoring` is off.

1. Clone the repo and create a virtualenv. Install `requests`.
2. Copy `systemd/user/efm-live.service` and `systemd/user/efm-live.timer` into `~/.config/systemd/user/`.
3. Set `EFM_ROOT` if the checkout is not in `~/Projects/eastern-flank-monitor`.
4. `systemctl --user daemon-reload`
5. Leave the timer disabled until the go-live checklist is done.
6. A manual check, with no model call: `python3 scripts/live/daily_run.py`
7. It should print that snapshot dates stay fixed.

## Go-live checklist

Do these in order. Stop if a step is unclear.

1. Have the disclaimer reviewed by a lawyer before any public site.
2. Set `monthly_cap_usd` in `config/budget.yaml` to a real-charge cap you can afford. `0` blocks every classification call.
3. Set `live_end_date` in `config/app.yaml`. The job refuses to run live without it. On that date the job stops, the countdown hides, and the page freezes with "Live monitoring ended <date>".
4. Switch `live_monitoring` to `on`.
5. Week one is a calibration. Compare the provider console charge with the estimate after the first small batch. If the real charge is higher, lower the cap before the next batch.
6. Each week, open `http://127.0.0.1:8765` after `python3 scripts/live/admin_server.py`. Approve, reject, or mark reported-only. Add a note. A draft never appears on the site. Aim for 20 minutes.
7. To stop early: set `live_monitoring` back to `off`, or set `live_end_date` to today, then `systemctl --user disable --now efm-live.timer`.

## TASS supplement

GDELT in the Now file almost stops carrying TASS after 16 September 2026. The count is in `docs/sources.md`. When live monitoring is on, `scripts/live/daily_run.py` reads the collector's already saved `tass-ru.xml.gz` and `tass-en.xml.gz` for that day. It does not fetch TASS itself. While live monitoring is off, those files are not added. The collector timers are still disabled, so a live day has a supplement only if a collector run has already saved that day.

## Costs already recorded

From `docs/budget.md`, not a live balance. xAI console readings: $0.72 then $3.54, total $4.26. Anthropic token-rate figures: $0.087150 then $0.342260, total $0.43. Recorded total: $4.69.

## Static site

The build copies `frontend/` to `site/` and leaves out `frontend/admin/`. `.github/workflows/pages.yml` can deploy that folder. It runs only when you start it by hand. It has not been run.
