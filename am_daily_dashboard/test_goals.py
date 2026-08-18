"""Unit tests for AM Brief Goals loader, run-rate, weighted score, isolation."""

from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
if str(PACKAGE_DIR) not in sys.path:
    sys.path.insert(0, str(PACKAGE_DIR))

from goals import (  # noqa: E402
    INCLUDED_WEIGHT_TOTAL,
    GoalsTarget,
    _status_for,
    achievement_ratio,
    build_agent_goals_block,
    clean_shape,
    load_goals_tsv,
    month_bounds,
    parse_number,
    run_rate_pace,
    shape_pace,
    strip_payload_for_am,
    targets_for_month,
)


SAMPLE_TSV = """Agent Name\tmonth\tQ\tyear\tDaily Avg Purchase\tDaily Avg Net Purchase\tMonthly Players w purchase\t#Reactivations\t#Players Upgraded to Elite\t% Active From Portfolio\tARPPU (avg purchase per paying player)
coral_s\t8\t3\t2026\t51,000.00\t30,000.00\t546.00\t53.00\t49.00\t96%\t2900
coral_s\t4\t2\t2026\t32,000.00\t18,000.00\t306.00\t67.00\t67.00\t85%\t
lee_t\t8\t3\t2026\t51,000.00\t30,000.00\t546.00\t53.00\t49.00\t96%\t2900
alon_tish\t8\t3\t2026\t1.00\t1.00\t1\t1\t1\t1%\t1
"""


class ParseNumberTests(unittest.TestCase):
    def test_commas_and_percent(self) -> None:
        self.assertEqual(parse_number("51,000.00"), 51000.0)
        self.assertEqual(parse_number("96%"), 96.0)

    def test_blank_arppu(self) -> None:
        self.assertIsNone(parse_number(""))
        self.assertIsNone(parse_number(None))
        self.assertIsNone(parse_number("   "))


class LoadGoalsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".tsv", delete=False, encoding="utf-8"
        )
        self.tmp.write(SAMPLE_TSV)
        self.tmp.close()
        self.path = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.path.unlink(missing_ok=True)

    def test_skips_alon_and_selects_month(self) -> None:
        rows = load_goals_tsv(self.path)
        agents = {r.agent for r in rows}
        self.assertNotIn("alon_tish", agents)
        aug = targets_for_month(date(2026, 8, 16), self.path)
        self.assertIn("coral_s", aug)
        self.assertEqual(aug["coral_s"].daily_avg_purchase, 51000.0)
        self.assertEqual(aug["coral_s"].arppu, 2900.0)
        self.assertEqual(aug["coral_s"].pct_active, 96.0)

    def test_q2_blank_arppu(self) -> None:
        rows = load_goals_tsv(self.path)
        apr = next(r for r in rows if r.agent == "coral_s" and r.month == 4)
        self.assertIsNone(apr.arppu)


class RunRateTests(unittest.TestCase):
    def test_month_bounds_aug_16(self) -> None:
        start, elapsed, dim = month_bounds(date(2026, 8, 16))
        self.assertEqual(start, date(2026, 8, 1))
        self.assertEqual(elapsed, 16)
        self.assertEqual(dim, 31)

    def test_run_rate(self) -> None:
        self.assertAlmostEqual(run_rate_pace(160, 16, 31), 310.0)

    def test_achievement_cap(self) -> None:
        self.assertEqual(achievement_ratio(200, 100), 1.0)
        self.assertAlmostEqual(achievement_ratio(50, 100), 0.5)


AUG_TARGET = GoalsTarget(
    agent="coral_s",
    year=2026,
    month=8,
    quarter=3,
    daily_avg_purchase=51000,
    daily_avg_net_purchase=30000,
    monthly_purchasers=546,
    reactivations=53,
    upgrades=49,
    pct_active=96,
    arppu=2900,
)


def kpi_by_key(block: dict, key: str) -> dict:
    return next(k for k in block["kpis"] if k["key"] == key)


