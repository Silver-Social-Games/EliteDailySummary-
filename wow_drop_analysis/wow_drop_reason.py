"""Shared WoW drop reason classification for daily summary and handoffs.

Classification logic (first match wins):
  1. Self-exclusion     — locked + lock_reason Exclusion
  2. Account locked     — locked, other reason
  3. Redemption         — open withdraw (pre_authorized or locked)
  4. Payment failed     — failed orders on report day + $0 purchased that day
  5. Big win (day before) — day-before NGR <= -$5k (player up)
  6. Churn / lapsed     — $0 purchased in rolling 7d
  7. Same-weekday skip  — $0 report day but purchased other days in 7d window
  8. Red flag           — elite_users.red_flag
  9. Spend softening    — still purchased but less than prior same weekday

Urgency (agent queue):
  Today  — contact today (redeem, payment, lock, red flag)
  48h    — reach out within 2 days (churn, spend down, 2-day purchase gap)
  Watch  — monitor only; no purchase push
  None   — do not contact (self-exclusion)

Inactive / suspicious player — Zendesk drill-down (manual; not fully automated):
  When a player is offline, churned, restricted, redeem-stuck, skipped purchase days, or Reason
  feels incomplete, always check Zendesk beyond the auto Reason subjects (Last 14D):
    0. Same-weekday skip — $0 on report day but purchased other days in 7D: confirm rhythm skip
       vs account block before any purchase push; check Zendesk if redeem workflow active,
       restricted, no play since last purchase, or POA/KYC tickets in 14D
    1. uam_accounts — locked, lock_reason, lock_reason_comment, status / redeem_status
    2. zendesk.ticket + ticket_comment — filter AID via requester; scan subjects + description;
       ticket_comment for POA resolution (valid POA received, restrictions lifted — e.g. TID587597)
    3. Priority tags — kyc_follow_up, verification, ops_escalation_address_query, suspend,
       unrestrict, restricted_states/country, esc_to_ops
    4. Missing unlock docs — POA declined, utility bill, bank statement, ID/KYC; ticket body
       often states what was rejected and what is still awaited (e.g. Richard AID 57064501:
       POA declined · valid recent utility bill / acceptable POA still awaited)
    5. Recommendation — escalate Compliance/Ops with the specific missing item; no purchase
       ask until account/redeem path is cleared
"""
from __future__ import annotations

import re
from datetime import date, timedelta

from elite_lib import HEAVY_QUERY_SCAN_CAP_BYTES, fmt_money, fmt_reason, run_query

from wow_drop_analysis.taxonomy import (
    AGENT_TAG_LABELS,
    CLASSIFICATION_RULES,
    DAY_DROP_LABELS,
    M_7D_PURCHASE,
    M_ACCOUNT_RESTRICTED,
    M_ACCOUNT_RESTRICTED_LEGAL,
    M_ACCOUNT_SUSPENDED,
    M_FAILED_CHECKOUT,
    M_LAST_PLAY_14D,
    M_LAST_PURCHASE_30D,
    M_NONE_IN_7D,
    M_NO_PLAY_7D,
    M_NO_PLAY_OR_PURCHASE_SINCE,
    M_NO_PURCHASES_7D,
    M_NO_REPORT_DAY_PLAY,
    M_PENDING_REDEEM,
    M_REPORT_DAY,
    M_ZENDESK_14D,
    MAX_ZD_SUBJECT,
    PENDING_REDEEM_STATUSES,
    REASON_EMPHASIS_PREFIXES,
    REASON_SEP,
    TOP_SAME_DAY_LIMIT,
    URGENCY_BY_CODE,
    URGENCY_OPTIONS,
    URGENCY_SORT,
)


def _truncate_text(text: str, limit: int) -> str:
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _compact_join(parts: list[str]) -> str:
    seen: set[str] = set()
    unique: list[str] = []
    for p in parts:
        text = (p or "").strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(text)
    return REASON_SEP.join(unique)


def split_reason_parts(reason: str) -> list[str]:
    if not reason:
        return []
    if REASON_SEP in reason:
        return [p.strip() for p in reason.split(REASON_SEP) if p.strip()]
    return [p.strip() for p in reason.split(" · ") if p.strip()]


def _reason_part_emoji(part: str) -> str:
    """Leading emoji for high-signal reason tags (first segment or emphasis tags only)."""
    pl = part.lower()
    if part.startswith("Red flag"):
        return "🚩 "
    if part.startswith("Redemption Blocked"):
        return "🚫 "
    if part.startswith("Redemption in progress"):
        return "⏳ "
    if part.startswith("Account locked") or "Suspended" in part:
        return "🔒 "
    if part.startswith("Needs Recent Acceptable POA") or "poa" in pl:
        return "📄 "
    if part.startswith("Needs KYC") or "verification document" in pl:
        return "📋 "
    if part.startswith("RD $") or part.startswith("Pending RD"):
        return "💸 "
    if part.startswith("Same weekday skip"):
        return "📅 "
    if part.startswith("Payment failed"):
        return "❌ "
    if part.startswith("No Purchases"):
        return "⚠️ "
    if part.startswith("Played Today"):
        return "🎰 "
    if part.startswith("Spend Softening"):
        return "📉 "
    if part.startswith("Redeem Status"):
        return "📋 "
    if part.startswith("Take a break"):
        return "⏰ "
    return ""


def _action_head_emoji(head: str) -> str:
    hl = head.lower()
    if head.startswith("Escalate Ops"):
        return "➡️ "
    if head.startswith("Escalate Compliance"):
        return "⚖️ "
    if head.startswith("Push purchase"):
        return "💰 "
    if head.startswith("Fix payment method"):
        return "💳 "
    if head.startswith("Remove restriction"):
        return "🔓 "
    if head.startswith("Send to Ops"):
        return "🔧 "
    if head.startswith("Soft check-in"):
        return "💬 "
    if head.startswith("Agent call"):
        return "📞 "
    if head.startswith("No action"):
        return "✓ "
    if "no outreach" in hl or "no purchase push" in hl:
        return "🛑 "
    return ""


def format_reason_markdown(reason: str) -> str:
    """Bold key reason segments for markdown tables; emoji on high-signal tags."""
    parts = split_reason_parts(reason)
    if not parts:
        return reason or ""
    styled: list[str] = []
    for i, part in enumerate(parts):
        emphasize = i == 0 or part.startswith(REASON_EMPHASIS_PREFIXES)
        emoji = _reason_part_emoji(part) if emphasize else ""
        text = f"{emoji}{part}"
        styled.append(f"**{text}**" if emphasize else part)
    return REASON_SEP.join(styled)


def _red_flag_tags(enrich: dict) -> list[str]:
    """Specific Elite risk flags shown when red_flag is the primary reason."""
    fields = [
        ("red_flag_chargeback", "Chargeback risk"),
        ("red_flag_refunds", "Refund risk"),
        ("red_flag_aml", "AML review"),
        ("red_flag_redeemed_to_purchase", "High redeem-to-purchase"),
        ("red_flag_locked", "Lock risk"),
        ("red_flag_state", "State / geo risk"),
    ]
    tags = [label for field, label in fields if int(enrich.get(field) or 0) == 1]
    return tags or ["Risk review"]


def format_action_markdown(action: str) -> str:
    """Bold the leading action verb phrase; emoji on action type."""
    action = (action or "").strip()
    if not action:
        return ""
    if " · " in action:
        head, tail = action.split(" · ", 1)
        return f"**{_action_head_emoji(head)}{head}** · {tail}"
    return f"**{_action_head_emoji(action)}{action}**"


def format_table_urgency(urgency: str) -> str:
    if urgency == "Today":
        return "⚡ **Today**"
    if urgency == "48h":
        return "**48h**"
    return urgency or ""


