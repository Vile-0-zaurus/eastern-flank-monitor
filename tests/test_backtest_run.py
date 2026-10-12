import unittest
from datetime import date

from pipeline.score.backtest_run import (
    c2_level,
    o1_level,
    o2_level,
    score_layers,
    test_a_passes,
    test_b_passes,
)


class C2HoldTest(unittest.TestCase):
    def test_registered_example_holds_four_weeks_and_supersedes(self):
        events = [
            {
                "region": "near_ukraine",
                "date": date(2022, 1, 24),
                "source_date": date(2022, 1, 28),
                "level": 3,
            },
            {
                "region": "near_ukraine",
                "date": date(2022, 2, 7),
                "source_date": date(2022, 2, 10),
                "level": 4,
            },
        ]
        self.assertIsNone(c2_level(events, "ukraine_test", date(2022, 1, 17)))
        self.assertEqual(c2_level(events, "ukraine_test", date(2022, 1, 24)), 3)
        self.assertEqual(c2_level(events, "ukraine_test", date(2022, 1, 31)), 3)
        self.assertEqual(c2_level(events, "ukraine_test", date(2022, 2, 7)), 4)
        self.assertEqual(c2_level(events, "ukraine_test", date(2022, 2, 21)), 4)
        self.assertEqual(c2_level(events, "ukraine_test", date(2022, 3, 7)), 4)
        self.assertIsNone(c2_level(events, "ukraine_test", date(2022, 3, 14)))

    def test_border_map_and_max_across_tags(self):
        events = [
            {
                "region": "near_ukraine",
                "date": date(2022, 1, 24),
                "source_date": date(2022, 1, 28),
                "level": 3,
            },
            {
                "region": "kaliningrad",
                "date": date(2022, 1, 24),
                "source_date": date(2022, 1, 28),
                "level": 2,
            },
            {
                "region": "belarus",
                "date": date(2022, 1, 24),
                "source_date": date(2022, 1, 28),
                "level": 1,
            },
            {
                "region": "western_md",
                "date": date(2022, 1, 24),
                "source_date": date(2022, 1, 28),
                "level": 4,
            },
        ]
        week = date(2022, 1, 24)
        self.assertEqual(c2_level(events, "ukraine_test", week), 4)
        self.assertEqual(c2_level(events, "eastern_flank", week), 4)
        self.assertIsNone(
            c2_level(
                [events[0]],
                "eastern_flank",
                week,
            )
        )
        self.assertIsNone(c2_level([events[1]], "ukraine_test", week))


class StepAndMonthTest(unittest.TestCase):
    def test_o1_holds_from_the_change_point_and_not_before(self):
        points = [
            {
                "date": date(2021, 4, 19),
                "source_date": date(2021, 4, 22),
                "level": 3,
            }
        ]
        self.assertIsNone(o1_level(points, date(2021, 4, 12)))
        self.assertEqual(o1_level(points, date(2021, 4, 19)), 3)
        self.assertEqual(o1_level(points, date(2022, 2, 14)), 3)

    def test_o2_uses_the_month_of_monday_and_does_not_borrow(self):
        months = [
            {
                "date": date(2021, 2, 1),
                "source_date": date(2021, 2, 19),
                "level": 0,
            },
            {
                "date": date(2021, 3, 1),
                "source_date": date(2021, 2, 19),
                "level": 0,
            },
            {
                "date": date(2021, 10, 1),
                "source_date": None,
                "level": None,
            },
        ]
        self.assertIsNone(o2_level(months, date(2021, 2, 8)))
        self.assertEqual(o2_level(months, date(2021, 2, 15)), 0)
        self.assertEqual(o2_level(months, date(2021, 3, 1)), 0)
        self.assertIsNone(o2_level(months, date(2021, 10, 4)))


class ConvergenceRunTest(unittest.TestCase):
    def test_hybrid_is_empty_and_unconfirmed_serious_is_not_plain_elevated(self):
        weights = {"opportunity": {"O1": 1, "O2": 1}, "capability": {"C2": 3}}
        scored = score_layers(2, 2, 2, None, weights)
        self.assertIsNone(scored["hybrid"])
        self.assertEqual(scored["proposed"], 3)
        self.assertEqual(scored["shown"], 2)
        self.assertEqual(
            scored["shown_label"],
            "Elevated (Serious proposed, awaiting confirmation)",
        )

    def test_intent_alone_stays_watchful(self):
        weights = {"opportunity": {"O1": 1, "O2": 1}, "capability": {"C2": 3}}
        scored = score_layers(4, None, None, None, weights)
        self.assertEqual(scored["proposed"], 1)
        self.assertEqual(scored["shown_label"], "Watchful")

    def test_partial_proposal_does_not_decide_the_tests(self):
        rows = [
            {
                "region": "eastern_flank",
                "week": date(2022, 2, 21),
                "partial": True,
                "proposed": 4,
                "shown": 2,
            },
            {
                "region": "ukraine_test",
                "week": date(2021, 3, 15),
                "partial": False,
                "proposed": 1,
                "shown": 1,
            },
        ]
        self.assertTrue(test_b_passes(rows))
        self.assertFalse(test_a_passes(rows))

    def test_ranked_serious_proposal_fails_test_b(self):
        rows = [
            {
                "region": "eastern_flank",
                "week": date(2021, 11, 22),
                "partial": False,
                "proposed": 3,
                "shown": 2,
            }
        ]
        self.assertFalse(test_b_passes(rows))


if __name__ == "__main__":
    unittest.main()
