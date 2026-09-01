"""Tests for AM Brief date-range helper (no BigQuery)."""
from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

from generate_am_brief_range import (
    archived_dates,
    catch_up_bounds,
    iter_report_dates,
)


class GenerateAmBriefRangeTests(unittest.TestCase):
    def test_archived_dates_ignores_per_am_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "2026-08-17_elite_am_brief.json").write_text("{}", encoding="utf-8")
            (root / "2026-08-17_elite_am_brief_coral.json").write_text("{}", encoding="utf-8")
            (root / "2026-08-22_elite_am_brief.json").write_text("{}", encoding="utf-8")
            self.assertEqual(
                archived_dates(root),
                [date(2026, 8, 17), date(2026, 8, 22)],
            )

    def test_catch_up_from_day_after_newest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "2026-08-20_elite_am_brief.json").write_text("{}", encoding="utf-8")
            bounds = catch_up_bounds(export_dir=root, through=date(2026, 8, 22))
            self.assertEqual(bounds, (date(2026, 8, 21), date(2026, 8, 22)))

    def test_catch_up_none_when_current(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "2026-08-22_elite_am_brief.json").write_text("{}", encoding="utf-8")
            self.assertIsNone(
                catch_up_bounds(export_dir=root, through=date(2026, 8, 22))
            )

    def test_iter_skip_existing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "2026-08-21_elite_am_brief.json").write_text("{}", encoding="utf-8")
            dates = iter_report_dates(
                date(2026, 8, 21),
                date(2026, 8, 23),
                export_dir=root,
                skip_existing=True,
            )
            self.assertEqual(dates, [date(2026, 8, 22), date(2026, 8, 23)])


if __name__ == "__main__":
    unittest.main()