def format_table_money(
    amount,
    *,
    emphasize_zero: bool = False,
    emphasize_high: bool = False,
    high_threshold: float = 2000.0,
) -> str:
    val = fmt_money(amount)
    amt = float(amount or 0)
    if emphasize_zero and amt <= 0:
        return f"**{val}**"
    if emphasize_high and amt >= high_threshold:
        return f"**{val}**"
    return val


def format_table_purchase_7d(text: str) -> str:
    label = (text or M_NONE_IN_7D).strip()
    if label == M_NONE_IN_7D:
        return f"**{label}**"
    return label


def _parse_zd_line(line: str) -> tuple[str, str]:
    line = (line or "").strip()
    if not line:
        return "", ""
    match = re.match(r'^(\d+\s+\w+)\s+"([^"]*)"', line)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return line, ""


def _short_zd_subject(subject: str) -> str:
    subject = " ".join((subject or "").split())
    if not subject:
        return ""
    if _is_promo_zd_subject(subject):
        return ""
    sl = subject.lower()
    keyword_map = (
        ("unrestrict", "Unrestrict"),
        ("account suspended", "Suspended"),
        ("suspend", "Suspended"),
        ("legal", "Legal"),
        ("restrict", "Restricted"),
        ("redemption status", "Redeem Status"),
        ("charge", "Disputed Charge"),
        ("money not given", "Funds Issue"),
        ("free sc", ""),
        ("ready for extra", ""),
        ("world cup raffle", ""),
    )
    for key, label in keyword_map:
        if key in sl:
            return label
    return _truncate_text(subject, MAX_ZD_SUBJECT)


_PROMO_ZD_HINTS = (
    "reward inside",
    "golden kick",
    "kick off",
    "celebrating you",
    "celebrations cont",
    "boom!",
    "you've been chosen",
    "you have been chosen",
    "exclusive offer",
    "free spin",
    "abandoned call",
    "player award",
    "promotion",
    "🌟",
    "🎁",
    "🎇",
    "💛",
    "🖤",
)


def _is_promo_zd_subject(subject: str) -> bool:
    sl = (subject or "").lower()
    return any(h in sl for h in _PROMO_ZD_HINTS)


def _last_purchase_on_prior_weekday(enrich: dict, report_date: date | None) -> bool:
    """True when last purchase date is exactly the prior same weekday (report_date - 7)."""
    if not report_date:
        return False
    last_date = _parse_enrich_date(enrich.get("last_purchase_date"))
    if not last_date:
        return False
    return last_date == report_date - timedelta(days=7)


def _restriction_tag(enrich: dict) -> str:
    """One-line restriction label for compact Reason."""
    lock_reason = (enrich.get("lock_reason") or "").strip()
    lock_comment = (enrich.get("lock_reason_comment") or "").strip()
    combined = f"{lock_reason} {lock_comment}".lower()

    if "legal" in combined:
        return "Legal Restriction"

    rz = (enrich.get("restriction_zendesk") or "").strip()
    if rz:
        dt, subj = _parse_zd_line(rz)
        short = _short_zd_subject(subj)
        if "legal" in subj.lower():
            return "Legal Restriction"
        if short == "Suspended":
            return f"Suspended {dt}"
        if short in ("Restricted", "Unrestrict"):
            return f"{short} {dt}"
        if short:
            return f"{short} {dt}"

    if bool(enrich.get("account_locked")) and lock_reason:
        if lock_reason.lower() == "exclusion":
            return "Self-Exclusion"
        if "legal" in lock_reason.lower():
            return "Legal Restriction"
        return f"Locked ({lock_reason})"

    return ""


def _parse_enrich_date(value) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not hasattr(value, "hour"):
        return value
    if hasattr(value, "date"):
        return value.date()
    s = str(value).strip()
    if not s:
        return None
    return date.fromisoformat(s[:10])


def _take_a_break_days(lock_reason: str) -> int | None:
    m = re.search(r"take a break\s*(\d+)", (lock_reason or "").lower())
    return int(m.group(1)) if m else None


def _parse_break_days_from_text(text: str) -> int | None:
    """Parse N from '7-day time-out' or 'take a break 7' in Zendesk text."""
    low = (text or "").lower()
    if days := _take_a_break_days(low):
        return days
    m = re.search(r"(\d+)[\s-]*day\s*time[\s-]*out", low)
    return int(m.group(1)) if m else None


def _timed_lock_context(enrich: dict) -> tuple[int | None, date | None]:
    """Days and lock-start date for Take a break N (account lock or Zendesk timeout)."""
    lock_reason = (enrich.get("lock_reason") or "").strip()
    lock_comment = (enrich.get("lock_reason_comment") or "").strip()
    days = _take_a_break_days(lock_reason) or _take_a_break_days(lock_comment)
    lock_d = _parse_enrich_date(enrich.get("locked_at"))

    if days is None:
        zd_text = " ".join(
            [
                enrich.get("zendesk_purchase_block") or "",
                enrich.get("zendesk_block_subject") or "",
            ]
        )
        days = _parse_break_days_from_text(zd_text)

    if days and not lock_d:
        ticket_d = _parse_enrich_date(enrich.get("zendesk_block_created_at"))
        if ticket_d:
            # Timeout ticket usually precedes lock apply by ~2 calendar days
            lock_d = ticket_d + timedelta(days=2)

    return days, lock_d


def _lock_unlock_date(enrich: dict) -> date | None:
    """Calendar date when a timed lock (Take a break N) ends and unlock is due."""
    days, lock_d = _timed_lock_context(enrich)
    if days is None or not lock_d:
        return None
    return lock_d + timedelta(days=days)


def _lock_eval_date(report_date: date | None) -> date:
    """As-of date for timed locks — use report date so historical runs keep days-left."""
    if report_date:
        return report_date
    return date.today()


def _lock_period_expired(enrich: dict, report_date: date | None) -> bool:
    """True when a timed lock (e.g. Take a break 7) has elapsed by eval date."""
    unlock_d = _lock_unlock_date(enrich)
    if not unlock_d:
        return False
    return _lock_eval_date(report_date) >= unlock_d


def _timed_lock_phrase(enrich: dict, report_date: date | None) -> str:
    """Single line for Take a break N — ended (remove restriction) or days remaining."""
    days, _ = _timed_lock_context(enrich)
    if days is None:
        return ""
    eval_d = _lock_eval_date(report_date)
    if _lock_period_expired(enrich, report_date):
        return f"Take a break {days} days ended — remove restriction"
    unlock_d = _lock_unlock_date(enrich)
    if unlock_d:
        remaining = (unlock_d - eval_d).days
        if remaining > 0:
            return (
                f"Take a break {days} days "
                f"({remaining}d left · unlock {fmt_short_date(unlock_d)})"
            )
        if remaining == 0:
            return f"Take a break {days} days · unlock today — remove restriction"
    return f"Take a break {days} days"


def _zendesk_adds_lock_context(
    zd: str, lock_reason: str, *, timed_break_days: int | None = None
) -> bool:
    """Skip Zendesk tags that repeat what the lock reason already states."""
    if not zd:
        return False
    zd_low = zd.lower()
    lock_low = (lock_reason or "").lower()
    days = _take_a_break_days(lock_reason) or timed_break_days
    if days:
        if "time" in zd_low and "out" in zd_low:
            return False
        if "take a break" in zd_low:
            return False
    if lock_low and (lock_low in zd_low or zd_low in lock_low):
        return False
    return True


def _account_lock_tags(enrich: dict, report_date: date | None) -> list[str]:
    """Tags after Account locked — one lock phrase, no duplicate purchase/zendesk noise."""
    lock_reason = (enrich.get("lock_reason") or "").strip()
    timed_days, _ = _timed_lock_context(enrich)
    tags: list[str] = []

    if phrase := _timed_lock_phrase(enrich, report_date):
        tags.append(phrase)
    elif lock_reason.lower() == "exclusion":
        tags.append("Self-Exclusion")
    elif "legal" in lock_reason.lower():
        tags.append("Legal Restriction")
    elif lock_reason:
        tags.append(lock_reason)
    else:
        tags.append("Ops lock")

    if zd := _zendesk_followup_tag(enrich):
        if _zendesk_adds_lock_context(zd, lock_reason, timed_break_days=timed_days):
            tags.append(zd)
    return tags


