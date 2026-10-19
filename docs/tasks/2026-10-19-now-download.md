# Now download and presentation fixes

Saved 2026-10-19 before any other work on this assignment.

No API calls. Never bypass blocks: no VPN, no DNS changes, no user-agent spoofing. Do not rescore the stored week table. Do not move the pre-registered tags. Do not delete the 2021–22 backfill. Commit and push after each section. If low on steps, stop at a committed point and say what is left.

Window for the download: the last 12 full weeks before Monday 2026-10-19, which is 2026-07-27 through 2026-10-18.

## Section 1 — start the download first

1. New resumable background service `efm-now-download`. systemd user service, enabled so it resumes after reboot. It waits for the network. It does not download when free disk is under 10 GB. At most 2 parallel downloads. A network or DNS error is retried and is never a final failure. Raw GKG files are streamed and not stored.
2. Keep every row from the Russian outlet list in `config/outlets.yaml`. Those totals are needed. Also keep a verified list of regional and Western outlets in `config/western-outlets.yaml`. For those, keep only rows whose title or location mentions Finland, Estonia, Latvia, Lithuania, Poland, the Baltics, Belarus, Kaliningrad, Russia, Ukraine, or NATO. Same columns as the backfill. Separate database `data/now/gkg-now.sqlite`. Daily totals per outlet.
3. After the first day of data, report the stored size for that day. If a day exceeds 50 MB of stored text, stop and say so.
4. `efm-status` shows Now-download progress, an arrival time, and that it pauses while the machine is off. Start the service, confirm it is running, then Section 2.
5. Live retention is a plan only. It is already in SPEC §14.6. Do not build it.

## Section 2 — presentation fixes, on the existing replay

6. Each Inside Russia card's main line is its most notable item. The count is small grey text.
7. An empty card that week is one line, or hidden. Never a big empty box.
8. A quiet week says "Last notable: <N> weeks ago — <one-line event>" with a source link.
9. The conscription card appears only during a spring or autumn call-up, or when conscription news exists. Public mood moves to a small Background box with the latest poll and its date.
10. The timeline marks notable weeks with small ticks. Play has an option to skip quiet weeks.
11. Self-test: one scroll, no jumping, no empty boxes. Commit, push, stop.
