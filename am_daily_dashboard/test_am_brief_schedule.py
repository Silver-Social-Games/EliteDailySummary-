"""Tests for AM Brief Sun-Thu send calendar."""
from __future__ import annotations

import unittest
from datetime import date

from am_brief_schedule import is_send_day, report_date_for_send_day


class AmBriefScheduleTests(unittest.TestCase):
    def test_sunday_is_send_day(self) -> None:
        self.assertTrue(is_send_day(date(2026, 8, 23)))  # Sunday

    def test_thursday_is_send_day(self) -> None:
        self.assertTrue(is_send_day(date(2026, 8, 27)))  # Thursday

    def test_friday_skipped(self) -> None:
        self.assertFalse(is_send_day(date(2026, 8, 28)))

    def test_saturday_skipped(self) -> None:
        self.assertFalse(is_send_day(date(2026, 8, 29)))

    def test_report_date_is_yesterday(self) -> None:
        self.assertEqual(report_date_for_send_day(date(2026, 8, 24)), date(2026, 8, 23))


if __name__ == "__main__":
    unittest.main()
