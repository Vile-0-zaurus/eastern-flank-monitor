# Four-file outlet sample

Checked 2026-10-26 from this machine. No API call. No VPN, no DNS change, and no user-agent change. The running now-download was not stopped.

This is four 15-minute GKG files, not four full days. A miss here is not proof a domain never appears. Zips were scanned in memory and not stored.

The data host's robots.txt returned 404 with an empty body. That host has no disallow rule. The www host's `/data/` rule does not apply here.

| File | Stream | Zip | Rows |
|---|---|---|---|
| 28 July 2026, 00:15 | English | 4.9 MB | 1,166 |
| 15 September 2026, 00:15 | English | 5.8 MB | 1,337 |
| 18 August 2026, 00:00 | Translation | 5.3 MB | 1,287 |
| 5 October 2026, 00:00 | Translation | 3.6 MB | 940 |

## Named domains

Every named domain had 0 rows and 0 relevant rows, in both streams.

lrt.lt, err.ee, news.err.ee, lsm.lv, eng.lsm.lv, pap.pl, reuters.com, apnews.com, delfi.lt, delfi.ee, delfi.lv, tvp.pl.

## Other country domains

The English files had no other Finland, Estonia, Latvia, Lithuania, or Poland domain with a region-relevant row.

The translation files had a few. The match is the project's title-or-location rule. Most of these are ordinary domestic pages that mention their own country, the Baltic Sea, or the word Finlandia. They are not flank news outlets.

| Domain | Relevant rows | What the row was |
|---|---|---|
| egospodarka.pl | 5 | Job ads |
| wp.pl | 3 | Domestic and world briefs, including one Moscow arrest line |
| ita-savo.fi | 2 | Nobel week, and a Finlandia architecture prize |
| savonsanomat.fi | 2 | The same two stories |
| propertynews.pl | 1 | A beach complex on the Baltic |
| farmer.pl | 1 | Polish food exports |
| se.pl | 1 | People returned from Hungary to Poland |
| naszdziennik.pl | 1 | A church paper line |
| trojmiasto.pl | 1 | A storm on the Tricity coast |
| newsweek.pl | 1 | A literary prize, with one line that Poland is worth defending |
| polskieradio.pl | 1 | A church anniversary |
| bialystok.pl | 1 | A music listing |
| bilety24.pl | 1 | Concert tickets in Gdansk |

## Recommendation

Add none.

None of the asked domains were present. The other hits would keep ordinary domestic pages, not coverage of Russia or Belarus. Adding a large Polish site such as wp.pl would keep almost every domestic story, because the filter matches the word Poland. That is the wrong list.

No second pass is planned. The gate for that pass was a domain actually worth adding. This sample did not produce one.

Counts are in `data/now/outlet-sample.json`, which is not committed. The scanner is `scripts/now/outlet_sample.py`.
