# Fix round part 2 — map and country logic

Saved 2026-10-18 before any other work on this assignment.

No API calls. Do not rescore the stored week table. Do not move the pre-registered tags. Do not delete data. Do not make anything public. Read gkg.sqlite read-only. Do not invent per-country levels.

## Fix

1. The map fills each country with its state color, muted, with a legend. Event dots have a short label. Dots fade in when an event starts and out when it expires. Hover shows one line. Click shows details and the source. The map stays readable in light and dark mode, and it is wide.
2. Until per-country levels exist, one region-wide state sits at the top. Country cards show only facts about that country. They do not inherit Tense.
3. A country panel lists an event only if it concerns that country. Belarus events facing Ukraine, including Mozyr and Gomel or Zyabrovka, are not shown for Finland, Estonia, or Latvia. Zapad and the western military district may show for Finland and the Baltics.
4. Country panels use stored headlines from gkg.sqlite that name that country. No model calls. Up to three lines, hostile-flagged first, each with an English line. Title stays "This week in <country>". A quiet week says "Quiet week — nothing notable."
5. Self-test, then a 30-second video at ~/Desktop/efm-fixed.mp4.
