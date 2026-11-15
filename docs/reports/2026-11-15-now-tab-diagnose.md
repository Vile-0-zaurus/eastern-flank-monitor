# Now tab diagnosis

Date: 15 November 2026. No API calls. The Now database was opened read-only. It was not rewritten.

Command: `python3 scripts/now/diagnose_now_tab.py`

## Why the chip and the dossier disagree

The Poland chip does not read the dossier, and the dossier does not read the Now database.

1. The chip reads `frontend/now-view.json`, field `attention`. That file was built from `data/now/gkg-now.sqlite`. The count is Russian-outlet titles in the frozen window that name the country. It is not deduplicated further: stored and unique were the same on every row below.
2. The country dossier reads `frontend/country-headlines.json` through `countryMedia()`. That file has no 2026 week. Every Now week therefore has zero dossier stories, so the page prints "No news about Poland this week."
3. The page never opens `gkg-now.sqlite`. The Now builder also does not write Russian headlines into the dossier file. It only stores Yle and BBC titles, already in English, in `now-view.json` under `news`. That list is the main news panel, not the country dossier.

The chip file has no week at 134. Poland's stored counts are 60, 78, 78, 90, 90, 98, 106, 110, 111, 136, 136, and 155. The two weeks at 136 are 14 September and 19 October 2026. If the screen said 134, it is not this file.

## Are Now headlines hidden for lack of an English line?

Yes. Two separate gates, and both are closed.

1. Russian Now titles are not in the file the dossier reads. They cannot be shown.
2. The page also drops a Cyrillic title that has no English line (`showNews` and `appendStory` in `frontend/app.js`). The Now table has no English column. A keyword check for an English title found almost none among the Russian rows. A hostile flag is not stored. The hostile column below is a keyword proxy from the gold-set pattern, labeled not a stored flag. It is not what the page shows.

Relevant here means the title names that country on a Russian outlet. That is the chip rule. It is the same number as stored.

Shown in the table is the country dossier count. It is 0 for every country and every Now week. Yle/BBC is the separate English list in `now-view.json`. It is not what the dossier shows.

## Counts

Format: stored / relevant / with English / shown. Yle/BBC is extra, not the dossier.

Week of 3 August 2026

- Finland: 58 / 58 / 0 / 0. Yle/BBC 6. Hostile keyword 0.
- Estonia: 18 / 18 / 0 / 0. Yle/BBC 0. Hostile keyword 1.
- Latvia: 58 / 58 / 0 / 0. Yle/BBC 0. Hostile keyword 7.
- Lithuania: 48 / 48 / 0 / 0. Yle/BBC 0. Hostile keyword 0.
- Poland: 111 / 111 / 0 / 0. Yle/BBC 2. Hostile keyword 2.

Week of 10 August 2026

- Finland: 30 / 30 / 0 / 0. Yle/BBC 7. Hostile keyword 0.
- Estonia: 7 / 7 / 0 / 0. Yle/BBC 1. Hostile keyword 0.
- Latvia: 40 / 40 / 0 / 0. Yle/BBC 0. Hostile keyword 1.
- Lithuania: 32 / 32 / 0 / 0. Yle/BBC 0. Hostile keyword 0.
- Poland: 110 / 110 / 0 / 0. Yle/BBC 0. Hostile keyword 5.

Week of 17 August 2026

- Finland: 48 / 48 / 0 / 0. Yle/BBC 7. Hostile keyword 1.
- Estonia: 23 / 23 / 0 / 0. Yle/BBC 0. Hostile keyword 0.
- Latvia: 36 / 36 / 0 / 0. Yle/BBC 0. Hostile keyword 2.
- Lithuania: 21 / 21 / 0 / 0. Yle/BBC 0. Hostile keyword 0.
- Poland: 78 / 78 / 0 / 0. Yle/BBC 0. Hostile keyword 0.

Week of 24 August 2026

- Finland: 76 / 76 / 1 / 0. Yle/BBC 7. Hostile keyword 1.
- Estonia: 17 / 17 / 0 / 0. Yle/BBC 0. Hostile keyword 0.
- Latvia: 23 / 23 / 0 / 0. Yle/BBC 0. Hostile keyword 1.
- Lithuania: 25 / 25 / 0 / 0. Yle/BBC 0. Hostile keyword 0.
- Poland: 60 / 60 / 0 / 0. Yle/BBC 0. Hostile keyword 0.

Week of 31 August 2026

