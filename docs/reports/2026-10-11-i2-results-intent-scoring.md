# I2 results and first Intent scoring

Date: 2026-10-11. No model call in this step. Classifier unit efm-ukraine-100-finish is inactive, Result=success. Cutoffs, weights, and prompts were not changed.

This is the first real-data scoring run under scoring-prereg-v2. The baseline method was amended to that tag before any real-data scoring run. The reason is the calibration window contains the 2021-05-24 spike. A mean would have treated that spike as normal. The center is the median. The scale is the median absolute deviation times 1.4826. Cutoffs stay 1.0, 1.5, 2.0, and 3.0.

## Gate

Every named sample row has one real grok-build-0.1 answer. Status is ok. hostile_framing is stored. Missing answers are zero. No named row has both ok and AI unavailable.

1. Ukraine 100/week subset: 6,100 of 6,100 ok. Before the finish run: 1,000 ok and 5,100 pending.
2. Eastern flank 200/week, sampled=1: 11,987 of 11,987 ok. Before: 11,700 ok and 287 pending.
3. 6,083 other Ukraine rows are still AI unavailable. They are outside the 100/week subset and were left out of both the numerator and the denominator.

I1 rows were not rewritten. indicators.sqlite still has 420 I1 rows and 420 I1_ukraine_test rows. I2 was written as 61 weeks per region. Checked sums: eastern flank 1,524 hostile of 11,987 classified. Ukraine 1,852 hostile of 6,100 classified.

## Method

Weekly I1 share is the week's sums divided, not the mean of daily shares. Week 2021-05-24 is 810 of 38,731, share 0.0209, which matches the stored I1 note.

Weekly I2 share is hostile yes divided by classified answers in that week's sample. A stored answer with hostile_framing is classified. AI unavailable is left out. No classified rows would be no data, not zero. None of these weeks were empty. The interval is the 95% Wilson interval from the existing function, z=1.96.

The baseline is the 25 full weeks fully inside 2021-01-01 through 2021-06-30. That is Monday 2021-01-04 through Monday 2021-06-21. A week with fewer than 7 in-window days is partial and is not ranked. Those weeks are 2020-12-28 and 2022-02-21. The date 2022-02-24 falls in the second of those, so it is not ranked against a 7-day week.

config/model.yaml also has a rolling 180-day window and a minimum of 30 points. A 180-day window holds about 25 weekly points, so that gate would make every weekly level no data. The levels below use the tagged calibration window, not that rolling gate. Cutoffs and weights were not changed. This note is the required report of how the tagged method was applied.

I3 has no rows. It is left out, not scored as zero. Intent level is the weighted average of the I1 level (weight 1) and the I2 level (weight 2), rounded, then clamped to 0-4. Capability, Opportunity, and Hybrid are empty, not zero. By the convergence rule the overall level cannot rise above Watchful. This report gives layer levels, not an overall level.

Three eastern flank weeks are full weeks with a short draw: 2021-01-04 (144), 2021-05-10 (192), and 2022-01-03 (194). They are scored. They are not partial. None of them reached Intent 2.

## Precision

The stored Sonnet judge sample is 200 eastern flank rows. Every one of them was grok hostile yes, and every one is in the 200/week sample. Sonnet said yes 123, no 71, unsure 6. Precision is yes divided by yes plus no: 123/194 = 0.6340. Unsure is not in that denominator.

Precision-corrected I2 share is the raw share times 0.6340. The same factor scales the calibration median and the scale, so the I2 level and the Intent level do not change. Checked on week 2021-11-22: raw 0.2450, corrected 0.1553, ratio 0.6340.

Ukraine precision was not measured. The flank factor was not applied to Ukraine.

## Spend

No call was made for this report.

ukraine-100-finish, recorded ticks: 35,448,122,000, which is $3.5448122, on 109 rows. Console balance before: $14.29. After: $10.75. Real cost from those readings: $3.54. The $0.0048122 difference was not closed by inventing tokens. Detail is in docs/budget.md.

Earlier grok-build-0.1 spend rows have no run id and no ticks: 255 rows, tracker usd $2.805212. That figure is the old tracker, not a console balance. Sonnet spend rows have no ticks: 200 rows, stored usd $0.438071.

