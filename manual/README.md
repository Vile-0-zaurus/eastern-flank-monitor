# Manual inputs

Empty on purpose. A blank file is no data. Do not read it as zero.

Until the admin page exists, edit these by hand. One source link per row. A row with no link does not count.

`source_date` is the publication date of the source, `YYYY-MM-DD`.

`date` is the Monday of that week, `YYYY-MM-DD`, except in the incident log. There, `date` is the incident's own date, not the week Monday.

| File | What `value` is | What `date` is |
|---|---|---|
| `o1-ukraine-war.csv` | Integer 0–4. Live weekly file. Header only. | Monday of the week |
| `o2-us-commitment.csv` | Integer 0–4. Live weekly file. Header only. | Monday of the week |
| `c2-force-posture.csv` | Short note. Live weekly file. Header only. | Monday of the week |
| `h2-incident-log.csv` | One incident note. Several incidents in one week are several rows. | The incident's own date |

No-hindsight rule: a row counts for week W only if source_date ≤ last day of W. Week W runs Monday through Sunday, so the last day is Sunday. A source published after that Sunday is ignored for W. It may count for a later week. A missing source_date does not count. Ignored is no data, not zero.

For a monthly O2 row, the last day is the last calendar day of that month. A source published after that day does not count for that month.

## Source rules

These rules apply to every backtest draft. They were written before any draft row.

1. Each entry needs a link and a `source_date`. The source must have been published on or before the last day of that entry's week or month.
2. An archived copy is allowed only if the capture date also falls on or before that last day. A later capture of an earlier page does not qualify.
3. Prefer official statements, major news outlets, and established think tanks. Do not use a model summary, a search snippet, or an undated page as the source.
4. Never write a row from model memory. If the page was not fetched, or the publication date was not on the page, do not write the row.
5. No source means leave the value empty. Empty is no data. It is never calm, and it is never zero.

## Dating rule

An entry is dated to the week, or the month, of its `source_date`. Never earlier.

The row `date` is the Monday of that week, or the first day of that month. It is not the day the event happened if that day falls in an earlier week or month. A source published on Monday belongs to that Monday's week. A source published on Sunday belongs to the week that began the previous Monday, not to the next week.

## O2 carry-forward

If a month has no new source, carry the last sourced value for up to 3 months. Mark that row `carried`. The fourth month with no new source is empty. A new source replaces the carry. A carried row keeps the link and `source_date` of the value it carries. It does not invent a publication date.

## Locked backtest scales

Locked 2026-10-11, before any draft. Tag `manual-scales` points at this commit. Do not retune these definitions after drafting starts.

SPEC still describes the live weekly indicators. This section does not amend SPEC. It locks the backtest reconstruction only. The live CSV files above stay header-only.

Rungs that are not written here are not part of the scale. Do not fill them in.

### O2 — US commitment to European security

Monthly. One row per calendar month from 2021-01 through 2022-02.

`date` is the first day of the month that contains `source_date`. It is not an earlier month.

- 0 = strong visible commitment
- 1 = commitment with some doubts
- 2 = mixed or contested signals
- 3 = weak commitment / significant pullback signals
- 4 = clear signals of withdrawal or abandonment

Amended 2026-10-11, before any approval. Reason: middle rungs were undefined. Tag `manual-scales-v2` points at this amendment. Tag `manual-scales` still points at the earlier lock, which had only the endpoints.

### O1 — availability of Russian ground forces for a new operation

Change-points only. Not a weekly series. The file name `o1-ukraine-war` is the existing stem. The locked construct is force availability, not a war-status label.

`date` is the Monday of the week that contains `source_date`. It is not an earlier week.

- 0 = heavily committed elsewhere
- 1 = mostly free with notable commitments
- 2 = moderately committed
- 3 = largely committed
- 4 = largely free

Amended 2026-10-11, before any approval. Reason: middle rungs were undefined. The numbers are the ones written in the amendment. They were not reordered.

### C2 — force posture

Event-based. Not a weekly series.

`date` is the Monday of the week that contains `source_date`. It is not an earlier week.

`region` is one of: `near_ukraine`, `belarus`, `kaliningrad`, `western_md`.

`value` is severity:

- 0 = normal
- 1 = unusual exercise
- 2 = large buildup reported
- 3 = buildup plus logistics signs (field hospitals, blood, fuel)
- 4 = forces in attack positions or official warnings of imminent attack

No dated event means no row.

## Approval page

Drafts are `*-draft.csv`. A click appends to the matching `*-approved.csv`. Approve, Reject, and Unsure save the draft value. "Value should be" saves a number from 0 to 4 plus the optional note, in `corrected_value`. The page is local only.

Start it with `python3 manual/approval_server.py`. It listens on 127.0.0.1:8765. If that port is already this page, stop that process before starting another.
