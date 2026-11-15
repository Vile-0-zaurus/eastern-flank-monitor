# UX restructure

Date: 15 November 2026. No API calls. No new data.

The chip row, Show all, the drawer close button, and the word Dossier are gone. One tab is always selected. The default is Lithuania. The selected tab is marked on the map.

The right column is a fixed briefing. The sections are Bottom line, What happened, What officials said, What Russian media says, and What regional media says. An empty section says "Nothing this week." The Russia tab shows the bottom line and the Inside Russia cards.

Tab labels are plain words, such as "Lithuania · 63 Russian stories (usual 46) · 0 incidents". Replay drops the Jaruzelski history piece. The relevance self-test checks that line.

`tests/click_selftest.py` passed. It clicks every tab in Now mode and in the 2021–22 replay, and checks the bottom line and the section order. Screenshots are in /home/supra/Desktop/efm-check2/.
