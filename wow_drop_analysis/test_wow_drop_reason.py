"""Unit tests for same-weekday drop classification and urgency rules.

Covers the "first match wins" ladder documented at the top of
``wow_drop_reason.py`` and the workspace rule that self-excluded and locked
accounts must never receive retention outreach.
"""

from __future__ import annotations

import unittest
from datetime import date

from wow_drop_analysis.ticket_draft import _ticket_outreach_disabled
from wow_drop_analysis.wow_drop_reason import (
    URGENCY_BY_CODE,
    build_action_step,
    classify_day_drop,
    sort_top10_rows,
)

REPORT_DATE = date(2026, 7, 7)  # Tuesday


class ClassifyDayDropTests(unittest.TestCase):
    def test_self_exclusion_wins_over_everything_else(self) -> None:
        enrich = {
            "account_locked": True,
            "lock_reason": "Exclusion",
            "red_flag": True,
            "pending_redeem": 500,
        }
        code, _detail, _action = classify_day_drop(
            0, 200, 0, enrich, weekday_name="Tuesday", report_date=REPORT_DATE
        )
        self.assertEqual(code, "self_exclusion")

    def test_locked_non_exclusion_is_account_locked(self) -> None:
        enrich = {"account_locked": True, "lock_reason": "Fraud"}
        code, _detail, _action = classify_day_drop(
            0, 200, 0, enrich, weekday_name="Tuesday", report_date=REPORT_DATE
        )
        self.assertEqual(code, "account_locked")

    def test_pending_redeem_before_payment_failed(self) -> None:
        enrich = {"pending_redeem": 500, "failed_orders": 3}
        code, _detail, _action = classify_day_drop(
            0, 200, 100, enrich, weekday_name="Tuesday", report_date=REPORT_DATE
        )
        self.assertEqual(code, "redemption_in_progress")

    def test_payment_failed_requires_zero_report_day(self) -> None:
        enrich = {"failed_orders": 2}
        code, _detail, _action = classify_day_drop(
            0, 200, 50, enrich, weekday_name="Tuesday", report_date=REPORT_DATE
        )
        self.assertEqual(code, "payment_failed")

    def test_big_win_day_before(self) -> None:
        enrich = {"day_before_ngr": -6000}
        code, _detail, _action = classify_day_drop(
            50, 200, 100, enrich, weekday_name="Tuesday", report_date=REPORT_DATE
        )
        self.assertEqual(code, "big_win_day_before")

    def test_churn_lapsed_when_no_purchase_in_7d(self) -> None:
        enrich = {}
        code, _detail, _action = classify_day_drop(
            0, 200, 0, enrich, weekday_name="Tuesday", report_date=REPORT_DATE
        )
        self.assertEqual(code, "churn_lapsed")

    def test_same_weekday_skip_when_still_active_this_week(self) -> None:
        enrich = {"rest_of_week": 75}
        code, _detail, _action = classify_day_drop(
            0, 200, 75, enrich, weekday_name="Tuesday", report_date=REPORT_DATE
        )
        self.assertEqual(code, "same_weekday_skip")

    def test_red_flag_when_nothing_more_specific_applies(self) -> None:
        enrich = {"red_flag": True}
        code, _detail, _action = classify_day_drop(
            50, 200, 150, enrich, weekday_name="Tuesday", report_date=REPORT_DATE
        )
        self.assertEqual(code, "red_flag")

    def test_general_spend_softening_default(self) -> None:
        enrich = {}
        code, _detail, _action = classify_day_drop(
            50, 200, 150, enrich, weekday_name="Tuesday", report_date=REPORT_DATE
        )
        self.assertEqual(code, "general_spend_softening")


class UrgencyMappingTests(unittest.TestCase):
    def test_every_classify_code_has_an_urgency(self) -> None:
        codes = [
            "self_exclusion",
            "account_locked",
            "redemption_in_progress",
            "payment_failed",
            "big_win_day_before",
            "churn_lapsed",
            "same_weekday_skip",
            "red_flag",
            "general_spend_softening",
        ]
        for code in codes:
            self.assertIn(code, URGENCY_BY_CODE, msg=f"missing urgency for {code}")

    def test_self_exclusion_urgency_is_none(self) -> None:
        self.assertEqual(URGENCY_BY_CODE["self_exclusion"], "None")

    def test_locked_and_redeem_and_payment_and_red_flag_are_today(self) -> None:
        for code in (
            "account_locked",
            "redemption_in_progress",
            "payment_failed",
            "red_flag",
        ):
            self.assertEqual(URGENCY_BY_CODE[code], "Today")


class NoOutreachRuleTests(unittest.TestCase):
    """Never recommend retention outreach for self-excluded or locked accounts."""

    def test_self_exclusion_action_step_is_no_outreach(self) -> None:
        action_step = build_action_step("self_exclusion", enrich={}, report_date=REPORT_DATE)
        self.assertEqual(action_step, "No outreach")

    def test_ticket_disabled_for_self_exclusion(self) -> None:
        self.assertTrue(_ticket_outreach_disabled("self_exclusion", "No outreach"))

    def test_ticket_disabled_for_locked_and_payment_and_red_flag(self) -> None:
        for code in ("account_locked", "payment_failed", "red_flag"):
            self.assertTrue(_ticket_outreach_disabled(code, "anything"))

    def test_ticket_enabled_for_churn_lapsed(self) -> None:
        self.assertFalse(_ticket_outreach_disabled("churn_lapsed", "Push purchase"))


class SortTop10RowsTests(unittest.TestCase):
    def test_today_sorts_before_48h_before_watch_before_none(self) -> None:
        rows = [
            {"AID": 1, "urgency": "Watch", "delta": 10},
            {"AID": 2, "urgency": "None", "delta": 999},
            {"AID": 3, "urgency": "Today", "delta": 1},
            {"AID": 4, "urgency": "48h", "delta": 5},
        ]
        ordered = [r["AID"] for r in sort_top10_rows(rows)]
        self.assertEqual(ordered, [3, 4, 1, 2])

    def test_within_same_urgency_sorts_by_delta_descending(self) -> None:
        rows = [
            {"AID": 1, "urgency": "Today", "delta": 10},
            {"AID": 2, "urgency": "Today", "delta": 50},
            {"AID": 3, "urgency": "Today", "delta": 25},
        ]
        ordered = [r["AID"] for r in sort_top10_rows(rows)]
        self.assertEqual(ordered, [2, 3, 1])


if __name__ == "__main__":
    unittest.main()
