# I2 backtest classification

Saved 2026-10-09 before any work. Approved budget for this task only: up to $8 estimated, hard stop at $10 actual. Never print keys.

Memory rule: stream and chunk. Never load gkg.sqlite fully. Stop if available memory is under 1.5 GB.

1. ukraine_test keywords: add Киев/Kyiv/Kiev (all forms), Донбасс/Donbas, ДНР, ЛНР. Recompute ukraine_test I1, old vs new weekly. Note: region definition change, scoring rules unchanged.
2. Deduplicate stories across days (same URL or near-identical title = one story).
3. I2 sampling: per region per week, random sample of up to 200 stories (all if fewer), fixed random seed recorded in config.
4. Cost estimate: grok-build-0.1 on all samples (prompt-v3, caching) + Sonnet Batch API on a random 200 of grok-flagged-hostile headlines. If estimate > $8: report and STOP.
5. If ≤ $8: run it. Retries save answers; missing = "AI unavailable", never silent. Log spend.
6. Compute I2 per region per week: hostile share in the sample + 95% confidence interval. Store in the indicators table. Weekly tables for both regions; note the highest weeks.
7. Classifier precision: Sonnet's verdict on the 200 flagged sample → % where Sonnet agrees it's hostile.
8. docs/decisions.md: "2026-10-09 — DeepSeek considered as a cheaper classifier, not used: geopolitical sensitivity of the project domain; savings small after sampling."
9. Report to docs/reports/, commit, push, STOP.
