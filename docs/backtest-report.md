# Backtest report

Date: 2026-10-12. No model call. The pre-registered tags were not moved.

The week table is docs/reports/2026-10-12-backtest-weeks.csv. A no-change rerun matched the stored proposed level and the stored shown level on every ranked week. The post-hoc section uses that same join. It does not replace the table.

## Pre-registered results

These results are unchanged. Tag scoring-prereg-v2 set the Intent baseline before any real-data scoring run, because the calibration window contains the 2021-05-24 spike. Tag backtest-run-prereg is f09b985. It set the manual rules before this run. Neither tag is changed here.

Test A: PASS. Ukraine's shown overall level reached Elevated on the week of 2021-04-19. That is a full week before 2022-02-24.

The registered bar was lenient. Test A asks only for shown overall at least Elevated. It does not ask for a confirmed Serious or Critical alarm. The week of 2021-04-19 was a plain Elevated: Intent 0, Capability 2, Opportunity 2. It was not a Serious proposal.

Serious was still proposed, and no invasion followed the first of those proposals. The week of 2021-04-26 proposed Serious. That is April 2021. The full-scale invasion was not that spring. The week of 2022-01-17 proposed Serious again. That Monday is 38 days before 2022-02-24, five weeks and three days, about five weeks. Both proposals were shown as Elevated, not as Serious.

Test B: FAIL. The eastern flank proposed Serious on the week of 2022-02-07.

That week was Intent 2, Capability 2, and Opportunity 2. Capability 2 is the Belarus row for that week, mapped to both regions by the registered shared-border rule. Opportunity 2 is not a stored 2. O1 is the saved correction 3. O2 is 0. The average is 1.5. The registered layer rule rounds 1.5 to 2. Three layers were then at Elevated, so the proposal was Serious.

Human confirmation: Serious was proposed. It was never confirmed. The shown label is "Elevated (Serious proposed, awaiting confirmation)". The numeric shown level stays 2. There is no Critical proposal in the pre-registered table. No week is shown as Serious or Critical.

Hybrid is no data on every week. Empty is not zero, and it is not Calm.

## Post-hoc analyses

NOT pre-registered. Each check was run on its own. Combinations were run after that. None of these numbers replaces the table above.

A layer is elevated at 2 or above. A layer is strong at 3 or above. Test A still passes if one ranked Ukraine week has shown level at least 2. Test B still fails if one ranked eastern-flank week has proposed level 3 or 4. Partial weeks do not decide either test. Serious and Critical stay unconfirmed, so a proposal of 3 or 4 is still shown as 2.

### a. Max-indicator Intent

NOT pre-registered. Intent is the higher of the stored I1 level and the stored I2 level. The weighted average is not used.

Test A: PASS. Test B: FAIL.

Intent changes on 57 of 118 ranked weeks. The flank gains a second Serious proposal, the week of 2022-02-14. Stored Intent that week is 1. The max is 2, because I1 is 2 and I2 is 0. Capability is 4 and Opportunity is 2, so three layers are elevated. The week of 2022-02-07 also stays a Serious proposal, with Intent raised from 2 to 3. This check makes the flank alarm larger. It does not remove it.

### b. Hostile count instead of share

NOT pre-registered. I2 is the weekly hostile count, not the share. Each region is fit on its own 25 calibration weeks, median and median absolute deviation times 1.4826. The same cutoffs are used. I1 stays the share. Intent is then the registered weighted average.

Eastern flank count baseline: median 24, scale 4.4478. Ukraine count baseline: median 29, scale 4.4478. Both scales are a median absolute deviation of 3 times 1.4826.

Test A: PASS. Test B: FAIL.

On every ranked week, the count-based I2 level equals the stored share-based I2 level. Intent does not change. The verdicts do not change. A short draw can lower a count. That did not move a ranked level in this window.

### c. Ukraine alternative calibration window

NOT pre-registered. Ukraine's median and scale are refit on the calibration weeks whose Monday is not in March or April 2021. Nine weeks are left out: 2021-03-01 through 2021-04-26. Sixteen weeks remain. The eastern flank baseline is not refit. Cutoffs and weights are not changed.

Ukraine share baseline on those 16 weeks: I1 median 0.0247, scale 0.0045. I2 median 0.3050, scale 0.0297. The registered 25-week baseline was I1 median 0.0271, scale 0.0059, and I2 median 0.2900, scale 0.0445.

Test A: PASS. Test B: FAIL.

Seventeen ranked Ukraine Intent levels change. The flank is unchanged, so Test B still fails on 2022-02-07. Ukraine's first Elevated week is still 2021-04-19. The April and January Serious proposals remain.

### d. Belarus by deployment direction

NOT pre-registered. Corrected 2026-10-12 from the source text, not the note. Southern Belarus maps to ukraine_test only. The other four rows still use the stored note, because this correction named one page.

The BBC page dated 10 February 2022 says the Allied Resolve drills take place close to the Belarusian border with Ukraine. That page is the source for the Belarus row dated 2022-02-07. The stored note did not use that sentence. The source text does. That row is southern. It maps to ukraine_test only.

1. 2022-02-07. Source text: Allied Resolve takes place close to the Belarusian border with Ukraine. Southern. Ukraine only.
2. 2022-02-14. The note says field hospitals near the Belarusian border with Ukraine. Southern. Ukraine only.
3. 2022-02-21. The note says an airfield near Mozyr, less than 40 km from Ukraine. Southern. Ukraine only.
4. 2021-09-20. The note says western Belarus. It does not mention Ukraine. Western. Eastern flank only.
5. 2022-01-17. The note gives no direction. The registered both-mapping stays.

