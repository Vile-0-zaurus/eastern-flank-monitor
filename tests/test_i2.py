import unittest

from pipeline.score.i2_sample import collapse_stories, draw_sample, hostile_yes, wilson_interval


def row(day, url, title, region="ukraine_test"):
    return {"day": day, "url": url, "title": title, "region": region}


class CollapseTest(unittest.TestCase):
    def test_same_url_on_two_days_is_one_story_on_the_earlier_day(self):
        stories = collapse_stories(
            [
                row("20210203", "https://tass.ru/a", "Украина закрыла границу на неделю"),
                row("20210201", "https://tass.ru/a", "Украина закрыла границу на неделю"),
            ]
        )
        self.assertEqual(len(stories), 1)
        self.assertEqual(stories[0]["day"], "20210201")
        self.assertEqual(stories[0]["week"], "2021-02-01")

    def test_near_identical_titles_with_different_urls_collapse(self):
        stories = collapse_stories(
            [
                row("20210302", "https://ria.ru/b", "Киев!"),
                row("20210301", "https://tass.ru/a", "киев"),
            ]
        )
        self.assertEqual(len(stories), 1)
        self.assertEqual(stories[0]["day"], "20210301")

    def test_different_titles_stay_separate(self):
        stories = collapse_stories(
            [
                row("20210301", "https://tass.ru/a", "Киев заявил о границе"),
                row("20210301", "https://tass.ru/b", "Донбасс открыл пункт"),
            ]
        )
        self.assertEqual(len(stories), 2)


class SampleTest(unittest.TestCase):
    def test_seed_is_stable_and_a_short_week_keeps_all(self):
        stories = collapse_stories(
            [row(f"202101{day:02d}", f"https://tass.ru/{i}", f"Украина номер {i}") for i, day in enumerate(range(1, 8), start=1)]
            + [row("20210104", f"https://tass.ru/x{i}", f"Киев номер {i}") for i in range(20)]
        )
        first = draw_sample(stories, seed=20261009, per_week=5)
        second = draw_sample(stories, seed=20261009, per_week=5)
        self.assertEqual(first, second)
        self.assertLess(len(first), len(stories))


class IntervalTest(unittest.TestCase):
    def test_no_classified_rows_is_no_data(self):
        self.assertIsNone(wilson_interval(0, 0))

    def test_interval_contains_the_share(self):
        share, low, high = wilson_interval(20, 100)
        self.assertAlmostEqual(share, 0.2)
        self.assertLessEqual(low, share)
        self.assertGreaterEqual(high, share)

    def test_missing_answer_is_not_hostile(self):
        self.assertIsNone(hostile_yes(None))
        self.assertIsNone(hostile_yes({"status": "AI unavailable"}))
        self.assertTrue(hostile_yes({"hostile_framing": "yes"}))
        self.assertFalse(hostile_yes({"hostile_framing": "no"}))


class KeywordTest(unittest.TestCase):
    def test_kyiv_donbas_and_the_republics_count_for_ukraine_only(self):
        from pipeline.score.i1 import matchers
        from pipeline.score.i1 import title_about_flank

        by_name = {spec["name"]: spec for spec in matchers()}
        ukraine = by_name["ukraine_test"]
        flank = by_name["eastern_flank"]

        def hit(spec, title):
            return title_about_flank(
                title, spec["stems"], spec["groups"], "tass.ru", spec["min_chars"], spec["pattern"]
            )

        self.assertTrue(hit(ukraine, "Киев заявил о закрытии границы"))
        self.assertTrue(hit(ukraine, "Kyiv closed the road for a week"))
        self.assertTrue(hit(ukraine, "Donbas talks stalled again today"))
        self.assertTrue(hit(ukraine, "ДНР сообщила о новом обстреле"))
        self.assertTrue(hit(ukraine, "ЛНР открыла пункт пропуска"))
        self.assertFalse(hit(flank, "Киев заявил о закрытии границы"))
        self.assertFalse(hit(ukraine, "Польша закрыла границу на неделю"))


if __name__ == "__main__":
    unittest.main()
