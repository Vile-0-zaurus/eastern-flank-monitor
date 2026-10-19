# Storage rules

Saved 2026-10-19 before any other work on this assignment.

No API calls. Do not build the retention roll. Do not delete data. Do not rescore the stored week table. Do not move the pre-registered tags. Do not add outlets in this pass.

There was no open assignment with a Section 1 for storage. These rules are that section.

## Section 1 — storage

1. Regional and Western outlets: keep only rows whose title or location mentions Finland, Estonia, Latvia, Lithuania, Poland, the Baltics, Belarus, Kaliningrad, Russia, Ukraine, or NATO. Russian outlets: keep all rows, as before. Those rows are needed for the totals.
2. After the first day of data, report the stored size for that day. If a day exceeds 50 MB, stop and say so. Do not keep collecting past that day.
3. Live retention is planned in SPEC §14.6. Last 12 months stay in full. Older data rolls into weekly summaries. That roll is not built.

Russian outlets are the list in `config/outlets.yaml`. Regional and Western outlets are any other outlet a later collection keeps. This pass does not name that list and does not change the 2021–22 backfill.

## Measured, 2026-10-19

Read-only scan of `data/backtest/gkg.sqlite`. No new collection. This file is Russian outlets only, all rows, which is the current rule.

1. First day, 2021-01-01: 2,216 rows, 3.21 MB of stored text.
2. Largest day, 2021-11-24: 7,390 rows, 10.8 MB of stored text.
3. 420 days, 2021-01-01 through 2022-02-24. None exceed 50 MB. Collection was not stopped for size.
4. Stored text across all days is 3,025 MB. The file on disk is 3.8 GB. The gap is SQLite overhead, not extra rows.