def _has_pending_redeem(enrich: dict) -> bool:
    """True when open withdraw requests exist (pre_authorized or locked)."""
    return float(enrich.get("pending_redeem") or 0) > 0


def _redeem_status_tag(enrich: dict) -> str:
    """Human-readable redeem workflow status — only when a real pending redeem exists."""
    if not _has_pending_redeem(enrich):
        return ""
    workflow = (enrich.get("redeem_status") or "").strip()
    if workflow and workflow not in ("default", "closed"):
        raw = workflow
    else:
        return "Redeem Status Pre-Authorized"
    label = raw.removeprefix("bw_").replace("_", " ")
    return f"Redeem Status {' '.join(w.capitalize() for w in label.split())}"


def _build_account_lock_recommendation(enrich: dict, report_date: date | None = None) -> str:
    days, _ = _timed_lock_context(enrich)
    if _lock_period_expired(enrich, report_date):
        if days:
            return sanitize_md(f"Remove restriction · Take a break {days} ended")
        return sanitize_md("Remove restriction")
    if days:
        phrase = _timed_lock_phrase(enrich, report_date)
        if phrase:
            return sanitize_md(f"Send to Ops · {phrase}")
    lock_reason = (enrich.get("lock_reason") or "lock").strip()
    return sanitize_md(f"Send to Ops · {lock_reason}")


def _zendesk_followup_tag(enrich: dict) -> str:
    """Up to 2 short Zendesk tags; skips restriction ticket and promo noise.

    Auto summary uses subjects only. When inactive/restricted/redeem-stuck looks suspicious,
    manually read zendesk.ticket description + tags for missing docs (POA, KYC, suspend).
    See module docstring: Inactive / suspicious player — Zendesk drill-down.
    """
    rz_line = (enrich.get("restriction_zendesk") or "").strip()
    tags: list[str] = []
    for chunk in (format_zendesk_recent(enrich) or "").split(","):
        chunk = chunk.strip()
        if not chunk or chunk == rz_line:
            continue
        dt, subj = _parse_zd_line(chunk)
        short = _short_zd_subject(subj)
        if not short:
            continue
        if short in ("Unrestrict", "Suspended", "Restricted", "Legal"):
            tag = f"{short} {dt}"
        else:
            tag = f"{dt} {short}"
        if tag not in tags:
            tags.append(tag)
        if len(tags) >= 2:
            break
    return ", ".join(tags)


_POA_STILL_AWAITED_PHRASES = (
    "invalid poa",
    "poa declined",
    "valid alternative recent poa still awaited",
    "not a utility bill",
    "poa outstanding",
    "poa is outstanding",
)

_QUOTED_EMAIL_REPLY_RE = re.compile(
    r"(sent from yahoo mail|on (?:monday|tuesday|wednesday|thursday|friday|saturday|sunday).+wrote:)",
    re.IGNORECASE,
)


def _zendesk_poa_resolved(enrich: dict) -> bool:
    """True when Zendesk comments confirm valid POA received and restrictions cleared."""
    if not (enrich.get("zendesk_poa_resolved") or "").strip():
        return False
    resolved_at = _parse_enrich_date(enrich.get("zendesk_poa_resolved_at"))
    doc_at = _parse_enrich_date(enrich.get("zendesk_missing_doc_at"))
    if resolved_at and doc_at and resolved_at < doc_at:
        return False
    return True


def _poa_doc_still_required(raw: str) -> bool:
    """False when POA mention is a resolved case or a quoted verification email reply."""
    low = raw.lower()
    if any(p in low for p in _POA_STILL_AWAITED_PHRASES):
        return True

    if re.search(r"what type of document.*do you need", low):
        return False

    if match := _QUOTED_EMAIL_REPLY_RE.search(low):
        player_part = low[: match.start()]
        if "poa" not in player_part and "proof of address" not in player_part:
            return False

    return "poa" in low or "proof of address" in low.replace("_", " ")


def _zendesk_missing_doc_tag(enrich: dict) -> str:
    """Missing unlock document from Zendesk ticket description (POA, KYC, etc.)."""
    if _zendesk_poa_resolved(enrich):
        return ""
    raw = (enrich.get("zendesk_missing_doc") or "").strip()
    if not raw:
        return ""
    low = raw.lower()
    if "poa" in low or "proof of address" in low.replace("_", " "):
        if not _poa_doc_still_required(raw):
            return ""
    if (
        "invalid poa" in low
        or "poa declined" in low
        or "valid alternative recent poa still awaited" in low
        or "not a utility bill" in low
    ):
        return "Needs Recent Acceptable POA (Utility Bill Or Accepted Type)"
    if "poa" in low or "proof of address" in low.replace("_", " "):
        return "Needs Recent Acceptable POA"
    if "kyc" in low or "verification" in low:
        return "Needs KYC / Verification Document"
    cleaned = raw.replace("|", " · ").replace("\n", " ")
    return _truncate_text(f"Needs Document · {cleaned}", 88)


def _purchase_gap_days(enrich: dict, report_date: date | None) -> int | None:
    """Calendar days from last purchase date to report date."""
    if not report_date:
        return None
    last_d = _parse_enrich_date(enrich.get("last_purchase_date"))
    if not last_d:
        return None
    return (report_date - last_d).days


def _needs_purchase_zendesk_check(
    enrich: dict, report_date: date | None, this_weekday: float = 0
) -> bool:
    """No report-day purchase and last purchase was 1+ calendar days ago (or unknown)."""
    if not report_date:
        return False
    report_purchased = float(
        enrich.get("report_day_purchased")
        if enrich.get("report_day_purchased") is not None
        else this_weekday
    )
    if report_purchased > 0:
        return False
    gap = _purchase_gap_days(enrich, report_date)
    if gap is None:
        return True
    return gap >= 1


def _zendesk_purchase_block_tag(enrich: dict) -> str:
    """One conclusive purchase-block tag from Zendesk description (as-of report date)."""
    tags_raw = (enrich.get("zendesk_block_ticket_tags") or "").lower()
    subject = (enrich.get("zendesk_block_subject") or "").strip()
    desc = (enrich.get("zendesk_purchase_block") or "").strip()
    desc_low = desc.lower()
    sub_low = subject.lower()
    combined = f"{tags_raw} {subject} {desc}".lower()

    if "please close this account" in desc_low or (
        "please close" in desc_low and "account" in desc_low
    ):
        return "Account Closure Requested"
    if sub_low.strip() in ("close account", "close account ") or (
        "close account" in sub_low and not desc_low.startswith("hi ")
    ):
        return "Account Closure Requested"
    if "taking a break from" in desc_low or (
        "taking a break" in desc_low and "close" in desc_low
    ):
        return "Break Requested · Not Closure"
    if "take the restriction off" in desc_low or "restriction off" in desc_low:
        return "Restriction Lift Requested"
    if "time-out" in combined or "timeout" in combined:
        return "Break / Timeout Requested"
    if "take a break" in desc_low and "close" not in desc_low:
        return "Break Requested"
    if "self_exclusion" in tags_raw or "delete_account" in tags_raw:
        if "closure" in sub_low or "close" in combined:
            return "Account Closure Thread"
    if "restrict" in combined and ("off" in combined or "lift" in combined):
        return "Restriction Lift Requested"
    return ""


CLOSURE_BREAK_BLOCK_TAGS = frozenset({
    "Account Closure Requested",
    "Account Closure Thread",
    "Break Requested",
    "Break / Timeout Requested",
})


def _zendesk_closure_or_break(enrich: dict) -> bool:
    return _zendesk_purchase_block_tag(enrich) in CLOSURE_BREAK_BLOCK_TAGS


