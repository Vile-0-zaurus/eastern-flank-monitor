# Stabilize the page

Date: 15 November 2026. No API calls. No new features.

## What was wrong

One process was listening on 8080: python3 pid 14323, started 15 November 17:09, working directory /home/supra/Projects/eastern-flank-monitor. It was already serving this repo. The file on disk and the file the server returned both contain the new banner. The old banner was the browser's cached copy of app.js, which had no version in the URL.

## What changed

The old server was stopped and a new one was started on 127.0.0.1:8080 from the same repo. JS, JSON, and CSS URLs used by the main page now end with ?v=633c44d.

The click test is tests/click_selftest.py. It uses Playwright with the installed Chrome, because the Playwright headless-shell browser is not on this machine. It passed all nine steps. Screenshots (b), (c), (d), and (f) are in /home/supra/Desktop/efm-check/.
