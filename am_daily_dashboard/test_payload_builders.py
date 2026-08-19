"""Unit tests for am_daily_dashboard/payload_builders.py.

Every test here is pure Python — no BigQuery, no credentials.  The builders
accept hand-written rows shaped like BQ results and produce payload dicts, so
they can be exercised exactly like goals.py's functions.

Coverage strategy (mirrors test_goals.py style):
- Each public builder gets at least a happy-path + one edge/boundary case.
- Helper functions (parse_date_val, fmt_price, etc.) get their own class.
- build_am_shares_and_overview closes the fixture NOTE about the local copy.
- queries._iso is tested separately at the bottom.
"""

from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent
for _p in (PROJECT_ROOT, PACKAGE_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from payload_builders import (  # noqa: E402
    AM_REASON_TONE,
    agent_display,
    aid_row,
    build_am_shares_and_overview,
    build_birthday_section,
    build_lock_section,
    build_package_fit,
    build_rd_section,
    build_top10_section,
    build_zd_section,
    fmt_price,
    focus_for_agent,
    greeting_lines,
    lock_bucket,
    parse_date_val,
    soften_decline_rows,
    soft_tone_for_code,
    unlock_info,
    _safe_int,
    _ticket_ids_list,
)

REPORT_DATE = date(2026, 8, 19)


# ---------------------------------------------------------------------------
# Helper: low-level utilities
# ---------------------------------------------------------------------------


class ParseDateValTests(unittest.TestCase):
    def test_iso_string(self) -> None:
        self.assertEqual(parse_date_val("2026-08-19"), date(2026, 8, 19))

    def test_date_passthrough(self) -> None:
        d = date(2026, 8, 19)
        self.assertEqual(parse_date_val(d), d)

    def test_none_returns_none(self) -> None:
        self.assertIsNone(parse_date_val(None))

    def test_empty_string_returns_none(self) -> None:
        self.assertIsNone(parse_date_val(""))

    def test_truncates_to_10_chars(self) -> None:
        self.assertEqual(parse_date_val("2026-08-19T12:34:56"), date(2026, 8, 19))


class SafeIntTests(unittest.TestCase):
    def test_int(self) -> None:
        self.assertEqual(_safe_int(5), 5)

    def test_float_string(self) -> None:
        # int("3.0") raises ValueError, so _safe_int returns 0 for float strings.
        # Callers that need float→int conversion first cast to float themselves.
        self.assertEqual(_safe_int("3.0"), 0)

    def test_none(self) -> None:
        self.assertEqual(_safe_int(None), 0)

    def test_invalid(self) -> None:
        self.assertEqual(_safe_int("abc"), 0)


class TicketIdsListTests(unittest.TestCase):
    def test_csv_string(self) -> None:
        self.assertEqual(_ticket_ids_list("101, 102"), ["101", "102"])

    def test_list_input(self) -> None:
        self.assertEqual(_ticket_ids_list([101, 102]), ["101", "102"])

    def test_none_returns_empty(self) -> None:
        self.assertEqual(_ticket_ids_list(None), [])

    def test_skips_none_elements(self) -> None:
        self.assertEqual(_ticket_ids_list([101, None, 102]), ["101", "102"])


class FmtPriceTests(unittest.TestCase):
    def test_whole_number(self) -> None:
        self.assertEqual(fmt_price(100), "$100")

    def test_cents(self) -> None:
        self.assertEqual(fmt_price(899.99), "$899.99")

    def test_none_dash(self) -> None:
        self.assertEqual(fmt_price(None), "—")

    def test_zero(self) -> None:
        self.assertEqual(fmt_price(0), "$0")

    def test_thousands(self) -> None:
        self.assertEqual(fmt_price(1000), "$1,000")


class BuildPackageFitTests(unittest.TestCase):
    def test_usual_and_ceiling(self) -> None:
        result = build_package_fit(199.99, 3, 299.99)
        self.assertEqual(result, "$199.99 ×3 → $299.99")

    def test_no_ceiling(self) -> None:
        result = build_package_fit(199.99, 2, None)
        self.assertEqual(result, "$199.99 ×2")

    def test_ceiling_not_higher_omitted(self) -> None:
        result = build_package_fit(299.99, 1, 199.99)
        self.assertEqual(result, "$299.99")

    def test_no_usual_returns_dash(self) -> None:
        self.assertEqual(build_package_fit(None, 0, None), "—")

    def test_single_order_no_multiplier(self) -> None:
        result = build_package_fit(99.99, 1, None)
        self.assertEqual(result, "$99.99")


class LockBucketTests(unittest.TestCase):
    def test_exclusion(self) -> None:
        bucket, tone = lock_bucket("Exclusion", "")
        self.assertEqual(bucket, "Self-exclusion")
        self.assertEqual(tone, "neutral")

    def test_self_exclud_in_comment(self) -> None:
        bucket, tone = lock_bucket("Other", "self_excluded player")
        self.assertEqual(bucket, "Self-exclusion")
        self.assertEqual(tone, "neutral")

    def test_take_a_break_from_comment(self) -> None:
        bucket, tone = lock_bucket("", "14 days take a break")
        self.assertEqual(bucket, "Take a break")
        self.assertEqual(tone, "warning")

    def test_other_locked(self) -> None:
        bucket, tone = lock_bucket("Fraud", "")
        self.assertEqual(bucket, "Other locked")
        self.assertEqual(tone, "warning")


class UnlockInfoTests(unittest.TestCase):
    """_take_a_break_days parses "take a break N" (case-insensitive, regex).
    A bare "14 days" comment does NOT match — the phrase must include the
    "take a break" prefix followed immediately by a number."""

    def test_upcoming_unlock(self) -> None:
        locked_at = date(2026, 8, 5)
        # "take a break 14" → 14-day break; locked Aug 5 → unlock Aug 19 → 0 remaining
        # Use 21 days so it's clearly in the future from Aug 19
        locked_at2 = date(2026, 8, 5)
        text, remaining = unlock_info("take a break 21", "", locked_at2, REPORT_DATE)
        # locked 2026-08-05, +21 days = 2026-08-26; report 2026-08-19 → 7 left
        self.assertEqual(remaining, 7)
        self.assertIn("7d left", text)
        self.assertIn("2026-08-26", text)

    def test_overdue(self) -> None:
        locked_at = date(2026, 8, 1)
        text, remaining = unlock_info("take a break 7", "", locked_at, REPORT_DATE)
        # unlock was 2026-08-08; report 2026-08-19 → remaining = -11
        self.assertIsNotNone(remaining)
        assert remaining is not None
        self.assertLess(remaining, 0)
        self.assertIn("remove restriction", text)

    def test_today_unlock(self) -> None:
        locked_at = date(2026, 8, 12)
        text, remaining = unlock_info("take a break 7", "", locked_at, REPORT_DATE)
        # 2026-08-12 + 7 = 2026-08-19 = report_date → 0 remaining
        self.assertEqual(remaining, 0)
        self.assertIn("today", text)

    def test_no_days_in_reason(self) -> None:
        # "Fraud" contains no "take a break N" pattern → returns ("", None)
        text, remaining = unlock_info("Fraud", "", None, REPORT_DATE)
        self.assertEqual(text, "")
        self.assertIsNone(remaining)

    def test_bare_days_comment_not_parsed(self) -> None:
        # "14 days" alone does NOT match "take a break N" → no unlock date
        text, remaining = unlock_info("Take a break", "14 days", None, REPORT_DATE)
        self.assertEqual(text, "")
        self.assertIsNone(remaining)

    def test_no_locked_at_with_valid_pattern(self) -> None:
        # Pattern matches but locked_at is None → returns the "N days" fallback
        text, remaining = unlock_info("take a break 14", "", None, REPORT_DATE)
        self.assertIn("14", text)
        self.assertIsNone(remaining)


class SoftToneTests(unittest.TestCase):
    def test_mapped_codes(self) -> None:
        self.assertEqual(soft_tone_for_code("payment_failed"), "danger")
        self.assertEqual(soft_tone_for_code("same_weekday_skip"), "info")
        self.assertEqual(soft_tone_for_code("big_win_day_before"), "success")

    def test_unknown_code_defaults_warning(self) -> None:
        self.assertEqual(soft_tone_for_code("some_new_code"), "warning")

    def test_none_defaults_warning(self) -> None:
        self.assertEqual(soft_tone_for_code(None), "warning")


class AgentDisplayTests(unittest.TestCase):
    def test_known_tag(self) -> None:
        # coral_s → "Coral" (from AGENT_TAG_LABELS in wow_drop_analysis)
        result = agent_display("coral_s")
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_unknown_tag_falls_back(self) -> None:
        result = agent_display("unknown_tag_xyz")
        self.assertIsInstance(result, str)


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------


def _top10_row(
    aid: int = 101,
    agent: str = "coral_s",
    *,
    purchased: float = 1200.0,
    usual_price: float | None = 199.99,
    usual_price_orders: int = 3,
    ceiling_price: float | None = 299.99,
    offer_unit_min: float = 199.99,
    offer_unit_max: float = 199.99,
) -> dict:
    return {
        "AID": aid, "name": "Test Player", "agent": agent,
        "rank_in_agent": 1, "purchased": purchased, "order_count": 5,
        "offer_code": "BOOST10", "offer_title": "Weekend Boost",
        "offer_qty": 2, "offer_amount": 399.98,
        "offer_unit_amount": 199.99,
        "offer_unit_min": offer_unit_min, "offer_unit_max": offer_unit_max,
        "usual_price": usual_price, "usual_price_orders": usual_price_orders,
        "ceiling_price": ceiling_price,
    }


class BuildTop10SectionTests(unittest.TestCase):
    def test_happy_path_keys(self) -> None:
        rows = [_top10_row()]
        out = build_top10_section(rows)
        self.assertEqual(len(out), 1)
        row = out[0]
        self.assertIn("aid", row)
        self.assertIn("aidUrl", row)
        self.assertIn("packageFit", row)
        self.assertIn("offerPrice", row)
        self.assertIn("offerPriceVaries", row)

    def test_price_not_varies_when_min_equals_max(self) -> None:
        out = build_top10_section([_top10_row(offer_unit_min=199.99, offer_unit_max=199.99)])
        self.assertFalse(out[0]["offerPriceVaries"])

    def test_price_varies_when_min_differs_from_max(self) -> None:
        out = build_top10_section([_top10_row(offer_unit_min=99.99, offer_unit_max=199.99)])
        self.assertTrue(out[0]["offerPriceVaries"])

    def test_package_fit_ceiling_included(self) -> None:
        out = build_top10_section([_top10_row(usual_price=199.99, ceiling_price=299.99)])
        self.assertIn("→", out[0]["packageFit"])

    def test_no_ceiling_no_arrow(self) -> None:
        out = build_top10_section([_top10_row(ceiling_price=None)])
        self.assertNotIn("→", out[0]["packageFit"])

    def test_empty_rows_returns_empty(self) -> None:
        self.assertEqual(build_top10_section([]), [])

    def test_tone_is_success(self) -> None:
        out = build_top10_section([_top10_row()])
        self.assertEqual(out[0]["tone"], "success")


def _rd_row(
    aid: int = 201,
    agent: str = "coral_s",
    *,
    amount: float = 7500.0,
    big_winner: bool = False,
    player_win_day: float = 0.0,
    created_date: str = "2026-08-19",
    locked: bool = False,
    lock_reason: str = "",
    lock_reason_comment: str = "",
) -> dict:
    return {
        "AID": aid, "name": "Test RD Player", "agent": agent,
        "redeem_id": f"RD{aid}", "amount": amount, "status": "locked",
        "created_date": created_date, "big_winner": big_winner,
        "player_win_day": player_win_day, "locked": locked,
        "lock_reason": lock_reason, "lock_reason_comment": lock_reason_comment,
    }


class BuildRdSectionTests(unittest.TestCase):
    def test_happy_path(self) -> None:
        out = build_rd_section([_rd_row()])
        self.assertEqual(len(out), 1)
        row = out[0]
        self.assertIn("aid", row)
        self.assertIn("amountNum", row)
        self.assertIn("bigWinner", row)
        self.assertEqual(row["bigWinner"], False)

    def test_big_winner_sets_danger_tone(self) -> None:
        out = build_rd_section([_rd_row(big_winner=True, player_win_day=6000.0)])
        self.assertEqual(out[0]["tone"], "danger")

    def test_big_winner_formats_won_yesterday(self) -> None:
        out = build_rd_section([_rd_row(big_winner=True, player_win_day=6000.0)])
        self.assertNotEqual(out[0]["wonYesterday"], "—")

    def test_zero_win_day_shows_dash(self) -> None:
        out = build_rd_section([_rd_row(player_win_day=0.0)])
        self.assertEqual(out[0]["wonYesterday"], "—")

    def test_aging_flag_when_threshold_reached(self) -> None:
        old = _rd_row(created_date="2026-08-17")  # 2 days ago
        out = build_rd_section([old], report_date=REPORT_DATE, aging_threshold_days=2)
        self.assertTrue(out[0]["agingFlag"])
        self.assertEqual(out[0]["tone"], "danger")

    def test_no_aging_when_below_threshold(self) -> None:
        recent = _rd_row(created_date="2026-08-19")  # today, 0 days
        out = build_rd_section([recent], report_date=REPORT_DATE, aging_threshold_days=2)
        self.assertFalse(out[0]["agingFlag"])

    def test_metrics_enrich_adds_docs_status(self) -> None:
        enrich = {201: {"lifetime_purchased": 12000, "purchased_7d": 500}}
        out = build_rd_section([_rd_row()], metrics_enrich=enrich)
        self.assertIn("docsStatus", out[0])
        self.assertIn("lifetimePurchase", out[0])

    def test_metrics_enrich_none_skips_docs(self) -> None:
        out = build_rd_section([_rd_row()])
        self.assertNotIn("docsStatus", out[0])

    def test_ticket_enrich_none_skips_draft(self) -> None:
        out = build_rd_section([_rd_row()])
        self.assertNotIn("ticketEnabled", out[0])

    def test_empty_rows(self) -> None:
        self.assertEqual(build_rd_section([]), [])


def _birthday_row(
    aid: int = 301,
    agent: str = "coral_s",
    *,
    locked: bool = False,
    lock_reason: str = "",
    lock_reason_comment: str = "",
) -> dict:
    return {
        "AID": aid, "name": "Birthday Player", "agent": agent,
        "email": "test@example.com", "dob": "1990-08-19", "age": 36,
        "locked": locked, "lock_reason": lock_reason,
        "lock_reason_comment": lock_reason_comment,
    }


class BuildBirthdaySectionTests(unittest.TestCase):
    def test_happy_path(self) -> None:
        out = build_birthday_section([_birthday_row()])
        self.assertEqual(len(out), 1)
        row = out[0]
        self.assertIn("dob", row)
        self.assertIn("age", row)
        # dob should be formatted as D/M/Y
        self.assertRegex(row["dob"], r"^\d+/\d+/\d+$")

    def test_tone_is_success(self) -> None:
        out = build_birthday_section([_birthday_row()])
        self.assertEqual(out[0]["tone"], "success")

    def test_ticket_enrich_none_skips_draft(self) -> None:
        out = build_birthday_section([_birthday_row()])
        self.assertNotIn("ticketEnabled", out[0])

    def test_ticket_enrich_empty_dict_attaches_keys(self) -> None:
        out = build_birthday_section([_birthday_row()], ticket_enrich={})
        # Draft fields should be present (locked=False so draft is enabled)
        self.assertIn("ticketEnabled", out[0])

    def test_locked_player_disables_ticket(self) -> None:
        out = build_birthday_section(
            [_birthday_row(locked=True, lock_reason="Exclusion")],
            ticket_enrich={},
        )
        self.assertFalse(out[0]["ticketEnabled"])

    def test_empty_rows(self) -> None:
        self.assertEqual(build_birthday_section([]), [])


def _zd_row(
    aid: int = 401,
    agent: str = "coral_s",
    *,
    open_tickets: int = 2,
    ticket_ids: str = "100001,100002",
) -> dict:
    return {
        "AID": aid, "name": "ZD Player", "agent": agent,
        "open_tickets": open_tickets, "ticket_ids": ticket_ids,
    }


class BuildZdSectionTests(unittest.TestCase):
    def test_happy_path(self) -> None:
        out = build_zd_section([_zd_row()])
        self.assertEqual(len(out), 1)
        row = out[0]
        self.assertIn("openTickets", row)
        self.assertIn("tickets", row)
        self.assertEqual(len(row["tickets"]), 2)
        for t in row["tickets"]:
            self.assertIn("id", t)
            self.assertIn("url", t)

    def test_ticket_urls_link_to_zendesk(self) -> None:
        out = build_zd_section([_zd_row(ticket_ids="999999")])
        self.assertIn("999999", out[0]["tickets"][0]["url"])

    def test_enrich_map_adds_ltp(self) -> None:
        enrich = {401: {"lifetime_purchased": 50000, "purchased_7d": 1000}}
        out = build_zd_section([_zd_row()], enrich_map=enrich)
        self.assertGreater(out[0]["lifetimePurchasedNum"], 0)

    def test_no_enrich_map_defaults_zero(self) -> None:
        out = build_zd_section([_zd_row()])
        self.assertEqual(out[0]["lifetimePurchasedNum"], 0)

    def test_tone_is_info(self) -> None:
        out = build_zd_section([_zd_row()])
        self.assertEqual(out[0]["tone"], "info")

    def test_empty_rows(self) -> None:
        self.assertEqual(build_zd_section([]), [])


def _lock_row(
    aid: int = 501,
    agent: str = "coral_s",
    *,
    lock_reason: str = "Take a break",
    lock_reason_comment: str = "14 days",
    days_ago: int = 0,
) -> dict:
    from datetime import timedelta
    return {
        "AID": aid, "name": "Locked Player", "agent": agent,
        "lock_reason": lock_reason, "lock_reason_comment": lock_reason_comment,
        "locked_at": (REPORT_DATE - timedelta(days=days_ago)).isoformat(),
    }


class BuildLockSectionTests(unittest.TestCase):
    def test_take_a_break_today_included(self) -> None:
        out = build_lock_section([_lock_row(days_ago=0)], REPORT_DATE)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["bucket"], "Take a break")

    def test_self_exclusion_today_included(self) -> None:
        out = build_lock_section(
            [_lock_row(lock_reason="Exclusion", lock_reason_comment="", days_ago=0)],
            REPORT_DATE,
        )
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["bucket"], "Self-exclusion")

    def test_old_lock_not_take_a_break_excluded(self) -> None:
        # Fraud lock 10 days old — neither the "today" path nor the
        # "due for review" path fires for a non-TAB lock this old.
        out = build_lock_section(
            [_lock_row(lock_reason="Fraud", lock_reason_comment="", days_ago=10)],
            REPORT_DATE,
        )
        self.assertEqual(len(out), 0)

    def test_overdue_take_a_break_gets_danger_tone(self) -> None:
        # Locked 30 days ago on a 7-day break → overdue by 23 days.
        # Must use "take a break 7" (not "7 days") so _take_a_break_days parses it.
        out = build_lock_section(
            [_lock_row(lock_reason_comment="take a break 7", days_ago=30)],
            REPORT_DATE,
        )
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["tone"], "danger")

    def test_missing_locked_at_skipped(self) -> None:
        row = {"AID": 999, "name": "X", "agent": "coral_s", "lock_reason": "Fraud",
               "lock_reason_comment": "", "locked_at": None}
        out = build_lock_section([row], REPORT_DATE)
        self.assertEqual(len(out), 0)

    def test_empty_rows(self) -> None:
        self.assertEqual(build_lock_section([], REPORT_DATE), [])


