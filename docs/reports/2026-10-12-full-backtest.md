# Full backtest report

Date: 2026-10-12. No model call. No post-hoc change.

Tag `backtest-run-prereg` is f09b985. The week table was written after that tag. The Intent baseline was not refit.

The Intent baseline was amended to `scoring-prereg-v2` before any real-data scoring run. The reason is the calibration window contains the 2021-05-24 spike. A mean would have treated that spike as normal. The center is the median. The scale is the median absolute deviation times 1.4826. Cutoffs stay 1.0, 1.5, 2.0, and 3.0. This run copied the stored Intent levels. It did not recompute them.

The saved O1 correction stays 3. It was not remapped to 1. Under `manual-scales-v3`, 3 means mostly free with notable commitments.

## Weekly table

The weekly table is `docs/reports/2026-10-12-backtest-weeks.csv`. It has 122 rows. Each region has 59 ranked full weeks, Mondays 2021-01-04 through 2022-02-14. The weeks of 2020-12-28 and 2022-02-21 are partial. They are in the table. They do not decide either test. Hybrid is empty on every row. Empty is no data, not zero.

## Verdicts

Test A: PASS. Ukraine shown overall level is at least Elevated on a ranked week before 2022-02-24.

Test B: FAIL. The eastern flank reaches a Serious proposal on a ranked week before 2022-02-24.

No week proposes Critical. No Serious or Critical level was confirmed. Each proposal is shown as Elevated, with the proposal named, not as plain Elevated, and not as Serious or Critical.

## First reach

Days are counted from that Monday to 2022-02-24. The count is a description. It is not a second pass rule.

Ukraine test:

1. Watchful: 2021-03-22, 339 days before. Inside the calibration window. First after the window: 2021-06-28, 241 days before.
2. Elevated: 2021-04-19, 311 days before. Inside the calibration window. First after the window: 2021-07-19, 220 days before.
3. Serious proposed: 2021-04-26, 304 days before. Inside the calibration window. First after the window: 2022-01-17, 38 days before.

Eastern flank:

1. Watchful: 2021-01-11, 409 days before. Inside the calibration window. First after the window: 2021-06-28, 241 days before.
2. Elevated: 2021-06-21, 248 days before. Inside the calibration window. First after the window: 2021-07-05, 234 days before.
3. Serious proposed: 2022-02-07, 17 days before. That week is after the calibration window.

## Deciding rows

These rows are copied from the week table. They are not a new score.

The week of 2021-04-19, Ukraine, is the first Elevated week. Intent 0. Capability 2, from near_ukraine 2. Opportunity 2, from O1 3 and O2 0. Proposed 2. Shown 2. Label Elevated.

The week of 2022-02-07, eastern flank, fails Test B. Intent 2. Capability 2, from belarus 2. Opportunity 2, from O1 3 and O2 0. Proposed 3. Shown 2. Label: Elevated (Serious proposed, awaiting confirmation).

Other Serious proposals, Ukraine only:

1. 2021-04-26. Intent 3, Capability 2, Opportunity 2. Proposed 3. Shown as Elevated, Serious proposed.
2. 2022-01-17. Intent 3, Capability 2, Opportunity 3. Proposed 3. Shown as Elevated, Serious proposed.
3. 2022-02-07. Intent 2, Capability 4, Opportunity 2. Proposed 3. Shown as Elevated, Serious proposed.

## Summary

The Intent baseline was amended to scoring-prereg-v2 before any real-data scoring run, because the calibration window contains the 2021-05-24 spike. This run did not refit it.

Test A passes. Ukraine's shown overall level reached Elevated on the week of 2021-04-19, a full week before 24 February 2022.

That first Elevated week is inside the calibration window. The first Elevated week after the window is 2021-07-19.

Test B fails. The eastern flank proposed Serious on the week of 2022-02-07.

That week was Intent 2, Capability 2, and Opportunity 2. Three elevated layers. It is shown as Elevated, with Serious proposed and not confirmed.

Opportunity 2 is the registered average of O1 3 and O2 0, rounded. The saved O1 correction stays 3. It was not remapped.

Hybrid is no data every week. There is no Critical proposal. Partial weeks did not decide either test.

No rule was changed after the table was written.

## Charts

xdg-open /home/supra/Projects/eastern-flank-monitor/docs/charts/eastern_flank-backtest.png

xdg-open /home/supra/Projects/eastern-flank-monitor/docs/charts/ukraine_test-backtest.png
