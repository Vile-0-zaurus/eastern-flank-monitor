# Russia side, part A — sources and data

Checked 2026-10-18 from this machine. No model call. No VPN, no DNS change, and no user-agent change. A timeout means this network did not answer. It does not mean the source does not exist.

This is a reading of public pages. It is not legal advice.

Raw pages stayed in `data/russia-probes/`, which is not committed. The small files in `manual/russia/` are the collected numbers.

## Table

| Group | Verdict | History back to 2021-01 | Note |
|---|---|---|---|
| 1. Telegram, verified Foreign Ministry channels | PARTLY | Yes. A 2017 page and pages inside 2021 opened. | Only two channels were named on the ministry site. The full window was not walked. Two excerpts are stored. |
| 2. Defense contractors in stored headlines | WORKS | Yes. The stored set covers the window. | 213 headlines in 52 of 60 weeks. Eight weeks have an example about production, shifts, hiring, contracts, or a state order. |
| 3. Economy | PARTLY | Yes for the ruble, the key rate, and Brent. Inflation is yearly, not monthly. | Bank of Russia and the U.S. Energy Information Administration answered. A monthly inflation table was not extracted. |
| 4. Defense-linked stock prices | FAILS | Not measured without an exchange. | No exchange was used. The KAMAZ site tells this user-agent not to fetch. The UAC site did not present a valid certificate. |
| 5. Public mood | PARTLY | Levada month indexes for 2021 and early 2022 opened. | Two Levada results are stored. VTsIOM and FOM opened, and no 2021-22 result of the asked kind was on the page. |
| 6. Regional officials | PARTLY | Not shown on the pages that opened. | Report only. Nothing was collected. Several ministry sites returned a browser check or did not answer. |

## What was collected

1. Telegram. `manual/russia/telegram.json`. The Russian Foreign Ministry home page names `t.me/MID_Russia`. The English page names `t.me/MFARussia`. Both previews answered. A page before message 500 is from January 2017. A page before message 17500 is from 12 November 2021. A page before message 10500 on the English channel is from 26 April 2021. Walking every page from January 2021 through February 2022 would be hundreds of requests. That walk was not done. Two excerpts are stored, with an English line written here.

The Defence Ministry site and the Kremlin site timed out. No channel was opened for them. The spokesperson page did not name a separate channel.

2. Contractors. `manual/russia/contractors.json`. Read-only pass over stored titles. No new fetch.

| Company | Headlines |
|---|---|
| Rostec | 86 |
| Kalashnikov | 51 |
| Almaz-Antey | 23 |
| Tactical Missiles | 20 |
| KAMAZ | 16 |
| UAC | 15 |
| Uralvagonzavod | 2 |

3. Economy. `manual/russia/economy.json`.

The ruble file is the Bank of Russia published dollar rate. 58 of 60 weeks have a rate. The first stored week in that file is 11 January 2021, at 73.5453 rubles per dollar. The key-rate table has 294 dated rows and 10 distinct rates, from 4.25 percent on 4 January 2021 to 20 percent on 28 February 2022. Brent is the monthly Europe spot price, from 54.77 dollars in January 2021 to 97.13 dollars in February 2022. Inflation from the World Bank is 6.7 percent in 2021 and 13.7 percent in 2022, yearly. The Bank of Russia inflation page opened, but its chart was not turned into a clean monthly table.

A published oil file on another site was disallowed by that site's robots.txt. It was not kept.

4. Stocks. Nothing stored. Connecting to a Russian exchange was out of scope. No other free daily history for 2021-22 was obtained.

5. Polls. `manual/russia/polls.json`. Levada, 17-21 February 2022, 1,618 people: good feelings toward Ukraine fell from 45 percent in November 2021 to 35 percent, and bad feelings rose from 43 percent to 52 percent. 60 percent named the United States and NATO countries as the start of the escalation in eastern Ukraine. A 9 February 2022 Levada page on Estonia states that 74 percent did not know an independent Estonian Republic existed before the Second World War. VTsIOM and FOM are state-run. Their opened pages did not show a matching 2021-22 result.

6. Regional officials. Nothing collected.

| Office | Opened page | 2021-22 archive on that page |
|---|---|---|
| Finland defence | Browser check. Not retried. | Not measured |
| Finland foreign | Home page opened. | Not shown |
| Estonia defence | Browser check. Not retried. | Not measured |
| Estonia foreign | Browser check. Not retried. | Not measured |
| Latvia defence | Blocked-request page. | Not measured |
| Latvia foreign | English home page and an RSS index opened. | Not shown |
| Lithuania defence | Browser check. Not retried. | Not measured |
| Lithuania foreign | Browser check. Not retried. | Not measured |
| Poland defence | Ministry page opened. | Not shown |
| Poland foreign | Ministry page opened. | Not shown |
| NATO | Press page and archives page opened. | 2021 is mentioned as a document count, not as a statement list |

## Language and quoting

The stored contractor titles are Russian or English, as they were already stored. Telegram samples are Russian or English, with an English line. Poll pages that were read are Russian. Economy figures are numbers from the linked page.

Quoting a published number or a short excerpt with the link is the use this assignment asked for. A lawyer has not reviewed the terms. The Bank of Russia paths that were used are not in its robots disallow list. The energy administration page that was used is allowed by its robots.txt. Levada asked for 10 seconds between requests. That pause was kept.

## Biggest risk

The Telegram window is real, and it was not collected. A card built from two excerpts would look more complete than the file is. The cheapest next step that stays inside the rules is a paced walk of the two verified channels from January 2021 through February 2022, keeping only posts that name the region, with the English line written here.

## Full walk, later the same day

The walk was done. Public preview only, one request a second, research user-agent. MID_Russia: 421 pages. MFARussia: 184 pages. Both walks passed back into December 2020, so the window was covered. After dropping false hits inside unrelated words, 1,009 posts remain, in all 60 weeks from 11 January 2021 through 28 February 2022. The week of 4 January 2021 had no matching post. Counts are in `manual/russia/telegram.json`. Each kept post has a date, a link, and an English line written here. The line names the action when the post is a briefing, a press answer, or a call, and names the topics in the text. It is not a full translation of every sentence.

One Levada search, for "дружественные и недружественные", found the 15 June 2021 survey. May 2021 results: Belarus was named a friend by 58 percent. As unfriendly: the United States 66 percent, Ukraine 40 percent, Latvia 21 percent, Poland 21 percent, Lithuania 20 percent, Estonia 9 percent. Finland and NATO were not in the printed tables. Stock prices stay out. The reason is in `docs/decisions.md`.