def _closure_redeem_recommendation() -> str:
    return "Agent call · confirm closure or break · Escalate Ops redeem · no purchase push"


def _build_redemption_reason(
    enrich: dict,
    *,
    report_date: date | None = None,
    this_weekday: float = 0,
) -> str:
    """Compact redemption Reason — only when pre_authorized pending redeem exists."""
    if not _has_pending_redeem(enrich):
        return ""

    if blocked := _conclusive_redeem_reason(enrich):
        return blocked

    parts: list[str] = ["Redemption in progress"]

    if not _zendesk_missing_doc_tag(enrich):
        if block := _zendesk_purchase_block_tag(enrich):
            parts.append(block)
        elif tag := _restriction_tag(enrich):
            parts.append(tag)

    parts.extend(_redeem_progress_tags(enrich))

    if purchase := _last_purchase_short(enrich):
        parts.append(purchase)

    return sanitize_md(_compact_join(parts))


def _append_purchase_zendesk_context(
    parts: list[str],
    enrich: dict,
    report_date: date | None,
    this_weekday: float = 0,
) -> None:
    """When purchase stalled, add one conclusive Zendesk blocker (POA, closure, restrict)."""
    if not _needs_purchase_zendesk_check(enrich, report_date, this_weekday):
        return
    existing = " ".join(parts).lower()
    if doc := _zendesk_missing_doc_tag(enrich):
        if doc.lower() not in existing:
            parts.append(doc)
            return
    if phrase := _timed_lock_phrase(enrich, report_date):
        if phrase.lower() not in existing:
            parts.append(phrase)
            return
    if block := _zendesk_purchase_block_tag(enrich):
        if block.lower() not in existing:
            parts.append(block)


def _last_purchase_short(enrich: dict) -> str:
    last_date = enrich.get("last_purchase_date")
    last_amt = float(enrich.get("last_purchase_amt") or 0)
    if last_date and last_amt > 0:
        return f"Last Purchase {fmt_short_date(last_date)} {fmt_money(last_amt)}"
    return ""


def _redeem_stage_label(enrich: dict) -> str:
    if not _has_pending_redeem(enrich):
        return ""
    workflow = (enrich.get("redeem_status") or "").strip()
    if workflow and workflow not in ("default", "closed"):
        label = workflow.removeprefix("bw_").replace("_", " ")
        return " ".join(w.capitalize() for w in label.split())
    return "Pre-Authorized"


def _redeem_missing_tag(enrich: dict) -> str:
    """What is still needed before redeem can approve."""
    if not _has_pending_redeem(enrich):
        return ""
    if doc := _zendesk_missing_doc_tag(enrich):
        return doc.replace("Needs ", "")

    restriction = _restriction_tag(enrich)
    if restriction.startswith("Suspended"):
        return "Compliance Unrestrict"
    if restriction == "Legal Restriction":
        return "Legal Review"
    if restriction.startswith("Restricted"):
        return "Restriction Lift"
    if restriction.startswith("Locked"):
        lock_reason = (enrich.get("lock_reason") or "Ops").strip()
        return f"Lock Clearance ({lock_reason})"

    workflow = (enrich.get("redeem_status") or "").strip().lower()
    if "pending_redeem_review" in workflow:
        return "Ops Approval"
    if "payment_processing" in workflow:
        return "Ops Payment Processing"
    return "Ops Approval To Release"


def _redeem_amount_tag(enrich: dict) -> str:
    pending = float(enrich.get("pending_redeem") or 0)
    count = int(enrich.get("pending_redeem_count") or 0)
    rid = (enrich.get("redeem_id") or "").strip()
    if pending <= 0:
        return ""
    if count > 1:
        base = f"RD {fmt_money(pending)} total ({count} open)"
        return f"{base} · latest ID {rid}" if rid else base
    if rid:
        return f"RD {fmt_money(pending)} (ID {rid})"
    return f"RD {fmt_money(pending)}"


def _missing_redundant_with_status(status: str, missing: str) -> bool:
    """Skip Needs tag when Redeem Status already states the same workflow step."""
    s = status.lower().removeprefix("redeem status ").strip()
    m = missing.lower().strip()
    if "payment processing" in s and "payment processing" in m:
        return True
    if "pending redeem review" in s and m == "ops approval":
        return True
    if s == "pre-authorized" and m == "ops approval to release":
        return True
    return False


def _redeem_progress_tags(enrich: dict) -> list[str]:
    """Redeem status, amount, and missing approval for redemption cases."""
    if not _has_pending_redeem(enrich):
        return []
    tags: list[str] = []
    status = _redeem_status_tag(enrich) or ""
    if status:
        tags.append(status)
    if amt := _redeem_amount_tag(enrich):
        tags.append(amt)
    if missing := _redeem_missing_tag(enrich):
        if not _missing_redundant_with_status(status, missing):
            tags.append(f"Needs {missing}")
    return tags


def _workflow_short(enrich: dict) -> str:
    workflow = (enrich.get("redeem_status") or enrich.get("account_status") or "").strip()
    if not workflow or workflow in ("default", "closed"):
        return ""
    label = workflow.removeprefix("bw_").replace("_", " ")
    return f"Workflow {_truncate_text(label, 28)}"


def _inactive_tag(enrich: dict) -> str:
    """Note when no play or purchase after last purchase.

    If this tag appears with restriction/redeem workflow, drill Zendesk per module docstring
    (Inactive / suspicious player — Zendesk drill-down) before concluding churn or skip.
    """
    note = _activity_since_last_purchase(enrich)
    if note == M_NO_PLAY_OR_PURCHASE_SINCE:
        return "Inactive Since Last Purchase"
    if M_NO_PURCHASES_7D in note:
        return M_NO_PURCHASES_7D
    if note.startswith(M_LAST_PLAY_14D):
        return note.replace("; ", REASON_SEP)
    return note


def _restriction_summary(enrich: dict) -> str:
    """Legacy long-form restriction note (handoffs). Prefer _restriction_tag in daily table."""
    tag = _restriction_tag(enrich)
    if not tag:
        return ""
    if tag.startswith(("Suspended", "Restricted", "Unrestrict")):
        return f"{M_ACCOUNT_SUSPENDED if tag.startswith('Suspended') else M_ACCOUNT_RESTRICTED} ({tag})."
    if tag == "Legal Restriction":
        return f"{M_ACCOUNT_RESTRICTED_LEGAL}."
    if tag == "Self-Exclusion":
        return "Self-Exclusion."
    return f"{tag}."



def sanitize_md(text: str) -> str:
    """Use ASCII hyphen in markdown-facing prose."""
    if not text:
        return text
    return text.replace("\u2014", "-").replace("\u2013", "-").replace("\u2192", "->")




def format_agent_name(row: dict) -> str:
    """Friendly manager name for reports; tag_agent_1 kept separately for filters."""
    tag = (row.get("agent") or row.get("agent_display") or "").strip()
    if not tag:
        return "n/a"
    if tag in AGENT_TAG_LABELS:
        return AGENT_TAG_LABELS[tag]
    short = tag.split("_")[0].capitalize()
    return short if short else tag


def fmt_day_drop_reason(code: str) -> str:
    return DAY_DROP_LABELS.get(code, fmt_reason(code))


def fmt_ngr_short(ngr: float | None) -> str:
    if ngr is None:
        return "n/a"
    v = float(ngr)
    if v < 0:
        tag = "↑"
    elif v > 0:
        tag = "↓"
    else:
        tag = ""
    return f"{fmt_money(v)}{tag}"


def fmt_hold_pct(net_purchase: float | None, deposits: float | None) -> str:
    """Hold % = net purchase / deposits — share kept in ecosystem vs money in."""
    dep = float(deposits or 0)
    net = float(net_purchase or 0)
    if dep <= 0:
        return "n/a"
    return f"{100 * net / dep:.1f}%"


