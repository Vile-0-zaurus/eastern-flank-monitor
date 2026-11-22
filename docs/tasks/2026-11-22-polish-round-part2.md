# Polish round, part 2 — content dedup, tests, screenshots

Saved 22 November 2026 before this part. No API calls.

Commit and push. If low on steps, stop at a committed point and say what is left.

Pre-approved: running scripts and tests, restarting the local page server, git commit and push.

| # | Task |
|---|------|
| 1 | No item appears twice in one briefing. A headline shown under "In the news" is not repeated under "What Russian media says" or any other section. |
| 2 | Near-duplicate stories (same event, different outlets) are merged into one item with both sources listed, for example "ria.ru, aif.ru". Apply in every section and both modes. |
| 3 | "What officials said" shows the side of each speaker again: a small label "Russian official" or "Regional or Western official", translated in all six languages. |
| 4 | Self-tests cover locale date formats, an unclipped week label, working zoom, no English sentence that contains a translated country name, no duplicate item in one briefing, and a side label on every official item. All tests pass. |
| 5 | Screenshots go to ~/Desktop/efm-check4/: Latvia in Lithuanian for the week of 14 September 2026, zoomed by the tab; Estonia in English on a quiet week; the map zoomed on Balvi; a week that shows merged sources. |
| 6 | Update STATE.md. Commit, push, report, stop. |
