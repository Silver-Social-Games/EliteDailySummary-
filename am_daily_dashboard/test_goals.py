"""Unit tests for AM Brief Goals loader, run-rate, weighted score, isolation."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

PACKAGE_DIR = Path(__file__).resolve().parent
if str(PACKAGE_DIR) not in sys.path:
    sys.path.insert(0, str(PACKAGE_DIR))

import canvas_to_html  # noqa: E402

import queries as am_queries  # noqa: E402

from goals_reference import load_reference_tsv, reference_for  # noqa: E402

from goals import (  # noqa: E402
    GOALS_AGENT_TAGS,
    INCLUDED_WEIGHT_TOTAL,
    MANAGER_APPRECIATION_MAX,
    TEAM_AGENT_TAG,
    GoalsTarget,
    _status_for,
    achievement_ratio,
    actuals_by_agent,
    appreciation_for_month,
    build_agent_goals_block,
    build_score_block,
    build_team_goals_block,
    clean_shape,
    load_goals_tsv,
    load_manager_appreciation,
    month_bounds,
    parse_number,
    run_rate_pace,
    shape_pace,
    strip_payload_for_am,
    targets_for_month,
    team_actuals,
    _display_gap,
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

        # % Active = MTD purchasers / portfolio; pace uses shaped purchasers.
        pct_active = kpi_by_key(block, "pct_active")
        self.assertAlmostEqual(pct_active["actual"], 472 / 621 * 100, places=2)
        self.assertAlmostEqual(
            pct_active["pace"], purchasers["pace"] / 621 * 100, places=2
        )

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

    def test_pct_active_is_mtd_purchasers_over_portfolio(self) -> None:
        """% Active = MTD purchasers / whole tagged book; pace uses shaped purchasers."""
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
        purchasers = kpi_by_key(block, "monthly_purchasers")
        self.assertAlmostEqual(pct_active["actual"], 472 / 594 * 100, places=2)
        self.assertAlmostEqual(
            pct_active["pace"], purchasers["pace"] / 594 * 100, places=2
        )
        self.assertIn("MTD purchasers", pct_active["paceBasis"])

    def test_pct_active_capped_and_safe_without_purchasers(self) -> None:
        base = {
            "mtd_purchase": 918_432,
            "mtd_net_purchase": 543_216,
            "reactivations": 55,
            "upgrades": 37,
            "portfolio_size": 594,
            "purchasers_shape": 0.919,
            "upgrades_shape": 0.876,
        }
        over = build_agent_goals_block(
            "coral_s", AUG_TARGET, {**base, "monthly_purchasers": 700},
            date(2026, 8, 16),
        )
        assert over is not None
        self.assertEqual(kpi_by_key(over, "pct_active")["actual"], 100.0)

        missing = build_agent_goals_block(
            "coral_s", AUG_TARGET, {**base, "monthly_purchasers": 0},
            date(2026, 8, 16),
        )
        assert missing is not None
        self.assertEqual(kpi_by_key(missing, "pct_active")["actual"], 0.0)

    def test_alon_returns_none(self) -> None:
        self.assertIsNone(
            build_agent_goals_block("alon_tish", None, {}, date(2026, 8, 16))
        )


TEAM_TARGET = GoalsTarget(
    agent=TEAM_AGENT_TAG,
    year=2026,
    month=8,
    quarter=3,
    daily_avg_purchase=210_000,
    daily_avg_net_purchase=122_000,
    monthly_purchasers=2_250,
    reactivations=220,
    upgrades=200,
    pct_active=96,
    arppu=2_900,
)

# The whole managed book rolled up, Alon included: 2,461 accounts, 1,883
# distinct purchasers (2026-08-17).
TEAM_ACTUALS = {
    "mtd_purchase": 3_535_949.0,
    "mtd_net_purchase": 1_685_244.0,
    "monthly_purchasers": 1_883,
    "reactivations": 221,
    "upgrades": 173,
    "portfolio_size": 2_461,
    "portfolio_size_all": 2_461,
    "portfolio_locked": 191,
    "active_players": 2_085,
    "purchasers_shape": 0.9288,
    "upgrades_shape": 0.8763,
}


class TeamGoalsTests(unittest.TestCase):
    """The manager's team view — Batch 11."""

    def test_team_targets_load_and_are_not_the_sum_of_the_ams(self) -> None:
        aug = targets_for_month(date(2026, 8, 17))
        self.assertIn(TEAM_AGENT_TAG, aug)
        team = aug[TEAM_AGENT_TAG]
        self.assertEqual(team.daily_avg_purchase, 210_000.0)
        self.assertEqual(team.monthly_purchasers, 2_250.0)
        # The whole point of loading them: four AM rows do not add up to these.
        am_sum = sum(
            aug[t].daily_avg_purchase
            for t in ("coral_s", "gabriel_e", "lee_t", "rachel_a")
        )
        self.assertEqual(am_sum, 204_000.0)
        self.assertNotEqual(am_sum, team.daily_avg_purchase)

    def test_team_row_picked_out_of_the_rollup(self) -> None:
        rows = [
            {"agent": "coral_s", "mtd_purchase": 1.0},
            {"agent": TEAM_AGENT_TAG, "mtd_purchase": 9.0},
        ]
        self.assertEqual(team_actuals(rows)["mtd_purchase"], 9.0)
        self.assertEqual(team_actuals([{"agent": "coral_s"}]), {})

    def test_block_has_no_score_meter(self) -> None:
        block = build_team_goals_block(
            TEAM_TARGET, TEAM_ACTUALS, date(2026, 8, 17)
        )
        assert block is not None
        self.assertTrue(block["available"])
        self.assertEqual(block["agent"], TEAM_AGENT_TAG)
        self.assertEqual(block["agentName"], "Team")
        self.assertNotIn("score", block)
        # The per-AM block still has one — this is a team-only omission.
        am = build_agent_goals_block(
            "coral_s", AUG_TARGET, TEAM_ACTUALS, date(2026, 8, 17)
        )
        assert am is not None
        self.assertIn("score", am)

    def test_ratios_are_rebuilt_from_team_totals_not_averaged(self) -> None:
        block = build_team_goals_block(
            TEAM_TARGET, TEAM_ACTUALS, date(2026, 8, 17)
        )
        assert block is not None
        arppu = kpi_by_key(block, "arppu")
        self.assertAlmostEqual(arppu["actual"], 3_535_949 / 1_883, places=2)
        pct = kpi_by_key(block, "pct_active")
        self.assertAlmostEqual(pct["actual"], 1_883 / 2_461 * 100, places=2)
        # Paced ARPPU clears the goal even though every AM's own MTD ARPPU is
        # far below it — averaging the four would have said the opposite.
        self.assertGreater(arppu["pace"], TEAM_TARGET.arppu)
        self.assertEqual(arppu["status"], "On track")

    def test_net_purchase_is_the_headline_miss(self) -> None:
        block = build_team_goals_block(
            TEAM_TARGET, TEAM_ACTUALS, date(2026, 8, 17)
        )
        assert block is not None
        net = kpi_by_key(block, "daily_avg_net_purchase")
        self.assertAlmostEqual(net["actual"], 1_685_244 / 17, places=2)
        self.assertEqual(net["status"], "Behind")

    def test_book_includes_alon_but_only_for_the_team(self) -> None:
        """Alon has no targets, yet the manager owns his portfolio.

        Leaving him out of the rollup understated Daily Avg Purchase by about
        $4,000/day against the manager's own sheet.
        """
        self.assertIn("'alon_tish'", am_queries.GOALS_BOOK_TAGS_SQL)
        self.assertNotIn("alon_tish", am_queries.GOALS_SCORED_TAGS_SQL)
        # He must not acquire a Goals block of his own.
        self.assertNotIn("alon_tish", GOALS_AGENT_TAGS)
        self.assertIsNone(
            build_agent_goals_block("alon_tish", AUG_TARGET, {}, date(2026, 8, 17))
        )
        # His per-agent actuals row is dropped before any block is built.
        indexed = actuals_by_agent(
            [{"agent": "alon_tish", "mtd_purchase": 1.0},
             {"agent": "coral_s", "mtd_purchase": 2.0}]
        )
        self.assertEqual(set(indexed), {"coral_s"})

    def test_month_shape_reference_excludes_alon(self) -> None:
        """Pace divisors stay measured on the four scored AMs.

        Otherwise adding Alon to the team rollup would silently move every AM's
        own Monthly Purchasers pace, and therefore their score.
        """
        sql = am_queries.goals_mtd_actuals_sql(date(2026, 8, 17))
        self.assertIn("scored_book", sql)
        self.assertIn("INNER JOIN scored_book s ON s.account_id = k.account_id", sql)
        self.assertIn("WHERE agent != 'alon_tish'", sql)

    def test_missing_team_target_reports_unavailable(self) -> None:
        block = build_team_goals_block(None, TEAM_ACTUALS, date(2026, 8, 17))
        assert block is not None
        self.assertFalse(block["available"])
        self.assertEqual(block["agentName"], "Team")

    def test_reference_file_accepts_a_team_row(self) -> None:
        """So the manager's own sheet self-diffs instead of being read aloud."""
        body = (
            "Agent Name\tmonth\tQ\tyear\tday\tDaily Avg Purchase\t"
            "Daily Avg Net Purchase\tMonthly Players w purchase\t#Reactivations\t"
            "#Players Upgraded to Elite\t% Active From Portfolio\t"
            "ARPPU (avg purchase per paying player)\n"
            "team\t8\t3\t2026\t17\t207,620.00\t99,014.00\t\t\t\t\t\n"
            "coral_s\t8\t3\t2026\t17\t56,387.00\t\t\t\t\t\t\n"
        )
        path = Path(tempfile.mkdtemp()) / "ref.tsv"
        path.write_text(body, encoding="utf-8")
        rows = load_reference_tsv(path)
        self.assertEqual({r.agent for r in rows}, {TEAM_AGENT_TAG, "coral_s"})
        theirs = reference_for(rows, TEAM_AGENT_TAG, "2026-08-17")
        self.assertEqual(theirs["Daily Avg Purchase"], 207_620.0)
        self.assertEqual(theirs["Daily Avg Net Purchase"], 99_014.0)
        # A different as-of day must not diff against this row.
        self.assertEqual(reference_for(rows, TEAM_AGENT_TAG, "2026-08-16"), {})

    def test_team_goals_never_reach_a_per_am_file(self) -> None:
        payload = {
            "report": {"title": "Elite AM Brief"},
            "agents": [{"agentName": "Coral", "goals": {"available": True}}],
            "amOrder": ["Coral", "Lee"],
            "teamGoals": {"available": True, "agent": TEAM_AGENT_TAG},
            "managerGate": "secret",
        }
        stripped = strip_payload_for_am(payload, "Coral", peer_mode=False)
        self.assertNotIn("teamGoals", stripped)
        self.assertNotIn("managerGate", stripped)
        self.assertNotIn("archive", stripped["report"])
        self.assertEqual(stripped["audienceSlug"], "coral")


