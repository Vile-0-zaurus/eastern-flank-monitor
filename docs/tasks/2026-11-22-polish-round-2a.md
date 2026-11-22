# Polish round 2, part A — map clarity

Saved 22 November 2026 before this part. No API calls.

Commit and push after each step. If low on steps, stop at a committed point and say what is left.

| # | Task |
|---|------|
| 1 | Show only incidents active in the selected week and the 4 weeks before. Older incidents stay hidden. |
| 2 | Remove count badges and permanent text labels on the map. Overlapping icons are spread slightly apart, never merged into a number. Icons stay a constant size at every zoom. |
| 3 | Hover, and tap on a phone, shows a small card next to the icon: type, place, date, one-sentence summary, and Officially confirmed or Reported only. A click zooms to it and opens the same item in the briefing with its source link. |
| 4 | Officially confirmed is a solid filled icon. Reported only is an outlined icon with no fill. The legend shows exactly these two, with a short line each. The briefing uses the same styling next to items. |
| 5 | Tests: no badges; no map text labels except country names; hidden incidents outside the 5-week window; a hover card for every visible icon; confirmed and reported styling matches the data. Screenshots of the Poland tab for the week of 21 September 2026, and the Latvia tab for the week of 10 August 2026 with the hover card on Balvi, go to ~/Desktop/efm-check5/. Commit, push, report, stop. |
