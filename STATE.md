# State

Updated: 14 November 2026. Product stop: a4f246f. These two files are the session notes added after that commit. Not pushed.

## Where we stopped

The last assignment closed on 27 October 2026. The Now window is frozen at 3 August 2026 through 25 October 2026. The Now download finished and is disabled. It will not start on boot.

The Now log has 11 incidents: Finland 3 drones, Estonia 1 sabotage, Latvia 3 drones, Lithuania 2 drones and 1 border, Poland 1 drone. GPS jamming and new cable or pipeline damage are empty. No dated 2026 Vilnius balloon closure was found.

The 2021–22 backfill is complete: 79,291 of 79,291 files, finished 9 October 2026. That service stays disabled. The backtest report is docs/backtest-report.md. Test A passed. No Serious or Critical level was confirmed. The stored week table was not rewritten.

Test B, pre-registered rules: FAIL. On the week of 7 February 2022 the eastern flank proposed Serious. Intent was 2. Capability was 2. Opportunity was 1.5, and the registered rule rounded 1.5 to 2. Three layers at Elevated made the proposal Serious. It was shown as Elevated, with the proposal named, not as Serious. It was not confirmed.

Test B, corrected rules, post-hoc, not pre-registered: not one result. The Belarus direction check, the no-rounding check, and the Capability floor each pass on their own. The first three checks still fail. Together, 52 of 63 combinations pass and 11 still fail. All six together pass: that week is a proposal of 2, not 3. Only the no-rounding rule was adopted, and only for the live app, tag live-rules-v1. It is not applied to the stored table.

## Next step

Fix README milestone table to match reports (L1).

## Open decisions

1. Whether to fill the empty Now gaps: dated GPS jamming, and new cable or pipeline damage. Last pass found neither.
2. Live retention in SPEC §14.6 is planned, not built. Do not build it unless an assignment says so.
3. Stage 2, a public site, is not started. The disclaimer has not had a legal review.
4. The project name is still a working title.
5. README’s milestone table is stale. It says the backtest and the dashboard were not started. Do not treat that table as current.
6. Main screen: user judged it not informative for an average user (Oct 2026). Decide: redesign, or ship as portfolio piece.
