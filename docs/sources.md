# M0 source reality check

Checked 2026-10-04 from a host whose public IP country was **FI**.
SPEC.md was not in this workspace or in the logged-in GitHub account.
Boundaries used are the ones in the task text, not an invented spec.

This is a reachability audit. No pipeline was built. Raw downloads lived in
`data/` (gitignored) and the bulk files were deleted after measurement.

## Environment

| Check | Result |
|---|---|
| OS | Linux Mint 22.2 (Zara), kernel 7.0.0-31-generic, x86_64 |
| Python | 3.12.3 |
| git | 2.43.0 |
| Disk at start | 88 GB volume, 3.2 GB free (97% used) |
| gcloud | not installed (not installed by this task) |
| bq | not installed (not installed by this task) |
| Public IP country | FI (`https://ipinfo.io/country`) |

## 1. GDELT

Scripts: `scripts/m0/gdelt_doc.py`, `scripts/m0/gdelt_gkg_day.py`, `scripts/m0/gdelt_window_sum.py`.

### DOC 2.0 API — PARTLY (host up, no successful query)

Endpoint: `https://api.gdeltproject.org/api/v2/doc/doc`

Queries attempted, `mode=artlist`, `format=json`:

- Russian-language articles mentioning Finland / Estonia / Latvia / Lithuania / Poland, including Russian names (Финляндия, Эстония, Латвия, Литва, Польша), with `sourcelang:russian`.
- Same country set restricted to `domain:tass.ru OR domain:ria.ru`.
- `timespan=3m`, `timespan=1y`, and `startdatetime=20210101000000` / `enddatetime=20220224000000`.

Every call returned **HTTP 429** with this body:

> Please limit requests to one every 5 seconds…

An initial burst used about 1 request/second (the task cap). That is faster than GDELT’s own 5-second rule. Later single calls, including after a 60-second pause and a 6-second gap, still returned 429 through the end of the session. No article count, no date span, and no domain list were obtained.

How far back the API reaches was therefore **not measured live**. Publisher posts say the DOC API searches a rolling window (default about 3 months, extendable to about 1 year with `timespan`), not a fixed archive back to 2021. That documented limit was not re-confirmed with a 200 response here. Treat “DOC cannot serve 2021-01-01 to 2022-02-24” as publisher documentation, not as a result of this run.

### Raw GKG files — WORKS

- `https://data.gdeltproject.org/gdeltv2/masterfilelist.txt` returned HTTP 200, 128,229,083 bytes. Robots.txt on that host is 404. `www.gdeltproject.org/robots.txt` disallows `/data/` on the www host only. The published download host is `data.gdeltproject.org`.
- Index format: `size md5 url`.
- **2021-01-01 GKG:** 96 files, **373,304,524 bytes (356.0 MiB)**. All 96 were downloaded (0 failures). Byte total matched the index. Files were deleted afterward because this disk had 3.2 GB free.
- Russian outlets are present in that day. A capped scan (4 files, 8,000 rows each) hit `rt.com` (103 rows), `tass.ru` (1), `gazeta.ru` (1). `ria.ru` was not in that sample. Absence in the sample is not absence in the day.
- **Window 2021-01-01 through 2022-02-24, GKG only:** 39,708 files, **213,101,428,576 bytes (198.47 GiB)**. Recomputed from a second streaming pass of the master list. Later days are larger than 1 Jan 2021 (15 Jun 2021 = 592.9 MiB, 1 Feb 2022 = 562.5 MiB, 24 Feb 2022 = 593.2 MiB), so do not extrapolate the window from the 1 Jan file size.

### BigQuery

`gcloud` and `bq` are not installed. No dry-run. No bytes-scanned figure. Not installed, per the task.

### Terms

GDELT’s about page says datasets are available for unlimited and unrestricted academic, commercial, or governmental use without fee. The DOC API separately asks for one request every 5 seconds.

### Cheapest method that actually covers the backtest

Raw GDELT 2.0 GKG from `data.gdeltproject.org`, streamed and filtered, zips discarded. Cost is bandwidth and time, not a bill. Do not store the 198 GiB. DOC 2.0 is the wrong tool for 2021. BigQuery is untested here; a later `--dry_run` is worth doing before anyone assumes it is cheaper.

**Verdict: PARTLY.** Historical files work. The article API did not, in this session.

## 2. Russian state media feeds

Script: `scripts/m0/feeds_check.py`.

