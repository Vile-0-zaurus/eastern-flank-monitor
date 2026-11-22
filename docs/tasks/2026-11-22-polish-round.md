# Polish round — translation quality, map, quiet weeks

Saved 22 November 2026 before any other work on this assignment.

Commit and push after each section. If low on steps, stop at a committed point and say what is left. API calls only in Section 1, and only after an OK.

## Section 1 — translation quality

1. Fix the language structure first. No API. Dates use a proper date function for each language. Article dates must not use the "week of" label. English content sentences stay fully English. Do not insert a translated country name into an English sentence. The banner and every visible label are fully translated. The Source link label and dates stay consistent next to English headlines.
2. Price a re-translation of every UI string from en.json into fi, et, lv, lt, and pl. Use Claude Sonnet, the judge model in config/llm.yaml, with the Anthropic key. Count strings and tokens. Apply the calibration rule. Add 20 percent. Hard cap 0.50 dollars real. Print the price and the run id ui-translate-1. Stop and wait for OK. Do not call before that.
3. After OK: run it, store the results, log the real cost in docs/budget.md, and write docs/i18n-review-lt.md with every Lithuanian string and its English source.

## Section 2 — map and layout

4. Map zoom and pan. Mouse wheel and buttons. Plus, minus, and reset. Incident icons get bigger and scale with the zoom. Clicking an incident in the briefing zooms the map to it.
5. The week label under the slider is never clipped, in any language. Test at 1280 by 800 and 1920 by 1080.

## Section 3 — quiet weeks

6. What happened: if that week has no incident, show the most relevant headline about that country, Russian or regional media, English first, with a link, labeled In the news. Nothing this week only if the week truly has no item.
7. A country fact card under the bottom line. Fixed text. Each fact has a source link: NATO member since, length of the border with Russia or Belarus, and incidents in this snapshot as a count plus the latest. Dated official or encyclopedic sources only. Never from memory.

## Section 4 — tests

8. Self-tests pass, including date formats per language, no clipped label, zoom works, and no English sentence that contains a translated country name. Screenshots of Latvia in Lithuanian for the week of 21 September 2026, Estonia in English on a quiet week, and the map zoomed on Balvi go to ~/Desktop/efm-check4/. Commit, push, report, stop.
