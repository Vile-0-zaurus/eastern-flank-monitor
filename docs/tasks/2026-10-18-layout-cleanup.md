# Layout cleanup — Briefing Room

Saved 2026-10-18 before any other work on this assignment.

No API calls. No new features. Do not rescore the stored week table. Do not move the pre-registered tags. Do not delete data.

1. On desktop the app fills the window. The page itself does not scroll. Only the drawer scrolls, with one scrollbar. Sections inside the drawer do not scroll on their own. A long list shows three items and Show more. On a phone, the page scrolls normally and nothing inside it scrolls on its own.
2. Fit and center the whole region in the map: Finland, the Baltics, Poland, Belarus, Kaliningrad, western Russia, and Ukraine. No empty half. Nothing cut off at the bottom. Draw Russia with its real border, not a straight-cut block.
3. The footer is one thin line at the bottom of the left rail: the short disclaimer and More. It must not overlap content.
4. Merge "What Russian state media says" and "News about <country>" into one section, "Russian media about <country>", using all stored headlines. "This week" uses that same data. It must not say nothing while news is shown below.
5. Remove "stored headlines" and "Cards list only…". Country chips show the name, the state word, and an arrow only. Deduplicate near-identical stories everywhere.
6. Self-test: on desktop, exactly one scrollable element, the drawer. No overlapping elements. No contradiction between This week and the news section. Screenshot and a 30-second video at ~/Desktop/efm-clean.mp4. Commit, push, stop.