class SoftenDeclineRowsTests(unittest.TestCase):
    """soften_decline_rows re-maps tones based on reason_code."""

    def _make_built_row(self, aid: str, agent_name: str) -> dict:
        return {
            "aid": aid, "agentName": agent_name,
            "urgency": "Today", "tone": "danger",
            "name": "Player X",
        }

    def _make_raw_row(self, aid: int, reason_code: str) -> dict:
        return {"AID": aid, "reason_code": reason_code}

    def test_big_win_maps_to_success(self) -> None:
        built = [self._make_built_row("101", "Coral")]
        raw = [self._make_raw_row(101, "big_win_day_before")]
        out = soften_decline_rows(built, raw)
        self.assertEqual(out[0]["tone"], "success")

    def test_same_weekday_skip_maps_to_info(self) -> None:
        built = [self._make_built_row("101", "Coral")]
        raw = [self._make_raw_row(101, "same_weekday_skip")]
        out = soften_decline_rows(built, raw)
        self.assertEqual(out[0]["tone"], "info")

    def test_urgency_none_maps_to_neutral(self) -> None:
        built = [dict(self._make_built_row("101", "Coral"), urgency="None")]
        raw = [self._make_raw_row(101, "same_weekday_skip")]
        out = soften_decline_rows(built, raw)
        self.assertEqual(out[0]["tone"], "neutral")

    def test_unknown_aid_defaults_warning(self) -> None:
        built = [self._make_built_row("999", "Coral")]
        raw = []
        out = soften_decline_rows(built, raw)
        self.assertEqual(out[0]["tone"], "warning")

    def test_does_not_mutate_original(self) -> None:
        built = [self._make_built_row("101", "Coral")]
        raw = [self._make_raw_row(101, "big_win_day_before")]
        _ = soften_decline_rows(built, raw)
        self.assertEqual(built[0]["tone"], "danger")


