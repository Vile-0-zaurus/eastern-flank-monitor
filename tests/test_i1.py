import unittest

from pipeline.score.i1 import daily_counts, flank_terms, story_key, title_about_flank


STEMS = ["польш", "латви", "финлянд", "Poland", "Latvia"]
GROUPS = [r"риг(а|и|е|у|ой)"]


def hit(title, domain="tass.ru"):
    return title_about_flank(title, STEMS, GROUPS, domain, min_chars=15)


class TitleRuleTest(unittest.TestCase):
    def test_a_five_country_title_counts(self):
        self.assertTrue(hit("Польша закрыла границу на неделю"))

    def test_kaliningrad_alone_does_not_count(self):
        self.assertFalse(hit("Калининград открыл новый парк у моря"))

    def test_kaliningrad_plus_a_flank_country_counts(self):
        self.assertFalse(hit("Калининград открыл новый парк у моря"))
        self.assertTrue(hit("Калининград и Польша спорят о границе"))

    def test_a_short_junk_title_does_not_count(self):
        self.assertFalse(hit("Польша"))

    def test_config_drops_kaliningrad_but_keeps_the_five(self):
        from pathlib import Path

        stems, _groups = flank_terms(Path(__file__).resolve().parents[1] / "config" / "region_keywords.yaml")
        low = {stem.lower() for stem in stems}
        self.assertNotIn("калининград", low)
        self.assertNotIn("kaliningrad", low)
        self.assertIn("польш", low)
        self.assertIn("poland", low)


class DedupTest(unittest.TestCase):
    def test_same_url_counts_once_and_a_blank_copy_does_not_erase_it(self):
        rows = [
            ("20210201", "tass.ru", "https://tass.ru/a", "Польша закрыла границу на неделю"),
            ("20210201", "tass.ru", "https://tass.ru/a", ""),
            ("20210201", "ria.ru", "https://ria.ru/b", "Обычная новость без региона"),
        ]
        day = daily_counts(rows, STEMS, GROUPS, min_chars=15)["20210201"]
        self.assertEqual(day["numerator"], 1)
        self.assertEqual(day["denominator"], 2)
        self.assertAlmostEqual(day["value"], 0.5)

    def test_no_stories_is_no_data_not_zero(self):
        day = daily_counts([], STEMS, GROUPS, min_chars=15).get("20210201")
        self.assertIsNone(day)

    def test_missing_url_uses_domain_and_title(self):
        self.assertEqual(
            story_key("tass.ru", "", "Польша закрыла границу"),
            story_key("tass.ru", "  ", "Польша закрыла границу"),
        )
        self.assertNotEqual(
            story_key("tass.ru", "", "Польша закрыла границу"),
            story_key("ria.ru", "", "Польша закрыла границу"),
        )


if __name__ == "__main__":
    unittest.main()