## Baselines

Eastern flank, 25 weeks: I1 median 0.0086, scale 0.0022. I2 median 0.1200, scale 0.0222.

Ukraine test, 25 weeks: I1 median 0.0271, scale 0.0059. I2 median 0.2900, scale 0.0445.

A zero scale did not occur.

## First reach

Days are counted from the week Monday to 2022-02-24. Each of these Mondays is 3 days plus a whole number of weeks before that Thursday.

Eastern flank, first ranked week at or above the level:

1. Level 1: 2021-01-11, 58 weeks and 3 days before. Inside the calibration window.
2. Level 2: 2021-03-15, 49 weeks and 3 days before. Inside the calibration window.
3. Level 3: 2021-07-26, 30 weeks and 3 days before.
4. Level 4: 2021-11-22, 13 weeks and 3 days before.

First eastern flank week after the baseline window: level 1 on 2021-06-28 (34 weeks and 3 days), level 2 on 2021-07-05 (33 weeks and 3 days). Levels 3 and 4 are the same weeks as above.

Ukraine test:

1. Levels 1, 2, and 3 first occur in the same week, 2021-03-22, 48 weeks and 3 days before. That week is inside the calibration window. I1 level was 0. I2 was 43 of 100, level 4. Intent rounded to 3.
2. Level 4: never, on a ranked week.
3. After the baseline window: level 1 on 2021-06-28 (34 weeks and 3 days), level 2 on 2021-07-19 (31 weeks and 3 days), level 3 on 2021-08-23 (26 weeks and 3 days).

The registered specificity note says a bump is not a failed test, and a war-level alarm is. War-level here means Intent 3 or 4. The eastern flank series does reach those levels. That is what the stored weeks show.

## Eastern flank weeks at Intent 2 or higher

Twelve full weeks. Two are inside the calibration window. Five are Intent 3 or 4.

1. 2021-03-15, Intent 2, inside the window. I1 share 0.0075, level 0. I2 35 of 200, share 0.1750, level 3. The level is from I2.
2. 2021-06-21, Intent 2, inside the window. I1 share 0.0073, level 0. I2 36 of 200, share 0.1800, level 3.
3. 2021-07-05, Intent 2. I1 share 0.0133, level 3. I2 32 of 200, share 0.1600, level 2.
4. 2021-07-19, Intent 2. I1 share 0.0091, level 0. I2 34 of 200, share 0.1700, level 3.
5. 2021-07-26, Intent 3. I1 share 0.0082, level 0. I2 48 of 200, share 0.2400, level 4. Stored hostile titles name Poland and Nord Stream 2, Estonia and language, and Ukrainian migration to Poland. Frame counts among the 48: F7_other 31, F5 11, F2 5.
6. 2021-08-02, Intent 3. I1 share 0.0160, level 4. I2 33 of 200, share 0.1650, level 3. Stored hostile titles name Poland and Nord Stream 2, Lithuania and migrants at the Belarus border, and Estonia.
7. 2021-11-01, Intent 2. I1 share 0.0091, level 0. I2 37 of 200, share 0.1850, level 3. Stored hostile titles name Estonia, Latvia, and a journalist case.
8. 2021-11-08, Intent 3. I1 share 0.0358, level 4. This is the highest full-week I1 share in the earlier I1 note. I2 32 of 200, share 0.1600, level 2. Stored hostile titles name Belarus, shots from the Poland side, a migration crisis, and Poland.
9. 2021-11-15, Intent 3. I1 share 0.0291, level 4. I2 36 of 200, share 0.1800, level 3. Stored hostile titles name Poland, the Belarus border, and migrants.
10. 2021-11-22, Intent 4. The only level 4 week. I1 share 0.0172, level 4. I2 49 of 200, share 0.2450, Wilson 0.1906 to 0.3090, level 4. Stored hostile titles name Lukashenko, refugees, Poland, Germany, and Belarus. Frame counts among the 49: F7_other 29, F5 17.
11. 2021-12-20, Intent 2. I1 share 0.0111, level 1. I2 35 of 200, share 0.1750, level 3.
12. 2022-02-07, Intent 2. I1 share 0.0138, level 3. I2 31 of 200, share 0.1550, level 2.

