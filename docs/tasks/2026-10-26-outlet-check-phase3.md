# Outlet check and Phase 3

Saved 2026-10-26 before any other work on this assignment.

No API calls. Never bypass blocks: no VPN, no DNS changes, no user-agent spoofing. Do not rescore the stored week table. Do not move the pre-registered tags. Do not delete the 2021–22 backfill. Do not stop the running now-download. Commit and push after each section. If low on steps, stop at a committed point and say what is left.

## Section 1 — raw outlet check

1. Download 4 raw GKG files (2 English, 2 translation, from different days in the window), scan in memory, delete. Count rows per domain for: lrt.lt, err.ee, news.err.ee, lsm.lv, eng.lsm.lv, pap.pl, reuters.com, apnews.com, delfi.lt, delfi.ee, delfi.lv, tvp.pl, and any other FI/EE/LV/LT/PL domain with region-relevant rows.
2. Recommend which domains to add (only those actually present with relevant rows). If any: plan a second background pass over the same window keeping ONLY those domains (same rules, same database). Do not start it. Give its estimated machine-on time. Report, and stop after Section 1 if the download is not yet 100%.

Window: 27 July 2026 through 18 October 2026.

Section 1 result, 2026-10-26: four files scanned, none of the asked domains present, no domain recommended, no second pass. See `docs/reports/2026-10-26-outlet-sample.md`. Section 2 stays closed until the now-download is 100% done.

## Section 2 — Phase 3

Gate: efm-now-download is 100% done. Do not start this section before that gate.

3. Incidents log for the Now window (27 Jul – 18 Oct 2026): drones/airspace violations, GPS jamming reports, cable/pipeline damage, balloons from Belarus, border incidents, sabotage — from official sources (defense ministries, border guards, governments, NATO) and from stored Yle/BBC rows. Each: date, type, place (coordinates), one-line English summary, official source link, source date. Dated sources only, never from memory.
4. "Now" tab next to the 2021–22 replay: same layout (Inside Russia main panel, small map with incident + event dots, country dossier, news English-first). Map dots get a type icon (drone, jamming, cable, border). Week slider over the 12 weeks.
5. Levels in Now mode: show only what is computable without analyst inputs — per-country Russian media attention vs usual + incident count; label clearly "Now: attention and incidents only; full tension level not computed".
6. Self-test (one scroll, no jumping, every incident has a source), video ~/Desktop/efm-now.mp4 (30 s). Commit, push, stop.
