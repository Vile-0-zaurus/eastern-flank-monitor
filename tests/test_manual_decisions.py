import unittest
from pathlib import Path

from pipeline.score.manual_decisions import applied_level, load_decisions

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "manual"
APPROVED = [
    MANUAL / "o1-ukraine-war-approved.csv",
    MANUAL / "o2-us-commitment-approved.csv",
    MANUAL / "c2-force-posture-approved.csv",
]


class DuplicateO2Test(unittest.TestCase):
    def test_january_o2_keeps_the_later_click(self):
        before = {path: path.read_bytes() for path in APPROVED}
        rows = load_decisions(APPROVED)
        january = [
            row
            for row in rows
            if row["input"] == "o2" and row["date"] == "2021-01-01"
        ]
        self.assertEqual(len(january), 1)
        self.assertEqual(january[0]["saved_at"], "2026-10-11T20:35:37")
        self.assertIsNone(applied_level(january[0]))
        self.assertEqual({path: path.read_bytes() for path in APPROVED}, before)

    def test_o1_uses_the_corrected_value_not_the_draft(self):
        rows = load_decisions(APPROVED)
        o1 = [row for row in rows if row["input"] == "o1"]
        self.assertEqual(len(o1), 1)
        self.assertEqual(o1[0]["value"], "1")
        self.assertEqual(applied_level(o1[0]), 3)

    def test_later_click_wins_when_the_values_differ(self):
        from pipeline.score.manual_decisions import collapse_latest

        kept = collapse_latest(
            [
                {
                    "input": "o2",
                    "date": "2021-01-01",
                    "region": "",
                    "value": "1",
                    "decision": "Approve",
                    "corrected_value": "",
                    "saved_at": "2026-10-11T20:00:07",
                },
                {
                    "input": "o2",
                    "date": "2021-01-01",
                    "region": "",
                    "value": "4",
                    "decision": "Approve",
                    "corrected_value": "",
                    "saved_at": "2026-10-11T20:35:37",
                },
            ]
        )
        self.assertEqual(len(kept), 1)
        self.assertEqual(applied_level(kept[0]), 4)


if __name__ == "__main__":
    unittest.main()