Test A: PASS. Test B: PASS.

The registered both-mapping had given the flank Capability 2 on 2022-02-07. That event no longer maps to the flank. The 17 January row is still inside its four-week hold, at level 1, which is not elevated. Intent is 2 and Opportunity is 2, so the proposal is 2, not 3.

Three weeks change. On 2022-02-07 flank Capability falls from 2 to 1. On 2022-02-14 it falls from 4 to 1, because the southern event is removed and the January hold is still active. On the partial week of 2022-02-21 it falls from 2 to no data. That partial week does not decide the test.

### e. No rounding

NOT pre-registered. Layer averages are kept as decimals. A layer is elevated only when the exact value is at least 2. A layer is strong only when the exact value is at least 3. 1.5 is not elevated. Intent is the unrounded weighted average of the stored I1 and I2 levels. Opportunity is the unrounded average of O1 and O2.

Test A: PASS. Test B: PASS.

On the week of 2022-02-07 the flank is Intent 2.333, Capability 2, and Opportunity 1.5. Intent is still elevated. Opportunity is not. Two layers are elevated, not three. The proposal is 2, not 3. Test B passes because the rounded third layer is gone.

Ukraine's week of 2021-04-19 is no longer Elevated. Intent is 0.333. Capability is 2. Opportunity is 1.5. One layer is elevated, so the week stays Watchful. The first Elevated week moves to 2021-04-26. Test A still passes. Ranked Ukraine weeks at shown Elevated fall from 22 to 10.

### f. Serious requires Capability at least 3

NOT pre-registered. If the registered rule would propose 3 or 4 and Capability is below 3, the proposal is capped at 2. The shown level stays 2. The confirmation gate is not removed.

Test A: PASS. Test B: PASS.

The flank week of 2022-02-07 has Capability 2, so the Serious proposal is capped. Test B passes. Ukraine's April and January Serious proposals are also capped, because Capability is 2. The Ukraine week of 2022-02-07 keeps a Serious proposal, because Capability is 4. Test A still passes on the plain Elevated week of 2021-04-19, which this cap does not touch.

### Combined

NOT pre-registered. All 63 non-empty combinations were scored. A combination applies the named checks together. Where two checks touch Intent, the alternative window and the count are fit first, and the max is taken after that if max-indicator is also on. The Belarus map is applied before the Serious cap. No rounding is applied to whatever average that combination still uses.

Test A does not fail in any combination.

Test B passes in 52 combinations. It still fails in the other 11. Every combination that includes the corrected Belarus map passes Test B. The map removes the Capability 2 that had made 2022-02-07 a Serious proposal.

It still fails in a, b, c, and every combination of those three. Those checks do not move the Belarus row.

It also still fails in a+f, a+b+f, a+c+f, and a+b+c+f. Those keep the registered Belarus map. Max-indicator raises the flank week of 2022-02-14 to a Serious proposal with Capability 4. The Capability floor does not remove a week whose Capability is already at least 3.

All six together: Test A PASS, Test B PASS. The flank week of 2022-02-07 is Intent 3, Capability 1, Opportunity 1.5. Capability 1 is the January hold. It is not elevated. Opportunity is below 2. The proposal is 2.

## Rules for the live app

These proposals were learned from 2021-22. They must be validated on future data. They are not applied to the stored table. The pre-registered tags stay where they are.

1. Keep the human confirmation gate. It is already registered. Serious was proposed. It was not confirmed. The live app should keep showing that as Elevated, with the proposal named.
2. Propose one later rule: do not round a layer average up to the next level. 1.5 is not 2. This was learned here because that rounding created the third elevated layer on the week Test B failed. Write it in a new envelope before the next test window. Do not use it to change this score.
3. Do not adopt max-indicator aggregation. On this window it added a flank Serious proposal. The volume-spike reading stays a separate note. It is not a live rule.
4. Do not adopt hostile count instead of share. It changed no ranked Intent level.
5. Do not adopt the alternative Ukraine calibration window. The window was chosen after the result. The registered baseline stays.
6. Do not adopt the Belarus direction map for the stored table. The source-text version is still not pre-registered. It would pass Test B, because the BBC page places the 7 February drills close to the Belarusian border with Ukraine. That was learned from this window. It stays a candidate for a future envelope. It does not change this score.
7. Do not adopt a rule that Serious requires Capability at least 3. It removes the only pre-registered flank Serious proposal. Adopting it from this result would fit the rule to the failed test. The confirmation gate already stops that proposal from being shown as Serious.

## Portfolio summary

The app is a weather station. It reads public instruments and shows the picture. It is not a siren, and it does not tell you what to do.

The 2021-22 run was the smoke-detector check. Ukraine is the fire. The eastern flank is the toast.

The rules were in a sealed envelope before the run. This report reads that result. It does not rewrite the envelope.

Test A passed. Ukraine reached Elevated on the week of 19 April 2021, before 24 February 2022.

The bar was low. Elevated was enough. Serious was proposed in April 2021, with no invasion, and again in January 2022. It was never confirmed.

Test B failed. On the week of 7 February 2022 the flank proposed Serious. Intent and Capability were both elevated. Opportunity was counted only because 1.5 was rounded to 2.

Two witnesses can raise the level above Watchful. An empty layer is not a witness. Hybrid had no data.

No war followed in Finland, Estonia, Latvia, Lithuania, or Poland. That is the toast check failing.

A temperature is read against the registered normal, not against a chart drawn after the result. The baseline was not refit.

Later checks sit beside this result. They are not the result. A new rule has to be tested on later weeks. It cannot change this score.