APPRECIATION_TSV = """year\tmonth\tagent\tpoints\tnote
2026\t8\tcoral_s\t18\tstrong recovery on net
2026\t8\tlee_t\t25\tover the cap
2026\t8\trachel_a\t\tno score yet
2026\t7\tgabriel_e\t12\tprior month
2026\t8\talon_tish\t20\tnot a goals AM
"""


class ManagerAppreciationTests(unittest.TestCase):
    def _tsv(self, body: str = APPRECIATION_TSV) -> Path:
        tmp = Path(tempfile.mkdtemp()) / "appreciation.tsv"
        tmp.write_text(body, encoding="utf-8")
        return tmp

    def test_loads_clamps_and_filters(self) -> None:
        rows = load_manager_appreciation(self._tsv())
        self.assertEqual(rows[(2026, 8, "coral_s")]["points"], 18.0)
        # Above the cap is clamped, not accepted.
        self.assertEqual(rows[(2026, 8, "lee_t")]["points"], 20.0)
        # A blank score is absent, never zero — 0 is a judgement not yet made.
        self.assertNotIn((2026, 8, "rachel_a"), rows)
        # Not a goals AM.
        self.assertNotIn((2026, 8, "alon_tish"), rows)

    def test_month_filter(self) -> None:
        aug = appreciation_for_month(date(2026, 8, 17), self._tsv())
        self.assertEqual(set(aug), {"coral_s", "lee_t"})
        jul = appreciation_for_month(date(2026, 7, 17), self._tsv())
        self.assertEqual(set(jul), {"gabriel_e"})

    def test_missing_file_is_not_an_error(self) -> None:
        missing = Path(tempfile.mkdtemp()) / "nope.tsv"
        self.assertEqual(load_manager_appreciation(missing), {})
        self.assertEqual(appreciation_for_month(date(2026, 8, 17), missing), {})

    def test_header_only_file_is_empty(self) -> None:
        self.assertEqual(
            load_manager_appreciation(self._tsv("year\tmonth\tagent\tpoints\tnote\n")),
            {},
        )

    def test_unscored_never_reports_out_of_100(self) -> None:
        score = build_score_block(75.8, 80.0, None)
        self.assertFalse(score["managerScored"])
        self.assertIsNone(score["managerPoints"])
        self.assertEqual(score["managerPointsDisplay"], "Pending")
        self.assertEqual(score["totalPoints"], 75.8)
        # The denominator stays at the KPI block: claiming /100 would spend the
        # manager's 20 points on the AM's behalf.
        self.assertEqual(score["totalPointsMax"], 80.0)
        self.assertEqual(score["totalDisplay"], "75.8 / 80")

    def test_scored_totals_out_of_100(self) -> None:
        score = build_score_block(75.8, 80.0, {"points": 17.0, "note": "good"})
        self.assertTrue(score["managerScored"])
        self.assertEqual(score["totalPoints"], 92.8)
        self.assertEqual(score["totalPointsMax"], 100.0)
        self.assertEqual(score["totalDisplay"], "92.8 / 100")
        self.assertEqual(score["scoreSubline"], "75.8 KPI + 17.0 manager")
        self.assertEqual(score["managerNote"], "good")

    def test_unavailable_kpi_shrinks_only_the_kpi_side(self) -> None:
        """Upgrade to Elite (5 pts) unavailable: the KPI block is out of 75 and
        the manager's 20 is untouched."""
        score = build_score_block(71.1, 75.0, {"points": 20.0, "note": ""})
        self.assertEqual(score["kpiPointsDisplay"], "71.1 / 75")
        self.assertEqual(score["managerPointsMax"], MANAGER_APPRECIATION_MAX)
        self.assertEqual(score["totalDisplay"], "91.1 / 95")

    def test_block_carries_score_and_defaults_to_pending(self) -> None:
        actuals = {
            "mtd_purchase": 51_000 * 16,
            "mtd_net_purchase": 30_000 * 16,
            "monthly_purchasers": 546 * 0.93,
            "reactivations": 53 * 16 / 31,
            "upgrades": 49 * 0.87,
            "portfolio_size": 560,
            "active_players": 545,
            "purchasers_shape": 0.93,
            "upgrades_shape": 0.87,
        }
        pending = build_agent_goals_block(
            "coral_s", AUG_TARGET, actuals, date(2026, 8, 16)
        )
        assert pending is not None
        self.assertEqual(pending["score"]["managerPointsDisplay"], "Pending")
        self.assertEqual(pending["score"]["totalPointsMax"], 80.0)

        scored = build_agent_goals_block(
            "coral_s",
            AUG_TARGET,
            actuals,
            date(2026, 8, 16),
            appreciation={"points": 16.0, "note": ""},
        )
        assert scored is not None
        self.assertEqual(scored["score"]["totalPointsMax"], 100.0)
        self.assertAlmostEqual(scored["score"]["totalPoints"], 96.0, places=1)


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
        coral = strip_payload_for_am(payload, "Coral", peer_mode=False)
        self.assertEqual(coral["amOrder"], ["Coral"])
        self.assertEqual(coral["goalsMeta"]["goalsAmOrder"], ["Coral"])
        self.assertEqual(coral["goalsMeta"]["includedWeightTotal"], 80)
        self.assertEqual(len(coral["agents"]), 1)
        self.assertEqual(coral["agents"][0]["agentName"], "Coral")
        self.assertEqual(coral["overview"], [])
        self.assertEqual(coral["amShares"], [])
        self.assertTrue(coral["singleAm"])
        self.assertEqual([a["agentName"] for a in coral["agents"]], ["Coral"])

    def _peer_source_payload(self) -> dict:
        return {
            "report": {"date": "2026-08-16", "title": "Elite AM Brief", "subtitle": "x",
                       "archive": [{"d": "2026-08-16", "f": "x.html"}]},
            "amShares": [{"agentName": "Coral"}, {"agentName": "Lee"}],
            "overview": [{"agentName": "Coral"}, {"agentName": "Lee"}],
            "agents": [
                {"agentName": "Coral", "goals": {"available": True}, "top10": [{"aid": "1"}]},
                {"agentName": "Lee", "goals": {"available": True}, "top10": [{"aid": "2"}]},
                {"agentName": "Alon", "goals": None, "top10": [{"aid": "3"}]},
            ],
            "amOrder": ["Coral", "Lee", "Alon"],
            "goalsMeta": {"includedWeightTotal": 80,
                          "goalsAmOrder": ["Coral", "Gabriel", "Lee", "Rachel"]},
            "teamGoals": {"available": True},
            "managerGate": "deadbeef",
        }

    def test_peer_mode_keeps_briefed_tabs_but_goals_home_only(self) -> None:
        payload = self._peer_source_payload()
        coral = strip_payload_for_am(payload, "Coral", peer_mode=True)
        # A tab for every AM with a brief of their own (a goals block), plus the
        # home AM. Alon has no goals => no snapshot => dropped from the switcher.
        self.assertEqual([a["agentName"] for a in coral["agents"]], ["Coral", "Lee"])
        self.assertEqual(coral["amOrder"], ["Coral", "Lee"])
        self.assertNotIn("Alon", [a["agentName"] for a in coral["agents"]])
        # Goals live only on the home AM; peers are stripped.
        goals_by_am = {a["agentName"]: a.get("goals") for a in coral["agents"]}
        self.assertIsNotNone(goals_by_am["Coral"])
        self.assertIsNone(goals_by_am["Lee"])
        # Coverage-board flags and audience.
        self.assertFalse(coral["singleAm"])
        self.assertTrue(coral["peerMode"])
        self.assertEqual(coral["homeAm"], "Coral")
        self.assertEqual(coral["audienceSlug"], "coral")

    def test_peer_mode_still_withholds_manager_only_data(self) -> None:
        payload = self._peer_source_payload()
        coral = strip_payload_for_am(payload, "Coral", peer_mode=True)
        self.assertEqual(coral["overview"], [])
        self.assertEqual(coral["amShares"], [])
        self.assertNotIn("teamGoals", coral)
        self.assertNotIn("managerGate", coral)
        self.assertNotIn("archive", coral["report"])
        self.assertEqual(coral["goalsMeta"]["goalsAmOrder"], ["Coral"])

    def test_peer_mode_does_not_mutate_source_agents(self) -> None:
        payload = self._peer_source_payload()
        strip_payload_for_am(payload, "Coral", peer_mode=True)
        # The shared manager payload's Lee block must keep its goals — the peer
        # strip works on copies, so a later manager render is untouched.
        lee = next(a for a in payload["agents"] if a["agentName"] == "Lee")
        self.assertIsNotNone(lee.get("goals"))