class GreetingLinesTests(unittest.TestCase):
    def test_returns_three_lines(self) -> None:
        lines = greeting_lines(
            "Coral", "Monday",
            purchase="$12,000", purchase_share="30.0%",
            purchased_players=40, total_players=560, player_share="10.5%",
        )
        self.assertEqual(len(lines), 3)

    def test_first_line_is_greeting(self) -> None:
        lines = greeting_lines(
            "Lee", "Wednesday",
            purchase="$8,000", purchase_share="20.0%",
            purchased_players=35, total_players=620, player_share="9.0%",
        )
        self.assertEqual(lines[0], "Good morning, Lee.")

    def test_bold_markers_in_body(self) -> None:
        lines = greeting_lines(
            "Rachel", "Thursday",
            purchase="$9,500", purchase_share="25.0%",
            purchased_players=38, total_players=570, player_share="9.5%",
        )
        full = " ".join(lines)
        self.assertIn("**$9,500**", full)
        self.assertIn("**38**", full)

    def test_no_book_size_uses_fallback(self) -> None:
        lines = greeting_lines(
            "Alon", "Sunday",
            purchase="$1,000", purchase_share="5.0%",
            purchased_players=5, total_players=0, player_share="—",
        )
        full = " ".join(lines)
        self.assertNotIn("of your **0**", full)


