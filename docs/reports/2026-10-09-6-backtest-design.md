# Backtest design

Date: 2026-10-09. No model calls. No scoring run.

Tag to follow this commit: `backtest-design`.

SPEC §8 now has two tests. Both use `scoring-prereg-v2`. Neither has been run.

1. Test A, method validity, target `ukraine_test`. A useful method should rise before 2022-02-24. That tests whether the method can see a known buildup. It is not a claim about the eastern flank.
2. Test B, specificity, target `eastern_flank`. A useful method should not raise a war-level alarm in this window. The November 2021 Belarus crisis may show as a bump. A bump is not a failed specificity test. A war-level alarm is.

The backtest report, when it is written, must say that the baseline method was amended to `scoring-prereg-v2` before any real-data scoring run, and why: the calibration window contains the 2021-05-24 spike.
