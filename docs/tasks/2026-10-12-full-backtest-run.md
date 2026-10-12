# Full backtest run

Saved 2026-10-12 before any work on this assignment. No API calls. Commit and push after each step. Do not commit unrelated local edits. Do not start the scoring run before the pre-registration tag.

The saved O1 correction stays 3. This assignment does not remap it.

## 0. Save this task

Save this file and commit it first.

## 1. Loader

One decision per manual entry. The latest click wins. The raw approved files stay unchanged as the audit trail. Test it with the duplicate O2 2021-01 row.

## 2. Pre-register

Before any run, write these rules in SPEC §8 and tag that commit `backtest-run-prereg`.

1. C2 region mapping by shared border: near_ukraine maps to ukraine_test. kaliningrad maps to eastern_flank. belarus and western_md map to both.
2. A C2 event holds for 4 weeks after its week unless superseded. The layer value is the max active event.
3. O1 is a step function. Each change-point holds until the next. Before the first one is no data.
4. O2 is monthly, as approved. Carried rows are values. Empty is no data.
5. Manual values 0–4 are used directly as levels.
6. Hybrid is no data.
7. Pass criteria. Test A passes if ukraine_test overall is at least Elevated in at least one full week before 2022-02-24. Test B passes if eastern_flank never reaches a Serious or Critical proposal before 2022-02-24. The Intent layer is exactly as scoring-prereg-v2.

## 3. Score

Run the full scoring for both regions, weekly. Each week has each layer level and the overall level. The convergence rule applies. An unconfirmed Serious or Critical is shown as "Elevated (… proposed, awaiting confirmation)".

## 4. Charts

One chart per region in docs/charts/. One panel per layer, plus the overall level. Event annotations and the invasion line. One xdg-open command per chart.

## 5. Report

Weekly table. Test A and Test B verdicts, PASS or FAIL, exactly by the criteria. The first week each region reached Watchful, Elevated, and Serious-proposed. A plain-language summary of at most 10 lines. Pre-registered results only. No post-hoc changes. Then stop.
