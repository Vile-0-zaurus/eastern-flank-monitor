# M0 filter check v2

Test day: 2021-06-15. VPN off. Research user-agent only. Max 2 parallel downloads. Zips were not kept.

| # | Task | Report back |
|---|---|---|
| 1 | Translingual stream check | 96 files, 822.9 MB. tass.ru, ria.ru, rg.ru, iz.ru, and gazeta.ru all appear (960 / 306 / 372 / 271 / 92 rows). |
| 2 | New region filter, both streams | Translation: 133 kept. English: 14 kept. Translation by domain: tass.ru 43, sputniknews.com 32, iz.ru 13, ria.ru 10, rg.ru 9, tvzvezda.ru 6, rt.com 6, vesti.ru 5, gazeta.ru 5, 1tv.ru 4. English by domain: tass.com 6, sputniknews.com 5, rt.com 3. Five Russian-language titles (translation stream; some PAGE_TITLE values are truncated or are just the outlet name): (1) ria.ru — Экс-президент Польши поделился ожиданиями… (2) iz.ru — Экс-министр Украины увидел угрозу… (3) tass.ru — Эксперт посоветовала Путину и Байдену… (4) tass.ru — Маленькие города, большие люди: записки из экспедиции по сельской России (5) tass.ru — ТАСС. |
| 3 | Daily totals, all articles, both streams combined | tass.ru 960, sputniknews.com 777, rg.ru 372, ria.ru 306, iz.ru 271, rt.com 222, tass.com 106, tvzvezda.ru 106, gazeta.ru 92, vesti.ru 83, 1tv.ru 58, sputnikglobe.com 0. English stream had none of the .ru outlets. |
| 4 | Speed test, VPN off | Sequential 4 files: 1567 KB/s. Two parallel connections, 4 files: 2130 KB/s. |
| 5 | Full window estimate | English 198.47 GiB + translation 294.04 GiB = 492.51 GiB. At 2130 KB/s: 67.3 hours. Filtered output, if this day's hit rate holds: on the order of 50,000 rows, well under 1 GB. |
| 6 | Reachability, research UA, VPN off | TASS Russian RSS `https://tass.ru/rss/v2.xml`: works (HTTP 200, RSS). MFA RSS `https://mid.ru/ru/rss/`: works (HTTP 200, Atom). `mil.ru`: timeout (connection failed, ports 443 and 80). |
| 7 | Collector logging | Confirmed. Example: `2026-10-05T07:49:19.656193+00:00 SUCCESS tass-en.xml HTTP 200 bytes=34212` |

## Biggest finding

The translation stream is the one that actually contains tass.ru, ria.ru, rg.ru, iz.ru, and gazeta.ru. The English stream does not. A backtest that uses only the English GKG will miss the Russian-language state outlets.

Region matches are still thin and noisy: 133 translation rows and 14 English rows in a full day, and some kept titles do not name the five countries. PAGE_TITLE is sometimes only "ТАСС".

Download of both streams for 2021-01-01 to 2022-02-24 is 492.51 GiB and about 67.3 hours at the best measured speed (2130 KB/s, two connections). That is under the 72-hour gate. Sequential speed would be 91.5 hours, which is over the gate, so the run must stay at two parallel connections and not fall back to one.

Recommendation: stream-filter both GKG streams, translation first, two downloads at a time, delete each zip immediately, keep only matched rows plus daily outlet totals. Do not use DOC, RSS, or gpsjam for the backtest.
