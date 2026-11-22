# State

Updated: 22 November 2026. Public-repo prep is committed. The repo is still private.

## Where we stopped

22 November 2026. TASS is almost gone from the Now GDELT file after 16 September. The live job reads saved TASS RSS only when monitoring is on. Russian outlet rows are no longer region-filtered. History was not rewritten. The daily collector timers stay disabled. To turn them back on: `systemctl --user enable --now daily-collect.timer daily-collect-safety.timer`. LICENSE is MIT for the code. A personal-info scan was reported. History was not rewritten. A timed-out approval is skipped, not retried, and does not stop the task. The report ends with a Needs your approval list. Map icons have no native tooltip. The hover card sits beside the icon. Confirmed icons are solid white on a dark circle. Reported icons are an amber dashed outline. Country facts with a dated source are on the card. Capital-to-border distance is left out. Finland has no allied-troops line. Poland has no conscription line. The Now background poll is the 16 June 2026 Levada release. Replay keeps the 2021 poll. Finland has no overall share on that page. Checks are in tests/round3_selftest.py. Screenshots are in ~/Desktop/efm-check6/. No API calls.

22 November 2026. Polish round 2, part B is done. A briefing item is not repeated. Official items keep a side label. The Russia tab keeps one display-only line. The technical notes are under About, Method. The Russia fact card lists only facts with a dated source. Armed forces size, Uralvagonzavod, and Kalashnikov Concern are left out because no dated page was opened. Checks are in tests/russia_selftest.py and tests/briefing_selftest.py. Screenshots are in ~/Desktop/efm-check5/. No API calls.

22 November 2026. Polish round 2, part A is done. The map shows only the selected week and the four weeks before it. Icons are not merged into a count. Hover shows a card. A click opens that item in the briefing. Confirmed icons are solid. Reported icons are outlines. Checks are in tests/map_clarity_selftest.py. Screenshots are in ~/Desktop/efm-check5/.

22 November 2026. Polish round part 2 is done. A headline in "In the news" is not repeated in another briefing section. Near-duplicate stories are one item with every outlet listed. Official items show a translated side label. Checks are in tests/briefing_selftest.py. Screenshots are in ~/Desktop/efm-check4/.

22 November 2026. Polish round part 1 is done. Section 3 (quiet-week headline and fact card) is `add4066`. Incident icons stay 18 px on screen (`c217e9f`). Close icons cluster into a count badge (`4206358`). A country tab zooms to that country and Reset returns to the region (`b1f4e83`). Page version pin is `5eb5a13`. Map checks are in `tests/map_selftest.py`.

22 November 2026. ui-translate-1 finished for Lithuanian only. Real cost $0.087150 from API usage tokens. ui-translate-2 then stored Finnish, Estonian, Latvian, and Polish for $0.342260.

15 November 2026, evening. The page uses six tabs: Finland, Estonia, Latvia, Lithuania, Poland, Russia. One tab is always selected. The default is Lithuania. The right column is a fixed briefing. Pushed through 19d8e16. Refresh Brave so it loads ?v=6a27978. Screenshots are in ~/Desktop/efm-check2/.

The Now log has 11 incidents: Finland 3 drones, Estonia 1 sabotage, Latvia 3 drones, Lithuania 2 drones and 1 border, Poland 1 drone. GPS jamming and new cable or pipeline damage are empty. No dated 2026 Vilnius balloon closure was found.

The 2021–22 backfill is complete: 79,291 of 79,291 files, finished 9 October 2026. That service stays disabled. The backtest report is docs/backtest-report.md. Test A passed. No Serious or Critical level was confirmed. The stored week table was not rewritten.

Test B, pre-registered rules: FAIL. On the week of 7 February 2022 the eastern flank proposed Serious. Intent was 2. Capability was 2. Opportunity was 1.5, and the registered rule rounded 1.5 to 2. Three layers at Elevated made the proposal Serious. It was shown as Elevated, with the proposal named, not as Serious. It was not confirmed.

Test B, corrected rules, post-hoc, not pre-registered: not one result. The Belarus direction check, the no-rounding check, and the Capability floor each pass on their own. The first three checks still fail. Together, 52 of 63 combinations pass and 11 still fail. All six together pass: that week is a proposal of 2, not 3. Only the no-rounding rule was adopted, and only for the live app, tag live-rules-v1. It is not applied to the stored table.

## Next step

None. The repo stays private until you run the public command yourself. The collector timers are off.

## Open decisions

1. Whether to fill the empty Now gaps: dated GPS jamming, and new cable or pipeline damage. Last pass found neither.
2. Live retention in SPEC §14.6 is planned, not built. Do not build it unless an assignment says so.
3. Stage 2, a public site, is not started. The disclaimer has not had a legal review.
4. The project name is still a working title.
5. README’s milestone table is stale. It says the backtest and the dashboard were not started. Do not treat that table as current.
6. Main screen: user judged it not informative for an average user (Oct 2026). Decide: redesign, or ship as portfolio piece.
