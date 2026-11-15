# UX restructure

Saved 15 November 2026 before any other work on this assignment.

No API calls. No new data. No new features. Restarting the local page server is allowed. Commit and push at the end, then stop.

1. Replace chips, Show all, the drawer, and Close with a tab row: Finland, Estonia, Latvia, Lithuania, Poland, Russia. Exactly one tab is always selected. Default is Lithuania. The selected tab is highlighted on the map. Remove the word Dossier.
2. The right column is a fixed briefing, always visible. Sections, in order: Bottom line (one sentence from that week's data: attention versus usual in words, plus the most notable incident or statement); What happened (incidents with Confirmed or Reported and a link); What officials said; What Russian media says (English first); What regional media says (Yle, BBC). An empty section is one grey line: Nothing this week. The Russia tab is Bottom line plus the Inside Russia cards.
3. Tab labels are plain words, for example: Finland · 38 Russian stories (usual 40) · 1 incident. No unexplained arrows or codes.
4. Replay relevance: drop history and culture pieces, such as Jaruzelski and how Poland rebelled. Add that case to the relevance self-test.
5. Update tests/click_selftest.py for tabs. Click every tab in both modes. Assert the bottom line is present and the sections are in order. Screenshots of Lithuania in the week of 19 October 2026, Poland, and Russia go to ~/Desktop/efm-check2/. Commit, push, stop.
