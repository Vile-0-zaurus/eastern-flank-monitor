# Bug fix round

Saved 2026-10-18 before any other work on this assignment.

No API calls. Do not rescore the stored week table. Do not move the pre-registered tags. Do not delete data. Do not make anything public.

## Fix

1. Pause stops playback immediately. Play and Pause are one toggle that shows the current state. Clicking the slider or a week also stops playback.
2. A week change updates the content in place. No auto-scroll. No page jump. Panels keep a fixed height so the layout does not shift.
3. The panel title is "This week in <country>", not "Why tense". A quiet week, with no events, no official statement, and no headline, shows one line: "Quiet week — nothing notable."
4. In dark mode the map uses lighter fills and borders, high-contrast labels and dots, and a wider map.
5. The self-test checks that Pause stops playback and that the scroll position does not change when the week changes.
