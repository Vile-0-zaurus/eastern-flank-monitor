import unittest
from datetime import date

from pipeline.fetch.now_download import (
    day_exceeds,
    disk_allows,
    full_weeks,
    keep_row,
    mentions_region,
)


class WindowTest(unittest.TestCase):
    def test_monday_uses_the_twelve_weeks_that_already_ended(self):
        start, end = full_weeks(date(2026, 10, 19))
        self.assertEqual(start, "20260727")
        self.assertEqual(end, "20261018")

    def test_sunday_does_not_include_the_unfinished_week(self):
        start, end = full_weeks(date(2026, 10, 18))
        self.assertEqual(end, "20261011")
        self.assertEqual(start, "20260720")


class KeepTest(unittest.TestCase):
    def test_russian_outlet_keeps_an_unrelated_row(self):
        self.assertTrue(keep_row(
            "tass.ru", {"tass.ru"}, {"reuters.com"},
            "London court ruling on Assange - senator", "", "",
        ))

    def test_western_outlet_drops_a_senator_line_with_no_region(self):
        self.assertFalse(mentions_region(
            "London court ruling on Assange worthy of independent justice - senator",
            "", "",
        ))
        self.assertFalse(keep_row(
            "reuters.com", {"tass.ru"}, {"reuters.com"},
            "London court ruling on Assange worthy of independent justice - senator",
            "1#London, United Kingdom#UK#LND", "",
        ))

    def test_western_outlet_keeps_nato_and_a_location_code(self):
        self.assertTrue(mentions_region("NATO ministerial meeting", "", ""))
        self.assertTrue(mentions_region("", "4#Kaliningrad, Kaliningrad, Russia#RS#23", ""))
        self.assertTrue(mentions_region("", "", "1#Helsinki, Finland#FI#01"))
        self.assertFalse(mentions_region("", "1#London#ENGLAND#UK", ""))


class GuardTest(unittest.TestCase):
    def test_disk_and_size_gates(self):
        self.assertFalse(disk_allows(9_999_999_999))
        self.assertTrue(disk_allows(10_000_000_000))
        self.assertFalse(day_exceeds(50_000_000))
        self.assertTrue(day_exceeds(50_000_001))


if __name__ == "__main__":
    unittest.main()
