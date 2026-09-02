"""Pure payload-building functions for the Elite AM Brief.

Every function here is a pure transformation from raw BigQuery rows (dicts) to
payload dicts. No BigQuery calls, no file I/O, no side effects.  These can be
unit-tested directly (see test_payload_builders.py) without any credentials or
mocked clients.

Extracted from generate_am_daily_dashboard.py in Phase 3 (2026-08-19) so the
god-module becomes a thin orchestration shell over testable builders.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING

from config import (  # noqa: E402
    LOCKS_REVIEW_WINDOW_DAYS,
    LOCKS_TAB_EXPIRE_DAYS,
    LOCKS_WINDOW_DAYS,
    TICKET_TOPIC_BASE_LABEL,
    TICKET_TOPIC_BASE_MULTIPLIER,
    TICKET_TOPIC_TIERS,
    TICKET_ZENDESK_TIER1_FIELD_VALUES,
    TICKET_ZENDESK_TIER2_FIELD_VALUES,
    TICKET_WEIGHT_30D_PURCHASE,
    TICKET_WEIGHT_LT_HOLD,
    TICKET_WEIGHT_LT_NGR,
    TICKET_WEIGHT_LT_PURCHASE,
)
from daily_summary.generate_daily_elite_canvas import fmt_money_short  # noqa: E402
from daily_summary.generate_daily_elite_summary import (  # noqa: E402
    looker_account_portal_url,
    zendesk_ticket_url,
)
from wow_drop_analysis.wow_drop_reason import (  # noqa: E402
    AGENT_TAG_LABELS,
    _take_a_break_days,
    _zendesk_missing_doc_tag,
    format_agent_name,
    format_lifetime_hold,
    format_lifetime_purchased,
)
from am_brief_ticket_drafts import (  # noqa: E402
    build_anniversary_ticket_draft,
    build_birthday_gift_ticket_draft,
    build_birthday_ticket_draft,
    build_first_time_rd_ticket_draft,
    outreach_lock_gate,
)

if TYPE_CHECKING:
    pass

# Softened tone palette for Top 20 WoW gaps in the AM Brief.
# The Daily Decline board uses raw red-heavy codes; the AM Brief de-emphasises
# them to keep the morning read actionable rather than alarming.
AM_REASON_TONE: dict[str, str] = {
    "redemption_in_progress": "danger",
    "payment_failed": "danger",
    "account_locked": "danger",
    "red_flag": "warning",
    "self_exclusion": "neutral",
    "churn_lapsed": "warning",
    "same_weekday_skip": "info",
    "general_spend_softening": "warning",
    "big_win_day_before": "success",
}


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------


def parse_date_val(val: object) -> date | None:
    """Coerce a BigQuery date-like value to a Python date, or None."""
    if val is None or val == "":
        return None
    if hasattr(val, "isoformat") and not isinstance(val, str):
        return val if isinstance(val, date) else val.date()  # type: ignore[attr-defined]
    return date.fromisoformat(str(val)[:10])


def _safe_int(val: object) -> int:
    try:
        return int(val or 0)
    except (TypeError, ValueError):
        return 0


def _ticket_ids_list(raw: object) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        return [p.strip() for p in raw.split(",") if p.strip()]
    try:
        return [str(t).strip() for t in list(raw) if t is not None and str(t).strip()]
    except TypeError:
        s = str(raw).strip()
        return [s] if s else []


def fmt_price(val: object) -> str:
    """Offer price keeping cents — $899.99 stays $899.99, not $900.

    Used on Top 10 Purchasers price ladder where cent-accuracy matters for the
    AM quoting a package price to a player.
    """
    if val is None:
        return "—"
    try:
        num = float(val)
    except (TypeError, ValueError):
        return "—"
    return f"${num:,.0f}" if num == int(num) else f"${num:,.2f}"


def agent_display(tag: str) -> str:
    """Human-readable agent name from a tag string."""
    return AGENT_TAG_LABELS.get(tag, format_agent_name({"agent": tag}))


def soft_tone_for_code(code: str | None) -> str:
    """AM Brief tone for a decline reason code (softened vs Daily Decline)."""
    if not code:
        return "warning"
    return AM_REASON_TONE.get(code, "warning")


def aid_row(aid: object, name: str = "", **extra: object) -> dict:
    """Base dict for any AID row — AID string + Looker link + name."""
    aid_s = str(aid or "").strip()
    return {
        "aid": aid_s,
        "aidUrl": looker_account_portal_url(aid_s),
        "name": name or "n/a",
        **extra,
    }


def build_package_fit(usual: object, usual_orders: object, ceiling: object) -> str:
    """Format the "usual → ceiling" cell for Top 10 Purchasers.

    One place so the canvas, standalone HTML, and Streamlit cannot drift.
    A missing ceiling means no proven headroom, not missing data.
    """
    if usual is None:
        return "—"
    text = fmt_price(usual)
    orders = _safe_int(usual_orders)
    if orders > 1:
        text += f" \u00d7{orders}"
    if ceiling is not None and float(ceiling) > float(usual):
        text += f" \u2192 {fmt_price(ceiling)}"
    return text


def lock_bucket(lock_reason: str, lock_comment: str) -> tuple[str, str]:
    """Classify a locked account into (bucket, tone).

    Bucket values: 'Self-exclusion' | 'Take a break' | 'Other locked'
    """
    reason = (lock_reason or "").strip()
    comment = (lock_comment or "").strip()
    low = f"{reason} {comment}".lower()
    if reason == "Exclusion" or "self_exclud" in low:
        return "Self-exclusion", "neutral"
    days = _take_a_break_days(reason) or _take_a_break_days(comment)
    if days or "take a break" in low:
        return "Take a break", "warning"
    return "Other locked", "warning"


def _birthday_row_excluded(
    locked: bool, lock_reason: str = "", lock_reason_comment: str = ""
) -> bool:
    """Birthday outreach is skipped for locked, self-excluded, or TAB players."""
    disabled, _ = outreach_lock_gate(locked, lock_reason, lock_reason_comment)
    if disabled:
        return True
    reason = (lock_reason or "").strip()
    comment = (lock_reason_comment or "").strip()
    low = f"{reason} {comment}".lower()
    if reason == "Exclusion" or "self_exclud" in low:
        return True
    if (
        _take_a_break_days(reason)
        or _take_a_break_days(comment)
        or "take a break" in low
    ):
        return True
    return False


def unlock_info(
    lock_reason: str,
    lock_comment: str,
    locked_at: date | None,
    report_date: date,
) -> tuple[str, int | None]:
    """Display text and remaining days for a take-a-break lock.

    remaining_days <= 0  → today/overdue; the restriction should be removed.
    None                 → no calculable unlock date (self-exclusion, other
                           locked, or a break with no locked_at timestamp).
    """
    days = _take_a_break_days(lock_reason or "") or _take_a_break_days(lock_comment or "")
    if not days:
        return "", None
    if not locked_at:
        return f"Take a break {days} days", None
    unlock = locked_at + timedelta(days=days)
    remaining = (unlock - report_date).days
    if remaining > 0:
        return f"{remaining}d left · unlock {unlock.isoformat()}", remaining
    if remaining == 0:
        return "Unlock today — remove restriction", 0
    return f"Ended {unlock.isoformat()} — remove restriction", remaining


# ---------------------------------------------------------------------------
# Section builders (pure: rows in → payload list out)
# ---------------------------------------------------------------------------


def build_top10_section(
    rows: list[dict],
    metrics_enrich: dict[int, dict] | None = None,
) -> list[dict]:
    """Format raw Top 10 Purchasers BQ rows into payload dicts.

    metrics_enrich: when provided, adds lifetime purchase/hold from the shared
    enrich_aids_sql batch (no extra query).
    """
    out = []
    for r in rows:
        unit_min = r.get("offer_unit_min")
        unit_max = r.get("offer_unit_max")
        row = aid_row(
            r.get("AID"),
            r.get("name") or "n/a",
            agent=r.get("agent") or "",
            agentName=agent_display(r.get("agent") or ""),
            rank=int(r.get("rank_in_agent") or 0),
            purchased=fmt_money_short(r.get("purchased")),
            purchasedNum=float(r.get("purchased") or 0),
            orderCount=int(float(r.get("order_count") or 0)),
            offerCode=r.get("offer_code") or "—",
            offerTitle=r.get("offer_title") or "",
            offerQty=int(float(r.get("offer_qty") or 0)),
            offerAmount=fmt_money_short(r.get("offer_amount"))
            if r.get("offer_amount") is not None
            else "—",
            offerPrice=fmt_price(r.get("offer_unit_amount")),
            # True when the same offer was bought at more than one amount,
            # so a single price is an average rather than the price paid.
            offerPriceVaries=bool(
                unit_min is not None
                and unit_max is not None
                and float(unit_min) != float(unit_max)
            ),
            usualPrice=fmt_price(r.get("usual_price")),
            usualPriceOrders=_safe_int(r.get("usual_price_orders")),
            ceilingPrice=fmt_price(r.get("ceiling_price")),
            frequentLast30d=fmt_price(r.get("usual_price")) if r.get("usual_price") is not None else "—",
            maxPurchase30d=fmt_price(r.get("max_purchase_30d")) if r.get("max_purchase_30d") is not None else "—",
            packageFit=build_package_fit(
                r.get("usual_price"),
                r.get("usual_price_orders"),
                r.get("ceiling_price"),
            ),
            tone="success",
        )
        if metrics_enrich is not None:
            m = metrics_enrich.get(_safe_int(r.get("AID")), {})
            ltp_num = float(m.get("lifetime_purchased") or 0)
            row.update(
                lifetimePurchase=format_lifetime_purchased(m) if m else fmt_money_short(0),
                lifetimePurchasedNum=ltp_num,
                lifetimeHold=format_lifetime_hold(m) if m else "n/a",
            )
        out.append(row)
    return out


def build_rd_section(
    rows: list[dict],
    report_date: date | None = None,
    aging_threshold_days: int | None = None,
    ticket_enrich: dict[int, dict] | None = None,
    metrics_enrich: dict[int, dict] | None = None,
) -> list[dict]:
    """Format raw Redemption rows into payload dicts.

    aging_threshold_days: flag rows created this many days ago or earlier
    (e.g. PENDING_RD_LOOKBACK_DAYS - 1) so agents can see which pending
    redemptions are nearing the edge of the lookback window. Pass None
    (default) to skip aging entirely — First-Time Locked RD has no window.

    ticket_enrich: when provided (AID → {"zendesk_user_id": ...}), attaches
    a Zendesk ticket draft (build_first_time_rd_ticket_draft), gated by the
    account's own locked/lock_reason (elite-core: never recommend retention
    outreach for a locked or self-excluded account). Pass None to skip —
    Pending RD ≥ $5k is view-only.

    metrics_enrich: when provided, adds missing-document status plus lifetime
    purchase/hold and 7-day purchase. Reuses the shared enrich_aids_sql result
    so this costs no extra query.
    """
    out = []
    for r in rows:
        created_d = parse_date_val(r.get("created_date"))
        days_pending = (report_date - created_d).days if (report_date and created_d) else None
        aging_flag = (
            aging_threshold_days is not None
            and days_pending is not None
            and days_pending >= aging_threshold_days
        )
        big_winner = bool(r.get("big_winner"))
        player_win = float(r.get("player_win_day") or 0)
        row = aid_row(
            r.get("AID"),
            r.get("name") or "n/a",
            agent=r.get("agent") or "",
            agentName=agent_display(r.get("agent") or ""),
            redeemId=str(r.get("redeem_id") or ""),
            amount=fmt_money_short(r.get("amount")),
            amountNum=float(r.get("amount") or 0),
            status=r.get("status") or "locked",
            created=str(r.get("created_date") or ""),
            daysPending=days_pending,
            agingFlag=aging_flag,
            bigWinner=big_winner,
            wonYesterday=fmt_money_short(player_win) if player_win > 0 else "—",
            wonYesterdayNum=player_win,
            # Big Winner outranks ageing for row tone: a held withdrawal from
            # someone who just won five figures is the row to open first.
            tone="danger" if (big_winner or aging_flag) else "warning",
        )
        if metrics_enrich is not None:
            m = metrics_enrich.get(_safe_int(r.get("AID")), {})
            ltp_num = float(m.get("lifetime_purchased") or 0)
            p7_num = float(m.get("purchased_7d") or 0)
            row.update(
                # Blank when nothing is flagged, on purpose: we can only prove
                # "no open ticket names a missing document", never that the
                # documents are verified complete, so the board stays silent
                # rather than implying an all-clear an AM might repeat to a
                # player waiting on a withdrawal.
                docsStatus=_zendesk_missing_doc_tag(m) if m else "",
                lifetimePurchase=format_lifetime_purchased(m) if m else fmt_money_short(0),
                lifetimePurchasedNum=ltp_num,
                lifetimeHold=format_lifetime_hold(m) if m else "n/a",
                purchase7d=fmt_money_short(p7_num),
                purchase7dNum=p7_num,
            )
        if ticket_enrich is not None:
            enrich = ticket_enrich.get(_safe_int(r.get("AID")), {})
            row.update(
                build_first_time_rd_ticket_draft(
                    r,
                    locked=bool(r.get("locked")),
                    lock_reason=r.get("lock_reason") or "",
                    lock_reason_comment=r.get("lock_reason_comment") or "",
                    zendesk_user_id=enrich.get("zendesk_user_id"),
                )
            )
        out.append(row)
    return out


def build_birthday_section(
    rows: list[dict], ticket_enrich: dict[int, dict] | None = None
) -> list[dict]:
    """Format raw Birthdays BQ rows into payload dicts.

    ticket_enrich: same locked/self-exclusion gate as build_rd_section,
    applied via build_birthday_ticket_draft. Locked, self-excluded, and TAB
    players are omitted from the section entirely.
    """
    out = []
    for r in rows:
        if _birthday_row_excluded(
            bool(r.get("locked")),
            r.get("lock_reason") or "",
            r.get("lock_reason_comment") or "",
        ):
            continue
        age = r.get("age")
        try:
            age_i = int(age) if age is not None else None
        except (TypeError, ValueError):
            age_i = None
        dob_raw = r.get("dob")
        dob_d = parse_date_val(dob_raw)
        if dob_d:
            dob_fmt = f"{dob_d.day}/{dob_d.month}/{dob_d.year}"
        else:
            dob_fmt = str(dob_raw or "")
        row = aid_row(
            r.get("AID"),
            r.get("name") or "n/a",
            agent=r.get("agent") or "",
            agentName=agent_display(r.get("agent") or ""),
            email=r.get("email") or "",
            dob=dob_fmt,
            age=age_i,
            tone="success",
        )
        if ticket_enrich is not None:
            enrich = ticket_enrich.get(_safe_int(r.get("AID")), {})
            row.update(
                build_birthday_ticket_draft(
                    r,
                    locked=bool(r.get("locked")),
                    lock_reason=r.get("lock_reason") or "",
                    lock_reason_comment=r.get("lock_reason_comment") or "",
                    zendesk_user_id=enrich.get("zendesk_user_id"),
                )
            )
        out.append(row)
    return out


def _fmt_day_month_year(val: object) -> str:
    """'2 Aug 2026' style date for the anniversary section; '' when unparseable."""
    d = parse_date_val(val)
    return f"{d.day} {d.strftime('%b %Y')}" if d else ""


def build_anniversary_section(
    rows: list[dict], enrich_map: dict[int, dict] | None = None
) -> list[dict]:
    """Format raw one-month anniversary BQ rows into payload dicts.

    Same outreach gate as Birthdays: locked, self-excluded, and TAB players are
    dropped entirely (elite-core). enrich_map (AID -> shared enrich row) adds
    LTP / Hold / 7D from the batch already fetched for Open Tickets, and a
    review-only Zendesk draft gated by build_anniversary_ticket_draft.
    """
    out = []
    for r in rows:
        if _birthday_row_excluded(
            bool(r.get("locked")),
            r.get("lock_reason") or "",
            r.get("lock_reason_comment") or "",
        ):
            continue
        row = aid_row(
            r.get("AID"),
            r.get("name") or "n/a",
            agent=r.get("agent") or "",
            agentName=agent_display(r.get("agent") or ""),
            firstName=r.get("first_name") or "",
            lastName=r.get("last_name") or "",
            email=r.get("email") or "",
            managedDate=_fmt_day_month_year(r.get("managed_date")),
            anniversaryDate=_fmt_day_month_year(r.get("anniversary_date")),
            tone="success",
        )
        if enrich_map is not None:
            m = enrich_map.get(_safe_int(r.get("AID")), {})
            p7_num = float(m.get("purchased_7d") or 0)
            row.update(
                lifetimePurchase=format_lifetime_purchased(m) if m else fmt_money_short(0),
                lifetimePurchasedNum=float(m.get("lifetime_purchased") or 0),
                lifetimeHold=format_lifetime_hold(m) if m else "n/a",
                purchase7d=fmt_money_short(p7_num),
                purchase7dNum=p7_num,
            )
            row.update(
                build_anniversary_ticket_draft(
                    r,
                    locked=bool(r.get("locked")),
                    lock_reason=r.get("lock_reason") or "",
                    lock_reason_comment=r.get("lock_reason_comment") or "",
                    zendesk_user_id=m.get("zendesk_user_id"),
                )
            )
        out.append(row)
    return out


def build_birthday_gift_section(
    rows: list[dict], enrich_map: dict[int, dict] | None = None
) -> list[dict]:
    """Format raw Birthday Gift eligibility rows into payload dicts.

    Eligibility (lifetime Hold % + trailing-30-day purchase) is decided in
    birthday_gift_sql; this only formats and gates. Same outreach gate as
    Birthdays: locked, self-excluded, and TAB players are dropped entirely
    (elite-core). Hold %, LTP and 30-day purchase come straight off the row
    (the query already computed them over the whole book). enrich_map only
    supplies zendesk_user_id so the gift draft can pre-select the requester.
    """
    out = []
    for r in rows:
        if _birthday_row_excluded(
            bool(r.get("locked")),
            r.get("lock_reason") or "",
            r.get("lock_reason_comment") or "",
        ):
            continue
        age = r.get("age")
        try:
            age_i = int(age) if age is not None else None
        except (TypeError, ValueError):
            age_i = None
        dob_d = parse_date_val(r.get("dob"))
        dob_fmt = f"{dob_d.day}/{dob_d.month}/{dob_d.year}" if dob_d else ""
        gross = float(r.get("lifetime_purchased") or 0)
        net = float(r.get("lifetime_net_purchase") or 0)
        p30 = float(r.get("purchased_30d") or 0)
        row = aid_row(
            r.get("AID"),
            r.get("name") or "n/a",
            agent=r.get("agent") or "",
            agentName=agent_display(r.get("agent") or ""),
            firstName=r.get("first_name") or "",
            lastName=r.get("last_name") or "",
            email=r.get("email") or "",
            birthday=dob_fmt,
            age=age_i,
            holdPct=format_lifetime_hold(r),
            holdPctNum=(100 * net / gross) if gross > 0 else 0.0,
            lifetimePurchase=format_lifetime_purchased(r),
            lifetimePurchasedNum=gross,
            purchase30d=fmt_money_short(p30),
            purchase30dNum=p30,
            tone="success",
        )
        enrich = (enrich_map or {}).get(_safe_int(r.get("AID")), {})
        row.update(
            build_birthday_gift_ticket_draft(
                r,
                locked=bool(r.get("locked")),
                lock_reason=r.get("lock_reason") or "",
                lock_reason_comment=r.get("lock_reason_comment") or "",
                zendesk_user_id=enrich.get("zendesk_user_id"),
            )
        )
        out.append(row)
    return out


def build_responsiveness_section(
    rows: list[dict], enrich_map: dict[int, dict] | None = None
) -> list[dict]:
    """Format raw ticket-inactivity rows into payload dicts.

    Selection (last ticket activity older than TICKET_INACTIVITY_DAYS) is
    decided in ticket_inactivity_sql; this only formats and gates. Same
    outreach gate as Birthdays / Anniversary: locked, self-excluded, and TAB
    players are dropped entirely (elite-core). enrich_map (AID -> shared enrich
    row) folds in LTP / Hold / 30-day purchase from the batch already fetched
    for Open Tickets, so the silent-book list still shows account value.
    lastContact / daysSinceTicket come straight off the row.
    """
    out = []
    for r in rows:
        if _birthday_row_excluded(
            bool(r.get("locked")),
            r.get("lock_reason") or "",
            r.get("lock_reason_comment") or "",
        ):
            continue
        days = r.get("days_since_ticket")
        try:
            days_i = int(days) if days is not None else None
        except (TypeError, ValueError):
            days_i = None
        row = aid_row(
            r.get("AID"),
            r.get("name") or "n/a",
            agent=r.get("agent") or "",
            agentName=agent_display(r.get("agent") or ""),
            firstName=r.get("first_name") or "",
            lastName=r.get("last_name") or "",
            email=r.get("email") or "",
            lastContact=_fmt_day_month_year(r.get("last_ticket_date")),
            daysSinceTicket=days_i,
            tone="neutral",
        )
        if enrich_map is not None:
            m = enrich_map.get(_safe_int(r.get("AID")), {})
            gross = float(m.get("lifetime_purchased") or 0)
            net = float(m.get("lifetime_net_purchase") or 0)
            p30_num = float(m.get("purchased_30d") or 0)
            row.update(
                lifetimePurchase=format_lifetime_purchased(m) if m else fmt_money_short(0),
                lifetimePurchasedNum=gross,
                holdPct=format_lifetime_hold(m) if m else "n/a",
                holdPctNum=(100 * net / gross) if gross > 0 else 0.0,
                purchase30d=fmt_money_short(p30_num),
                purchase30dNum=p30_num,
            )
        out.append(row)
    return out


def build_big_winners_section(
    rows: list[dict],
    enrich_map: dict[int, dict] | None = None,
) -> list[dict]:
    """Players who won ≥ BIG_WINNER_SECTION_MIN on report_date.

    Non-Elite rows (is_elite=False / agent=None) are included and appear in
    every AM's tab — this is the only section that reaches outside the Elite
    book. Elite rows are filtered to their AM in focus_for_agent via isElite
    and agentName. Non-Elite rows carry a warning tone so they read as a
    portfolio-wide signal rather than the AM's own player.

    GGR sign: player win = negative GGR day. win_ggr is already the positive
    player win (flipped by the query: win_ggr = -ggr_day).
    """
    out = []
    for r in rows:
        is_elite = bool(r.get("is_elite"))
        agent_tag = r.get("agent") or ""
        agent_name = agent_display(agent_tag) if is_elite and agent_tag else ""
        win = float(r.get("win_ggr") or 0)
        sc_turnover = float(r.get("sc_turnover") or 0)
        sc_won = float(r.get("sc_won") or 0)
        pending_rd = float(r.get("pending_rd_amount") or 0)
        activity_d = parse_date_val(r.get("activity_date"))
        row = aid_row(
            r.get("AID"),
            r.get("name") or "n/a",
            agent=agent_tag,
            agentName=agent_name,
            isElite=is_elite,
            created=activity_d.isoformat() if activity_d else "",
            winGgr=fmt_money_short(win),
            winGgrNum=win,
            scTurnover=fmt_money_short(sc_turnover),
            scWon=fmt_money_short(sc_won),
            game=r.get("game") or "—",
            pendingRd=fmt_money_short(pending_rd) if pending_rd > 0 else "—",
            pendingRdNum=pending_rd,
            # Non-Elite: warning so the AM knows this is outside their book.
            # Elite: neutral — a big win is notable but not a risk flag itself.
            tone="warning" if not is_elite else "neutral",
        )
        if enrich_map is not None:
            m = enrich_map.get(_safe_int(r.get("AID")), {})
            ltp_num = float(m.get("lifetime_purchased") or 0)
            p7_num = float(m.get("purchased_7d") or 0)
            row.update(
                lifetimePurchase=format_lifetime_purchased(m) if m else fmt_money_short(0),
                lifetimePurchasedNum=ltp_num,
                purchase7d=fmt_money_short(p7_num),
                purchase7dNum=p7_num,
            )
        out.append(row)
    return out


def build_big_losers_section(
    rows: list[dict],
    enrich_map: dict[int, dict] | None = None,
) -> list[dict]:
    """Players who lost ≥ BIG_LOSER_SECTION_MIN to the house on report_date."""
    out = []
    for r in rows:
        is_elite = bool(r.get("is_elite"))
        agent_tag = r.get("agent") or ""
        agent_name = agent_display(agent_tag) if is_elite and agent_tag else ""
        loss = float(r.get("loss_ggr") or 0)
        sc_turnover = float(r.get("sc_turnover") or 0)
        sc_won = float(r.get("sc_won") or 0)
        pending_rd = float(r.get("pending_rd_amount") or 0)
        activity_d = parse_date_val(r.get("activity_date"))
        row = aid_row(
            r.get("AID"),
            r.get("name") or "n/a",
            agent=agent_tag,
            agentName=agent_name,
            isElite=is_elite,
            created=activity_d.isoformat() if activity_d else "",
            lossGgr=fmt_money_short(loss),
            lossGgrNum=loss,
            scTurnover=fmt_money_short(sc_turnover),
            scWon=fmt_money_short(sc_won),
            game=r.get("game") or "—",
            pendingRd=fmt_money_short(pending_rd) if pending_rd > 0 else "—",
            pendingRdNum=pending_rd,
            tone="warning" if not is_elite else "neutral",
        )
        if enrich_map is not None:
            m = enrich_map.get(_safe_int(r.get("AID")), {})
            ltp_num = float(m.get("lifetime_purchased") or 0)
            p7_num = float(m.get("purchased_7d") or 0)
            row.update(
                lifetimePurchase=format_lifetime_purchased(m) if m else fmt_money_short(0),
                lifetimePurchasedNum=ltp_num,
                purchase7d=fmt_money_short(p7_num),
                purchase7dNum=p7_num,
            )
        out.append(row)
    return out


def _classify_token(token: str) -> tuple[float, str]:
    norm = token.strip().lower()
    if norm in TICKET_ZENDESK_TIER1_FIELD_VALUES:
        return 2.0, "Redemption / Security"
    if norm in TICKET_ZENDESK_TIER2_FIELD_VALUES:
        return 1.5, "Account / KYC / Promo"
    for multiplier, label, pattern in TICKET_TOPIC_TIERS:
        if re.search(pattern, norm):
            return multiplier, label
    return TICKET_TOPIC_BASE_MULTIPLIER, TICKET_TOPIC_BASE_LABEL


def _label_multiplier(label: str) -> float:
    if label == "Redemption / Security":
        return 2.0
    if label == "Account / KYC / Promo":
        return 1.5
    if label == "Service Issue":
        return 1.2
    return TICKET_TOPIC_BASE_MULTIPLIER


def _ticket_topic(
    subjects: list[str],
    zendesk_fields: list[str] | None = None,
) -> tuple[float, str, list[str]]:
    """Return (best_multiplier, primary_label, topic_labels) for a player.

    Classifies Zendesk custom-field values (the agent-set Topic) before subject
    regex. Each distinct subject and field value is classified on its own.
    """
    unique_subjects = list(dict.fromkeys(s.strip() for s in subjects if s and str(s).strip()))
    unique_fields = list(
        dict.fromkeys(s.strip() for s in (zendesk_fields or []) if s and str(s).strip())
    )
    tokens = unique_fields + unique_subjects
    if not tokens:
        return TICKET_TOPIC_BASE_MULTIPLIER, TICKET_TOPIC_BASE_LABEL, [TICKET_TOPIC_BASE_LABEL]

    labels: list[str] = []
    best_mult = TICKET_TOPIC_BASE_MULTIPLIER
    primary = TICKET_TOPIC_BASE_LABEL

    for token in tokens:
        mult, label = _classify_token(token)
        if mult > best_mult:
            best_mult = mult
            primary = label
        if label not in labels:
            labels.append(label)

    ordered = [primary] + [l for l in labels if l != primary]
    if any(l != TICKET_TOPIC_BASE_LABEL for l in labels):
        ordered = [l for l in ordered if l != TICKET_TOPIC_BASE_LABEL]
    if not ordered:
        ordered = [TICKET_TOPIC_BASE_LABEL]
    # Do not show a lower-tier subject guess beside a security / self-exclusion topic.
    if best_mult >= 2.0:
        ordered = [l for l in ordered if _label_multiplier(l) >= 2.0] or [primary]

    return best_mult, primary, ordered[:2]


def build_zd_section(
    rows: list[dict],
    enrich_map: dict[int, dict] | None = None,
    report_date: date | None = None,
) -> list[dict]:
    """Format raw Open Tickets BQ rows into payload dicts.

    Rows are sorted descending by priority_score, which weights four lifetime
    financial signals by their normalised weights and scales the result by a
    topic multiplier derived from the ticket subjects.
    """
    enrich_map = enrich_map or {}
    out = []
    for r in rows:
        tids = _ticket_ids_list(r.get("ticket_ids"))
        tickets = [{"id": tid, "url": zendesk_ticket_url(tid)} for tid in tids]
        try:
            aid_i = int(r.get("AID") or 0)
        except (TypeError, ValueError):
            aid_i = 0
        enrich = enrich_map.get(aid_i, {})
        ltp_num = float(enrich.get("lifetime_purchased") or 0)
        lt_hold_num = float(enrich.get("lifetime_net_purchase") or 0)
        lt_ngr_num = float(enrich.get("lifetime_ngr") or 0)
        p30_num = float(enrich.get("purchased_30d") or 0)
        p7_num = float(enrich.get("purchased_7d") or 0)

        subjects: list[str] = list(r.get("subjects") or [])
        zendesk_fields: list[str] = list(r.get("zendesk_fields") or [])
        topic_mult, topic_label, topic_labels = _ticket_topic(subjects, zendesk_fields)
        oldest = parse_date_val(r.get("oldest_ticket_at"))
        if isinstance(oldest, datetime):
            oldest = oldest.date()
        latest = parse_date_val(r.get("latest_ticket_at"))
        if isinstance(latest, datetime):
            latest = latest.date()
        ticket_age_days = (report_date - oldest).days if report_date and oldest else None
        ticket_updated_age_days = (report_date - latest).days if report_date and latest else None
        if oldest:
            ticket_created = oldest.strftime("%d %b %Y")
        else:
            ticket_created = "—"
        if latest:
            ticket_updated = latest.strftime("%d %b %Y")
        else:
            ticket_updated = "—"

        raw_score = (
            lt_hold_num * TICKET_WEIGHT_LT_HOLD
            + lt_ngr_num * TICKET_WEIGHT_LT_NGR
            + ltp_num * TICKET_WEIGHT_LT_PURCHASE
            + p30_num * TICKET_WEIGHT_30D_PURCHASE
        ) * topic_mult

        out.append(
            aid_row(
                r.get("AID"),
                r.get("name") or "n/a",
                agent=r.get("agent") or "",
                agentName=agent_display(r.get("agent") or ""),
                openTickets=int(r.get("open_tickets") or 0),
                ticketIds=", ".join(tids),
                tickets=tickets,
                lifetimePurchase=format_lifetime_purchased(enrich)
                if enrich
                else fmt_money_short(0),
                lifetimePurchasedNum=ltp_num,
                lifetimeHold=format_lifetime_hold(enrich) if enrich else "n/a",
                purchase7d=fmt_money_short(p7_num),
                purchase7dNum=p7_num,
                topicLabel=topic_label,
                topicLabels=topic_labels,
                topicMult=topic_mult,
                ticketCreated=ticket_created,
                ticketAgeDays=ticket_age_days if ticket_age_days is not None and ticket_age_days >= 0 else None,
                ticketUpdated=ticket_updated,
                ticketUpdatedAgeDays=ticket_updated_age_days if ticket_updated_age_days is not None and ticket_updated_age_days >= 0 else None,
                priorityScore=round(raw_score, 2),
                priorityScoreFmt=fmt_money_short(raw_score),
                tone="info",
            )
        )
    out.sort(key=lambda x: float(x.get("priorityScore") or 0), reverse=True)
    return out


def build_lock_section(rows: list[dict], report_date: date) -> list[dict]:
    """Format raw Locked Players rows into payload dicts.

    Two selection paths (config.py), so a stale take-a-break is never missed
    just because it's no longer "new":
    - Any lock reason: locked_at within the trailing LOCKS_WINDOW_DAYS ending
      on report_date (1 = locked today) — the "what just happened" feed.
    - Take a break only: unlock date within LOCKS_REVIEW_WINDOW_DAYS days, or
      already passed — regardless of how long ago the lock started.
    """
    out = []
    for r in rows:
        locked_at_d = parse_date_val(r.get("locked_at"))
        if locked_at_d is None:
            continue
        age_days = (report_date - locked_at_d).days
        if age_days < 0:
            continue
        bucket, tone = lock_bucket(
            r.get("lock_reason") or "",
            r.get("lock_reason_comment") or "",
        )
        unlock, remaining_days = unlock_info(
            r.get("lock_reason") or "",
            r.get("lock_reason_comment") or "",
            locked_at_d,
            report_date,
        )
        locked_today = age_days < LOCKS_WINDOW_DAYS
        due_for_review = (
            remaining_days is not None and remaining_days <= LOCKS_REVIEW_WINDOW_DAYS
        )
        if bucket == "Take a break" and remaining_days is not None:
            if remaining_days < -LOCKS_TAB_EXPIRE_DAYS:
                continue
        if not (locked_today or due_for_review):
            continue
        # Emphasize take-a-break locks whose window has already ended (or ends
        # today) — the restriction is stale and should be removed.
        if remaining_days is not None and remaining_days <= 0:
            tone = "danger"
        out.append(
            aid_row(
                r.get("AID"),
                r.get("name") or "n/a",
                agent=r.get("agent") or "",
                agentName=agent_display(r.get("agent") or ""),
                bucket=bucket,
                lockReason=r.get("lock_reason") or "",
                unlockDetail=unlock,
                unlockRemainingDays=remaining_days,
                lockedAt=locked_at_d.isoformat() if locked_at_d else "",
                created=locked_at_d.isoformat() if locked_at_d else "",
                tone=tone,
            )
        )
    return out


def soften_decline_rows(rows: list[dict], raw_top20: list[dict]) -> list[dict]:
    """Re-map tones to green-heavy AM Brief palette; keep all other fields."""
    by_aid = {str(r.get("AID")): r for r in raw_top20}
    out = []
    for row in rows:
        code = (by_aid.get(row["aid"]) or {}).get("reason_code")
        row = dict(row)
        row["tone"] = soft_tone_for_code(code)
        if (row.get("urgency") or "").lower() == "none":
            row["tone"] = "neutral"
        out.append(row)
    return out


def greeting_lines(
    agent_name: str,
    weekday: str,
    *,
    purchase: str,
    purchase_share: str,
    purchased_players: int,
    player_share: str,
) -> list[str]:
    """Two-line morning intro for a per-AM Morning Brief.

    Uses **amount** markers so the HTML can bold the key numbers.
    """
    return [
        f"Good morning, {agent_name}.",
        (
            f"Your portfolio generated **{purchase}** on {weekday} ({purchase_share} of Elite purchase) · "
            f"**{purchased_players:,}** purchased players ({player_share} of Elite). "
            f"Own the gaps, clear blockers, and make {weekday} count 🚀"
        ),
    ]


def focus_for_agent(
    agent_name: str,
    weekday: str,
    *,
    top10: list[dict],
    decline: list[dict],
    rd5k: list[dict],
    rd_first: list[dict],
    birthdays: list[dict],
    anniversary: list[dict],
    birthday_gift: list[dict],
    zd: list[dict],
    locks: list[dict],
    big_winners: list[dict],
    big_losers: list[dict],
    purchase: dict | None,
    total_players: int,
    elite_rev: float,
    elite_ply: int,
    goals: dict | None = None,
) -> dict:
    """Assemble the full per-AM payload block from pre-built section lists."""

    def filt(rows: list[dict]) -> list[dict]:
        return [r for r in rows if r.get("agentName") == agent_name]

    def filt_bw(rows: list[dict]) -> list[dict]:
        # Non-Elite rows (isElite=False) appear in every AM's tab.
        # Elite rows only for their own AM.
        return [r for r in rows if not r.get("isElite") or r.get("agentName") == agent_name]

    zd_a = filt(zd)
    locks_a = filt(locks)
    bw_a = filt_bw(big_winners)
    bl_a = filt([r for r in big_losers if r.get("isElite")])
    exclusion = sum(1 for r in locks_a if r.get("bucket") == "Self-exclusion")
    tab = sum(1 for r in locks_a if r.get("bucket") == "Take a break")
    other = sum(1 for r in locks_a if r.get("bucket") == "Other locked")
    decline_a = list(decline)
    purch_num = float((purchase or {}).get("purchased") or 0)
    purch_ply = int((purchase or {}).get("purchased_players") or 0)
    purchase_fmt = fmt_money_short((purchase or {}).get("purchased"))
    purchase_share = f"{(purch_num / elite_rev * 100):.1f}%" if elite_rev else "—"
    player_share = f"{(purch_ply / elite_ply * 100):.1f}%" if elite_ply else "—"
    book_rate = f"{(purch_ply / total_players * 100):.1f}%" if total_players else "—"
    rd_a = filt(rd5k)
    open_zd = sum(int(r.get("openTickets") or 0) for r in zd_a)
    return {
        "agentName": agent_name,
        "greetingLines": greeting_lines(
            agent_name,
            weekday,
            purchase=purchase_fmt,
            purchase_share=purchase_share,
            purchased_players=purch_ply,
            player_share=player_share,
        ),
        "purchase": purchase_fmt,
        "purchasedPlayers": purch_ply,
        "totalPlayers": total_players,
        "purchaseNum": purch_num,
        "purchaseShare": purchase_share,
        "playerShare": player_share,
        "bookPurchaseRate": book_rate,
        "purchasedOfBook": f"{purch_ply} / {total_players}",
        "focus": {
            "openZd": open_zd,
            "locked": len(locks_a),
            "takeABreak": tab,
            "selfExclusion": exclusion,
            "otherLocked": other,
            "rdOver5k": len(rd_a),
            "birthdays": len(filt(birthdays)),
            "anniversary": len(filt(anniversary)),
            "birthdayGift": len(filt(birthday_gift)),
            "declineCount": len(decline_a),
            "bigWinners": len(bw_a),
            "bigLosers": len(bl_a),
        },
        "top10": filt(top10),
        "decline": decline_a,
        "rdOver5k": filt(rd5k),
        "rdFirstTime": filt(rd_first),
        "birthdays": filt(birthdays),
        "anniversary": filt(anniversary),
        "birthdayGift": filt(birthday_gift),
        "zendesk": zd_a,
        "locks": locks_a,
        "bigWinners": bw_a,
        "bigLosers": bl_a,
        "goals": goals,
    }


def build_am_shares_and_overview(agents: list[dict]) -> tuple[list[dict], list[dict]]:
    """Derive amShares and overview from the assembled agents list.

    amShares: one row per AM with purchase/book metrics for the Dashboard card.
    overview: same plus the focus counters, for the Overview table.

    Previously duplicated inline in build_payload (generate_am_daily_dashboard)
    and in testing/payload_fixtures._am_shares_and_overview. Phase 3 extracts
    it once here so neither caller can drift.
    """
    am_shares = [
        {
            "agentName": a["agentName"],
            "purchase": a["purchase"],
            "purchasedPlayers": a["purchasedPlayers"],
            "totalPlayers": a["totalPlayers"],
            "purchasedOfBook": a["purchasedOfBook"],
            "bookPurchaseRate": a["bookPurchaseRate"],
            "purchaseShare": a["purchaseShare"],
            "playerShare": a["playerShare"],
            "tone": "success",
        }
        for a in agents
    ]
    overview = [
        {
            "agentName": a["agentName"],
            "purchase": a["purchase"],
            "purchasedPlayers": a["purchasedPlayers"],
            "totalPlayers": a["totalPlayers"],
            "purchasedOfBook": a["purchasedOfBook"],
            **a["focus"],
            "tone": "success",
        }
        for a in agents
    ]
    return am_shares, overview
