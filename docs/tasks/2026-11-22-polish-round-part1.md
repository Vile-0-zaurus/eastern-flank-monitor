# Polish round, part 1 — commit, then map icon fixes

Saved 22 November 2026 before this part. No API calls.

Commit and push after each step. If low on steps, stop at a committed point and say what is left.

Pre-approved: running scripts and tests, restarting the local page server, git commit and push.

| # | Task |
|---|------|
| 1 | First: commit and push Section 3 (quiet weeks "In the news" plus fact cards) if not already pushed. Report the commit. |
| 2 | Icon size: incident icons keep a constant on-screen size at every zoom (scale inversely to zoom, about 18 px radius on screen). They must never grow with zoom. |
| 3 | Overlap: icons closer than about 2 icon widths on screen are clustered into one badge with a count ("2"). Clicking the badge zooms in until they separate. Icons and country labels never cover each other. |
| 4 | Tab auto-zoom: selecting a country tab smoothly zooms the map to that country. Reset returns to the region view. At country zoom, show a short label next to each icon (type and date). |
| 5 | Tests: icon on-screen size identical at zoom 1×, 2×, and 4×; no icon overlapping a country label at country zoom; tab auto-zoom works for all 5 countries. Commit, push, report, stop. |