Week 2021-05-24 is the I1 spike, share 0.0209, I1 level 4. I2 that week is 21 of 200, share 0.1050, level 0. Intent is 1. It is not in the list above.

The November titles are quotes of what the stored headlines name. They are not a claim about cause.

## Charts

One file per region. Grey band is 2021-01-01 through 2021-06-30. Vertical line is 2022-02-24, labeled Invasion. Event labels are notes, not a rescore: Ryanair/Minsk on 2021-05-23, Lithuania border crisis in July 2021, Poland border crisis in November 2021, and the spring 2021 buildup in March–April. The last partial week is a dotted segment and is not ranked. The fourth panel is the raw hostile count. I2 panel is the raw share and the Wilson band. Eastern flank also has the precision-corrected line. Ukraine is marked precision not measured. Drawn with matplotlib from the project venv. No GPU. No model call.

1. xdg-open /home/supra/Projects/eastern-flank-monitor/docs/charts/eastern_flank-intent.png
2. xdg-open /home/supra/Projects/eastern-flank-monitor/docs/charts/ukraine_test-intent.png

Week rows checked against indicators.sqlite are also in docs/reports/2026-10-11-i2-weeks.csv. Corrected column is blank for Ukraine.

## Week table

Corrected is raw times 0.6340 for eastern flank only. A blank Intent cell is a partial week and was not ranked.
## Eastern flank weeks