class ShapePaceTests(unittest.TestCase):
    def test_clean_shape_band(self) -> None:
        self.assertEqual(clean_shape(0.93), 0.93)
        self.assertIsNone(clean_shape(None))
        self.assertIsNone(clean_shape(1.4))
        self.assertIsNone(clean_shape(0.0))

    def test_shape_pace_never_below_mtd_or_above_cap(self) -> None:
        self.assertAlmostEqual(shape_pace(472, 0.92), 513.04, places=1)
        self.assertEqual(shape_pace(472, 0.92, cap=480), 480)
        self.assertEqual(shape_pace(472, 1.0), 472)
        self.assertIsNone(shape_pace(472, None))


class WeightedGoalsTests(unittest.TestCase):
    def test_all_kpis_on_track_scores_full_included_weight(self) -> None:
        actuals = {
            "mtd_purchase": 51_200 * 16,
            "mtd_net_purchase": 30_000 * 16,
            "monthly_purchasers": 546 * 0.93,
            "reactivations": 53 * 16 / 31,
            "upgrades": 49 * 0.87,
            "portfolio_size": 560,
            "active_players": 545,
            "purchasers_shape": 0.93,
            "upgrades_shape": 0.87,
        }
        block = build_agent_goals_block(
            "coral_s", AUG_TARGET, actuals, date(2026, 8, 16)
        )
        assert block is not None
        self.assertTrue(block["available"])
        self.assertEqual(len(block["kpis"]), 7)
        self.assertEqual(INCLUDED_WEIGHT_TOTAL, 80.0)
        self.assertEqual(
            [k["status"] for k in block["kpis"]], ["On track"] * 7
        )
        self.assertAlmostEqual(block["weightedTrackedPct"], 100.0, places=1)
        self.assertIn("80", block["weightedTrackedDisplay"])

    def test_saturating_kpis_do_not_use_linear_run_rate(self) -> None:
        actuals = {
            "mtd_purchase": 918_432,
            "mtd_net_purchase": 543_216,
            "monthly_purchasers": 472,
            "reactivations": 30,
            "upgrades": 37,
            "portfolio_size": 621,
            "active_players": 508,
            "purchasers_shape": 0.92,
            "upgrades_shape": 0.87,
        }
        block = build_agent_goals_block(
            "coral_s", AUG_TARGET, actuals, date(2026, 8, 16)
        )
        assert block is not None
        purchasers = kpi_by_key(block, "monthly_purchasers")
        self.assertAlmostEqual(purchasers["pace"], 513.04, places=1)
        self.assertLess(purchasers["pace"], 472 * 31 / 16)
        self.assertLessEqual(purchasers["pace"], 621)

        upgrades = kpi_by_key(block, "upgrades")
        self.assertAlmostEqual(upgrades["pace"], 42.53, places=1)
        self.assertLess(upgrades["pace"], 37 * 31 / 16)

        # Reactivations do accrue linearly, so they keep the run rate.
        self.assertAlmostEqual(
            kpi_by_key(block, "reactivations")["pace"], 30 * 31 / 16, places=2
        )

        # ARPPU is rebuilt from paced spend / paced purchasers, not MTD/MTD.
        arppu = kpi_by_key(block, "arppu")
        mtd_arppu = 918_432 / 472
        self.assertGreater(arppu["pace"], mtd_arppu * 1.5)
        self.assertAlmostEqual(
            arppu["pace"], (918_432 / 16 * 31) / purchasers["pace"], places=2
        )

        # % Active is point-in-time from active_players, not paced purchasers.
        pct_active = kpi_by_key(block, "pct_active")
        self.assertAlmostEqual(pct_active["actual"], 508 / 621 * 100, places=2)
        self.assertAlmostEqual(pct_active["pace"], pct_active["actual"], places=6)

    def test_missing_shape_falls_back_to_mtd_status(self) -> None:
        actuals = {
            "mtd_purchase": 918_432,
            "mtd_net_purchase": 543_216,
            "monthly_purchasers": 472,
            "reactivations": 30,
            "upgrades": 37,
            "portfolio_size": 621,
        }
        block = build_agent_goals_block(
            "coral_s", AUG_TARGET, actuals, date(2026, 8, 16)
        )
        assert block is not None
        purchasers = kpi_by_key(block, "monthly_purchasers")
        self.assertIsNone(purchasers["pace"])
        self.assertEqual(purchasers["paceDisplay"], "—")
        self.assertEqual(purchasers["status"], "Behind")
        self.assertIn("No month-end projection", purchasers["paceBasis"])
        self.assertIsNone(kpi_by_key(block, "arppu")["pace"])

    def test_pct_active_is_point_in_time_not_derived(self) -> None:
        """% Active comes from active_players (last purchase inside the window)
        over the whole tagged book, locked included — a tagged player contributes
        to every KPI regardless of lock status. Not derived from monthly
        purchasers, and never paced."""
        actuals = {
            "mtd_purchase": 918_432,
            "mtd_net_purchase": 543_216,
            "monthly_purchasers": 472,
            "reactivations": 55,
            "upgrades": 37,
            "portfolio_size": 594,
            "active_players": 508,
            "purchasers_shape": 0.919,
            "upgrades_shape": 0.876,
        }
        block = build_agent_goals_block(
            "coral_s", AUG_TARGET, actuals, date(2026, 8, 16)
        )
        assert block is not None

        pct_active = kpi_by_key(block, "pct_active")
        self.assertAlmostEqual(pct_active["actual"], 508 / 594 * 100, places=2)
        # Point-in-time: pace equals actual, no projection.
        self.assertAlmostEqual(pct_active["pace"], pct_active["actual"], places=6)
        self.assertIn("Point-in-time", pct_active["paceBasis"])
        # Must not be purchasers / portfolio.
        self.assertNotAlmostEqual(
            pct_active["actual"], 472 / 594 * 100, places=2
        )

    def test_pct_active_capped_and_safe_without_actives(self) -> None:
        base = {
            "mtd_purchase": 918_432,
            "mtd_net_purchase": 543_216,
            "monthly_purchasers": 472,
            "reactivations": 55,
            "upgrades": 37,
            "portfolio_size": 594,
            "purchasers_shape": 0.919,
            "upgrades_shape": 0.876,
        }
        # More actives than book (stale tag snapshot) must not exceed 100%.
        over = build_agent_goals_block(
            "coral_s", AUG_TARGET, {**base, "active_players": 700},
            date(2026, 8, 16),
        )
        assert over is not None
        self.assertEqual(kpi_by_key(over, "pct_active")["actual"], 100.0)

        missing = build_agent_goals_block(
            "coral_s", AUG_TARGET, base, date(2026, 8, 16)
        )
        assert missing is not None
        self.assertEqual(kpi_by_key(missing, "pct_active")["actual"], 0.0)

    def test_alon_returns_none(self) -> None:
        self.assertIsNone(
            build_agent_goals_block("alon_tish", None, {}, date(2026, 8, 16))
        )


