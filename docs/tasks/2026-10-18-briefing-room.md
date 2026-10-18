# Design round — Briefing Room

Saved 2026-10-18 before any other work on this assignment.

No API calls. No new features. No data changes. Do not rescore the stored week table. Do not move the pre-registered tags. Do not delete data. One design round, then one polish at most.

1. On first load, two dark panels split open diagonally, about one second, revealing the map. Once per visit. A Skip button. Off when prefers-reduced-motion is set.
2. Full-width dark map as the centerpiece. Left rail fixed: Play/Pause, the week slider, and Week of the date. Top slim strip: the region state and five country chips. Right drawer slides in when a country is picked: state, why, News about that country, Officials say, and Inside Russia. Closing the drawer returns to the map. On a phone, the drawer is a bottom sheet and the rail is a bottom bar.
3. Near-black navy background. One cool teal accent. State colors are muted green, amber, and red, always with the word. Sans-serif for text, vendored. Monospace for dates, counts, and sources, vendored. Small-caps section labels. Hairline borders. A subtle grid on the map background. No gradients except a soft glow on countries. No stamps, no secret or classified wording, no red flashing.
4. Motion only with a purpose: the drawer slides, event dots pulse once when they appear, numbers count up briefly on a week change, content updates in place. All of it respects prefers-reduced-motion.
5. Keep the existing content rules: English first, the relevance filter, no scare words, and the disclaimer. Light mode may stay simple. Dark is the main look.
6. Self-test: no layout shift, controls reachable while playing, contrast AA, reduced-motion works. Screenshots to docs/screenshots/. Video ~/Desktop/efm-briefing-room.mp4, 30 seconds, including the door opening. Commit, push, stop.
