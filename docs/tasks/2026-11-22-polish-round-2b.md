# Polish round 2, part B — dedup, Russia facts, tests

Saved 22 November 2026 before this part. No API calls.

Commit and push. If low on steps, stop at a committed point and say what is left.

| # | Task |
|---|------|
| 1 | No item twice in one briefing. A headline in "In the news" is not repeated under "What Russian media says" or any other section. Near-duplicate stories are one item with every outlet listed. Both modes. |
| 2 | "What officials said" shows a small side label on each item: "Russian official" or "Regional or Western official", in all 6 languages. |
| 3 | Russia tab: move the grey technical notes ("No model call", "median weekly count", "frozen window", fetch dates) into the About panel under "Method". The briefing keeps only "Display only — does not change the reading." |
| 4 | Russia fact card under the bottom line. Fixed text. Each fact has a dated source link: land borders with Finland, Estonia, Latvia, Lithuania, Poland, and Belarus; active armed forces size; defense spending as a share of GDP; one line each for Rostec, Almaz-Antey, Uralvagonzavod, Kalashnikov Concern, and UAC; latest published conscription call-up size. Never from memory. If a fact has no reachable dated source, leave it out. Translate the labels in all 6 languages. |
| 5 | Self-tests: no duplicate item in one briefing; a side label on every official item; the Russia fact card has a source on every fact; locale date formats; the week label is not clipped; no English sentence contains a translated country name. All pass. |
| 6 | Screenshots of the Russia tab for the week of 12 October 2026, and a week with merged sources, go to ~/Desktop/efm-check5/. Update STATE.md. Commit, push, report, stop. |