week | partial | I1 share | I1 level | hostile | classified | I2 share | low | high | corrected | I2 level | Intent
---|---|---|---|---|---|---|---|---|---|---|---
2020-12-28 | yes | 0.0087 |  | 13 | 57 | 0.2281 | 0.1384 | 0.3521 | 0.1446 |  | 
2021-01-04 |  | 0.0075 | 0 | 10 | 144 | 0.0694 | 0.0382 | 0.1231 | 0.0440 | 0 | 0
2021-01-11 |  | 0.0069 | 0 | 29 | 200 | 0.1450 | 0.1029 | 0.2005 | 0.0919 | 1 | 1
2021-01-18 |  | 0.0062 | 0 | 21 | 200 | 0.1050 | 0.0697 | 0.1552 | 0.0666 | 0 | 0
2021-01-25 |  | 0.0066 | 0 | 20 | 200 | 0.1000 | 0.0657 | 0.1494 | 0.0634 | 0 | 0
2021-02-01 |  | 0.0093 | 0 | 28 | 200 | 0.1400 | 0.0987 | 0.1949 | 0.0888 | 0 | 0
2021-02-08 |  | 0.0093 | 0 | 27 | 200 | 0.1350 | 0.0945 | 0.1893 | 0.0856 | 0 | 0
2021-02-15 |  | 0.0086 | 0 | 19 | 200 | 0.0950 | 0.0617 | 0.1436 | 0.0602 | 0 | 0
2021-02-22 |  | 0.0071 | 0 | 21 | 200 | 0.1050 | 0.0697 | 0.1552 | 0.0666 | 0 | 0
2021-03-01 |  | 0.0082 | 0 | 18 | 200 | 0.0900 | 0.0577 | 0.1378 | 0.0571 | 0 | 0
2021-03-08 |  | 0.0098 | 0 | 22 | 200 | 0.1100 | 0.0738 | 0.1609 | 0.0697 | 0 | 0
2021-03-15 |  | 0.0075 | 0 | 35 | 200 | 0.1750 | 0.1286 | 0.2336 | 0.1110 | 3 | 2
2021-03-22 |  | 0.0070 | 0 | 20 | 200 | 0.1000 | 0.0657 | 0.1494 | 0.0634 | 0 | 0
2021-03-29 |  | 0.0086 | 0 | 26 | 200 | 0.1300 | 0.0903 | 0.1837 | 0.0824 | 0 | 0
2021-04-05 |  | 0.0082 | 0 | 24 | 200 | 0.1200 | 0.0820 | 0.1723 | 0.0761 | 0 | 0
2021-04-12 |  | 0.0112 | 1 | 24 | 200 | 0.1200 | 0.0820 | 0.1723 | 0.0761 | 0 | 0
2021-04-19 |  | 0.0109 | 0 | 26 | 200 | 0.1300 | 0.0903 | 0.1837 | 0.0824 | 0 | 0
2021-04-26 |  | 0.0097 | 0 | 24 | 200 | 0.1200 | 0.0820 | 0.1723 | 0.0761 | 0 | 0
2021-05-03 |  | 0.0126 | 2 | 28 | 200 | 0.1400 | 0.0987 | 0.1949 | 0.0888 | 0 | 1
2021-05-10 |  | 0.0063 | 0 | 24 | 192 | 0.1250 | 0.0855 | 0.1793 | 0.0793 | 0 | 0
2021-05-17 |  | 0.0097 | 0 | 31 | 200 | 0.1550 | 0.1114 | 0.2116 | 0.0983 | 2 | 1
2021-05-24 |  | 0.0209 | 4 | 21 | 200 | 0.1050 | 0.0697 | 0.1552 | 0.0666 | 0 | 1
2021-05-31 |  | 0.0108 | 0 | 24 | 200 | 0.1200 | 0.0820 | 0.1723 | 0.0761 | 0 | 0
2021-06-07 |  | 0.0108 | 0 | 27 | 200 | 0.1350 | 0.0945 | 0.1893 | 0.0856 | 0 | 0
2021-06-14 |  | 0.0114 | 1 | 19 | 200 | 0.0950 | 0.0617 | 0.1436 | 0.0602 | 0 | 0
2021-06-21 |  | 0.0073 | 0 | 36 | 200 | 0.1800 | 0.1329 | 0.2391 | 0.1141 | 3 | 2
2021-06-28 |  | 0.0090 | 0 | 29 | 200 | 0.1450 | 0.1029 | 0.2005 | 0.0919 | 1 | 1
2021-07-05 |  | 0.0133 | 3 | 32 | 200 | 0.1600 | 0.1157 | 0.2171 | 0.1014 | 2 | 2
2021-07-12 |  | 0.0083 | 0 | 16 | 200 | 0.0800 | 0.0498 | 0.1260 | 0.0507 | 0 | 0
2021-07-19 |  | 0.0091 | 0 | 34 | 200 | 0.1700 | 0.1243 | 0.2282 | 0.1078 | 3 | 2
2021-07-26 |  | 0.0082 | 0 | 48 | 200 | 0.2400 | 0.1861 | 0.3037 | 0.1522 | 4 | 3
2021-08-02 |  | 0.0160 | 4 | 33 | 200 | 0.1650 | 0.1200 | 0.2227 | 0.1046 | 3 | 3
2021-08-09 |  | 0.0156 | 4 | 27 | 200 | 0.1350 | 0.0945 | 0.1893 | 0.0856 | 0 | 1
2021-08-16 |  | 0.0092 | 0 | 22 | 200 | 0.1100 | 0.0738 | 0.1609 | 0.0697 | 0 | 0
2021-08-23 |  | 0.0107 | 0 | 30 | 200 | 0.1500 | 0.1071 | 0.2061 | 0.0951 | 1 | 1
2021-08-30 |  | 0.0094 | 0 | 13 | 200 | 0.0650 | 0.0384 | 0.1080 | 0.0412 | 0 | 0
2021-09-06 |  | 0.0098 | 0 | 13 | 200 | 0.0650 | 0.0384 | 0.1080 | 0.0412 | 0 | 0
2021-09-13 |  | 0.0098 | 0 | 22 | 200 | 0.1100 | 0.0738 | 0.1609 | 0.0697 | 0 | 0
2021-09-20 |  | 0.0091 | 0 | 19 | 200 | 0.0950 | 0.0617 | 0.1436 | 0.0602 | 0 | 0
2021-09-27 |  | 0.0072 | 0 | 26 | 200 | 0.1300 | 0.0903 | 0.1837 | 0.0824 | 0 | 0
2021-10-04 |  | 0.0103 | 0 | 24 | 200 | 0.1200 | 0.0820 | 0.1723 | 0.0761 | 0 | 0
2021-10-11 |  | 0.0080 | 0 | 15 | 200 | 0.0750 | 0.0460 | 0.1200 | 0.0476 | 0 | 0
2021-10-18 |  | 0.0129 | 2 | 27 | 200 | 0.1350 | 0.0945 | 0.1893 | 0.0856 | 0 | 1
2021-10-25 |  | 0.0142 | 3 | 25 | 200 | 0.1250 | 0.0861 | 0.1780 | 0.0793 | 0 | 1
2021-11-01 |  | 0.0091 | 0 | 37 | 200 | 0.1850 | 0.1373 | 0.2446 | 0.1173 | 3 | 2
2021-11-08 |  | 0.0358 | 4 | 32 | 200 | 0.1600 | 0.1157 | 0.2171 | 0.1014 | 2 | 3
2021-11-15 |  | 0.0291 | 4 | 36 | 200 | 0.1800 | 0.1329 | 0.2391 | 0.1141 | 3 | 3
2021-11-22 |  | 0.0172 | 4 | 49 | 200 | 0.2450 | 0.1906 | 0.3090 | 0.1553 | 4 | 4
2021-11-29 |  | 0.0130 | 2 | 22 | 200 | 0.1100 | 0.0738 | 0.1609 | 0.0697 | 0 | 1
2021-12-06 |  | 0.0125 | 2 | 18 | 200 | 0.0900 | 0.0577 | 0.1378 | 0.0571 | 0 | 1
2021-12-13 |  | 0.0124 | 2 | 27 | 200 | 0.1350 | 0.0945 | 0.1893 | 0.0856 | 0 | 1
2021-12-20 |  | 0.0111 | 1 | 35 | 200 | 0.1750 | 0.1286 | 0.2336 | 0.1110 | 3 | 2
2021-12-27 |  | 0.0095 | 0 | 23 | 200 | 0.1150 | 0.0779 | 0.1666 | 0.0729 | 0 | 0
2022-01-03 |  | 0.0102 | 0 | 18 | 194 | 0.0928 | 0.0595 | 0.1419 | 0.0588 | 0 | 0
2022-01-10 |  | 0.0121 | 2 | 22 | 200 | 0.1100 | 0.0738 | 0.1609 | 0.0697 | 0 | 1
2022-01-17 |  | 0.0113 | 1 | 29 | 200 | 0.1450 | 0.1029 | 0.2005 | 0.0919 | 1 | 1
2022-01-24 |  | 0.0102 | 0 | 21 | 200 | 0.1050 | 0.0697 | 0.1552 | 0.0666 | 0 | 0
2022-01-31 |  | 0.0160 | 4 | 19 | 200 | 0.0950 | 0.0617 | 0.1436 | 0.0602 | 0 | 1
2022-02-07 |  | 0.0138 | 3 | 31 | 200 | 0.1550 | 0.1114 | 0.2116 | 0.0983 | 2 | 2
2022-02-14 |  | 0.0130 | 2 | 28 | 200 | 0.1400 | 0.0987 | 0.1949 | 0.0888 | 0 | 1
2022-02-21 | yes | 0.0134 |  | 5 | 200 | 0.0250 | 0.0107 | 0.0572 | 0.0159 |  | 

