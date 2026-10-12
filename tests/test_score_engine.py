import unittest
from datetime import date

from pipeline.score.engine import (
    counts_for_week,
    layer_level,
    level_from_z,
    manual_level_for_week,
    overall_level,
    rolling_baseline,
    rolling_baseline_mad,
    rows_for_week,
    indicator_level,
    visible_incidents,
    load_model,
)


WEEK = date(2022, 2, 7)  # Monday. Week ends Sunday 2022-02-13.


def row(source_date, value="4", on="2022-02-07"):
    return {
        "date": on,
        "value": value,
        "source_link": "https://example.test/source",
        "source_date": source_date,
    }


class NoHindsightTest(unittest.TestCase):
    def test_later_source_date_is_ignored_for_that_week(self):
        late = row("2022-02-14")
        self.assertFalse(counts_for_week(late, WEEK))
        self.assertEqual(rows_for_week([late], WEEK), [])

    def test_source_dated_on_the_last_day_counts(self):
        on_time = row("2022-02-13")
        self.assertTrue(counts_for_week(on_time, WEEK))
        self.assertEqual(rows_for_week([on_time], WEEK), [on_time])

    def test_week_score_ignores_a_source_published_later(self):
        rows = [
            row("2022-02-10", value="1"),
            row("2022-02-20", value="4"),
        ]
        self.assertEqual(manual_level_for_week(rows, WEEK), 1)

    def test_a_row_about_another_week_is_not_used(self):
        other = row("2022-02-10", value="4", on="2022-02-14")
        self.assertIsNone(manual_level_for_week([other], WEEK))


class NoDataTest(unittest.TestCase):
    def test_missing_indicator_is_not_treated_as_zero(self):
        level = layer_level({"I1": None, "I2": 4}, {"I1": 1, "I2": 1})
        self.assertEqual(level, 4)

    def test_short_history_is_no_data_not_a_zero_baseline(self):
        points = [(date(2022, 1, 1), 10.0)]
        result = rolling_baseline(points, date(2022, 1, 2), window_days=180, min_points=30)
        self.assertIsNone(result)

    def test_baseline_uses_the_trailing_window_and_not_today(self):
        points = [
            (date(2022, 1, 1), 1.0),
            (date(2022, 1, 2), 2.0),
            (date(2022, 1, 3), 3.0),
            (date(2022, 1, 4), 100.0),
        ]
        mean, std = rolling_baseline(points, date(2022, 1, 4), window_days=180, min_points=3)
        self.assertEqual(mean, 2.0)
        self.assertEqual(std, 1.0)


class ConvergenceTest(unittest.TestCase):
    def test_one_layer_rise_stays_at_or_below_watchful(self):
        result = overall_level(
            {"intent": 4, "capability": 0, "opportunity": 0, "hybrid": 0},
            confirmed=True,
            elevated_level=2,
            strong_level=3,
        )
        self.assertLessEqual(result.shown, 1)
        self.assertLessEqual(result.proposed, 1)

    def test_hybrid_alone_stays_at_or_below_watchful(self):
        result = overall_level(
            {"intent": 0, "capability": 0, "opportunity": 0, "hybrid": 4},
            confirmed=True,
            elevated_level=2,
            strong_level=3,
        )
        self.assertLessEqual(result.shown, 1)

    def test_opportunity_alone_stays_at_or_below_watchful(self):
        result = overall_level(
            {"intent": 0, "capability": 0, "opportunity": 4, "hybrid": 0},
            confirmed=True,
            elevated_level=2,
            strong_level=3,
        )
        self.assertLessEqual(result.shown, 1)

    def test_two_elevated_layers_can_reach_elevated(self):
        result = overall_level(
            {"intent": 2, "capability": 2, "opportunity": 0, "hybrid": 0},
            confirmed=False,
            elevated_level=2,
            strong_level=3,
        )
        self.assertEqual(result.proposed, 2)
        self.assertEqual(result.shown, 2)

    def test_serious_is_not_shown_without_confirmation(self):
        result = overall_level(
            {"intent": 2, "capability": 2, "opportunity": 2, "hybrid": 0},
            confirmed=False,
            elevated_level=2,
            strong_level=3,
        )
        self.assertEqual(result.proposed, 3)
        self.assertEqual(result.shown, 2)

    def test_unconfirmed_serious_is_not_shown_as_plain_elevated(self):
        result = overall_level(
            {"intent": 2, "capability": 2, "opportunity": 2, "hybrid": 0},
            confirmed=False,
            elevated_level=2,
            strong_level=3,
        )
        self.assertEqual(
            result.shown_label,
            "Elevated (Serious proposed, awaiting confirmation)",
        )
        self.assertNotEqual(result.shown_label, "Elevated")

    def test_unconfirmed_critical_is_not_shown_as_plain_elevated(self):
        result = overall_level(
            {"intent": 4, "capability": 4, "opportunity": 0, "hybrid": 2},
            confirmed=False,
            elevated_level=2,
            strong_level=3,
        )
        self.assertEqual(
            result.shown_label,
            "Elevated (Critical proposed, awaiting confirmation)",
        )
        self.assertNotEqual(result.shown_label, "Elevated")

    def test_confirmed_serious_can_be_shown(self):
        result = overall_level(
            {"intent": 2, "capability": 2, "opportunity": 2, "hybrid": 0},
            confirmed=True,
            elevated_level=2,
            strong_level=3,
        )
        self.assertEqual(result.shown, 3)

    def test_critical_needs_a_third_layer_and_confirmation(self):
        unconfirmed = overall_level(
            {"intent": 4, "capability": 4, "opportunity": 0, "hybrid": 2},
            confirmed=False,
            elevated_level=2,
            strong_level=3,
        )
        confirmed = overall_level(
            {"intent": 4, "capability": 4, "opportunity": 0, "hybrid": 2},
            confirmed=True,
            elevated_level=2,
            strong_level=3,
        )
        self.assertEqual(unconfirmed.proposed, 4)
        self.assertEqual(unconfirmed.shown, 2)
        self.assertEqual(confirmed.shown, 4)

    def test_missing_layers_are_not_a_calm_zero(self):
        result = overall_level(
            {"intent": None, "capability": None, "opportunity": None, "hybrid": None},
            confirmed=True,
            elevated_level=2,
            strong_level=3,
        )
        self.assertIsNone(result.shown)
        self.assertIsNone(result.proposed)


