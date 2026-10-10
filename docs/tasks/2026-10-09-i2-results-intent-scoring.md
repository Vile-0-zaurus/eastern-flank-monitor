# I2 results and first Intent scoring run

Saved 2026-10-09 before any work. No new API spend. Do not change cutoffs, weights, or prompts.

Memory rule: stream and chunk. Never load gkg.sqlite fully. Stop if available memory is under 1.5 GB.

1. GATE: is the I2 classification run finished, all answers saved (missing = "AI unavailable")? If not: report progress + ETA, STOP.
2. Finish steps 6–9 of the previous task: I2 hostile share per region per week with 95% CI; Sonnet precision on the 200 flagged sample; actual spend; report to docs/reports/.
3. First scoring run, Intent layer only, using scoring-prereg-v2 exactly as tagged: weekly I1 level, I2 level, Intent layer level (0–4) for eastern_flank (Test B) and ukraine_test (Test A). Note: other layers are empty, so by the convergence rule the overall level can't exceed Watchful — report layer levels, not overall.
4. Charts (PNG, matplotlib, no GPU needed): one per region, weekly I1 share, I2 hostile share (with CI band), and Intent level, vertical line at 2022-02-24, shaded calibration period 2021-01..06. Save to docs/charts/. Give one xdg-open command per chart.
5. Plain-language summary (max 10 lines): when did each region's Intent level first reach 1, 2, 3, 4; how many weeks before 2022-02-24; any "false alarm" weeks for eastern_flank and what was happening then (only facts from the data, no speculation).
6. docs/validation-report.md: add limitation "prompt-v3-ukraine validated by AI judge only, no human audit".
7. Commit, push, STOP.
