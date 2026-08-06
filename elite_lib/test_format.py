"""Unit tests for shared formatting helpers."""

from __future__ import annotations

import unittest
from datetime import date

from elite_lib.format import (
    fmt_money,
    fmt_reason,
    format_aid_markdown,
    format_ticket_markdown,
    looker_account_portal_url,
    weekday_label,
    zendesk_new_ticket_url,
    zendesk_ticket_url,
)


class FmtMoneyTests(unittest.TestCase):
    def test_none_is_dash(self) -> None:
        self.assertEqual(fmt_money(None), "-")

    def test_rounds_and_adds_thousands_separator(self) -> None:
        self.assertEqual(fmt_money(1234.6), "$1,235")

    def test_zero(self) -> None:
        self.assertEqual(fmt_money(0), "$0")


class FmtReasonTests(unittest.TestCase):
    def test_known_code(self) -> None:
        self.assertEqual(fmt_reason("self_exclusion"), "Self-exclusion")

    def test_unknown_code_falls_back_to_title_ish(self) -> None:
        self.assertEqual(fmt_reason("some_new_code"), "some new code")


class WeekdayLabelTests(unittest.TestCase):
    def test_returns_full_weekday_name(self) -> None:
        # 2026-07-07 is a Tuesday.
        self.assertEqual(weekday_label(date(2026, 7, 7)), "Tuesday")


class LookerUrlTests(unittest.TestCase):
    def test_blank_aid_returns_empty(self) -> None:
        self.assertEqual(looker_account_portal_url(""), "")
        self.assertEqual(looker_account_portal_url(None), "")

    def test_builds_dashboard_link(self) -> None:
        url = looker_account_portal_url(12345)
        self.assertIn("12345", url)
        self.assertIn("lookerpatrianna.cloud.looker.com", url)

    def test_format_aid_markdown_wraps_link(self) -> None:
        md = format_aid_markdown(12345)
        self.assertEqual(md, f"[12345]({looker_account_portal_url(12345)})")

    def test_format_aid_markdown_blank(self) -> None:
        self.assertEqual(format_aid_markdown(""), "")


class ZendeskUrlTests(unittest.TestCase):
    def test_new_ticket_without_requester(self) -> None:
        url = zendesk_new_ticket_url()
        self.assertTrue(url.endswith("/agent/tickets/new/1"))

    def test_new_ticket_with_numeric_requester(self) -> None:
        url = zendesk_new_ticket_url(42)
        self.assertTrue(url.endswith("requester_id=42"))

    def test_new_ticket_ignores_non_numeric_requester(self) -> None:
        url = zendesk_new_ticket_url("not-a-number")
        self.assertNotIn("requester_id", url)

    def test_existing_ticket_url(self) -> None:
        url = zendesk_ticket_url(587597)
        self.assertTrue(url.endswith("/agent/tickets/587597"))

    def test_existing_ticket_blank_id(self) -> None:
        self.assertEqual(zendesk_ticket_url(""), "")


class TicketMarkdownTests(unittest.TestCase):
    def test_disabled_ticket_shows_dash(self) -> None:
        self.assertEqual(format_ticket_markdown({"ticketEnabled": False}), "—")

    def test_enabled_ticket_shows_draft_link(self) -> None:
        md = format_ticket_markdown(
            {
                "ticketEnabled": True,
                "zendeskUrl": "https://jackpotahelp.zendesk.com/agent/tickets/new/1",
                "ticketSubject": "Checking In On You",
            }
        )
        self.assertIn("[Draft]", md)
        self.assertIn("Checking In On You", md)


if __name__ == "__main__":
    unittest.main()
