# Part B, section 2 — languages

Date: 22 November 2026. No API calls.

The interface strings live in frontend/i18n/en.json. Finnish, Estonian, Latvian, Lithuanian, and Polish files have the same keys. The switcher is EN, FI, ET, LV, LT, PL. The choice is stored in the browser when storage works. News lines, summaries, and the bottom line stay English. A non-English mode shows a note that the interface is machine-translated.

Checks:

1. python3 tests/i18n_selftest.py — PASS. 6 languages, 232 keys. A copied English UI string fails this test.
2. tests/lang_selftest.py — PASS. All six languages open About. No sideways overflow. The Russia tab shows the ruble line.
3. tests/click_selftest.py — PASS in English.

Screenshots: /home/supra/Desktop/efm-check3/lithuania-lt.png, lithuania-pl.png, and russia-now-2026-10-19.png.
