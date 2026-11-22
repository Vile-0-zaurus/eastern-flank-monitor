# Polish round 3 — last before finish

Saved 22 November 2026 before this round. No API calls. No bypass of blocks. Research user-agent only.

Commit and push after each section. If low on steps, stop at a committed point and say what is left.

Pre-approved: read-only database scans, running scripts and tests, restarting the local page server, read-only fetch of official or established pages for facts and Levada, git commit and push.

## Section 1 — hover fix

1. Remove the native browser tooltip (title attribute) from all map icons and anywhere it duplicates a custom card. Only the custom hover card remains.
2. The card never covers the hovered icon. It sits beside the icon and flips near the map edges. It closes on mouse leave. Only one card is visible at a time. A tap on a phone opens it. A tap elsewhere closes it.

## Section 2 — icon visibility

3. Every icon sits on a dark circular background so it reads on any map color.
4. Officially confirmed is a solid white icon. Reported only is an amber dashed outline. The legend and the briefing items use the same styling. Check contrast on land and sea, and in light and dark mode.

## Section 3 — country facts

5. Add to Finland, Estonia, Latvia, Lithuania, and Poland, each with a dated source link. Never from memory. If no dated source is reachable, leave that fact out.
   - Defense spending as a share of GDP, latest year, NATO estimate.
   - Allied troops present, for example a NATO multinational battlegroup or brigade and its lead nation. Do not put these on the map.
   - Conscription: yes or no, and since when if the page states it.
   - Distance from the capital to the Russian or Belarusian border, in kilometres. Label it computed if it comes from map coordinates.
   - No ethnic or language statistics.
   - Translate the labels in all 6 languages.

## Section 4 — poll update

6. Levada Center: find the latest published "friends and enemies of Russia" survey published on or before 25 October 2026. Store the date, the question, the results for Finland, Estonia, Latvia, Lithuania, Poland, and the United States and Ukraine as reference, and the link.
7. Now tab: the background poll card shows that latest poll, with its year. Replay keeps the 2021 poll. If no newer poll than 2021 is reachable, the Now card says "Latest reachable poll: 2021." Record the outcome in docs/sources.md.

## Section 5 — tests and screenshots

8. Tests: no native title tooltip on the map; one hover card at a time; confirmed is solid white; reported is amber dashed; every country fact has a source; the poll date is on or before the window end in Now, and 2021 in replay. All existing tests pass.
9. Screenshots to ~/Desktop/efm-check6/: Latvia, week of 10 August 2026, hovering Balvi (confirmed); Lithuania, week of 12 October 2026, hovering a reported icon; a country facts card; the Russia tab poll card in Now. Update STATE.md. Commit, push, report, stop.