class IsolationTests(unittest.TestCase):
    def test_strip_payload_drops_other_ams(self) -> None:
        payload = {
            "report": {"date": "2026-08-16", "title": "Elite AM Brief", "subtitle": "x"},
            "amShares": [{"agentName": "Coral"}, {"agentName": "Lee"}],
            "overview": [{"agentName": "Coral"}, {"agentName": "Lee"}],
            "agents": [
                {"agentName": "Coral", "goals": {"available": True}, "top10": [{"aid": "1"}]},
                {"agentName": "Lee", "goals": {"available": True}, "top10": [{"aid": "2"}]},
            ],
            "amOrder": ["Coral", "Lee", "Rachel", "Gabriel", "Alon"],
            "goalsMeta": {
                "includedWeightTotal": 80,
                "goalsAmOrder": ["Coral", "Gabriel", "Lee", "Rachel"],
            },
        }
        coral = strip_payload_for_am(payload, "Coral")
        self.assertEqual(coral["amOrder"], ["Coral"])
        self.assertEqual(coral["goalsMeta"]["goalsAmOrder"], ["Coral"])
        self.assertEqual(coral["goalsMeta"]["includedWeightTotal"], 80)
        self.assertEqual(len(coral["agents"]), 1)
        self.assertEqual(coral["agents"][0]["agentName"], "Coral")
        self.assertEqual(coral["overview"], [])
        self.assertEqual(coral["amShares"], [])
        self.assertTrue(coral["singleAm"])
        self.assertEqual([a["agentName"] for a in coral["agents"]], ["Coral"])


if __name__ == "__main__":
    unittest.main()
