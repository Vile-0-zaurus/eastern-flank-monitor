# Manual approval stopped before the backtest

Date: 2026-10-11 20:44 EEST. No model call. The backtest was not started.

## Saved

main is even with origin. Tag manual-scales-v3 points at 928aafa.

- 274d6d1 saved the approval rows. 26 entries. Approved 24, corrected 2, rejected 0, unsure 0. One extra Approve row is a second click on O2 2021-01-01. It was left in place.
- 3362a7d saved the v3 assignment.
- 928aafa corrected the inverted O1 middle rungs, recorded the C2 value-4 rule, and recorded that future pages auto-acknowledge carried and empty rows.

The approval page on 127.0.0.1:8765 was stopped.

## Open point

The applied O1 value is the saved correction 3, not the draft value 1. The approved row was not rewritten. Under v3, 3 means mostly free with notable commitments. Under v2, 3 meant largely committed. The number was not remapped to 1. Confirm that meaning before the backtest if it is wrong.

## Next

The next step is the full backtest run. Do not start it until asked.
