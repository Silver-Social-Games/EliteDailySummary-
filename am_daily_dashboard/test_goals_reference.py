"""Unit tests for the AM-supplied Goals reference diff.

The point of the reference file is to catch a drift automatically, so it has to be
trustworthy itself — a silently misaligned column would report a fake mismatch and
send the next investigation down the wrong path. Both faults these tests cover are
ones the first version actually shipped with: an off-by-one column read, and
"Monthly Purchasers" rendered as dollars because the unit was sniffed from the
label and "Purchasers" contains "Purchase".
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
if str(PACKAGE_DIR) not in sys.path:
    sys.path.insert(0, str(PACKAGE_DIR))

from goals_reference import (  # noqa: E402
    KPI_SPECS,
    gap_text,
    load_reference_tsv,
    reference_for,
)

HEADER = (
    "Agent Name\tmonth\tday\tyear\tDaily Avg Purchase\tDaily Avg Net Purchase\t"
    "Monthly Players w purchase\t#Reactivations\t#Players Upgraded to Elite\t"
    "% Active From Portfolio\tARPPU (avg purchase per paying player)"
)
ROW = "rachel_a\t8\t17\t2026\t48,537.00\t24,177.00\t433\t\t9\t85%\t1,900.00"


def _write(*lines: str) -> Path:
    path = Path(tempfile.mkdtemp()) / "ref.tsv"
    path.write_text("\n".join((HEADER, *lines)) + "\n", encoding="utf-8")
    return path


class LoadTests(unittest.TestCase):
    def test_missing_file_is_not_an_error(self) -> None:
        # The file is optional; a board run must not fail because nobody pasted.
        self.assertEqual(load_reference_tsv(Path("nope") / "absent.tsv"), [])

    def test_columns_land_on_the_right_kpi(self) -> None:
        rows = load_reference_tsv(_write(ROW))
        self.assertEqual(len(rows), 1)
        v = rows[0].values
        self.assertEqual(v["Daily Avg Purchase"], 48537.0)
        self.assertEqual(v["Daily Avg Net Purchase"], 24177.0)
        self.assertEqual(v["Monthly Purchasers"], 433.0)
        self.assertEqual(v["Upgrade to Elite"], 9.0)
        self.assertEqual(v["% Active from portfolio"], 85.0)
        self.assertEqual(v["ARPPU"], 1900.0)

    def test_blank_cell_does_not_diff(self) -> None:
        rows = load_reference_tsv(_write(ROW))
        self.assertNotIn("# Reactivation", rows[0].values)

    def test_unknown_agent_and_bad_date_are_skipped(self) -> None:
        rows = load_reference_tsv(
            _write(
                "someone_else\t8\t17\t2026\t1\t1\t1\t1\t1\t1%\t1",
                "rachel_a\t8\t\t2026\t1\t1\t1\t1\t1\t1%\t1",
                ROW,
            )
        )
        self.assertEqual([r.agent for r in rows], ["rachel_a"])
        self.assertEqual(rows[0].day, 17)


class LookupTests(unittest.TestCase):
    def test_matches_only_the_same_as_of_date(self) -> None:
        # A reference captured on the 16th says nothing about the 17th — every
        # average and count shifts with the elapsed-day divisor.
        rows = load_reference_tsv(_write(ROW))
        self.assertTrue(reference_for(rows, "rachel_a", "2026-08-17"))
        self.assertEqual(reference_for(rows, "rachel_a", "2026-08-16"), {})
        self.assertEqual(reference_for(rows, "coral_s", "2026-08-17"), {})

    def test_unparseable_as_of_returns_nothing(self) -> None:
        rows = load_reference_tsv(_write(ROW))
        self.assertEqual(reference_for(rows, "rachel_a", ""), {})


class GapTextTests(unittest.TestCase):
    def test_every_kpi_label_has_a_unit(self) -> None:
        for label, (column, unit) in KPI_SPECS.items():
            self.assertIn(unit, {"usd", "count", "pct"}, label)
            self.assertTrue(column, label)

    def test_counts_are_not_formatted_as_dollars(self) -> None:
        theirs, gap = gap_text("Monthly Purchasers", 433.0, 433.0)
        self.assertEqual(theirs, "433")
        self.assertEqual(gap, "match")

    def test_usd_is_formatted_as_dollars(self) -> None:
        theirs, _ = gap_text("Daily Avg Net Purchase", 24177.0, 24177.0)
        self.assertEqual(theirs, "$24,177")

    def test_percent_gap_is_in_points(self) -> None:
        theirs, gap = gap_text("% Active from portfolio", 83.0, 82.0)
        self.assertEqual(theirs, "82.0%")
        self.assertEqual(gap, "+1.0pp")

    def test_gap_shows_absolute_and_relative(self) -> None:
        _, gap = gap_text("Upgrade to Elite", 53.0, 8.0)
        self.assertEqual(gap, "+45 (+562.5%)")

    def test_no_reference_means_no_columns(self) -> None:
        self.assertEqual(gap_text("ARPPU", 1989.0, None), ("", ""))

    def test_unavailable_actual_still_shows_their_figure(self) -> None:
        theirs, gap = gap_text("ARPPU", None, 1900.0)
        self.assertEqual((theirs, gap), ("$1,900", ""))

    def test_zero_reference_does_not_divide_by_zero(self) -> None:
        _, gap = gap_text("Upgrade to Elite", 5.0, 0.0)
        self.assertEqual(gap, "+5")


if __name__ == "__main__":
    unittest.main()