class FocusForAgentTests(unittest.TestCase):
    """focus_for_agent assembles the per-AM payload block from section lists."""

    def _minimal_focus(self, agent_name: str = "Coral") -> dict:
        return focus_for_agent(
            agent_name, "Monday",
            top10=[], decline=[], rd5k=[], rd_first=[], birthdays=[],
            zd=[], locks=[],
            purchase={"purchased": 12000.0, "purchased_players": 40},
            total_players=560,
            elite_rev=40000.0, elite_ply=130,
        )

    def test_required_keys_present(self) -> None:
        result = self._minimal_focus()
        for key in ("agentName", "greetingLines", "purchase", "purchasedPlayers",
                    "totalPlayers", "focus", "top10", "decline", "rdOver5k",
                    "rdFirstTime", "birthdays", "zendesk", "locks", "goals"):
            self.assertIn(key, result)

    def test_agent_name_matches(self) -> None:
        result = self._minimal_focus("Rachel")
        self.assertEqual(result["agentName"], "Rachel")

    def test_focus_counters_zero_when_empty(self) -> None:
        result = self._minimal_focus()
        focus = result["focus"]
        for key in ("openZd", "locked", "takeABreak", "selfExclusion",
                    "otherLocked", "rdOver5k", "birthdays", "declineCount"):
            self.assertEqual(focus[key], 0, msg=key)

    def test_purchase_share_computed(self) -> None:
        result = self._minimal_focus()
        self.assertRegex(result["purchaseShare"], r"^\d+\.\d+%$")

    def test_no_purchase_data_gives_zero(self) -> None:
        result = focus_for_agent(
            "Alon", "Monday",
            top10=[], decline=[], rd5k=[], rd_first=[], birthdays=[],
            zd=[], locks=[], purchase=None, total_players=0,
            elite_rev=40000.0, elite_ply=130,
        )
        self.assertEqual(result["purchasedPlayers"], 0)
        self.assertEqual(result["purchase"], "$0")

    def test_section_rows_filtered_by_agent_name(self) -> None:
        """Only rows whose agentName matches the requested AM are included."""
        # Build rows that belong to two different AMs
        coral_row = {
            "aid": "101", "agentName": "Coral", "name": "Coral Player",
            "openTickets": 2, "tone": "info",
        }
        gabriel_row = {
            "aid": "201", "agentName": "Gabriel", "name": "Gabriel Player",
            "openTickets": 1, "tone": "info",
        }
        result = focus_for_agent(
            "Coral", "Monday",
            top10=[], decline=[], rd5k=[], rd_first=[], birthdays=[],
            zd=[coral_row, gabriel_row], locks=[],
            purchase={"purchased": 0, "purchased_players": 0},
            total_players=0, elite_rev=0, elite_ply=0,
        )
        self.assertEqual(len(result["zendesk"]), 1)
        self.assertEqual(result["zendesk"][0]["agentName"], "Coral")