class ArchiveCalendarTests(unittest.TestCase):
    """The calendar is only safe if it never offers a file that does not exist."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        for name in [
            "2026-07-27_elite_am_brief.html",
            "2026-08-06_elite_am_brief.html",
            "2026-08-16_elite_am_brief.html",
            "2026-08-16_elite_am_brief_coral.html",
            "2026-08-16_elite_am_brief_lee.html",
            "elite_am_brief.html",
            "elite_am_brief_coral.html",
            "2026-08-16_elite_am_brief.json",
            "notes.html",
        ]:
            (self.dir / name).write_text("x", encoding="utf-8")
        patcher = mock.patch.object(canvas_to_html, "OUT_DIR", self.dir)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)

    def test_audience_slug_from_filename(self) -> None:
        cases = {
            "2026-08-17_elite_am_brief.html": "",
            "elite_am_brief.html": "",
            "2026-08-17_elite_am_brief_coral.html": "coral",
            "elite_am_brief_rachel.html": "rachel",
            "something_else.html": "",
        }
        for name, expected in cases.items():
            self.assertEqual(canvas_to_html.audience_slug(Path(name)), expected, name)

    def test_payload_beats_filename_for_audience(self) -> None:
        """A caller-chosen --out name carries no audience; the payload does."""
        single = {"singleAm": True, "singleAmName": "Rachel"}
        self.assertEqual(
            canvas_to_html.audience_slug(Path("anything.html"), single), "rachel"
        )
        # A single-AM payload must not be read as the manager just because the
        # filename looks like one.
        self.assertEqual(
            canvas_to_html.audience_slug(Path("elite_am_brief.html"), single), "rachel"
        )
        self.assertEqual(
            canvas_to_html.audience_slug(Path("out.html"), {"agents": []}), ""
        )
        self.assertEqual(
            canvas_to_html.audience_slug(
                Path("out.html"),
                {"singleAm": True, "agents": [{"agentName": "Lee"}]},
            ),
            "lee",
        )

    def test_am_payload_never_gets_the_managers_archive(self) -> None:
        """Regression: an --out name outside the convention leaked manager dates."""
        payload = {
            "report": {"date": "2026-08-17"},
            "singleAm": True,
            "singleAmName": "Coral",
        }
        out = self.dir / "custom_name_for_coral.html"
        canvas_to_html.write_am_brief_html(payload, out)
        text = out.read_text(encoding="utf-8")
        self.assertIn("2026-08-16_elite_am_brief_coral.html", text)
        self.assertNotIn("2026-07-27_elite_am_brief.html", text)
        self.assertNotIn("2026-08-06_elite_am_brief.html", text)

    def test_manager_archive_lists_only_manager_files(self) -> None:
        entries = canvas_to_html.archive_entries("", "2026-08-17")
        self.assertEqual(
            [e["d"] for e in entries],
            ["2026-07-27", "2026-08-06", "2026-08-16", "2026-08-17"],
        )
        self.assertEqual(entries[0]["f"], "2026-07-27_elite_am_brief.html")

    def test_am_archive_never_offers_a_day_without_their_file(self) -> None:
        """Coral has one archived day; the manager's extra days must not leak in."""
        coral = canvas_to_html.archive_entries("coral", "2026-08-17")
        self.assertEqual([e["d"] for e in coral], ["2026-08-16", "2026-08-17"])
        self.assertEqual(coral[0]["f"], "2026-08-16_elite_am_brief_coral.html")
        rachel = canvas_to_html.archive_entries("rachel", "2026-08-17")
        self.assertEqual([e["d"] for e in rachel], ["2026-08-17"])

    def test_report_date_is_always_offered(self) -> None:
        """The day being generated is clickable even before its file is closed."""
        entries = canvas_to_html.archive_entries("", "2026-08-20")
        self.assertIn("2026-08-20", [e["d"] for e in entries])

    def test_dateless_and_foreign_files_are_not_archive_entries(self) -> None:
        names = {e["f"] for e in canvas_to_html.archive_entries("", "2026-08-17")}
        self.assertNotIn("elite_am_brief.html", names)
        self.assertNotIn("notes.html", names)
        self.assertNotIn("2026-08-16_elite_am_brief.json", names)

    def test_with_archive_does_not_mutate_the_caller_payload(self) -> None:
        payload = {"report": {"date": "2026-08-17"}, "agents": []}
        out = canvas_to_html.with_archive(payload, "coral")
        self.assertNotIn("archive", payload["report"])
        self.assertTrue(out["report"]["archive"])

    def test_writer_attaches_archive_so_a_json_refresh_keeps_the_calendar(self) -> None:
        """Regression: the standalone refresh used to produce a calendar-less file."""
        payload = {
            "report": {"date": "2026-08-17", "subtitle": "Monday 17 Aug 2026"},
            "singleAm": True,
            "singleAmName": "Coral",
        }
        out = self.dir / "2026-08-17_elite_am_brief_coral.html"
        canvas_to_html.write_am_brief_html(payload, out)
        text = out.read_text(encoding="utf-8")
        self.assertIn('"archive"', text)
        self.assertIn("2026-08-16_elite_am_brief_coral.html", text)
        # The manager's own extra dates must not reach an AM's file.
        self.assertNotIn("2026-07-27_elite_am_brief.html", text)

    def test_manager_payload_gets_the_manager_archive(self) -> None:
        payload = {"report": {"date": "2026-08-17"}}
        out = self.dir / "2026-08-17_elite_am_brief.html"
        canvas_to_html.write_am_brief_html(payload, out)
        text = out.read_text(encoding="utf-8")
        self.assertIn("2026-07-27_elite_am_brief.html", text)

    def test_existing_archive_on_payload_is_rebuilt_for_audience(self) -> None:
        payload = {
            "report": {
                "date": "2026-08-17",
                "archive": [{"d": "2026-01-01", "f": "wrong_manager.html"}],
            },
            "singleAm": True,
            "singleAmName": "Coral",
        }
        out = self.dir / "2026-08-17_elite_am_brief_coral.html"
        canvas_to_html.write_am_brief_html(payload, out)
        text = out.read_text(encoding="utf-8")
        self.assertNotIn("wrong_manager.html", text)
        self.assertIn("2026-08-16_elite_am_brief_coral.html", text)

    def test_per_am_json_refresh_does_not_overwrite_the_manager_file(self) -> None:
        payload_path = self.dir / "2026-08-17_elite_am_brief_lee.json"
        payload_path.write_text(
            json.dumps({"report": {"date": "2026-08-17"}, "singleAm": True}),
            encoding="utf-8",
        )
        with mock.patch.object(canvas_to_html, "OUT_DIR", self.dir):
            out = canvas_to_html.convert(payload_path)
        self.assertEqual(out.name, "2026-08-17_elite_am_brief_lee.html")


class DisplayGapTests(unittest.TestCase):
    def test_money_sign(self) -> None:
        self.assertEqual(_display_gap("daily_avg_purchase", 2340), "$2,340")
        self.assertEqual(_display_gap("daily_avg_purchase", -4633), "-$4,633")
        self.assertEqual(_display_gap("daily_avg_purchase", 0), "$0")

    def test_count_signed(self) -> None:
        self.assertEqual(_display_gap("monthly_purchasers", 196), "+196")
        self.assertEqual(_display_gap("monthly_purchasers", -12), "-12")

    def test_pct_active_keeps_pp(self) -> None:
        self.assertEqual(_display_gap("pct_active", -2.5), "-2.5pp")


if __name__ == "__main__":
    unittest.main()