def format_lifetime_purchased(enrich: dict) -> str:
    return fmt_money(float(enrich.get("lifetime_purchased") or 0))


def format_lifetime_hold(enrich: dict) -> str:
    return fmt_hold_pct(
        enrich.get("lifetime_net_purchase"),
        enrich.get("lifetime_purchased"),
    )


def format_table_lifetime_purchase(amount) -> str:
    val = fmt_money(amount)
    if float(amount or 0) >= 50000:
        return f"**{val}**"
    return val


def format_table_lifetime_hold(text: str) -> str:
    label = (text or "n/a").strip()
    if label.endswith("%"):
        try:
            if float(label.rstrip("%")) >= 70:
                return f"**{label}**"
        except ValueError:
            pass
    return label


def extract_metrics_7d(enrich: dict) -> dict[str, float | int | str]:
    deposits = float(enrich.get("purchased_7d") or 0)
    net = float(enrich.get("net_purchases_7d") or 0)
    return {
        "deposits_7d": deposits,
        "net_purchases_7d": net,
        "hold_pct_7d": fmt_hold_pct(net, deposits),
        "bets_7d": float(enrich.get("bets_7d") or 0),
        "ggr_7d": float(enrich.get("ggr_7d") or 0),
        "ngr_7d": float(enrich.get("ngr_7d") or 0),
        "spins_7d": int(enrich.get("spins_7d") or 0),
    }


def format_activity_7d(enrich: dict) -> str:
    m = extract_metrics_7d(enrich)
    parts = [f"deposits {fmt_money(m['deposits_7d'])}"]
    if m["bets_7d"] > 0:
        parts.append(f"bets {fmt_money(m['bets_7d'])}")
    if m["ggr_7d"] != 0:
        parts.append(f"GGR {fmt_money(m['ggr_7d'])}")
    parts.append(f"NGR {fmt_ngr_short(m['ngr_7d'])}")
    if m["spins_7d"] > 0:
        parts.append(f"{m['spins_7d']:,} spins")
    return " · ".join(parts)


def format_purchase_calendar(enrich: dict) -> str:
    """Human-readable: 'Saturday $1,770' = purchased $1,770 that day in the 7D window."""
    cal = (enrich.get("purchase_calendar") or "").strip()
    return cal if cal else M_NONE_IN_7D


def _weekdays_in_7d_window(report_date: date) -> list[str]:
    return [(report_date - timedelta(days=6 - i)).strftime("%A") for i in range(7)]


def _short_weekday(name: str) -> str:
    return name[:3]


def _parse_purchase_days(cal: str) -> list[str]:
    """Weekday names with a purchase in the 7D window, e.g. 'Monday $2525, Tuesday $1335'."""
    if not cal or cal == M_NONE_IN_7D:
        return []
    days: list[str] = []
    for part in cal.split(","):
        part = part.strip()
        if not part:
            continue
        day_name = part.split()[0]
        if day_name:
            days.append(day_name)
    return days


def _consecutive_no_purchase_days(enrich: dict) -> int:
    """Calendar days with $0 purchase ending on report date (from enrich SQL)."""
    return int(enrich.get("consecutive_no_purchase_days") or 0)


def _recommendation_for_purchase_streak(enrich: dict) -> str | None:
    """2+ consecutive no-purchase days ending report date → agent touch."""
    streak = _consecutive_no_purchase_days(enrich)
    if streak >= 3:
        return "Push purchase"
    if streak >= 2:
        return "Soft check-in only"
    return None


def format_purchase_7d_combined(enrich: dict, report_date: date | None = None) -> str:
    """7D Purchase: total + days bought / 7, then missed or bought days (not both)."""
    total = float(enrich.get("purchased_7d") or 0)
    cal = (enrich.get("purchase_calendar") or "").strip()
    bought_days = _parse_purchase_days(cal)
    n = len(bought_days)

    if total <= 0 and n == 0:
        return M_NONE_IN_7D

    base = f"{fmt_money(total)} · {n}/7 days"

    if n == 0:
        return base if total > 0 else M_NONE_IN_7D

    if n == 1:
        return f"{base} ({_short_weekday(bought_days[0])})"

    if report_date:
        window = _weekdays_in_7d_window(report_date)
        bought_set = set(bought_days)
        missing = [d for d in window if d not in bought_set]
        if n >= 4 and missing:
            miss = ", ".join(_short_weekday(d) for d in missing)
            return f"{base} · missed {miss}"
        if n <= 3:
            bought = ", ".join(_short_weekday(d) for d in bought_days)
            return f"{base} · {bought}"

    if n >= 4:
        return base
    bought = ", ".join(_short_weekday(d) for d in bought_days)
    return f"{base} · {bought}"


def format_purchase_7d_help() -> str:
    return (
        "**7D Purchase** = rolling 7 days ending on the report date. "
        "Shows **total purchased**, **days with a purchase / 7**, then either **missed days** "
        "(when 4+ days had a purchase) or **which days purchased** (when 3 or fewer). "
        f"Example: `$5,919 · 4/7 days · missed Fri, Sat, Sun`. `{M_NONE_IN_7D}` = no purchases in window."
    )


def format_urgency_legend() -> str:
    action = {
        "Today": "Contact today",
        "48h": "Reach out within 2 days",
        "Watch": "Monitor only",
        "None": "Do not contact",
    }
    lines = ["**Urgency:**"]
    for label, desc in URGENCY_OPTIONS:
        lines.append(f"- **{label}** — {action.get(label, label)}: {desc}")
    return "\n".join(lines)


def format_urgency_legend_one_line() -> str:
    action = {
        "Today": "contact today",
        "48h": "reach out within 2 days",
        "Watch": "monitor only",
        "None": "do not contact",
    }
    parts = [f"{label} ({action.get(label, label.lower())}: {desc})" for label, desc in URGENCY_OPTIONS]
    return f"Urgency: {' · '.join(parts)}"


def format_favourite_game_7d(enrich: dict) -> str:
    title = (enrich.get("favourite_game_7d") or "").strip()
    return title if title else "—"


def format_zendesk_recent(enrich: dict) -> str:
    return (enrich.get("recent_zendesk") or "").strip()


def _activity_since_last_purchase(enrich: dict) -> str:
    """Note when no play or purchase after last purchase."""
    last_date = enrich.get("last_purchase_date")
    last_play = enrich.get("last_play_date")
    p7d = float(enrich.get("purchased_7d") or 0)
    if not last_date:
        return ""
    last_d = str(last_date)[:10]
    if p7d == 0:
        if not last_play or str(last_play)[:10] <= last_d:
            return M_NO_PLAY_OR_PURCHASE_SINCE
        return f"{M_LAST_PLAY_14D} {fmt_short_date(last_play)}; {M_NO_PURCHASES_7D}"
    if last_play and str(last_play)[:10] > last_d:
        return f"{M_LAST_PLAY_14D} {fmt_short_date(last_play)}"
    return ""


def _last_purchase_clause(enrich: dict) -> str:
    return _last_purchase_short(enrich)


def _report_day_play_tag(enrich: dict) -> str:
    """Played on report day but no purchase that day (same-weekday skip signal)."""
    spins = int(enrich.get("report_day_spins") or 0)
    bets = float(enrich.get("report_day_bets") or 0)
    if spins > 0 or bets > 0:
        return "Played Today — No Purchase"
    return ""


