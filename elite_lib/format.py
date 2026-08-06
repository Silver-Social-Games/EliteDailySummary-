"""Shared money/date/URL formatting for Elite reports.

Moved out of ``daily_summary.generate_daily_elite_summary`` so that
``wow_drop_analysis`` (and every other initiative) does not need to import
the daily summary module just to format a dollar amount or an AID link.
"""

from __future__ import annotations

import os
from datetime import date

# S-Jackpota Account Portal (Looker dashboard 5207). Override via LOOKER_ACCOUNT_PORTAL_URL.
DEFAULT_LOOKER_ACCOUNT_PORTAL_URL = (
    "https://lookerpatrianna.cloud.looker.com/dashboards/5207?Account+ID+={aid}"
)
DEFAULT_ZENDESK_AGENT_BASE = "https://jackpotahelp.zendesk.com"


def fmt_money(v) -> str:
    if v is None:
        return "-"
    return f"${round(float(v)):,}"


REASON_LABELS = {
    "self_exclusion": "Self-exclusion",
    "redemption_in_progress": "Redemption in progress",
    "big_win_last_7d": "Big win (7d)",
    "big_loss_last_7d": "Big loss (7d)",
    "same_weekday_skip": "Same weekday skip",
    "account_locked": "Account locked",
    "red_flag": "Red flag",
    "general_spend_softening": "General spend softening",
}


def fmt_reason(code: str) -> str:
    return REASON_LABELS.get(code, code.replace("_", " "))


def weekday_label(d: date) -> str:
    return d.strftime("%A")


def looker_account_portal_url(aid: object) -> str:
    """Looker Jackpota Account Portal for an AID. Template uses {aid} or {account_id}."""
    aid_s = str(aid or "").strip()
    if not aid_s:
        return ""
    template = os.environ.get("LOOKER_ACCOUNT_PORTAL_URL", DEFAULT_LOOKER_ACCOUNT_PORTAL_URL)
    return template.format(aid=aid_s, account_id=aid_s)


def format_aid_markdown(aid: object) -> str:
    aid_s = str(aid or "").strip()
    if not aid_s:
        return ""
    url = looker_account_portal_url(aid_s)
    return f"[{aid_s}]({url})" if url else aid_s


def zendesk_new_ticket_url(requester_id: object = None) -> str:
    """Zendesk Agent Workspace new ticket. Pre-selects requester when id is known."""
    base = os.environ.get("ZENDESK_AGENT_BASE_URL", DEFAULT_ZENDESK_AGENT_BASE).rstrip("/")
    url = f"{base}/agent/tickets/new/1"
    rid = str(requester_id or "").strip()
    if rid and rid.isdigit():
        return f"{url}?requester_id={rid}"
    return url


def zendesk_ticket_url(ticket_id: object) -> str:
    """Open an existing Zendesk ticket in Agent Workspace."""
    tid = str(ticket_id or "").strip()
    if not tid:
        return ""
    base = os.environ.get("ZENDESK_AGENT_BASE_URL", DEFAULT_ZENDESK_AGENT_BASE).rstrip("/")
    return f"{base}/agent/tickets/{tid}"


def format_ticket_markdown(draft: dict) -> str:
    if not draft.get("ticketEnabled"):
        return "—"
    url = draft.get("zendeskUrl") or ""
    subject = (draft.get("ticketSubject") or "").replace("|", "/")
    preview = subject if len(subject) <= 48 else subject[:47].rstrip() + "…"
    if url:
        return f"[Draft]({url}) · _{preview}_"
    return f"_{preview}_"