- Finland: 62 / 62 / 0 / 0. Yle/BBC 4. Hostile keyword 0.
- Estonia: 31 / 31 / 0 / 0. Yle/BBC 0. Hostile keyword 2.
- Latvia: 18 / 18 / 0 / 0. Yle/BBC 0. Hostile keyword 0.
- Lithuania: 23 / 23 / 0 / 0. Yle/BBC 0. Hostile keyword 0.
- Poland: 78 / 78 / 0 / 0. Yle/BBC 0. Hostile keyword 1.

Week of 7 September 2026

- Finland: 42 / 42 / 0 / 0. Yle/BBC 7. Hostile keyword 2.
- Estonia: 27 / 27 / 0 / 0. Yle/BBC 0. Hostile keyword 0.
- Latvia: 38 / 38 / 0 / 0. Yle/BBC 0. Hostile keyword 2.
- Lithuania: 63 / 63 / 2 / 0. Yle/BBC 0. Hostile keyword 0.
- Poland: 90 / 90 / 1 / 0. Yle/BBC 3. Hostile keyword 5.

Week of 14 September 2026

- Finland: 53 / 53 / 0 / 0. Yle/BBC 7. Hostile keyword 0.
- Estonia: 13 / 13 / 0 / 0. Yle/BBC 0. Hostile keyword 0.
- Latvia: 36 / 36 / 0 / 0. Yle/BBC 0. Hostile keyword 0.
- Lithuania: 59 / 59 / 0 / 0. Yle/BBC 0. Hostile keyword 0.
- Poland: 136 / 136 / 0 / 0. Yle/BBC 0. Hostile keyword 7.

Week of 21 September 2026

- Finland: 24 / 24 / 0 / 0. Yle/BBC 6. Hostile keyword 0.
- Estonia: 18 / 18 / 0 / 0. Yle/BBC 0. Hostile keyword 1.
- Latvia: 31 / 31 / 0 / 0. Yle/BBC 0. Hostile keyword 0.
- Lithuania: 45 / 45 / 0 / 0. Yle/BBC 2. Hostile keyword 0.
- Poland: 155 / 155 / 0 / 0. Yle/BBC 3. Hostile keyword 5.

Week of 28 September 2026

- Finland: 24 / 24 / 0 / 0. Yle/BBC 6. Hostile keyword 0.
- Estonia: 32 / 32 / 0 / 0. Yle/BBC 3. Hostile keyword 0.
- Latvia: 33 / 33 / 0 / 0. Yle/BBC 0. Hostile keyword 0.
- Lithuania: 37 / 37 / 0 / 0. Yle/BBC 0. Hostile keyword 0.
- Poland: 106 / 106 / 1 / 0. Yle/BBC 0. Hostile keyword 0.

Week of 5 October 2026

- Finland: 39 / 39 / 2 / 0. Yle/BBC 9. Hostile keyword 1.
- Estonia: 73 / 73 / 0 / 0. Yle/BBC 0. Hostile keyword 0.
- Latvia: 25 / 25 / 0 / 0. Yle/BBC 0. Hostile keyword 0.
- Lithuania: 68 / 68 / 0 / 0. Yle/BBC 0. Hostile keyword 0.
- Poland: 98 / 98 / 0 / 0. Yle/BBC 8. Hostile keyword 0.

Week of 12 October 2026

- Finland: 25 / 25 / 0 / 0. Yle/BBC 10. Hostile keyword 1.
- Estonia: 36 / 36 / 0 / 0. Yle/BBC 0. Hostile keyword 0.
- Latvia: 65 / 65 / 0 / 0. Yle/BBC 0. Hostile keyword 5.
- Lithuania: 48 / 48 / 0 / 0. Yle/BBC 0. Hostile keyword 2.
- Poland: 90 / 90 / 0 / 0. Yle/BBC 0. Hostile keyword 1.

Week of 19 October 2026

- Finland: 38 / 38 / 0 / 0. Yle/BBC 6. Hostile keyword 1.
- Estonia: 24 / 24 / 0 / 0. Yle/BBC 0. Hostile keyword 0.
- Latvia: 22 / 22 / 0 / 0. Yle/BBC 0. Hostile keyword 0.
- Lithuania: 63 / 63 / 0 / 0. Yle/BBC 0. Hostile keyword 0.
- Poland: 136 / 136 / 0 / 0. Yle/BBC 0. Hostile keyword 5.

Every chip number matched the read-only database count. Shown in the dossier is 0 on every row.