def _conclusive_redeem_reason(enrich: dict) -> str | None:
    """One decisive summary for suspended/restricted redeem cases (e.g. Richard)."""
    restriction = _restriction_tag(enrich)
    if not restriction:
        return None

    parts = ["Redemption Blocked"]
    if restriction.startswith("Suspended"):
        parts.append(restriction)
    elif restriction == "Legal Restriction":
        parts.append("Legal Restriction")
    else:
        parts.append(restriction)

    if rs := _redeem_status_tag(enrich):
        parts.append(rs)

    if doc := _zendesk_missing_doc_tag(enrich):
        parts.append(doc)

    last_date = enrich.get("last_purchase_date")
    last_amt = float(enrich.get("last_purchase_amt") or 0)
    p7d = float(enrich.get("purchased_7d") or 0)
    if last_date and last_amt > 0 and p7d == 0:
        parts.append(f"Offline Since {fmt_short_date(last_date)} Purchase ({fmt_money(last_amt)})")
    elif inactive := _inactive_tag(enrich):
        parts.append(inactive)

    zd = _zendesk_followup_tag(enrich)
    if zd and "Unrestrict" in zd:
        parts.append("Unrestrict Requested")
    elif zd:
        parts.append(zd)

    pending = float(enrich.get("pending_redeem") or 0)
    if pending > 0:
        parts.append(f"Pending RD {fmt_money(pending)}")

    return _compact_join(parts)


def build_reason_table(
    code: str,
    *,
    weekday_name: str,
    this_weekday: float,
    prior_weekday: float,
    purchased_7d: float,
    enrich: dict,
    purchase_7d_summary: str = "",
    report_date: date | None = None,
) -> str:
    """Compact Reason column: short tags joined with middle dots."""
    pending = float(enrich.get("pending_redeem") or 0)
    failed = int(enrich.get("failed_orders") or 0)
    failed_since = int(enrich.get("failed_orders_since_last_purchase") or 0)
    lock_reason = enrich.get("lock_reason") or ""
    ngr_7d = float(enrich.get("ngr_7d") or 0)
    label = fmt_day_drop_reason(code)
    p7d = float(enrich.get("purchased_7d") or purchased_7d)
    parts: list[str] = [label]

    if code == "redemption_in_progress":
        return _build_redemption_reason(
            enrich, report_date=report_date, this_weekday=this_weekday
        )

    if code == "churn_lapsed":
        if tag := _restriction_tag(enrich):
            parts.append(tag)
        if purchase := _last_purchase_short(enrich):
            parts.append(purchase)
        inactive = _inactive_tag(enrich)
        if inactive == "Inactive Since Last Purchase":
            bets = float(enrich.get("bets_7d") or 0)
            parts.append(f"Still Betting {fmt_money(bets)}" if bets > 0 else M_NO_PLAY_7D)
        elif inactive:
            parts.append(inactive)
        else:
            bets = float(enrich.get("bets_7d") or 0)
            parts.append(f"Still Betting {fmt_money(bets)}" if bets > 0 else M_NO_PLAY_7D)
        if zd := _zendesk_followup_tag(enrich):
            parts.append(zd)
        _append_purchase_zendesk_context(parts, enrich, report_date, this_weekday)
        if not _last_purchase_on_prior_weekday(enrich, report_date):
            parts.append(f"Prior {weekday_name} {fmt_money(prior_weekday)}")
        return sanitize_md(_compact_join(parts))

    if code == "same_weekday_skip":
        parts.append(f"$0 vs Prior {fmt_money(prior_weekday)}")
        if play_tag := _report_day_play_tag(enrich):
            parts.append(play_tag)
        elif purchase := _last_purchase_short(enrich):
            parts.append(purchase)
        _append_purchase_zendesk_context(parts, enrich, report_date, this_weekday)
        return sanitize_md(_compact_join(parts))

    if code == "payment_failed":
        parts.append(f"{failed} Failed Checkout")
        if purchase := _last_purchase_short(enrich):
            parts.append(purchase)
        else:
            parts.append(f"Prior {weekday_name} {fmt_money(prior_weekday)}")
        if failed_since > 0:
            parts.append(f"{failed_since} Failed Post-Purchase")
        _append_purchase_zendesk_context(parts, enrich, report_date, this_weekday)
        return sanitize_md(_compact_join(parts))

    if code == "account_locked":
        parts.extend(_account_lock_tags(enrich, report_date))
        return sanitize_md(_compact_join(parts))

    if code == "self_exclusion":
        parts.append(lock_reason or "Exclusion")
        parts.append("No Outreach")
        return sanitize_md(_compact_join(parts))

    if code == "red_flag":
        parts.extend(_red_flag_tags(enrich))
        parts.append(f"{fmt_money(this_weekday)} vs Prior {fmt_money(prior_weekday)}")
        parts.append(f"{M_7D_PURCHASE} {fmt_money(p7d)}")
        return sanitize_md(_compact_join(parts))

    if code == "general_spend_softening":
        parts = ["Spend Softening", f"{fmt_money(this_weekday)} vs Prior {fmt_money(prior_weekday)}"]
        if purchase_7d_summary and purchase_7d_summary != M_NONE_IN_7D:
            parts.append(purchase_7d_summary)
        elif p7d > 0:
            parts.append(f"{fmt_money(p7d)} In 7D")
        _append_purchase_zendesk_context(parts, enrich, report_date, this_weekday)
        return sanitize_md(_compact_join(parts))

    if code == "big_win_day_before":
        parts.append("Post-Win Cool-Down")
        parts.append(f"{M_7D_PURCHASE} {fmt_money(p7d)}")
        return sanitize_md(_compact_join(parts))

    return sanitize_md(build_reason_detail(
        code,
        weekday_name=weekday_name,
        this_weekday=this_weekday,
        prior_weekday=prior_weekday,
        purchased_7d=purchased_7d,
        enrich=enrich,
    ))


def format_last_purchase(enrich: dict) -> str:
    last_date = enrich.get("last_purchase_date")
    last_amt = float(enrich.get("last_purchase_amt") or 0)
    if last_date and last_amt > 0:
        return f"{fmt_money(last_amt)} on {fmt_short_date(last_date)}"
    return "n/a"


def format_report_day_play(enrich: dict) -> str:
    spins = int(enrich.get("report_day_spins") or 0)
    bets = float(enrich.get("report_day_bets") or 0)
    parts: list[str] = []
    if spins > 0:
        parts.append(f"{spins:,} Spins")
    if bets > 0:
        parts.append(f"{fmt_money(bets)} Bets")
    return ", ".join(parts) if parts else M_NO_REPORT_DAY_PLAY


def format_recent_days(enrich: dict) -> str:
    """Report Day + day before snapshot."""
    rd_p = float(enrich.get("report_day_purchased") or 0)
    db_p = float(enrich.get("day_before_purchased") or 0)
    db_ngr = enrich.get("day_before_ngr")
    rd_bets = float(enrich.get("report_day_bets") or 0)
    chunks = [f"{M_REPORT_DAY} Purchase {fmt_money(rd_p)}"]
    if rd_bets > 0:
        chunks.append(f"Bets {fmt_money(rd_bets)}")
    if db_p > 0 or db_ngr is not None:
        line = f"Day Before Purchase {fmt_money(db_p)}"
        if db_ngr is not None and float(db_ngr) != 0:
            line += f", 7D NGR {fmt_ngr_short(float(db_ngr))}"
        chunks.append(line)
    return "; ".join(chunks)


def fmt_short_date(d) -> str:
    if isinstance(d, date):
        return f"{d.strftime('%a')} {d.day} {d.strftime('%b')}"
    if d:
        s = str(d)[:10]
        try:
            parsed = date.fromisoformat(s)
            return f"{parsed.strftime('%a')} {parsed.day} {parsed.strftime('%b')}"
        except ValueError:
            return s
    return "n/a"