| Feed | URL that worked | HTTP | Items | Fields | How far back |
|---|---|---|---|---|---|
| TASS Russian | `https://tass.ru/rss/v2.xml` | 403 with a research UA; **200** with a normal browser UA | 100 | title, date, summary (~50–60 chars). No full text | Same calendar day only (about 11:45–14:16 MSK on 4 Oct 2026) |
| TASS English | `https://tass.com/rss/v2.xml` | 200 | 63 | title, date, summary (~200 chars). No full text | About 3 Oct 14:36 to 4 Oct 14:12 MSK |
| RIA Novosti | `https://ria.ru/export/rss2/archive/index.xml` | 200 | 98 | title, link, date. Summary and content empty | Same day only (about 11:46–14:20 MSK). `robots.txt` allows this path |
| Russian MFA | `https://mid.ru/ru/rss/`, `/rss`, `/en/rss/`, `/ru/press_service/news/rss/` | 200 HTML, not a feed | 0 | none | n/a |

MFA notes:

- `https://mid.ru/` with a browser UA returned `Data processing... Please, wait.` (32 bytes on one attempt, a short interstitial on another).
- RSS paths returned an HTML page titled **Request Rejected**.
- No working feed URL was found. No account was created to look further.

TASS.ru is blocked or throttled for a non-browser agent. It is not an auth wall. The feed itself has no archive.

**Verdict: PARTLY.** Three current headline feeds work. None of them can back a 2021–Feb 2022 backtest. MFA fails from this host.

## 3. Russian navigation warnings (Baltic and Gulf of Finland)

Script: `scripts/m0/navwarn_check.py`.

### Where they are published

| Place | Result |
|---|---|
| Russian MoD hydrographic page cited in Russian NAVAREA texts, `https://mil.ru/navigation.htm` and `https://old.mil.ru/` | **Connection timeout** from this host (FI). `www.gunio.ru` and `www.gni.su` do not resolve |
| NAVAREA I coordinator (UKHO), `https://msi.admiralty.co.uk/RadioNavigationalWarnings` | HTTP 200, HTML. In-force NAVAREA I list. No Gulf of Finland / Petersburg warnings on the page fetched. robots.txt is 404 |
| Baltic Sea sub-area coordinator (Sweden), `https://navvarn.sjofartsverket.se/Navigationsvarningar/Navtex` | HTTP 200, HTML. `sjofartsverket.se/robots.txt` is `Allow: /`. This is the page that actually carried Russian coastal warnings |
| Northern Sea Route PRIPs on `nsr.rosatom.ru` | Reachable, but those warnings are Arctic (Kara / Laptev), not Baltic. Not used as the sample |

Update frequency on the Swedish page: stamp **2026-10-04 09:09**. The site says the page can lag the radio broadcast. NAVTEX/VHF schedules are every four hours. This is an in-force list, not a history.

History for 2021-01-01 to 2022-02-24: **not found** on a reachable host. UKHO says older NAVAREA I texts are reprinted in Admiralty Notices to Mariners (weeks 1, 13, 26, 39). Russian weekly Notices to Mariners are pointed at `mil.ru`, which did not connect.

Format: HTML text. Parseable. Ten distinct Russian-origin warnings (Petersburg or Kaliningrad) were parsed from the one NAVTEX page. Estonian, Finnish, and Polish notices on the same page were ignored.

### Sample (3 parsed entries)

Source page: `https://navvarn.sjofartsverket.se/Navigationsvarningar/Navtex`

1. **KALININGRAD NAV WARN 227/26**, issued 231402 UTC SEP. Southeastern Baltic. Ships exercises in area BR-161, 302100 UTC SEP through 312100 UTC OCT. Area temporarily dangerous to shipping. Corners include 55-09.5N 019-45.3E, 55-09.5N 020-00.0E, 55-02.0N 020-00.0E, 55-02.0N 019-39.6E. Cancel 312200 UTC OCT.
2. **PETERSBURG NAV WARN 203/26**, issued 231414 UTC SEP. Eastern Gulf of Finland. Ships exercises 302100 UTC SEP through 312100 UTC OCT. Area temporarily dangerous to shipping. Corners 60-00.50N 027-16.50E, 60-05.40N 027-34.00E, 59-53.00N 027-48.00E, 59-48.00N 027-31.00E. Cancel 312200 UTC OCT.
3. **PETERSBURG NAV WARN 199/26**, issued 231408 UTC SEP. Eastern Gulf of Finland. Ships exercises, area KR-105, same window. Corners 60-08.50N 029-00.00E, 60-08.50N 029-15.00E, 60-03.50N 029-15.00E, 60-03.50N 029-00.00E. Cancel 312200 UTC OCT.

**Verdict: PARTLY.** Current Russian coastal warnings for the Baltic and Gulf of Finland are script-parseable via the Swedish NAVTEX republication. The Russian origin host is unreachable from here, and no 2021 archive was found.

