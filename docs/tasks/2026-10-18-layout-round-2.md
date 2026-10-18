# Layout round 2

Saved 2026-10-18 before any other work on this assignment.

No API calls. No new features. Do not rescore the stored week table. Do not move the pre-registered tags. Do not delete data.

1. Map smaller: about 35–40% of the width (desktop). The dossier gets the rest, about 60%, and is open by default. When no country is picked, it shows the region overview.
2. Region status strip: fixed widths for every element (state word, arrow, chips) so nothing moves or reflows when the week changes during playback.
3. Play controls: fully visible at all window heights (min-height check). Never cut off. Still one scroll on desktop.
4. Self-test: measure element positions across 10 played weeks. The region strip and the controls must not move. Controls fully inside the viewport at 768px and 1080px window heights. Video at ~/Desktop/efm-layout2.mp4. Commit, push, stop.