def explain_same_weekday_skip(
    weekday_name: str,
    prior_weekday: float,
    rest: float,
    purchased_7d: float,
    enrich: dict,
) -> str:
    spins_today = int(enrich.get("report_day_spins") or 0)
    bets_today = float(enrich.get("report_day_bets") or 0)
    last_date = enrich.get("last_purchase_date")
    last_amt = float(enrich.get("last_purchase_amt") or 0)
    pending = float(enrich.get("pending_redeem") or 0)
    ngr_7d = float(enrich.get("ngr_7d") or 0)

    msg = (
        f"Same weekday skip: purchased {fmt_money(prior_weekday)} last {weekday_name}, "
        f"$0 purchase this {weekday_name}. "
    )
    # Purchase calendar shown in dedicated column on daily summary.

    why: list[str] = []
    if spins_today > 0 or bets_today > 0:
        why.append(
            f"played this {weekday_name} ({spins_today:,} spins, {fmt_money(bets_today)} bets) "
            f"without a new purchase - likely on existing balance, not skipping the site"
        )
    elif int(enrich.get("spins_7d") or 0) > 0:
        why.append(f"little or no play logged this {weekday_name} - may be offline that day")

    if last_date and last_amt > 0:
        why.append(
            f"last purchase {fmt_money(last_amt)} on {fmt_short_date(last_date)} "
            f"(before this {weekday_name})"
        )
        if rest >= prior_weekday * 0.5:
            why.append(
                "front-loaded the week on other days - already purchased recently, "
                f"so no need to purchase again on {weekday_name}"
            )

    if pending > 0:
        why.append(
            f"pending redeem {fmt_money(pending)} - may pause new purchases until redeem clears"
        )

    if ngr_7d < -3000:
        why.append("up vs house this week - may be playing down balance after a win")
    elif ngr_7d >= 5000:
        why.append("down vs house this week - may be spacing purchases after losses")

    if not why:
        why.append(
            f"purchase rhythm moved off {weekday_name} (payday, promo, or personal schedule) - "
            f"still {fmt_money(purchased_7d)} purchased in 7d"
        )

    msg += "Likely why: " + "; ".join(why) + ". Not churn."
    return sanitize_md(msg)


def explain_spend_softening(
    this_weekday: float,
    prior_weekday: float,
    purchased_7d: float,
    enrich: dict,
) -> str:
    ngr = float(enrich.get("ngr_7d") or 0)
    bets = float(enrich.get("bets_7d") or 0)
    spins = int(enrich.get("spins_7d") or 0)
    other_days = purchased_7d - this_weekday
    pct_drop = (1 - this_weekday / prior_weekday) * 100 if prior_weekday else 0

    if purchased_7d > prior_weekday and this_weekday < prior_weekday * 0.25:
        msg = (
            f"Report-day purchase collapsed ({fmt_money(prior_weekday)} -> {fmt_money(this_weekday)}, "
            f"-{pct_drop:.0f}%) but player is still active: {fmt_money(other_days)} purchased on other days in 7d"
        )
        if spins > 0:
            msg += f", {spins:,} spins"
        if bets > 0:
            msg += f", {fmt_money(bets)} wagered"
        msg += ". "
        if ngr >= 5000:
            msg += "Player down big vs house (NGR positive) - likely slowing purchases after losses, not churn."
        elif ngr < -5000:
            msg += "Player up big vs house - may be pausing after a win streak."
        else:
            msg += "Timing shift on this weekday, not a full stop."
        return msg

    return (
        f"Report-day purchase down ({fmt_money(prior_weekday)} -> {fmt_money(this_weekday)}). "
        f"{fmt_money(purchased_7d)} total purchased in 7d."
    )


def build_reason_detail(
    code: str,
    *,
    weekday_name: str,
    this_weekday: float,
    prior_weekday: float,
    purchased_7d: float,
    enrich: dict,
) -> str:
    label = fmt_day_drop_reason(code)
    recent = format_recent_days(enrich)
    lock_reason = enrich.get("lock_reason") or ""
    pending = float(enrich.get("pending_redeem") or 0)
    failed = int(enrich.get("failed_orders") or 0)
    rest = float(enrich.get("rest_of_week") or 0)
    rid = enrich.get("redeem_id") or "n/a"

    if code == "self_exclusion":
        return f"{label}: account blocked ({lock_reason or 'Exclusion'}). No purchases possible."
    if code == "account_locked":
        return f"{label}: {lock_reason or 'unknown'}. Purchases blocked until Ops clears."
    if code == "redemption_in_progress":
        return (
            f"{label}: pending redeem {fmt_money(pending)} (ID {rid}). "
            f"Report day purchase {fmt_money(this_weekday)} vs prior {fmt_money(prior_weekday)}."
        )
    if code == "payment_failed":
        return (
            f"{label}: {failed} failed checkout on report day. "
            f"Prior same weekday purchase {fmt_money(prior_weekday)}."
        )
    if code == "big_win_day_before":
        return f"{label}: cooled after win. {recent}."
    if code == "churn_lapsed":
        bets = float(enrich.get("bets_7d") or 0)
        play_note = "no bets in 7d" if bets == 0 else f"still betting ({fmt_money(bets)}) but no purchases"
        return (
            f"{label}: $0 purchased in 7d ({play_note}). "
            f"Prior same weekday purchase was {fmt_money(prior_weekday)}."
        )
    if code == "same_weekday_skip":
        return explain_same_weekday_skip(
            weekday_name, prior_weekday, rest, purchased_7d, enrich
        )
    if code == "red_flag":
        tags = ", ".join(_red_flag_tags(enrich))
        return (
            f"{label}: {tags}. Report day {fmt_money(this_weekday)} vs prior {fmt_money(prior_weekday)}."
        )
    if code == "general_spend_softening":
        return explain_spend_softening(this_weekday, prior_weekday, purchased_7d, enrich)
    return label


def build_same_weekday_recommendation(enrich: dict, report_date: date | None = None) -> str:
    """Minimal action for same-weekday skip."""
    if _timed_lock_context(enrich)[0]:
        return _build_account_lock_recommendation(enrich, report_date)

    if doc := _zendesk_missing_doc_tag(enrich):
        return sanitize_md(f"Escalate Compliance · {doc.replace('Needs ', '')}")

    if _zendesk_closure_or_break(enrich):
        if _has_pending_redeem(enrich):
            return sanitize_md(_closure_redeem_recommendation())
        return sanitize_md("No action")

    if streak_rec := _recommendation_for_purchase_streak(enrich):
        return sanitize_md(streak_rec)

    cal = (enrich.get("purchase_calendar") or "").strip()
    bought_days = _parse_purchase_days(cal)
    n = len(bought_days)

    if n <= 2:
        return sanitize_md("Push purchase")

    if n == 3:
        return sanitize_md("Soft check-in only")

    if report_date:
        window = _weekdays_in_7d_window(report_date)
        missing = [d for d in window if d not in set(bought_days)]
        if len(missing) >= 3:
            return sanitize_md("Push purchase")

    return sanitize_md("No action")


def _build_redeem_recommendation(enrich: dict) -> str:
    if doc := _zendesk_missing_doc_tag(enrich):
        return sanitize_md(f"Escalate Compliance · {doc.replace('Needs ', '')}")

    if _zendesk_closure_or_break(enrich):
        if _has_pending_redeem(enrich):
            return sanitize_md(_closure_redeem_recommendation())
        return sanitize_md("Agent call · confirm closure or break · no purchase push")

    if not _has_pending_redeem(enrich):
        return sanitize_md("Escalate Ops · clear redeem workflow")

    pending = float(enrich.get("pending_redeem") or 0)
    rid = (enrich.get("redeem_id") or "n/a").strip()
    count = int(enrich.get("pending_redeem_count") or 0)
    missing = _redeem_missing_tag(enrich)
    stage = _redeem_stage_label(enrich)
    rd_label = (
        f"RD {fmt_money(pending)} total ({count} open · latest ID {rid})"
        if count > 1
        else f"RD {fmt_money(pending)} (ID {rid})"
    )

    if missing:
        return sanitize_md(f"Escalate Ops · clear {rd_label} · {missing}")

    if stage:
        return sanitize_md(f"Escalate Ops · clear {rd_label} · {stage}")

    return sanitize_md(f"Escalate Ops · clear {rd_label}")


