"""Pure payload-building functions for the Elite AM Brief.

Every function here is a pure transformation from raw BigQuery rows (dicts) to
payload dicts. No BigQuery calls, no file I/O, no side effects.  These can be
unit-tested directly (see test_payload_builders.py) without any credentials or
mocked clients.

Extracted from generate_am_daily_dashboard.py in Phase 3 (2026-08-19) so the
god-module becomes a thin orchestration shell over testable builders.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

from config import LOCKS_REVIEW_WINDOW_DAYS, LOCKS_WINDOW_DAYS  # noqa: E402
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
    build_birthday_ticket_draft,
    build_first_time_rd_ticket_draft,
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


def build_top10_section(rows: list[dict]) -> list[dict]:
    """Format raw Top 10 Purchasers BQ rows into payload dicts."""
    out = []
    for r in rows:
        unit_min = r.get("offer_unit_min")
        unit_max = r.get("offer_unit_max")
        out.append(
            aid_row(
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
                packageFit=build_package_fit(
                    r.get("usual_price"),
                    r.get("usual_price_orders"),
                    r.get("ceiling_price"),
                ),
                tone="success",
            )
        )
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
    applied via build_birthday_ticket_draft.
    """
    out = []
    for r in rows:
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


def build_zd_section(rows: list[dict], enrich_map: dict[int, dict] | None = None) -> list[dict]:
    """Format raw Open Tickets BQ rows into payload dicts."""
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
        p7_num = float(enrich.get("purchased_7d") or 0)
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
                tone="info",
            )
        )
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
    total_players: int,
    player_share: str,
) -> list[str]:
    """Three-line morning greeting for a per-AM tab intro.

    Uses **amount** markers so the canvas/HTML can bold the key numbers.
    """
    if total_players > 0:
        book_bit = (
            f"**{purchased_players}** of your **{total_players}** Elite players purchased"
        )
    else:
        book_bit = f"**{purchased_players}** purchased players"
    return [
        f"Good morning, {agent_name}.",
        (
            f"Your {weekday} brief is ready, and the Elite book feels your hand on it. "
            f"You drove **{purchase}** ({purchase_share} of Elite purchase) with "
            f"**{purchased_players}** purchased players ({player_share} of Elite)."
        ),
        (
            f"That's {book_bit}. Shoulder tap: they lean on you for a reason. "
            f"Own the gaps, clear the blockers, and make {weekday} count 🚀"
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
    zd: list[dict],
    locks: list[dict],
    purchase: dict | None,
    total_players: int,
    elite_rev: float,
    elite_ply: int,
    goals: dict | None = None,
) -> dict:
    """Assemble the full per-AM payload block from pre-built section lists."""

    def filt(rows: list[dict]) -> list[dict]:
        return [r for r in rows if r.get("agentName") == agent_name]

    zd_a = filt(zd)
    locks_a = filt(locks)
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
    return {
        "agentName": agent_name,
        "greetingLines": greeting_lines(
            agent_name,
            weekday,
            purchase=purchase_fmt,
            purchase_share=purchase_share,
            purchased_players=purch_ply,
            total_players=total_players,
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
            "openZd": sum(int(r.get("openTickets") or 0) for r in zd_a),
            "locked": len(locks_a),
            "takeABreak": tab,
            "selfExclusion": exclusion,
            "otherLocked": other,
            "rdOver5k": len(filt(rd5k)),
            "birthdays": len(filt(birthdays)),
            "declineCount": len(decline_a),
        },
        "top10": filt(top10),
        "decline": decline_a,
        "rdOver5k": filt(rd5k),
        "rdFirstTime": filt(rd_first),
        "birthdays": filt(birthdays),
        "zendesk": zd_a,
        "locks": locks_a,
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
