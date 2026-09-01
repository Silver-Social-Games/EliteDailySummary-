"""Zendesk ticket draft copy for the AM Brief's First-Time Locked RD and
Birthdays sections.

Review-only, same policy as WoW Gaps (wow_drop_analysis/ticket_draft.py,
ZENDESK_TICKET_RULES.md): agent edits the draft in the canvas modal, copies
it, opens Zendesk, and sends manually. Nothing is auto-created or auto-sent.

Both draft builders are gated by `outreach_lock_gate`, which implements the
elite-core rule "never recommend retention outreach for self-excluded or
locked accounts" — checked here using uam_accounts.locked / lock_reason
before a draft is offered, same signal as the AM Brief's own Locked/Take A
Break section (see lock_bucket() in generate_am_daily_dashboard.py, which
this mirrors).
"""

from __future__ import annotations

from elite_lib import zendesk_new_ticket_url


def _first_name(name: str) -> str:
    name = (name or "").strip()
    if not name or name.lower() == "n/a":
        return "there"
    return name.split()[0]


def outreach_lock_gate(
    locked: bool, lock_reason: str = "", lock_reason_comment: str = ""
) -> tuple[bool, str]:
    """Returns (disabled, label). Mirrors lock_bucket()'s classification so
    the disabled reason shown to the agent matches the wording used in the
    Locked/Take A Break section."""
    if not locked:
        return False, ""
    reason = (lock_reason or "").strip()
    comment = (lock_reason_comment or "").strip()
    low = f"{reason} {comment}".lower()
    if reason == "Exclusion" or "self_exclud" in low:
        return True, "Locked — Self-exclusion"
    if "take a break" in low or reason:
        return True, f"Locked — {reason or 'Take a break'}"
    return True, "Locked — Other"


def _sanitize_ticket_copy(text: str) -> str:
    return text.replace("—", ", ").replace("  ", " ").strip()


def build_first_time_rd_ticket_draft(
    row: dict,
    *,
    locked: bool = False,
    lock_reason: str = "",
    lock_reason_comment: str = "",
    zendesk_user_id: object = None,
) -> dict:
    """Draft for a player's first-ever withdraw request currently locked for
    review. Same shape/keys as wow_drop_analysis.ticket_draft's output so it
    slots into the existing TicketDraftCell / TicketDraftModal."""
    disabled, lock_label = outreach_lock_gate(locked, lock_reason, lock_reason_comment)
    enabled = not disabled
    first_name = _first_name(row.get("name") or "")
    subject = _sanitize_ticket_copy("Your Redemption Is Being Reviewed") if enabled else ""
    body = ""
    if enabled:
        body = _sanitize_ticket_copy(
            f"Hi {first_name},\n\n"
            "Congratulations on your first redemption request! 🎉\n\n"
            "I wanted to personally let you know it's currently under review, this is a "
            "standard check we run for first-time redemptions, and I'm keeping a close eye "
            "on it for you.\n\n"
            "I'll follow up as soon as I have an update, thanks for your patience in the "
            "meantime.\n\n"
            "Best regards,"
        )
    return {
        "ticketEnabled": enabled,
        "ticketSubject": subject,
        "ticketBody": body,
        "ticketDisabledReason": lock_label,
        "zendeskUrl": zendesk_new_ticket_url(zendesk_user_id) if enabled else "",
    }


def build_anniversary_ticket_draft(
    row: dict,
    *,
    locked: bool = False,
    lock_reason: str = "",
    lock_reason_comment: str = "",
    zendesk_user_id: object = None,
) -> dict:
    """Draft for a player reaching their one-month managed anniversary. Same
    shape/keys as wow_drop_analysis.ticket_draft's output so it slots into the
    existing TicketDraftCell / TicketDraftModal."""
    disabled, lock_label = outreach_lock_gate(locked, lock_reason, lock_reason_comment)
    enabled = not disabled
    first_name = _first_name(row.get("name") or "")
    subject = _sanitize_ticket_copy("Your Elite Monthiversary 🎁") if enabled else ""
    body = ""
    if enabled:
        body = _sanitize_ticket_copy(
            f"Hi {first_name},\n\n"
            "A whole month with Elite already, and I'm thrilled to have you! 🎉\n\n"
            "To celebrate, I've added YYY GC & XXX SC to your account, it's all yours "
            "to enjoy.\n\n"
            "Good luck, and here's to many more wins together!\n\n"
            "The Elite Team"
        )
    return {
        "ticketEnabled": enabled,
        "ticketSubject": subject,
        "ticketBody": body,
        "ticketDisabledReason": lock_label,
        "zendeskUrl": zendesk_new_ticket_url(zendesk_user_id) if enabled else "",
    }


