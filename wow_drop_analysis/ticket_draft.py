"""Zendesk ticket draft copy for agent review.

Split out of wow_drop_reason.py: builds ticket subject/body text from an
already-classified row. Never sends anything - drafts are for agent
review only. See wow_drop_analysis/ZENDESK_TICKET_RULES.md.
"""

from __future__ import annotations

from datetime import date

from elite_lib import zendesk_new_ticket_url


def _first_name(name: str) -> str:
    name = (name or "").strip()
    if not name or name.lower() == "n/a":
        return "there"
    return name.split()[0]


def _ticket_outreach_disabled(code: str, recommendation: str) -> bool:
    if code in {"self_exclusion", "red_flag", "account_locked", "payment_failed"}:
        return True
    rec = (recommendation or "").strip().lower()
    if rec in {"no action", "no outreach"}:
        return True
    if "no purchase push" in rec and code != "big_win_day_before":
        return True
    return False


def _sanitize_ticket_copy(text: str) -> str:
    return text.replace("\u2014", ", ").replace("  ", " ").strip()


TICKET_SIGN_OFF = "\n\nBest regards,"
TICKET_SIGN_OFF_PUSH = "\n\nHave a good one,"

TICKET_SUBJECTS = {
    "CheckIn": "Checking In On You 👑",
    "Redemption": "Redemption Status 🔄",
    "LightTouch": "Still Buzzing About Your Run 🎉",
    "PushPurchase": "You've Been Chosen 🎁",
}


def _normalize_ticket_recommendation(recommendation: str) -> str:
    return (recommendation or "").strip().lower()


def _is_push_purchase_recommendation(recommendation: str) -> bool:
    rec = _normalize_ticket_recommendation(recommendation)
    return rec == "push purchase" or rec.endswith("push purchase")


def _ticket_family(code: str, recommendation: str = "") -> str:
    if code == "redemption_in_progress":
        return "Redemption"
    if code == "big_win_day_before":
        return "LightTouch"
    if _is_push_purchase_recommendation(recommendation):
        return "PushPurchase"
    return "CheckIn"


def _build_ticket_subject(code: str, recommendation: str = "") -> str:
    return TICKET_SUBJECTS.get(_ticket_family(code, recommendation), TICKET_SUBJECTS["CheckIn"])


def _build_ticket_body(code: str, *, first_name: str, recommendation: str = "") -> str:
    """Player-facing message. See ZENDESK_TICKET_RULES.md."""
    family = _ticket_family(code, recommendation)
    bodies = {
        "CheckIn": (
            f"Hi {first_name},\n\n"
            "It's been a little while, and I just wanted to check in on how everything's going? 💬\n"
            "I hope you've been doing well and still enjoying the fun at Jackpota!\n\n"
            "If you ever need anything: game recommendations, slot tips or just chat, I am here for you.\n\n"
            "I'd love to hear from you and see how I can make your experience even better."
        ),
        "Redemption": (
            f"Hi {first_name},\n\n"
            "Congratulations on your win! 🎉\n\n"
            "I'm personally keeping an eye on your redemption, "
            "and I'll update you as soon as there's news.\n\n"
            "In the meantime, drop me a message if you need anything else."
        ),
        "LightTouch": (
            f"Hi {first_name},\n\n"
            "Hope you've been enjoying your time on Jackpota. Congratulations on your recent run!\n"
            "I just wanted to check in and see how everything is going.\n\n"
            "Let me know if you need anything to improve your experience."
        ),
        "PushPurchase": (
            f"Hey {first_name},\n\n"
            "Noticed things were quiet on Jackpota lately, and I wanted to check in personally 👋\n\n"
            "I've activated an exclusive offer for you: just grab the {GC_package_name} and reply once you do, "
            "I'll personally add a little extra on top 🎁\n\n"
            "Sometimes one spin is all you need to win BIG."
        ),
    }
    sign_off = TICKET_SIGN_OFF_PUSH if family == "PushPurchase" else TICKET_SIGN_OFF
    return bodies.get(family, bodies["CheckIn"]) + sign_off


def build_zendesk_ticket_draft(
    row: dict,
    enrich: dict,
    *,
    report_date: date | None = None,
) -> dict:
    """Zendesk ticket draft for agent review only — never auto-sent. See ZENDESK_TICKET_RULES.md."""
    from elite_lib import zendesk_new_ticket_url

    code = row.get("reason_code") or ""
    recommendation = row.get("recommendation") or row.get("action") or ""
    name = row.get("name") or enrich.get("name") or "n/a"
    first_name = _first_name(name)
    requester_id = enrich.get("zendesk_user_id")

    enabled = not _ticket_outreach_disabled(code, recommendation)
    subject = _sanitize_ticket_copy(_build_ticket_subject(code, recommendation)) if enabled else ""
    body = _sanitize_ticket_copy(_build_ticket_body(code, first_name=first_name, recommendation=recommendation)) if enabled else ""

    return {
        "ticketEnabled": enabled,
        "ticketSubject": subject,
        "ticketBody": body,
        "zendeskUrl": zendesk_new_ticket_url(requester_id) if enabled else "",
        "zendeskRequesterId": str(requester_id) if requester_id else "",
    }