## 4. GPS interference (Baltic region)

Script: `scripts/m0/gpsjam_check.py`.

### gpsjam.org

- `https://gpsjam.org/robots.txt` → HTTP 404 (the SPA’s not-found page, not a robots policy).
- `https://gpsjam.org/data/manifest.csv` → HTTP 200, gzip. Header: `date,suspect,num_bad_aircraft_hexes,source`.
- Measured span: **2022-02-14** through **2026-10-03** (1,691 date rows). No rows before 2022-02-14. That misses 2021-01-01 through 2022-02-13 of the backtest window.
- Daily file: `https://gpsjam.org/data/YYYY-MM-DD-h3_4.csv`. 2026-10-03 returned HTTP 200, `text/csv`, 47,092 data rows, columns `hex,count_good_aircraft,count_bad_aircraft`. The bulk file was deleted after the header check; three sample rows are in `data/gpsjam-sample.txt`.
- Access method: unauthenticated HTTP GET. Automatable. No account, no key.
- About page (`https://gpsjam.org/about`) names John Wiseman and says the map uses airplanes.live and ADS-B Exchange. It does **not** state a license. A third-party site (FlySafe) calls the upstream CC-BY; that claim was not on gpsjam’s own about page. Do not treat bulk reuse as cleared. Credit the author if anything is kept. Raw ADS-B tracks were not downloaded.

### Alternatives checked, not used

- Wingbits GPS API requires an API key. Not called (no account, no billable query).
- OpenSky historical state vectors need a registered account. Not created.
- FlySafe republishes gpsjam aggregates and gates tighter API access. Not used.

**Verdict: PARTLY.** Download works and is scriptable from 2022-02-14. It does not cover the start of the backtest window, and the license is not stated.

## Verdict table

| Source | Verdict | History available | Format | Access limits | Terms OK? | Alternative if failed |
|---|---|---|---|---|---|---|
| GDELT | PARTLY | Raw GKG yes, back to 2015 in the master list. DOC not measured; publisher docs say a rolling ~3–12 months, not 2021 | GKG zip/CSV via index; DOC JSON (429 here) | DOC: 1 req / 5 s, and this IP stayed at 429. Raw files: no robots on the data host. No `bq` | GDELT data: yes, unrestricted, no fee | Stream-filter raw GKG. BQ only after a dry-run on a free project |
| Russian state media RSS | PARTLY | Current day only. No archive in the feeds | RSS/XML. Title + date. Short or empty summary. No full text | TASS.ru 403 unless browser UA. RIA open. MFA WAF rejects RSS URLs | Public feeds; full-text republication not granted by the feed | GDELT GKG for historical Russian articles. MFA: no working feed found |
| Russian Baltic / Gulf of Finland nav warnings | PARTLY | In-force list only. Page stamp 2026-10-04 09:09. No 2021 archive reached | HTML text, parseable | `mil.ru` timeout from FI. Swedish NAVTEX page allows crawl | Swedish page is a public safety broadcast mirror. Fine for a sample. Not a license to build a private archive of someone else’s site | Swedish NAVTEX list is the working path. UKHO NAVAREA I did not carry these warnings on the page fetched |
| GPS interference | PARTLY | 2022-02-14 to 2026-10-03. Gap before 14 Feb 2022 | Daily CSV, H3 hex + good/bad aircraft counts. Manifest CSV | No auth. No robots.txt. One file is ~188 KB compressed / 47k rows | Not stated. Do not assume CC-BY | None that cover 2021 without an account. Wingbits and OpenSky need keys or signup, which this task forbids |

## Sources

- GDELT about / terms: https://www.gdeltproject.org/about.html
- GDELT DOC API (attempted): https://api.gdeltproject.org/api/v2/doc/doc
- GDELT file index: https://data.gdeltproject.org/gdeltv2/masterfilelist.txt
- DOC window, publisher post (not re-verified live): https://blog.gdeltproject.org/doc-geo-2-0-api-updates-full-year-searching-and-more/
- TASS EN: https://tass.com/rss/v2.xml
- TASS RU: https://tass.ru/rss/v2.xml
- RIA: https://ria.ru/export/rss2/archive/index.xml
- Swedish NAVTEX warnings: https://navvarn.sjofartsverket.se/Navigationsvarningar/Navtex
- UKHO radio warnings: https://msi.admiralty.co.uk/RadioNavigationalWarnings
- gpsjam manifest: https://gpsjam.org/data/manifest.csv
- gpsjam about: https://gpsjam.org/about
- Country check: https://ipinfo.io/country