def build_birthday_gift_ticket_draft(
    row: dict,
    *,
    locked: bool = False,
    lock_reason: str = "",
    lock_reason_comment: str = "",
    zendesk_user_id: object = None,
) -> dict:
    """Draft inviting a gift-eligible Elite player (birthday this month) to pick
    their birthday gift. Eligibility (birthday month + hold + 30-day spend) is
    decided upstream; this is the outreach copy. gift_month (report month name,
    which is also the player's birthday month here) fills the greeting so the
    wording stays current. Same shape/keys as wow_drop_analysis.ticket_draft's
    output so it slots into the existing TicketDraftCell / TicketDraftModal."""
    disabled, lock_label = outreach_lock_gate(locked, lock_reason, lock_reason_comment)
    enabled = not disabled
    first_name = _first_name(row.get("name") or "")
    month = (row.get("gift_month") or "").strip() or "this month"
    subject = _sanitize_ticket_copy("A Birthday Treat Just for You 🎁") if enabled else ""
    body = ""
    if enabled:
        body = _sanitize_ticket_copy(
            f"Dear {first_name},\n\n"
            "Happy Birthday Month!\n\n"
            f"Everyone at Jackpota joins me in wishing you a wonderful {month}!\n"
            "As one of our valued Elite players, I'd love to help make your birthday "
            "month even more special with a gift just for you.\n\n"
            "Before I arrange everything, could you please confirm that your mailing "
            "address is up to date?\n"
            "Then, let me know which of these you'd enjoy most:\n\n"
            "- Gourmet Gift Box\n"
            "- Restaurant Voucher\n"
            "- Amazon Gift Card\n"
            "- Gift Card to your favorite store\n\n"
            "I'll do my very best to accommodate your preference, subject to "
            "availability.\n"
            "I look forward to hearing from you and celebrating with you!\n\n"
            "Warm regards,"
        )
    return {
        "ticketEnabled": enabled,
        "ticketSubject": subject,
        "ticketBody": body,
        "ticketDisabledReason": lock_label,
        "zendeskUrl": zendesk_new_ticket_url(zendesk_user_id) if enabled else "",
    }


def build_birthday_ticket_draft(
    row: dict,
    *,
    locked: bool = False,
    lock_reason: str = "",
    lock_reason_comment: str = "",
    zendesk_user_id: object = None,
) -> dict:
    """Draft for a birthday check-in within the trailing BIRTHDAYS_LOOKBACK_DAYS
    window. Same shape/keys as wow_drop_analysis.ticket_draft's output."""
    disabled, lock_label = outreach_lock_gate(locked, lock_reason, lock_reason_comment)
    enabled = not disabled
    first_name = _first_name(row.get("name") or "")
    subject = _sanitize_ticket_copy("Happy Birthday!") if enabled else ""
    body = ""
    if enabled:
        body = _sanitize_ticket_copy(
            f"Hi {first_name},\n\n"
            "Happy birthday! 🎂🎉 Wishing you a fantastic day.\n\n"
            "Thank you for being such a valued part of the Jackpota family, here's to an "
            "even better year ahead.\n\n"
            "Let me know if there's anything I can do for you.\n\n"
            "Best regards,"
        )
    return {
        "ticketEnabled": enabled,
        "ticketSubject": subject,
        "ticketBody": body,
        "ticketDisabledReason": lock_label,
        "zendeskUrl": zendesk_new_ticket_url(zendesk_user_id) if enabled else "",
    }
