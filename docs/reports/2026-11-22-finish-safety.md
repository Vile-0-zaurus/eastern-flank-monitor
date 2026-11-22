# Finish safety check

Date: 22 November 2026. Report only. History was not rewritten.

## Secret scan

Scanned all 184 commits on `main` and `origin/main`. Tags were included because `git rev-list --all` walks them. No other branches.

1. `.env` is in `.gitignore`. No commit has ever added `.env`.
2. No `sk-ant-` string in any committed file.
3. No token shaped like `sk-` plus 12 or more letters, and no `xai-` key longer than a test fixture.
4. `API_KEY` appears only as a variable name: `XAI_API_KEY` and `ANTHROPIC_API_KEY`. The value is read from the environment. It is not stored in the repo.
5. `Bearer` appears once, as a header built from that environment value, in `pipeline/llm/client.py`.
6. `xai-` appears in the log redaction rule and in a 19-character test fixture. That fixture is not a live key.
7. The letters `sk-` inside stored headlines are ordinary text, not keys.

The repo is private: `Vile-0-zaurus/eastern-flank-monitor`, visibility PRIVATE. It was not made public.

## What can run on its own

`live_monitoring` is off in `config/app.yaml`.

Enabled project timers, left on, asking before any change:

1. `daily-collect.timer` — 06:15 every day. Runs `scripts/m0/daily_collect.py`. Public page fetches only. No model call.
2. `daily-collect-safety.timer` — 18:00 every day. Runs the same free script again.

Already off:

1. `efm-now-download.service` — disabled. The Now window stays frozen.
2. `gkg-backfill.service` — disabled. The 2021–22 backfill stays finished.
3. `efm-ukraine-100-finish`, `efm-ukraine-calib-20`, and `efm-i2-unavailable-retry` are not enabled.

No user crontab. Desktop services (PipeWire, keyring, portals) were left alone. They do not call the project key.

`hermes-gateway.service` is enabled. It is the agent gateway, not an Eastern Flank job. It was not stopped.
