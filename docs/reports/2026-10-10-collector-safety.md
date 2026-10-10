# Collector safety run

Date: 2026-10-10. The I2 retry was not stopped. Its unit stayed active, pid 12738, zero restarts.

## Today's feeds

The 06:15 slot was missed because the machine was off. The boot catch-up ran at 11:19 and every enabled source failed on DNS or connection errors. That job exited 0.

A second run at 14:39, after the connectivity wait, saved the enabled feeds. Connectivity check succeeded before the fetch. Disabled sources were not requested.

1. TASS English: saved. 50,035 bytes.
2. TASS Russian: saved. 65,225 bytes.
3. Baltic navigation warnings: saved. 10 Russian-origin warnings, 3,829 bytes.
4. RIA Novosti: skipped, disabled.
5. Russian foreign ministry: skipped, disabled.

Status now says those three were collected today and missed 0 days. It does not raise ACTION NEEDED for them.

## Code

Before a fetch, the collector waits until one enabled host resolves and one test request succeeds, for at most 60 minutes, then starts the normal fetch anyway. If every enabled source fails, the process exits 1. A same-day run does nothing when each enabled feed already has a saved file and a latest SUCCESS.

The oneshot timeout is 2 hours, above the wait plus the per-source retries. `daily-collect-safety.timer` is enabled, 18:00 local, Persistent=true. It calls the same service. If today's feeds are already saved, that run does not fetch.