class ThresholdTest(unittest.TestCase):
    def test_z_score_uses_config_thresholds_and_missing_z_is_no_data(self):
        thresholds = {1: 0.5, 2: 1.5, 3: 2.5, 4: 3.5}
        self.assertEqual(level_from_z(0.0, thresholds), 0)
        self.assertEqual(level_from_z(1.5, thresholds), 2)
        self.assertIsNone(level_from_z(None, thresholds))

    def test_indicator_with_no_baseline_is_no_data_not_zero(self):
        level = indicator_level(
            10.0,
            [(date(2022, 1, 1), 1.0)],
            date(2022, 1, 2),
            window_days=180,
            min_points=30,
            thresholds={1: 0.5},
        )
        self.assertIsNone(level)


class IncidentTest(unittest.TestCase):
    def test_later_source_and_later_week_are_ignored(self):
        in_week = row("2022-02-08", value="cable", on="2022-02-09")
        late_source = row("2022-02-16", value="drone", on="2022-02-09")
        next_week = row("2022-02-08", value="airspace", on="2022-02-14")
        self.assertEqual(visible_incidents([in_week, late_source, next_week], WEEK), [in_week])


class ConfigTest(unittest.TestCase):
    def test_weights_and_thresholds_come_from_model_yaml(self):
        from pathlib import Path

        config = load_model(Path(__file__).resolve().parents[1] / "config" / "model.yaml")
        weights = config["weights"]["intent"]
        level = layer_level({"I1": 0, "I2": 4, "I3": None}, weights)
        equal = layer_level({"I1": 0, "I2": 4, "I3": None}, {"I1": 1, "I2": 1, "I3": 1})
        self.assertGreater(weights["I2"], weights["I1"])
        self.assertNotEqual(level, equal)
        result = overall_level(
            {"intent": 4, "capability": 0, "opportunity": 0, "hybrid": 0},
            confirmed=True,
            elevated_level=config["elevated_level"],
            strong_level=config["strong_level"],
        )
        self.assertLessEqual(result.shown, 1)

    def test_draft_cutoffs_match_the_preregistration(self):
        from pathlib import Path

        config = load_model(Path(__file__).resolve().parents[1] / "config" / "model.yaml")
        self.assertEqual(config["z_levels"][1], 1.0)
        self.assertEqual(config["z_levels"][2], 1.5)
        self.assertEqual(config["z_levels"][3], 2.0)
        self.assertEqual(config["z_levels"][4], 3.0)
        self.assertEqual(config["baseline_method"], "median_mad")
        self.assertEqual(config["mad_scale"], 1.4826)

    def test_a_spike_moves_the_mean_and_not_the_median(self):
        from datetime import timedelta

        points = [(date(2022, 1, 1) + timedelta(days=i), 1.0) for i in range(29)]
        points.append((date(2022, 1, 20), 100.0))
        as_of = date(2022, 2, 1)
        mean, _std = rolling_baseline(points, as_of, window_days=180, min_points=10)
        center, scale = rolling_baseline_mad(points, as_of, 180, 10, 1.4826)
        self.assertGreater(mean, center)
        self.assertEqual(center, 1.0)
        self.assertEqual(scale, 0.0)
        level = indicator_level(
            1.0,
            points,
            as_of,
            window_days=180,
            min_points=10,
            thresholds={1: 1.0, 2: 1.5, 3: 2.0, 4: 3.0},
        )
        self.assertEqual(level, 0)
        off = indicator_level(
            4.0,
            points,
            as_of,
            window_days=180,
            min_points=10,
            thresholds={1: 1.0},
        )
        self.assertIsNone(off)

    def test_live_rule_keeps_one_point_five(self):
        from pathlib import Path

        from pipeline.score.engine import live_layer_level, load_model

        config = load_model(Path(__file__).resolve().parents[1] / "config" / "model.yaml")
        self.assertEqual(config["live_round_layer_average"], 0)
        level = live_layer_level({"O1": 3, "O2": 0}, {"O1": 1, "O2": 1}, round_average=False)
        self.assertEqual(level, 1.5)


if __name__ == "__main__":
    unittest.main()
