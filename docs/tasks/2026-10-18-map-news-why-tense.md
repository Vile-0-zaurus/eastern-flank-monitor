# Map, news, and why tense

Saved 2026-10-18 before any other work on this assignment. No API calls. Do not rescore the stored week table. Do not move the pre-registered tags. Do not delete data. Do not make the repo public. Commit and push after each part. Stop only for money, deleting data, changing pre-registered results or tags, or making anything public.

## Assignment

1. Main screen layout: (top) country strip FI/EE/LV/LT/PL, each Normal/Tense/Danger signs (Calm→Normal; Watchful, Elevated→Tense; Serious/Critical proposed→Danger signs, unconfirmed) + one short reason; (middle left) MAP; (middle right) NEWS feed; (bottom) timeline with Play + slider + "Week of <date>". Timeline moves everything together. Layer cards and charts leave the main screen → "How it works" page.

2. MAP: offline, free — public-domain country outlines (Natural Earth), vendored locally, no tile server. Show FI, EE, LV, LT, PL, BY, Kaliningrad, western RU, UA. Each approved event = a dot at its location (Mozyr, Gomel/Zyabrovka, Belgorod, Voronezh/Pogonovo, Yelnya, Crimea, Soloti, Belarus west, etc.; add coordinates to the event data). Color by severity, active only while the event holds (4 weeks). Click → what happened + source link + date.

3. NEWS feed: real Russian state media headlines for the selected week, original + English ("Machine translation"), outlet, date, link; filter "All / Hostile only" ("Flagged by AI; about 2 in 3 confirmed"); grouped by country; deduplicated by story.

4. "WHY TENSE" panel (click a country or event): three blocks — What happened (events), What official sources say, What Russian state media says.

5. Official statements: for 10–15 key weeks (Ryanair May 2021; Lithuania border crisis Jul–Aug 2021; Poland border crisis Sep–Nov 2021; Zapad Sep 2021; Nov–Dec 2021 buildup; Jan–Feb 2022 Belarus deployments; Feb 2022 warnings), collect statements from official sources of FI/EE/LV/LT/PL governments, ministries, NATO, US — dated within that week, with link. One-line summary each, labeled "Summarized by AI from the linked source." No source found → say so. Never from memory.

6. Self-test: extend tests/ui_selftest.py (all weeks, map dots match events, links work, no clipping, no raw codes, no NaN). Then a "fresh eyes" pass: read every screen as a non-expert; rewrite anything unclear. Repeat until clean.

7. Video ~/Desktop/efm-map.mp4 (30–40 s): play Jul 2021 → Feb 2022, click Poland in Nov 2021, then Ukraine in Feb 2022. Commit, push. Final report in plain words to docs/reports/. STOP.

## Rules that stay in force

- The five countries show the stored eastern-flank reading. They are not scored separately. Ukraine, when opened, shows the stored Ukraine-test reading. Belarus, Russia, and Kaliningrad are map geography, not scored countries.
- Calm is Normal. Watchful and Elevated are Tense. A Serious or Critical proposal is "Danger signs, unconfirmed". The stored number is not changed.
- An event dot uses a place the approved note already names. Coordinates are added. Notes, levels, tags, and source links are not rewritten.
- A headline keeps its stored English line. No new translation and no model call. A week with no stored English line says so.
- An official line is included only after the linked page is fetched and the page itself shows a date inside that week. Otherwise the panel says no source was found.
- Layer cards and charts move to How it works. They still read the stored table.
