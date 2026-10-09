import unittest

from pipeline.score.i1 import daily_counts, flank_terms, story_key, title_about_flank


STEMS = ["польш", "латви", "финлянд", "Poland", "Latvia"]
GROUPS = [r"риг(а|и|е|у|ой)"]


def hit(title, domain="tass.ru"):
    return title_about_flank(title, STEMS, GROUPS, domain, min_chars=15)


def hit_config(title, stems, groups, min_chars, domain="tass.ru"):
    return title_about_flank(title, stems, groups, domain, min_chars)


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

    def test_sea_only_baltic_does_not_count_and_the_country_phrase_does(self):
        from pathlib import Path

        from pipeline.score.region_filter import load_keywords

        path = Path(__file__).resolve().parents[1] / "config" / "region_keywords.yaml"
        stems, groups = flank_terms(path)
        _fips, _names, _stems, _groups, min_chars = load_keywords(path)
        low = {stem.lower() for stem in stems}
        self.assertNotIn("балтий", low)
        self.assertNotIn("балтик", low)
        self.assertNotIn("baltic", low)
        self.assertIn("прибалт", low)
        self.assertFalse(hit_config("Балтийское море закрыли для учений", stems, groups, min_chars))
        self.assertFalse(hit_config("The Baltic Sea stays open this week", stems, groups, min_chars))
        self.assertTrue(hit_config("Балтийские страны обсудили границу", stems, groups, min_chars))
        self.assertTrue(hit_config("В балтийских республиках сменилось правительство", stems, groups, min_chars))
        self.assertTrue(hit_config("Балтийским государствам направили ноту", stems, groups, min_chars))
        self.assertTrue(hit_config("Baltic states argue over the border", stems, groups, min_chars))
        self.assertTrue(hit_config("Прибалтика ждёт нового заявления", stems, groups, min_chars))


class RegionFileTest(unittest.TestCase):
    def test_ukraine_matches_the_country_and_not_poland(self):
        from pipeline.score.i1 import matchers

        by_name = {spec["name"]: spec for spec in matchers()}
        ukraine = by_name["ukraine_test"]
        flank = by_name["eastern_flank"]
        self.assertEqual(ukraine["indicator"], "I1_ukraine_test")
        self.assertEqual(flank["indicator"], "I1")
        self.assertTrue(
            title_about_flank(
                "Украина закрыла границу на неделю",
                ukraine["stems"],
                ukraine["groups"],
                "tass.ru",
                ukraine["min_chars"],
                ukraine["pattern"],
            )
        )
        self.assertTrue(
            title_about_flank(
                "Ukraine closed the border for a week",
                ukraine["stems"],
                ukraine["groups"],
                "tass.ru",
                ukraine["min_chars"],
                ukraine["pattern"],
            )
        )
        self.assertFalse(
            title_about_flank(
                "Польша закрыла границу на неделю",
                ukraine["stems"],
                ukraine["groups"],
                "tass.ru",
                ukraine["min_chars"],
                ukraine["pattern"],
            )
        )


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