def build_action_step(code: str, *, enrich: dict, report_date: date | None = None) -> str:
    failed = int(enrich.get("failed_orders") or 0)
    lock_reason = enrich.get("lock_reason") or ""

    steps = {
        "self_exclusion": "No outreach",
        "account_locked": _build_account_lock_recommendation(enrich, report_date),
        "redemption_in_progress": _build_redeem_recommendation(enrich),
        "payment_failed": f"Fix payment method · {failed} failed checkout",
        "big_win_day_before": "No purchase push",
        "churn_lapsed": "Push purchase",
        "same_weekday_skip": build_same_weekday_recommendation(enrich, report_date),
        "red_flag": "Compliance sign-off before offer",
        "general_spend_softening": "Soft check-in · no hard sell",
    }
    return sanitize_md(steps.get(code, "See handoff"))


def build_action(code: str, *, enrich: dict, report_date: date | None = None) -> str:
    urgency = URGENCY_BY_CODE.get(code, "48h")
    return sanitize_md(f"{urgency}: {build_action_step(code, enrich=enrich, report_date=report_date)}")


from wow_drop_analysis.ticket_draft import build_zendesk_ticket_draft


from wow_drop_analysis.queries import (
    enrich_aids_sql,
    same_day_selection_summary,
    select_top_same_day_players,
    top10_delta_sql,
    top_same_day_sql,
)


def classify_day_drop(
    this_weekday: float,
    prior_weekday: float,
    purchased_7d: float,
    enrich: dict,
    *,
    weekday_name: str = "weekday",
    report_date: date | None = None,
) -> tuple[str, str, str]:
    locked = bool(enrich.get("account_locked"))
    lock_reason = enrich.get("lock_reason") or ""
    timed_break_days, _ = _timed_lock_context(enrich)
    failed = int(enrich.get("failed_orders") or 0)
    rest = float(enrich.get("rest_of_week") or 0)
    day_before_ngr = enrich.get("day_before_ngr")
    red_flag = bool(enrich.get("red_flag"))
    p7d = float(enrich.get("purchased_7d") or purchased_7d)

    if locked and lock_reason == "Exclusion":
        code = "self_exclusion"
    elif locked or timed_break_days:
        code = "account_locked"
    elif _has_pending_redeem(enrich):
        code = "redemption_in_progress"
    elif failed > 0 and this_weekday == 0:
        code = "payment_failed"
    elif day_before_ngr is not None and float(day_before_ngr) <= -5000:
        code = "big_win_day_before"
    elif p7d == 0 and prior_weekday > 0:
        code = "churn_lapsed"
    elif this_weekday == 0 and rest > 0:
        code = "same_weekday_skip"
    elif red_flag:
        code = "red_flag"
    elif this_weekday < prior_weekday:
        code = "general_spend_softening"
    else:
        code = "general_spend_softening"

    detail = sanitize_md(build_reason_detail(
        code,
        weekday_name=weekday_name,
        this_weekday=this_weekday,
        prior_weekday=prior_weekday,
        purchased_7d=p7d,
        enrich=enrich,
    ))
    action = build_action(code, enrich=enrich, report_date=report_date)
    return code, detail, action


def sort_top10_rows(rows: list[dict]) -> list[dict]:
    """Today first, then 48h, Watch, None; within tier largest prior-weekday gap first."""
    return sorted(
        rows,
        key=lambda r: (
            URGENCY_SORT.get(r.get("urgency") or "", 9),
            -float(r.get("delta") or 0),
        ),
    )


def classify_same_day_candidate_rows(
    client,
    report_date: date,
    rows: list[dict],
) -> list[dict]:
    """Enrich + classify already-selected same-day gap rows (Daily Top 20 logic)."""
    from elite_lib import weekday_label

    if not rows:
        return []
    aids = [int(r["AID"]) for r in rows]
    enrich_rows = run_query(
        client,
        enrich_aids_sql(aids, report_date),
        maximum_bytes_billed=HEAVY_QUERY_SCAN_CAP_BYTES,
    )
    enrich_map = {int(e["AID"]): e for e in enrich_rows}
    day_name = weekday_label(report_date)
    out = []
    for r in rows:
        aid = int(r["AID"])
        enrich = enrich_map.get(aid, {})
        code, detail, action = classify_day_drop(
            float(r.get("this_weekday") or 0),
            float(r.get("prior_weekday") or 0),
            float(r.get("purchased_7d") or 0),
            enrich,
            weekday_name=day_name,
            report_date=report_date,
        )
        urgency = URGENCY_BY_CODE.get(code, "48h")
        if (
            code == "same_weekday_skip"
            and _consecutive_no_purchase_days(enrich) >= 2
        ):
            urgency = "48h"
        action_step = build_action_step(code, enrich=enrich, report_date=report_date)
        purchase_7d_combined = format_purchase_7d_combined(enrich, report_date)
        reason_table = build_reason_table(
            code,
            weekday_name=day_name,
            this_weekday=float(r.get("this_weekday") or 0),
            prior_weekday=float(r.get("prior_weekday") or 0),
            purchased_7d=float(r.get("purchased_7d") or 0),
            enrich=enrich,
            purchase_7d_summary=purchase_7d_combined,
            report_date=report_date,
        )
        row_out = {
            **r,
            **extract_metrics_7d(enrich),
            "reason_code": code,
            "reason": fmt_day_drop_reason(code),
            "reason_detail": detail,
            "reason_table": reason_table,
            "action": action_step,
            "recommendation": action_step,
            "action_full": action,
            "urgency": urgency,
            "purchase_calendar": format_purchase_calendar(enrich),
            "purchase_7d_combined": purchase_7d_combined,
            "last_purchase": format_last_purchase(enrich),
            "report_day_play": format_report_day_play(enrich),
            "favourite_game_7d": format_favourite_game_7d(enrich),
            "lifetime_purchased": float(enrich.get("lifetime_purchased") or 0),
            "lifetime_purchased_fmt": format_lifetime_purchased(enrich),
            "lifetime_hold_pct": format_lifetime_hold(enrich),
            "context": detail,
            "player_email": enrich.get("player_email"),
            "zendesk_user_id": enrich.get("zendesk_user_id"),
        }
        ticket = build_zendesk_ticket_draft(row_out, enrich, report_date=report_date)
        row_out.update(ticket)
        out.append(row_out)
    return sort_top10_rows(out)


def fetch_top10_by_delta(
    client,
    report_date: date,
    *,
    elite_wow_drop: float | None = None,
) -> list[dict]:
    candidates = run_query(client, top_same_day_sql(report_date))
    if not candidates:
        return []
    rows = select_top_same_day_players(candidates, elite_wow_drop=elite_wow_drop)
    return classify_same_day_candidate_rows(client, report_date, rows)


def fetch_top_same_day_by_agent(
    client,
    report_date: date,
    agent_names: list[str],
    *,
    elite_wow_drop: float | None = None,
    limit: int = TOP_SAME_DAY_LIMIT,
) -> dict[str, list[dict]]:
    """Per-agent Top N using the same selection + classify logic as Daily Elite Summary."""
    candidates = run_query(client, top_same_day_sql(report_date))
    if not candidates:
        return {name: [] for name in agent_names}

    picked_by_agent: dict[str, list[dict]] = {}
    ordered: list[dict] = []
    seen_aids: set[int] = set()
    for name in agent_names:
        pool = [c for c in candidates if format_agent_name(c) == name]
        picked = select_top_same_day_players(
            pool, limit=limit, elite_wow_drop=elite_wow_drop
        )
        picked_by_agent[name] = picked
        for r in picked:
            aid = int(r["AID"])
            if aid not in seen_aids:
                ordered.append(r)
                seen_aids.add(aid)

    classified = classify_same_day_candidate_rows(client, report_date, ordered)
    by_aid = {int(r["AID"]): r for r in classified}
    return {
        name: [by_aid[int(r["AID"])] for r in picked if int(r["AID"]) in by_aid]
        for name, picked in picked_by_agent.items()
    }

