"""Unit tests for reward decision rules."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from reward_check.decision import (
    verify_free_spins,
    verify_purchase_credit,
    verify_tournament_prize,
)


class FreeSpinDecisionTests(unittest.TestCase):
    def test_received_used(self) -> None:
        result = verify_free_spins(
            [],
            [
                {
                    "campaign_code": "20260710_onlp_tigerjackpots_20",
                    "total_spins": 20,
                    "left_spins": 0,
                    "used": datetime(2026, 7, 11, tzinfo=timezone.utc),
                    "status": "finished",
                }
            ],
            expected_fs=20,
            campaign_code="20260710_onlp_tigerjackpots_20",
        )
        self.assertEqual(result.status, "received_used")

    def test_received_unused_even_without_reward_facts(self) -> None:
        result = verify_free_spins(
            [],
            [
                {
                    "campaign_code": "20260710_onlp_tigerjackpots_20",
                    "total_spins": 20,
                    "left_spins": 20,
                    "used": None,
                    "expired": datetime(2026, 7, 30, tzinfo=timezone.utc),
                    "status": "created",
                }
            ],
            expected_fs=20,
            campaign_code="20260710_onlp_tigerjackpots_20",
        )
        self.assertEqual(result.status, "received_unused")

    def test_missing_after_successful_purchase(self) -> None:
        result = verify_free_spins(
            [{"status": "succeeded", "refunded": False, "order_id": 9245679}],
            [],
            expected_fs=125,
            offer_code="conv_20kg_10s_9_99",
        )
        self.assertEqual(result.status, "missing")


class PurchaseDecisionTests(unittest.TestCase):
    def test_purchase_credit_received(self) -> None:
        result = verify_purchase_credit(
            [
                {
                    "status": "succeeded",
                    "refunded": False,
                    "order_id": 9245679,
                    "sc_amount": 10,
                    "gc_amount": 20000,
                }
            ],
            expected_sc=10,
            expected_gc=20000,
        )
        self.assertEqual(result.status, "received")

    def test_purchase_amount_mismatch(self) -> None:
        result = verify_purchase_credit(
            [
                {
                    "status": "succeeded",
                    "refunded": False,
                    "order_id": 1,
                    "sc_amount": 10,
                    "gc_amount": 20000,
                }
            ],
            expected_sc=15,
            expected_gc=None,
        )
        self.assertEqual(result.status, "amount_mismatch")


class TournamentDecisionTests(unittest.TestCase):
    def test_tournament_payout_received(self) -> None:
        result = verify_tournament_prize(
            [
                {
                    "accepted": True,
                    "bonus_reward_id": 36753896,
                    "sc_amount": 15,
                    "gc_amount": 0,
                }
            ],
            expected_sc=15,
            expected_gc=None,
        )
        self.assertEqual(result.status, "received")

    def test_tournament_not_paid(self) -> None:
        result = verify_tournament_prize(
            [],
            expected_sc=15,
            expected_gc=None,
        )
        self.assertEqual(result.status, "not_paid")


if __name__ == "__main__":
    unittest.main()
