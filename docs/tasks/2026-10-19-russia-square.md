# Russia square and cleanups

Saved 2026-10-19 before any other work on this assignment.

No API calls. No new data. Do not rescore the stored week table. Do not move the pre-registered tags. Do not delete data. If low on steps, stop at a committed point and say what is left.

## Tasks

1. Add a Russia square to the top strip, after Poland. It has its own accent and border. It is not a tension reading. Click opens Inside Russia in the dossier. Close, or clicking the square again, returns to the region. Clicking Russia on the map does the same.
2. Inside Russia is closable from every way it can be opened. It is not stuck on the dossier. The open or closed state stays while the weeks play.
3. Public mood is one plain sentence plus a small horizontal bar chart. Bars, in this order: Lithuania, Latvia, Estonia, Poland, Finland, then USA and Ukraine as reference. The axis is "% of Russians naming this country unfriendly". Sentence: "In May 2021, Russians often named the Baltic states and Poland as unfriendly (Levada)." Under the chart: poll date, pollster, "Polls in Russia may not reflect honest opinion", source link, and Full poll behind a toggle. Shown only from that poll's publication week onward. Finland was not in the printed table. Do not invent a number for it. The later stored Levada pages do not have this breakdown, so they do not replace the chart.
4. News sections stay compact: 3 items, then Show more.
5. Conscription card: leave unchanged.
6. Side check: a Russian speaker, including a senator or a Federation Council member, never appears under Regional and Western officials. An off-topic item such as the Assange headline is dropped by the relevance rule. The bug is that "nato" is found inside "senator". Add a self-test for that exact item.
7. Self-test: one scroll, no jumping, Russia square toggles. Video at ~/Desktop/efm-russia-square.mp4, 30 seconds. Commit, push, stop.

## Risk

Risk 3.5. The sixth square can clip the strip at 1280px. The side rule must not treat a US, French, or Dutch senator as Russian. Finland must stay "not listed".

Confidence 7.5 before the self-test. The poll numbers are already in manual/russia/polls.json. The screen code is in frontend/app.js.
