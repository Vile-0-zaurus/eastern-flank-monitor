import tempfile
import unittest
from pathlib import Path

from scripts.m0.daily_collect import (
    collect_exit_code,
    enabled_sources,
    feeds_already_saved,
    wait_for_connectivity,
)


class SavedFeedsTest(unittest.TestCase):
    def test_skip_only_when_every_enabled_feed_is_saved(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            (dest / "tass-en.xml.gz").write_bytes(b"x")
            (dest / "tass-ru.xml.gz").write_bytes(b"y")
            (dest / "collect.log").write_text(
                "2026-10-10T08:00:00+00:00 SUCCESS tass-en.xml HTTP 200 bytes=1\n"
                "2026-10-10T08:00:01+00:00 FAILURE tass-ru.xml HTTP 500\n",
                encoding="utf-8",
            )
            names = ["tass-en.xml", "tass-ru.xml", "navtex-ru"]
            self.assertFalse(feeds_already_saved(dest, names))
            (dest / "navtex-ru.txt.gz").write_bytes(b"z")
            (dest / "collect.log").write_text(
                "2026-10-10T08:00:00+00:00 SUCCESS tass-en.xml HTTP 200 bytes=1\n"
                "2026-10-10T08:00:01+00:00 SUCCESS tass-ru.xml HTTP 200 bytes=1\n"
                "2026-10-10T08:00:02+00:00 SUCCESS navtex-ru HTTP 200 warnings=1 bytes=1\n",
                encoding="utf-8",
            )
            self.assertTrue(feeds_already_saved(dest, names))

    def test_a_later_failure_is_not_saved(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            (dest / "tass-en.xml.gz").write_bytes(b"x")
            (dest / "collect.log").write_text(
                "2026-10-10T08:00:00+00:00 SUCCESS tass-en.xml HTTP 200 bytes=1\n"
                "2026-10-10T18:00:00+00:00 FAILURE tass-en.xml HTTP 500\n",
                encoding="utf-8",
            )
            self.assertFalse(feeds_already_saved(dest, ["tass-en.xml"]))

    def test_disabled_sources_are_not_required(self):
        disabled = {"ria.xml": "blocked", "mfa.xml": "blocked"}
        names = enabled_sources(disabled)
        self.assertEqual(names, ["tass-en.xml", "tass-ru.xml", "navtex-ru"])
        self.assertNotIn("ria.xml", names)


class ExitCodeTest(unittest.TestCase):
    def test_all_enabled_failures_exit_1_and_a_partial_save_exits_0(self):
        names = ["tass-en.xml", "tass-ru.xml", "navtex-ru"]
        self.assertEqual(collect_exit_code(names, {name: "FAILURE" for name in names}), 1)
        self.assertEqual(
            collect_exit_code(names, {"tass-en.xml": "SUCCESS", "tass-ru.xml": "FAILURE", "navtex-ru": "FAILURE"}),
            0,
        )
        self.assertEqual(collect_exit_code([], {}), 0)


class ConnectivityWaitTest(unittest.TestCase):
    def test_returns_when_dns_and_one_request_succeed(self):
        notes = []
        calls = {"request": 0}

        def resolve(host):
            return host == "tass.com"

        def request(url):
            calls["request"] += 1
            return "tass.com" in url

        clock = {"t": 0.0}

        def monotonic():
            return clock["t"]

        ok = wait_for_connectivity(
            ["https://tass.com/rss/v2.xml", "https://tass.ru/rss/v2.xml"],
            lambda level, source, detail: notes.append((level, source, detail)),
            resolve=resolve,
            request=request,
            sleep=lambda _s: None,
            monotonic=monotonic,
            deadline_s=3600,
            poll_s=30,
        )
        self.assertTrue(ok)
        self.assertEqual(notes[-1][0], "OK")
        self.assertEqual(calls["request"], 1)

    def test_starts_the_fetch_after_60_minutes_without_connectivity(self):
        notes = []
        clock = {"t": 0.0}

        def monotonic():
            return clock["t"]

        def sleep(seconds):
            clock["t"] += seconds

        ok = wait_for_connectivity(
            ["https://tass.com/rss/v2.xml"],
            lambda level, source, detail: notes.append((level, source, detail)),
            resolve=lambda _host: False,
            request=lambda _url: False,
            sleep=sleep,
            monotonic=monotonic,
            deadline_s=3600,
            poll_s=30,
        )
        self.assertFalse(ok)
        self.assertIn("60 minutes", notes[-1][2])
        self.assertLessEqual(clock["t"], 3600 + 30)


if __name__ == "__main__":
    unittest.main()
