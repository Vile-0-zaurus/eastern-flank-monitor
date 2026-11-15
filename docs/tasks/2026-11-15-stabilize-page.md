# Stabilize the page

Saved 15 November 2026 before any other work on this assignment.

No API calls. No new features. Restarting the local page server is allowed. Commit and push at the end, then stop.

1. Find why http://127.0.0.1:8080/frontend/ still serves the old page (old banner "Now — frozen window… Not a tension score"). List every process listening on 8080 and the directory it serves. Kill stale servers. Serve this repo's frontend from main. Add cache-busting (?v=<commit hash>) to all JS, JSON, and CSS URLs.
2. Click test with a headless browser (Playwright), in this exact order, screenshot after each step: (a) load page, Now tab; (b) click Lithuania; (c) slider to week 2026-10-19; (d) click Poland; (e) click Show all; (f) click Russia; (g) click Close; (h) switch to 2021–22 replay; (i) click Finland. After every click, assert: the selected chip is highlighted, the dossier title names that country (or Region / Inside Russia), no text says "not in a separate file", and the banner says "Snapshot: 3 Aug – 25 Oct 2026" in Now mode.
3. Fix every failed assertion. Re-run until all pass. Keep the test as tests/click_selftest.py.
4. Save screenshots (b), (c), (d), and (f) to ~/Desktop/efm-check/. Report what was wrong, what was fixed, and the test result. Commit, push, stop.
