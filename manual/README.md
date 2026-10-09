# Manual inputs

Empty on purpose. A blank file is no data. Do not read it as zero.

Until the admin page exists, edit these by hand. One source link per row. A row with no link does not count.

`source_date` is the publication date of the source, `YYYY-MM-DD`.

`date` is the Monday of that week, `YYYY-MM-DD`, except in the incident log. There, `date` is the incident's own date, not the week Monday.

| File | What `value` is | What `date` is |
|---|---|---|
| `o1-ukraine-war.csv` | Integer 0–4. Ukraine war status for the week. | Monday of the week |
| `o2-us-commitment.csv` | Integer 0–4. US commitment to European defense for the week. | Monday of the week |
| `c2-force-posture.csv` | Short note. Official intelligence report or established think tank only. | Monday of the week |
| `h2-incident-log.csv` | One incident note. Several incidents in one week are several rows. | The incident's own date |

No-hindsight rule: a row counts for week W only if source_date ≤ last day of W. Week W runs Monday through Sunday, so the last day is Sunday. A source published after that Sunday is ignored for W. It may count for a later week. A missing source_date does not count. Ignored is no data, not zero.

The 0–4 scale is not tuned yet. Do not invent rows.
