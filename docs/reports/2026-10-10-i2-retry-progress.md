# I2 unavailable retry — progress, then stop

Date: 2026-10-10. Run id `i2-unavailable-retry`. Classifier still running. This is a progress report only. No scoring. No further spend from this session.

## Gate

Higher grok figure for 20,570 unavailable rows, batch size 50: expected $4.42, output-cap $6.10, retry gate $6.10. Approved cap is $6.10. The old $8 approval was not used. `config/llm.yaml` `hard_stop_usd` is still $1.00. The runner ceiling for new spend is $6.10 on top of the $1.2295 already in the answers spend table.

Status script, after two saved batches: $9.13 of the $10 xAI top-up remains. Anthropic is not part of that remainder.

Project key and the Hermes login were compared by name and fingerprint only. The project key is not in the Hermes process environment and not in a Hermes config key field.

## Service

Unit: `efm-i2-unavailable-retry.service`. `Restart=no`. No install section, so a reboot does not auto-spend. Linger is on, so a desktop logout does not stop it. After a reboot, once logged in: `systemctl --user start efm-i2-unavailable-retry.service`. Do not start a second copy.

Parent is the user systemd manager, not the chat process. Commit `d70f096` is on `main`.

## Stored counts

Checked against `data/llm/i2-answers.sqlite` at 12:05 EEST, after two new batches. The service is still running, so these counts will move.

1. grok-build-0.1 ok: 3,700. Was 3,600. The 100 new rows are the two saved batches.
2. grok-build-0.1 AI unavailable: 20,470. Was 20,570.
3. claude-sonnet-5-5 ok: 200. Unchanged. This retry does not call Sonnet.

First new spend line was `spent=1.2403`, continuing from the stored $1.2295, not from zero. Second line: `spent=1.2514`. New grok spend so far: $0.021983. Answers table grok total: $0.8134 across 74 spend rows.

## Rate and ETA

Started 12:01:47. First batch stored 12:03:12 (85s). Second stored 12:05:15 (123s later). 410 batches remain.

1. Pace so far, 104s per batch: about 11 hours 50 minutes.
2. Last gap, 123s: about 14 hours.
3. Projected new spend at the measured $0.010991 per batch: $4.53. That is under the $6.10 cap. It is an early rate, not a promise.

Circuit breaker and balance-stop are on. A stop or pause does not mark the current batch.

## Not done

I2 shares, precision correction, Intent levels, charts, and the validation-report line wait until every sample row has a real answer. A missing answer is not zero.
