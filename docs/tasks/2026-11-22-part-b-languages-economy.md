# Part B — languages and the economy gap

Saved 22 November 2026 before any other work on this assignment.

No API calls. Never bypass blocks. No VPN, no DNS change, no user-agent spoof. Research user-agent only. Commit and push after each section. If low on steps, stop at a committed point and say what is left.

## Section 1 — economy gap

1. Fetch Bank of Russia data for 3 August through 25 October 2026 from the same official sources already used for 2021–22. Official ruble per dollar rate, daily then weekly. Key rate. No new sources.
2. If reachable, add Ruble and Key rate lines to the Now Russia tab. Each line: the value that week, the change versus last week, and a source link. If unreachable or blocked, one honest line: "Ruble and key rate: official data not reachable for this window." Record the outcome in docs/sources.md. Commit and push.

## Section 2 — languages, UI only

3. Move every interface string into frontend/i18n/en.json. No hard-coded UI text left. Add a self-test that fails on an untranslated UI string.
4. Translate en.json into fi.json, et.json, lv.json, lt.json, and pl.json. No API. Country names in each language. Keep the About disclaimer meaning exact.
5. Language switcher in the header: EN, FI, ET, LV, LT, PL. Default English. Remember the choice in localStorage, wrapped in try/catch. It must work if storage is missing.
6. Headlines stay English first, with the original. Summaries and bottom lines stay English. In a non-English mode, show a small note: "Interface machine-translated. News content in English." Translate that note.
7. Self-test: switch through all six languages. Every UI string is present. No layout overflow. About opens in each. The Russia tab shows economy lines or the honest not-reachable line. Screenshots of the Lithuania tab in Lithuanian and Polish, and the Russia tab in Now for the week of 19 October 2026, go to ~/Desktop/efm-check3/. Commit, push, report, stop.
