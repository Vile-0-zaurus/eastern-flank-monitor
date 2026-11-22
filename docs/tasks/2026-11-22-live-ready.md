# Release part 2: live-ready, off, plus mobile

Saved 22 November 2026 before edits. No API calls. Commit and push after each section. live_monitoring stays off.

0. Add the classifier and judge to the README tech line.
1. Mobile layout for iPhone 13, Pixel 7, and iPad, in English and Lithuanian. Add tests/mobile_selftest.py. Screenshots in ~/Desktop/efm-mobile/.
2. Build scripts/live/daily_run.py. Rolling 12-week window in live mode only. Snapshot dates stay fixed. No paid translation. Classification only when live_monitoring is on, under a monthly real-charge cap.
3. Daily incident drafts from official sources and stored Yle/BBC rows. Drafts stay off the site until approved.
4. Local admin page: Approve, Reject, Reported-only, plus a note. Approved items go to the incident file.
5. config/app.yaml: live_monitoring off, live_end_date, next_update_time. Unit tests for on, off, and after the end date.
6. A workflow_dispatch-only dry-run for one day. No schedule. No deploy.
7. Document the same job on a small Linux server in DEPLOY.md.
8. A self-contained site folder and a workflow_dispatch-only Pages workflow. Do not run it.
9. Go-live checklist in DEPLOY.md. README Deploy section links it.
10. All tests pass. Update STATE.md. Report and stop.