## Ukraine test weeks

week | partial | I1 share | I1 level | hostile | classified | I2 share | low | high | corrected | I2 level | Intent
---|---|---|---|---|---|---|---|---|---|---|---
2020-12-28 | yes | 0.0283 |  | 32 | 100 | 0.3200 | 0.2367 | 0.4166 |  |  | 
2021-01-04 |  | 0.0200 | 0 | 26 | 100 | 0.2600 | 0.1840 | 0.3537 |  | 0 | 0
2021-01-11 |  | 0.0197 | 0 | 32 | 100 | 0.3200 | 0.2367 | 0.4166 |  | 0 | 0
2021-01-18 |  | 0.0190 | 0 | 30 | 100 | 0.3000 | 0.2189 | 0.3959 |  | 0 | 0
2021-01-25 |  | 0.0214 | 0 | 29 | 100 | 0.2900 | 0.2101 | 0.3854 |  | 0 | 0
2021-02-01 |  | 0.0255 | 0 | 20 | 100 | 0.2000 | 0.1334 | 0.2888 |  | 0 | 0
2021-02-08 |  | 0.0239 | 0 | 33 | 100 | 0.3300 | 0.2456 | 0.4269 |  | 0 | 0
2021-02-15 |  | 0.0239 | 0 | 31 | 100 | 0.3100 | 0.2278 | 0.4063 |  | 0 | 0
2021-02-22 |  | 0.0300 | 0 | 29 | 100 | 0.2900 | 0.2101 | 0.3854 |  | 0 | 0
2021-03-01 |  | 0.0254 | 0 | 24 | 100 | 0.2400 | 0.1669 | 0.3323 |  | 0 | 0
2021-03-08 |  | 0.0293 | 0 | 31 | 100 | 0.3100 | 0.2278 | 0.4063 |  | 0 | 0
2021-03-15 |  | 0.0287 | 0 | 28 | 100 | 0.2800 | 0.2014 | 0.3749 |  | 0 | 0
2021-03-22 |  | 0.0228 | 0 | 43 | 100 | 0.4300 | 0.3373 | 0.5278 |  | 4 | 3
2021-03-29 |  | 0.0369 | 2 | 23 | 100 | 0.2300 | 0.1584 | 0.3215 |  | 0 | 1
2021-04-05 |  | 0.0551 | 4 | 29 | 100 | 0.2900 | 0.2101 | 0.3854 |  | 0 | 1
2021-04-12 |  | 0.0422 | 3 | 28 | 100 | 0.2800 | 0.2014 | 0.3749 |  | 0 | 1
2021-04-19 |  | 0.0336 | 1 | 29 | 100 | 0.2900 | 0.2101 | 0.3854 |  | 0 | 0
2021-04-26 |  | 0.0311 | 0 | 44 | 100 | 0.4400 | 0.3467 | 0.5377 |  | 4 | 3
2021-05-03 |  | 0.0375 | 2 | 35 | 100 | 0.3500 | 0.2636 | 0.4475 |  | 1 | 1
2021-05-10 |  | 0.0275 | 0 | 34 | 100 | 0.3400 | 0.2546 | 0.4372 |  | 1 | 1
2021-05-17 |  | 0.0231 | 0 | 29 | 100 | 0.2900 | 0.2101 | 0.3854 |  | 0 | 0
2021-05-24 |  | 0.0234 | 0 | 31 | 100 | 0.3100 | 0.2278 | 0.4063 |  | 0 | 0
2021-05-31 |  | 0.0271 | 0 | 32 | 100 | 0.3200 | 0.2367 | 0.4166 |  | 0 | 0
2021-06-07 |  | 0.0382 | 2 | 24 | 100 | 0.2400 | 0.1669 | 0.3323 |  | 0 | 1
2021-06-14 |  | 0.0311 | 0 | 26 | 100 | 0.2600 | 0.1840 | 0.3537 |  | 0 | 0
2021-06-21 |  | 0.0269 | 0 | 40 | 100 | 0.4000 | 0.3094 | 0.4980 |  | 3 | 2
2021-06-28 |  | 0.0301 | 0 | 34 | 100 | 0.3400 | 0.2546 | 0.4372 |  | 1 | 1
2021-07-05 |  | 0.0269 | 0 | 29 | 100 | 0.2900 | 0.2101 | 0.3854 |  | 0 | 0
2021-07-12 |  | 0.0417 | 3 | 23 | 100 | 0.2300 | 0.1584 | 0.3215 |  | 0 | 1
2021-07-19 |  | 0.0401 | 3 | 35 | 100 | 0.3500 | 0.2636 | 0.4475 |  | 1 | 2
2021-07-26 |  | 0.0300 | 0 | 36 | 100 | 0.3600 | 0.2727 | 0.4576 |  | 2 | 1
2021-08-02 |  | 0.0348 | 1 | 35 | 100 | 0.3500 | 0.2636 | 0.4475 |  | 1 | 1
2021-08-09 |  | 0.0281 | 0 | 39 | 100 | 0.3900 | 0.3002 | 0.4880 |  | 3 | 2
2021-08-16 |  | 0.0373 | 2 | 37 | 100 | 0.3700 | 0.2818 | 0.4678 |  | 2 | 2
2021-08-23 |  | 0.0379 | 2 | 39 | 100 | 0.3900 | 0.3002 | 0.4880 |  | 3 | 3
2021-08-30 |  | 0.0372 | 2 | 36 | 100 | 0.3600 | 0.2727 | 0.4576 |  | 2 | 2
2021-09-06 |  | 0.0357 | 1 | 38 | 100 | 0.3800 | 0.2910 | 0.4779 |  | 3 | 2
2021-09-13 |  | 0.0275 | 0 | 32 | 100 | 0.3200 | 0.2367 | 0.4166 |  | 0 | 0
2021-09-20 |  | 0.0241 | 0 | 23 | 100 | 0.2300 | 0.1584 | 0.3215 |  | 0 | 0
2021-09-27 |  | 0.0317 | 0 | 29 | 100 | 0.2900 | 0.2101 | 0.3854 |  | 0 | 0
2021-10-04 |  | 0.0219 | 0 | 22 | 100 | 0.2200 | 0.1500 | 0.3107 |  | 0 | 0
2021-10-11 |  | 0.0350 | 1 | 23 | 100 | 0.2300 | 0.1584 | 0.3215 |  | 0 | 0
2021-10-18 |  | 0.0312 | 0 | 36 | 100 | 0.3600 | 0.2727 | 0.4576 |  | 2 | 1
2021-10-25 |  | 0.0332 | 1 | 43 | 100 | 0.4300 | 0.3373 | 0.5278 |  | 4 | 3
2021-11-01 |  | 0.0376 | 2 | 15 | 100 | 0.1500 | 0.0931 | 0.2328 |  | 0 | 1
2021-11-08 |  | 0.0332 | 1 | 30 | 100 | 0.3000 | 0.2189 | 0.3959 |  | 0 | 0
2021-11-15 |  | 0.0309 | 0 | 30 | 100 | 0.3000 | 0.2189 | 0.3959 |  | 0 | 0
2021-11-22 |  | 0.0368 | 2 | 35 | 100 | 0.3500 | 0.2636 | 0.4475 |  | 1 | 1
2021-11-29 |  | 0.0461 | 4 | 26 | 100 | 0.2600 | 0.1840 | 0.3537 |  | 0 | 1
2021-12-06 |  | 0.0469 | 4 | 30 | 100 | 0.3000 | 0.2189 | 0.3959 |  | 0 | 1
2021-12-13 |  | 0.0346 | 1 | 20 | 100 | 0.2000 | 0.1334 | 0.2888 |  | 0 | 0
2021-12-20 |  | 0.0409 | 3 | 32 | 100 | 0.3200 | 0.2367 | 0.4166 |  | 0 | 1
2021-12-27 |  | 0.0407 | 3 | 28 | 100 | 0.2800 | 0.2014 | 0.3749 |  | 0 | 1
2022-01-03 |  | 0.0350 | 1 | 20 | 100 | 0.2000 | 0.1334 | 0.2888 |  | 0 | 0
2022-01-10 |  | 0.0373 | 2 | 28 | 100 | 0.2800 | 0.2014 | 0.3749 |  | 0 | 1
2022-01-17 |  | 0.0667 | 4 | 40 | 100 | 0.4000 | 0.3094 | 0.4980 |  | 3 | 3
2022-01-24 |  | 0.0792 | 4 | 28 | 100 | 0.2800 | 0.2014 | 0.3749 |  | 0 | 1
2022-01-31 |  | 0.0749 | 4 | 31 | 100 | 0.3100 | 0.2278 | 0.4063 |  | 0 | 1
2022-02-07 |  | 0.0894 | 4 | 35 | 100 | 0.3500 | 0.2636 | 0.4475 |  | 1 | 2
2022-02-14 |  | 0.1537 | 4 | 22 | 100 | 0.2200 | 0.1500 | 0.3107 |  | 0 | 1
2022-02-21 | yes | 0.2731 |  | 21 | 100 | 0.2100 | 0.1417 | 0.2998 |  |  | 
