import io
import tempfile
import unittest
import urllib.error
from pathlib import Path

from pipeline.llm.call_guard import decide, error_record, log_provider_error


def http_error(status, body, reason="error"):
    return urllib.error.HTTPError(
        "https://api.x.ai/v1/chat/completions",
        status,
        reason,
        hdrs={},
        fp=io.BytesIO(body if isinstance(body, bytes) else body.encode("utf-8")),
    )


class ErrorLogTest(unittest.TestCase):
    def test_status_code_and_message_are_logged(self):
        record = error_record(http_error(429, b'{"error":{"message":"too many requests"}}'))
        self.assertEqual(record["status"], 429)
        self.assertIn("too many requests", record["message"])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "errors.log"
            line = log_provider_error(record, path)
            stored = path.read_text(encoding="utf-8")
        self.assertIn("status=429", line)
        self.assertIn("too many requests", line)
        self.assertEqual(stored, line)

    def test_a_key_in_the_error_body_is_not_logged(self):
        record = error_record(http_error(401, b'{"error":{"message":"bad key xai-secretvalue1234"}}'))
        self.assertNotIn("xai-secretvalue1234", record["message"])
        self.assertIn("[redacted]", record["message"])


class RateLimitTest(unittest.TestCase):
    def test_429_backs_off_and_retries_without_marking(self):
        first = decide(http_error(429, b'{"error":{"message":"too many requests"}}'), attempt=0, failures=[])
        second = decide(http_error(429, b'{"error":{"message":"too many requests"}}'), attempt=1, failures=[])
        self.assertEqual(first["action"], "retry")
        self.assertFalse(first["mark"])
        self.assertGreater(second["wait"], first["wait"])
        self.assertIn("status=429", first["log"])
        self.assertIn("too many requests", first["log"])


class StopRunTest(unittest.TestCase):
    def test_auth_and_balance_stop_without_marking_rows(self):
        auth = decide(http_error(401, b'{"error":{"message":"invalid api key"}}'), attempt=0, failures=[])
        balance = decide(http_error(402, b'{"error":{"message":"insufficient credits"}}'), attempt=0, failures=[])
        words = decide(http_error(400, b'{"error":{"message":"credit balance too low"}}'), attempt=0, failures=[])
        for decision in (auth, balance, words):
            self.assertEqual(decision["action"], "stop")
            self.assertFalse(decision["mark"])
            self.assertIn("status=", decision["log"])


class CircuitBreakerTest(unittest.TestCase):
    def test_more_than_ten_percent_of_the_last_100_calls_pauses(self):
        almost = [False] * 89 + [True] * 10
        tripped = decide(http_error(500, b'{"error":{"message":"upstream"}}'), attempt=0, failures=almost)
        self.assertEqual(tripped["action"], "pause")
        self.assertFalse(tripped["mark"])
        self.assertIn("11", tripped["report"])
        self.assertIn("100", tripped["report"])

    def test_ten_percent_does_not_pause(self):
        almost = [False] * 90 + [True] * 9
        held = decide(http_error(500, b'{"error":{"message":"upstream"}}'), attempt=0, failures=almost)
        self.assertNotEqual(held["action"], "pause")

    def test_a_short_run_does_not_trip_the_breaker(self):
        early = decide(http_error(500, b'{"error":{"message":"upstream"}}'), attempt=2, failures=[True] * 10)
        self.assertNotEqual(early["action"], "pause")


class ResumeTest(unittest.TestCase):
    def test_unavailable_rows_are_retried_and_real_answers_are_not(self):
        from pipeline.score.i2_run import grok_pending

        rows = [
            {"id": "1", "region": "eastern_flank", "week": "2021-01-04", "title": "a"},
            {"id": "2", "region": "eastern_flank", "week": "2021-01-04", "title": "b"},
            {"id": "3", "region": "ukraine_test", "week": "2021-01-04", "title": "c"},
        ]
        stored = {"1": "ok", "2": "AI unavailable"}
        pending = grok_pending(rows, stored)
        self.assertEqual([row["id"] for row in pending], ["2", "3"])


class RunnerStopTest(unittest.TestCase):
    def test_auth_error_does_not_store_the_batch(self):
        import sqlite3
        from unittest.mock import patch

        import pipeline.score.i2_run as run

        con = sqlite3.connect(":memory:")
        con.execute(
            """
            CREATE TABLE answers (
              sample_id TEXT, model TEXT, region TEXT, week TEXT,
              status TEXT, hostile TEXT, relevant TEXT, result_json TEXT
            )
            """
        )
        con.execute("CREATE TABLE spend (id INTEGER PRIMARY KEY, model TEXT, usd REAL, note TEXT)")
        batch = [{"id": "9", "region": "eastern_flank", "week": "2021-01-04", "title": "x"}]
        err = http_error(401, b'{"error":{"message":"invalid api key"}}')
        with patch.object(run, "complete", side_effect=err), patch.object(run.time, "sleep"):
            with self.assertRaises(SystemExit):
                run._one_grok(con, {}, "prompt", "eastern_flank", batch, 10.0, tries_left=2)
        stored = con.execute("SELECT COUNT(*) FROM answers").fetchone()[0]
        self.assertEqual(stored, 0)


class RetryGateTest(unittest.TestCase):
    def test_retry_gate_is_the_higher_grok_figure_without_sonnet(self):
        from pipeline.score.i2_run import estimate

        est = estimate(100, 50)
        self.assertEqual(est["retry_gate"], max(est["grok_expected"], est["grok_cap"]))
        self.assertLess(est["retry_gate"], est["gate"])

    def test_a_retry_above_the_approved_cap_does_not_call(self):
        from pipeline.score.i2_run import assert_retry_allowed, retry_spend_ceiling

        with self.assertRaises(SystemExit) as caught:
            assert_retry_allowed(6.11)
        self.assertIn("6.11", str(caught.exception))
        self.assertIn("No call was made", str(caught.exception))
        assert_retry_allowed(6.10)
        assert_retry_allowed(6.0964)
        self.assertAlmostEqual(retry_spend_ceiling(1.2295, 6.10, 10.0), 7.3295)
        self.assertEqual(retry_spend_ceiling(0.0, 6.10, 5.0), 5.0)


if __name__ == "__main__":
    unittest.main()