class BuildAmSharesAndOverviewTests(unittest.TestCase):
    """build_am_shares_and_overview replaces the local copy in payload_fixtures."""

    def _make_agent(self, name: str, purchased: int = 40, total: int = 560) -> dict:
        purchase_share = f"{purchased / total * 100:.1f}%" if total else "—"
        return {
            "agentName": name,
            "purchase": "$12,000", "purchasedPlayers": purchased,
            "totalPlayers": total, "purchasedOfBook": f"{purchased} / {total}",
            "bookPurchaseRate": "7.1%",
            "purchaseShare": purchase_share, "playerShare": "30.8%",
            "focus": {
                "openZd": 2, "locked": 1, "takeABreak": 1, "selfExclusion": 0,
                "otherLocked": 0, "rdOver5k": 0, "birthdays": 0, "declineCount": 3,
            },
        }

    def test_am_shares_and_overview_lengths_match_agents(self) -> None:
        agents = [self._make_agent("Coral"), self._make_agent("Gabriel")]
        am_shares, overview = build_am_shares_and_overview(agents)
        self.assertEqual(len(am_shares), 2)
        self.assertEqual(len(overview), 2)

    def test_am_shares_has_no_focus_keys(self) -> None:
        agents = [self._make_agent("Coral")]
        am_shares, _ = build_am_shares_and_overview(agents)
        self.assertNotIn("openZd", am_shares[0])
        self.assertNotIn("declineCount", am_shares[0])

    def test_overview_includes_focus_keys(self) -> None:
        agents = [self._make_agent("Coral")]
        _, overview = build_am_shares_and_overview(agents)
        self.assertIn("openZd", overview[0])
        self.assertIn("declineCount", overview[0])

    def test_both_have_success_tone(self) -> None:
        agents = [self._make_agent("Lee")]
        am_shares, overview = build_am_shares_and_overview(agents)
        self.assertEqual(am_shares[0]["tone"], "success")
        self.assertEqual(overview[0]["tone"], "success")

    def test_agent_names_preserved(self) -> None:
        agents = [self._make_agent("Rachel")]
        am_shares, overview = build_am_shares_and_overview(agents)
        self.assertEqual(am_shares[0]["agentName"], "Rachel")
        self.assertEqual(overview[0]["agentName"], "Rachel")

    def test_empty_agents_list(self) -> None:
        am_shares, overview = build_am_shares_and_overview([])
        self.assertEqual(am_shares, [])
        self.assertEqual(overview, [])


# ---------------------------------------------------------------------------
# queries._iso safety guard
# ---------------------------------------------------------------------------


class QueriesIsoTests(unittest.TestCase):
    def setUp(self) -> None:
        import queries as am_queries
        self._iso = am_queries._iso

    def test_returns_iso_string(self) -> None:
        self.assertEqual(self._iso(date(2026, 8, 19)), "2026-08-19")

    def test_rejects_string(self) -> None:
        with self.assertRaises(TypeError):
            self._iso("2026-08-19")  # type: ignore[arg-type]

    def test_rejects_none(self) -> None:
        with self.assertRaises(TypeError):
            self._iso(None)  # type: ignore[arg-type]

    def test_rejects_int(self) -> None:
        with self.assertRaises(TypeError):
            self._iso(20260819)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
