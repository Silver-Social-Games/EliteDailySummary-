"""Unit tests for am_daily_dashboard/bonus_calculator.py (Inbound V5 NGR)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent
for _p in (PROJECT_ROOT, PACKAGE_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from bonus_calculator import (  # noqa: E402
    BonusCalcInput,
    apply_gwg,
    bonus_status_for_ratio,
    compute_free_bonus,
)


class TestBonusStatus(unittest.TestCase):
    def test_low_ratio_is_no_low_bonus_user(self) -> None:
        label, mult = bonus_status_for_ratio(0.02)
        self.assertEqual(label, "No/Low Bonus user")
        self.assertAlmostEqual(mult, 1.0)

    def test_high_ratio_is_abuser(self) -> None:
        label, mult = bonus_status_for_ratio(0.50)
        self.assertEqual(label, "Abuser")
        self.assertAlmostEqual(mult, 0.1)


class TestApplyGwg(unittest.TestCase):
    def test_none_pct_returns_base_only(self) -> None:
        gwg, total = apply_gwg(100.0, 0.0)
        self.assertEqual(gwg, 0.0)
        self.assertEqual(total, 100.0)

    def test_three_five_ten_percent(self) -> None:
        self.assertEqual(apply_gwg(100.0, 0.03), (3.0, 103.0))
        self.assertEqual(apply_gwg(100.0, 0.05), (5.0, 105.0))
        self.assertEqual(apply_gwg(100.0, 0.10), (10.0, 110.0))


class TestComputeFreeBonus(unittest.TestCase):
    def _inp(self, **kwargs) -> BonusCalcInput:
        base = dict(
            active=True,
            ggr=500.0,
            bonus=50.0,
            purchase_count=5,
            purchase_amount=200.0,
            bonus_pct_window=0.05,
            bonus_pct_lifetime=0.04,
            locked=False,
            lock_label="",
        )
        base.update(kwargs)
        return BonusCalcInput(**base)

    def test_locked_player_blocked(self) -> None:
        out = compute_free_bonus(self._inp(locked=True, lock_label="Self-exclusion"))
        self.assertTrue(out.blocked)
        self.assertEqual(out.path, "blocked")
        self.assertEqual(out.offer_label, "No Free Bonus Allowed")
        self.assertIn("Self-exclusion", out.blocked_reason)

    def test_active_positive_ngr_returns_sc_bonus(self) -> None:
        out = compute_free_bonus(self._inp())
        self.assertFalse(out.blocked)
        self.assertEqual(out.path, "positive_ngr")
        self.assertIsNotNone(out.free_bonus)
        self.assertIn("SC", out.offer_label)
        self.assertGreater(out.free_bonus or 0, 0)
        self.assertGreater(out.lookup_amount, 0)

    def test_active_non_positive_ngr_not_eligible(self) -> None:
        out = compute_free_bonus(self._inp(ggr=40.0, bonus=50.0))
        self.assertFalse(out.blocked)
        self.assertEqual(out.path, "not_eligible")
        self.assertIsNone(out.free_bonus)
        self.assertEqual(out.offer_label, "Not eligible")
        self.assertNotIn("FS", out.offer_label)

    def test_inactive_positive_ngr_reactivation_path(self) -> None:
        out = compute_free_bonus(self._inp(active=False, ggr=800.0, bonus=100.0))
        self.assertFalse(out.blocked)
        self.assertEqual(out.path, "inactive")
        self.assertIn("SC", out.offer_label)
        self.assertIn("Inactive", out.segment_label)

    def test_non_positive_ngr_inactive_no_bonus(self) -> None:
        out = compute_free_bonus(self._inp(active=False, ggr=10.0, bonus=20.0))
        self.assertEqual(out.path, "none")
        self.assertEqual(out.offer_label, "No Free Bonus Allowed")


if __name__ == "__main__":
    unittest.main()
