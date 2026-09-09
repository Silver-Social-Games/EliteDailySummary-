"""Unit tests for lock/TAB management Slack alerts."""

from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

PACKAGE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PACKAGE_DIR.parent))
sys.path.insert(0, str(PACKAGE_DIR))

import post_lock_tab_slack as alerts  # noqa: E402
from config import (  # noqa: E402
    LOCK_TAB_ALERT_MIN_30D_PURCHASE,
    LOCK_TAB_ALERT_MIN_HOLD_PCT,
)
from payload_builders import lock_bucket  # noqa: E402

REPORT_DATE = date(2026, 9, 8)


def _row(
    *,
    aid: int = 123456789,
    lock_reason: str = "take a break 21",
    lock_reason_comment: str = "",
    purchased_30d: float = 12_000,
    hold_pct: float = 0.62,
    locked_at: date | None = None,
) -> dict:
    return {
        "AID": aid,
        "name": "Jane Doe",
        "agent": "coral_s",
        "lock_reason": lock_reason,
        "lock_reason_comment": lock_reason_comment,
        "locked_at": locked_at or REPORT_DATE,
        "lifetime_purchased": 85_000,
        "lifetime_net_purchase": 52_700,
        "purchased_30d": purchased_30d,
        "hold_pct": hold_pct,
    }


class LockBucketFilterTests(unittest.TestCase):
    def test_take_a_break_included(self) -> None:
        bucket, _ = lock_bucket("take a break 21", "")
        self.assertEqual(bucket, "Take a break")
        out = alerts.filter_alert_rows([_row()])
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["bucket"], "Take a break")

    def test_other_locked_included(self) -> None:
        out = alerts.filter_alert_rows([_row(lock_reason="Account closure")])
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["bucket"], "Other locked")

    def test_self_exclusion_excluded(self) -> None:
        out = alerts.filter_alert_rows([_row(lock_reason="Exclusion")])
        self.assertEqual(out, [])


class ThresholdTests(unittest.TestCase):
    def test_meets_thresholds(self) -> None:
        self.assertGreaterEqual(12_000, LOCK_TAB_ALERT_MIN_30D_PURCHASE)
        self.assertGreaterEqual(0.62, LOCK_TAB_ALERT_MIN_HOLD_PCT)

    def test_message_includes_metrics(self) -> None:
        row = alerts.filter_alert_rows([_row()])[0]
        text = alerts.format_alert_message(row)
        self.assertIn("• AID: 123456789", text)
        self.assertIn("<https://lookerpatrianna.cloud.looker.com/dashboards/5207?Account+ID+=123456789|Jane Doe>", text)
        self.assertIn("• AM: Coral", text)
        self.assertIn("*Elite Lock Alert*", text)
        self.assertIn("• Lock Date:", text)
        self.assertIn("• 30D Purchase:", text)
        self.assertNotIn("|Looker>", text)

    def test_duplicate_reason_collapsed(self) -> None:
        row = alerts.filter_alert_rows([
            _row(lock_reason="Customer request", lock_reason_comment="Customer request")
        ])[0]
        text = alerts.format_alert_message(row)
        self.assertIn("• Reason: Customer request", text)
        self.assertNotIn("Customer request — Customer request", text)


class DedupeTests(unittest.TestCase):
    def test_same_lock_not_sent_twice(self) -> None:
        row = _row()
        key = alerts.dedupe_key(row)
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "sent.json"
            with patch.object(alerts, "SENT_STATE", state):
                alerts.save_sent_keys({key})
                loaded = alerts.load_sent_keys()
                self.assertIn(key, loaded)
                pending = [row] if key not in loaded else []
                self.assertEqual(pending, [])


class SendDayTests(unittest.TestCase):
    def test_sunday_through_thursday(self) -> None:
        self.assertTrue(alerts.is_elite_send_day(date(2026, 9, 13)))  # Sun
        self.assertTrue(alerts.is_elite_send_day(date(2026, 9, 7)))   # Mon
        self.assertTrue(alerts.is_elite_send_day(date(2026, 9, 10)))  # Thu

    def test_friday_saturday_skipped(self) -> None:
        self.assertFalse(alerts.is_elite_send_day(date(2026, 9, 11)))  # Fri
        self.assertFalse(alerts.is_elite_send_day(date(2026, 9, 12)))  # Sat

    def test_run_skips_fri_without_force(self) -> None:
        with patch.object(alerts, "is_elite_send_day", return_value=False):
            code = alerts.run(send=False, report_date=REPORT_DATE)
        self.assertEqual(code, 0)


class RunIntegrationTests(unittest.TestCase):
    def test_dry_run_does_not_write_state(self) -> None:
        row = _row()
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "sent.json"
            with patch.object(alerts, "SENT_STATE", state):
                with patch.object(alerts, "fetch_candidates", return_value=[{**row, "bucket": "Take a break"}]):
                    with patch.object(alerts, "is_elite_send_day", return_value=True):
                        code = alerts.run(send=False, report_date=REPORT_DATE, force=True)
            self.assertEqual(code, 0)
            self.assertFalse(state.exists())


if __name__ == "__main__":
    unittest.main()
