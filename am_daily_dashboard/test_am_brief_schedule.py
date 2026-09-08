"""Tests for AM Brief daily send calendar."""
from __future__ import annotations

import unittest
from datetime import date

from am_brief_schedule import is_send_day, report_date_for_send_day


class AmBriefScheduleTests(unittest.TestCase):
    def test_every_weekday_is_send_day(self) -> None:
        for d in (
            date(2026, 8, 23),  # Sun
            date(2026, 8, 27),  # Thu
            date(2026, 8, 28),  # Fri
            date(2026, 8, 29),  # Sat
        ):
            with self.subTest(d=d):
                self.assertTrue(is_send_day(d))

    def test_report_date_is_yesterday(self) -> None:
        self.assertEqual(report_date_for_send_day(date(2026, 8, 24)), date(2026, 8, 23))


if __name__ == "__main__":
    unittest.main()
