import sqlite3
import unittest
from unittest.mock import patch

from pipeline.llm.client import load_budget
from pipeline.score.i2_run import (
    _one_grok,
    estimate,
    real_cap_blocks,
    real_spend_usd,
    upfront_usd,
)
from pipeline.score.ukraine_100_finish import CAP, priced


class RealCapTest(unittest.TestCase):
    def test_ticks_sum_to_dollars(self):
        self.assertEqual(real_spend_usd([2_500_000_000, 2_200_000_000]), 0.47)

    def test_missing_ticks_block_the_next_call(self):
        self.assertTrue(real_cap_blocks([100, None], 4.70))

    def test_reaching_the_cap_blocks_and_a_cent_under_does_not(self):
        self.assertTrue(real_cap_blocks([47_000_000_000], 4.70))
        self.assertFalse(real_cap_blocks([46_999_999_999], 4.70))

    def test_an_empty_run_is_not_already_at_the_cap(self):
        self.assertFalse(real_cap_blocks([], 4.70))

    def test_a_batch_does_not_call_when_recorded_ticks_are_at_the_cap(self):
        con = sqlite3.connect(":memory:")
        con.execute("CREATE TABLE spend (id INTEGER PRIMARY KEY, model TEXT, usd REAL, note TEXT, ticks INTEGER, run_id TEXT)")
        con.execute("CREATE TABLE answers (sample_id TEXT, model TEXT, region TEXT, week TEXT, status TEXT, hostile TEXT, relevant TEXT, result_json TEXT)")
        con.execute(
            "INSERT INTO spend (model, usd, note, ticks, run_id) VALUES (?,?,?,?,?)",
            ("grok-build-0.1", 4.70, "ukraine_test", 47_000_000_000, "ukraine-100-finish"),
        )
        batch = [{"id": "1", "region": "ukraine_test", "week": "2022-01-03", "title": "x"}]

        def boom(*args, **kwargs):
            raise AssertionError("complete was called")

        with patch("pipeline.score.i2_run.complete", side_effect=boom):
            result = _one_grok(
                con, {}, "prompt", "ukraine_test", batch, 100.0, tries_left=2,
                real_cap=4.70, spend_after=0, run_id="ukraine-100-finish",
            )
        self.assertEqual(result, "stop")
        self.assertEqual(con.execute("SELECT COUNT(*) FROM answers").fetchone()[0], 0)

    def test_measured_gate_is_under_the_cap_and_the_higher_figure_is_not(self):
        budget = load_budget()
        self.assertTrue(budget["calibration_factor_set"])
        self.assertEqual(budget["calibration_factor"], 3.2)
        est = estimate(5387, 50)
        self.assertGreater(upfront_usd(est["grok_expected"], est["grok_cap"], 3.2), CAP)
        quote = priced(5387)
        self.assertLessEqual(quote["measured"], CAP)
        self.assertGreater(quote["upfront"], CAP)


if __name__ == "__main__":
    unittest.main()
