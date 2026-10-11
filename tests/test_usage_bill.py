import unittest

from pipeline.llm.client import billed_usd, load_config, usage_parts


PRICES = {
    "models": {
        "grok-build-0.1": {"input": 1.0, "cached": 0.2, "output": 2.0, "reasoning": 2.0},
    }
}


class UsageBillTest(unittest.TestCase):
    def test_ticks_are_the_billed_amount(self):
        usage = {
            "prompt_tokens": 1000,
            "completion_tokens": 100,
            "cost_in_usd_ticks": 7_200_000_000,
        }
        self.assertEqual(billed_usd(usage, PRICES, "grok-build-0.1"), 0.72)

    def test_reasoning_outside_completion_is_added_at_the_output_rate(self):
        usage = {
            "prompt_tokens": 1000,
            "completion_tokens": 100,
            "reasoning_tokens": 500,
            "total_tokens": 1600,
        }
        self.assertEqual(billed_usd(usage, PRICES, "grok-build-0.1"), 0.0022)

    def test_nested_reasoning_inside_completion_is_not_added_twice(self):
        usage = {
            "prompt_tokens": 1000,
            "completion_tokens": 600,
            "completion_tokens_details": {"reasoning_tokens": 500},
            "total_tokens": 1600,
        }
        self.assertEqual(usage_parts(usage)["reasoning_extra"], 0)
        self.assertEqual(billed_usd(usage, PRICES, "grok-build-0.1"), 0.0022)

    def test_cached_input_uses_the_lower_rate(self):
        usage = {
            "prompt_tokens": 1000,
            "completion_tokens": 0,
            "prompt_tokens_details": {"cached_tokens": 800},
        }
        self.assertAlmostEqual(billed_usd(usage, PRICES, "grok-build-0.1"), 0.00036)

    def test_stored_visible_tokens_do_not_become_the_console_bill(self):
        usage = {"prompt_tokens": 50428, "completion_tokens": 85799, "cached_tokens": 18496}
        self.assertAlmostEqual(billed_usd(usage, PRICES, "grok-build-0.1"), 0.2072292)

    def test_config_reads_the_cached_and_reasoning_rates(self):
        prices = load_config()["models"]["grok-build-0.1"]
        self.assertEqual(prices["cached"], 0.2)
        self.assertEqual(prices["reasoning"], 2.0)


if __name__ == "__main__":
    unittest.main()
