# Part A — fixes, About, stamp

Saved 22 November 2026 before any other work on this assignment.

No API calls. Never bypass blocks. Commit and push after this part. If low on steps, stop at a committed point and say what is left.

1. Map legend with icons: drone, aircraft, border, sabotage. Same icons on the map dots. Show Confirmed and Reported.
2. Re-check all 11 incidents against their source text. Aircraft, such as the Russian IL-20 near Utö, Finland, must be aircraft, not drone. List every changed type in the report.
3. Regional media: hide the section when empty. When stories exist, also show them under What happened, labeled Regional media. Never say Nothing this week for this section.
4. Russia tab in Now mode: fill Inside Russia cards from Now data. Defense ministry headlines, defense contractors, conscription, from gkg-now.sqlite, with English lines written here. Plus ruble rate and key rate for the Now window if the Bank of Russia data already used covers 2026. No new sources. Each card: one story line, a small count versus usual, and a link. No card identical across weeks unless the data really is.
5. Replay tab counts come from all stored headlines naming the country, as in I1, not the classified sample. No false 0 Russian stories. Never two Nothing this week lines in a row. Merge empty sections into one line.
6. Replace the More disclaimer expander with an About button at the top right. The panel says what the app is and is not, how it works in short form from docs/explainers.md, data sources, and the exact public-sources paragraph. Footer keeps one short line: Not an official warning service.
7. Header stamp: Data as of 25 Oct 2026 · page built <build date>.
8. Countdown component, built but hidden: Next update in hh:mm, driven by config/app.yaml live_monitoring and next_update_time. Shown only when live_monitoring is on. It is off, so the countdown is not visible. Unit test both states.
9. Extend click_selftest. Legend present. About opens and closes. No More expander. Countdown hidden while off. No duplicate empty lines. All tests pass. Screenshots of Now Lithuania week 2026-10-12, the Russia tab, and the About panel go to ~/Desktop/efm-check3/. Commit, push, report, stop.
