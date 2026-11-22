#!/usr/bin/env python3
"""Live gates, drafts, and the site build. No API calls. No downloads."""
from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "live"))

from build_site import build_site  # noqa: E402
from drafts import collect_drafts, decide, published_incidents  # noqa: E402
from gate import classify_allowed, monitoring_state, rolling_weeks, window_for  # noqa: E402


class GateTest(unittest.TestCase):
    def test_off_keeps_the_snapshot(self):
        state = monitoring_state({"live_monitoring": "off", "live_end_date": ""}, date(2026, 11, 22))
        self.assertFalse(state["run"])
        self.assertTrue(state["snapshot"])
        window = window_for(
            {"live_monitoring": "off"},
            date(2026, 11, 22),
            {"window_start": "2026-08-03", "window_end": "2026-10-25"},
        )
        self.assertEqual(window["start"], "2026-08-03")
        self.assertEqual(window["end"], "2026-10-25")
        self.assertFalse(window["changed"])

    def test_on_without_an_end_date_is_refused(self):
        with self.assertRaises(ValueError):
            monitoring_state({"live_monitoring": "on"}, date(2026, 11, 22))

    def test_on_uses_a_rolling_12_week_window(self):
        state = monitoring_state({"live_monitoring": "on", "live_end_date": "2026-12-31"}, date(2026, 11, 22))
        self.assertTrue(state["run"])
        start, end = rolling_weeks(date(2026, 11, 22))
        self.assertEqual(end, "2026-11-22")
        self.assertEqual(start, "2026-08-31")

    def test_after_the_end_date_the_job_stops(self):
        state = monitoring_state({"live_monitoring": "on", "live_end_date": "2026-11-22"}, date(2026, 11, 22))
        self.assertFalse(state["run"])
        self.assertTrue(state["ended"])
        self.assertIn("Live monitoring ended 2026-11-22", state["message"])

    def test_classification_stops_at_the_cap(self):
        self.assertFalse(classify_allowed(False, 0, 0.01, 5))
        self.assertFalse(classify_allowed(True, 0, 0.01, 0))
        self.assertFalse(classify_allowed(True, 4.99, 0.02, 5))
        self.assertTrue(classify_allowed(True, 4.99, 0.01, 5))


class DraftTest(unittest.TestCase):
    def test_a_draft_is_not_published_until_approved(self):
        rows = collect_drafts([
            {"source": "https://yle.fi/a/1", "source_date": "2026-11-01", "summary": "A stored Yle row"},
            {"source": "https://example.com/nope", "source_date": "2026-11-01", "summary": "skip"},
        ])
        self.assertEqual(len(rows), 1)
        self.assertEqual(published_incidents(rows), [])
        approved = decide(rows[0], "approve", "checked")
        self.assertEqual(approved["status"], "approved")
        self.assertEqual(len(published_incidents([approved])), 1)
        reported = decide(rows[0], "reported", "")
        self.assertEqual(reported["status"], "reported")

    def test_reject_stays_off_the_site(self):
        row = collect_drafts([{"url": "https://www.bbc.com/news/1", "date": "2026-11-02", "english": "A stored BBC row"}])[0]
        rejected = decide(row, "reject", "not an incident")
        self.assertEqual(published_incidents([rejected]), [])


class SiteTest(unittest.TestCase):
    def test_the_admin_page_is_not_copied(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            frontend = root / "frontend"
            (frontend / "admin").mkdir(parents=True)
            (frontend / "admin" / "index.html").write_text("secret", encoding="utf-8")
            (frontend / "index.html").write_text("page", encoding="utf-8")
            dest = build_site(frontend, root / "site")
            self.assertTrue((dest / "index.html").exists())
            self.assertFalse((dest / "admin").exists())


if __name__ == "__main__":
    unittest.main()
