"""
Elite AM Brief — morning board per AM (Coral, Gabriel, Lee, Rachel, Alon).

Run from repo root:
  python am_daily_dashboard/generate_am_daily_dashboard.py
  python am_daily_dashboard/generate_am_daily_dashboard.py --date 2026-07-27
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PACKAGE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PACKAGE_DIR))

from elite_lib.bigquery import HEAVY_QUERY_SCAN_CAP_BYTES, get_client, run_query  # noqa: E402
from elite_lib.export_paths import mirror_to_cursor  # noqa: E402

from config import (  # noqa: E402
    LOCKS_REVIEW_WINDOW_DAYS,
    LOCKS_WINDOW_DAYS,
    PENDING_RD_LOOKBACK_DAYS,
    manager_gate_token,
)
import queries as am_queries  # noqa: E402
from goals import (  # noqa: E402
    GOALS_AGENT_DISPLAY,
    GOALS_AGENT_TAGS,
    INCLUDED_WEIGHT_TOTAL,
    actuals_by_agent,
    build_agent_goals_block,
    strip_payload_for_am,
    targets_for_month,
)
from goals_reference import (  # noqa: E402
    gap_text,
    load_reference_tsv,
    reference_for,
)
from am_brief_canvas import render_am_brief_canvas  # noqa: E402
from canvas_to_html import publish_am_brief, write_am_brief_html  # noqa: E402
from daily_summary.generate_daily_elite_canvas import build_report, build_top10_rows, fmt_money_short  # noqa: E402
from daily_summary.generate_daily_elite_summary import (  # noqa: E402
    build_sql,
    day_row,
    looker_account_portal_url,
    weekday_label,
    zendesk_ticket_url,
)
from wow_drop_analysis.wow_drop_reason import (  # noqa: E402
    AGENT_TAG_LABELS,
    _take_a_break_days,
    enrich_aids_sql,
    fetch_top_same_day_by_agent,
    format_agent_name,
    format_lifetime_hold,
    format_lifetime_purchased,
)
from am_brief_ticket_drafts import (  # noqa: E402
    build_birthday_ticket_draft,
    build_first_time_rd_ticket_draft,
)

OUTPUT_DIR = Path(__file__).resolve().parent / "exports"
DEFAULT_CANVAS_DIR = Path(
    r"C:\Users\Owner\.cursor\projects\c-Users-Owner-Downloads-Elite\canvases"
)

AM_ORDER = ["Coral", "Gabriel", "Lee", "Rachel", "Alon"]
# Goals exports (file-level isolation) — Alon omitted.
GOALS_AM_ORDER = ["Coral", "Gabriel", "Lee", "Rachel"]

UPGRADES_NOTE = (
    "Upgrade to Elite = first Elite `dbt_utils.elite_account_tags` snapshot "
    "in the month through as-of, for accounts that were not Elite on the last "
    "snapshot before month start. Tag history starts 2026-04-08; attributed to "
    "tag_agent_1 on that first in-window snapshot (not current roster only)."
)

# Soften red vs daily decline baseline
AM_REASON_TONE = {
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


def resolve_report_date(arg: str | None) -> date:
    if arg:
        return date.fromisoformat(arg)
    return date.today() - timedelta(days=1)


def agent_display(tag: str) -> str:
    return AGENT_TAG_LABELS.get(tag, format_agent_name({"agent": tag}))


def soft_tone_for_code(code: str | None) -> str:
    if not code:
        return "warning"
    return AM_REASON_TONE.get(code, "warning")


def lock_bucket(lock_reason: str, lock_comment: str) -> tuple[str, str]:
    """Return (bucket, tone)."""
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
    """Returns (display text, remaining days) for a take-a-break lock.
    remaining_days <= 0 means today/overdue — the restriction should be
    removed. None means no calculable unlock date (e.g. self-exclusion,
    other locked, or a break with no locked_at)."""
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


def parse_date_val(val) -> date | None:
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


def aid_row(aid: object, name: str = "", **extra) -> dict:
    aid_s = str(aid or "").strip()
    return {
        "aid": aid_s,
        "aidUrl": looker_account_portal_url(aid_s),
        "name": name or "n/a",
        **extra,
    }


def build_top10_section(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
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
                tone="success",
            )
        )
    return out


def build_rd_section(
    rows: list[dict],
    report_date: date | None = None,
    aging_threshold_days: int | None = None,
    ticket_enrich: dict[int, dict] | None = None,
) -> list[dict]:
    """aging_threshold_days: flag rows created this many days ago or earlier
    (e.g. PENDING_RD_LOOKBACK_DAYS - 1) so agents can see which pending
    redemptions are nearing the edge of the lookback window. Pass None
    (default) to skip aging entirely — e.g. First-Time Locked RD isn't
    windowed the same way.

    ticket_enrich: when provided (AID -> {"zendesk_user_id": ...}), attaches
    a Zendesk ticket draft (build_first_time_rd_ticket_draft), gated by the
    account's own locked/lock_reason (elite-core: never recommend retention
    outreach for a locked or self-excluded account). Pass None (default) to
    skip — Pending RD >=5k is view-only, no ticket draft offered there."""
    out = []
    for r in rows:
        created_d = parse_date_val(r.get("created_date"))
        days_pending = (report_date - created_d).days if (report_date and created_d) else None
        aging_flag = (
            aging_threshold_days is not None
            and days_pending is not None
            and days_pending >= aging_threshold_days
        )
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
            tone="danger" if aging_flag else "warning",
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
    """ticket_enrich: see build_rd_section — same locked/self-exclusion gate,
    applied here via build_birthday_ticket_draft."""
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


def _ticket_ids_list(raw) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        return [p.strip() for p in raw.split(",") if p.strip()]
    try:
        return [str(t).strip() for t in list(raw) if t is not None and str(t).strip()]
    except TypeError:
        s = str(raw).strip()
        return [s] if s else []


def build_zd_section(rows: list[dict], enrich_map: dict[int, dict] | None = None) -> list[dict]:
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
    """Two ways in, so a stale take-a-break is never missed just because it's
    no longer "new" (config.py):
    - Any lock reason: locked_at within the trailing LOCKS_WINDOW_DAYS
      ending on report_date (1 day = locked today) — the "what just
      happened" feed.
    - Take a break only: unlock date within LOCKS_REVIEW_WINDOW_DAYS days,
      or already passed — regardless of how long ago the lock started."""
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
        # Emphasize take-a-break locks whose window has already ended (or
        # ends today) — the restriction is stale and should be removed.
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
    """Re-map tones to green-heavy palette; keep Looker/ticket/reason fields."""
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
    """Intro lines. Use **amount** markers for bold in canvas/HTML."""
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


def build_goals_blocks(report_date: date, client) -> dict[str, dict | None]:
    """Goals block per AM display name. One query, so `--goals-only` can verify
    the numbers without paying for the whole board."""
    print("  Fetching Elite Goals MTD actuals...")
    goals_raw = run_query(
        client,
        am_queries.goals_mtd_actuals_sql(report_date),
        maximum_bytes_billed=HEAVY_QUERY_SCAN_CAP_BYTES,
    )
    goals_actuals = actuals_by_agent(goals_raw)
    goals_targets = targets_for_month(report_date)
    goals_by_display: dict[str, dict | None] = {}
    for tag in GOALS_AGENT_TAGS:
        block = build_agent_goals_block(
            tag,
            goals_targets.get(tag),
            goals_actuals.get(tag) or {},
            report_date,
            upgrades_available=True,
            upgrades_note=UPGRADES_NOTE,
        )
        goals_by_display[GOALS_AGENT_DISPLAY[tag]] = block
        if block and block.get("available"):
            purchasers = next(
                (
                    k["actual"]
                    for k in block["kpis"]
                    if k["key"] == "monthly_purchasers"
                ),
                None,
            )
            print(
                f"    {GOALS_AGENT_DISPLAY[tag]}: purchasers={purchasers} "
                f"tracked={block.get('weightedTrackedDisplay')}"
            )
    for name in AM_ORDER:
        if name not in goals_by_display:
            goals_by_display[name] = None  # Alon
    return goals_by_display


def build_payload(report_date: date, client) -> dict:
    print(f"Fetching AM Brief data for {report_date}...")
    top10_raw = run_query(client, am_queries.top10_purchasers_sql(report_date))
    print(f"  Top 10 rows: {len(top10_raw)}")
    rd5k_raw = run_query(client, am_queries.locked_rd_over_5k_sql(report_date))
    print(f"  Pending Redemptions (>=$5k, 3d): {len(rd5k_raw)}")
    rd_first_raw = run_query(client, am_queries.first_time_locked_rd_sql())
    print(f"  First-time locked RD: {len(rd_first_raw)}")
    bday_raw = run_query(client, am_queries.birthdays_last_3d_sql(report_date))
    print(f"  Birthdays (3d): {len(bday_raw)}")
    zd_raw = run_query(client, am_queries.open_zendesk_sql())
    print(f"  Open ZD players: {len(zd_raw)}")
    # One shared enrich fetch (lifetime purchase/hold for Open Tickets, plus
    # zendesk_user_id so First-Time Locked RD / Birthdays tickets can
    # pre-select the requester) covering every AID that needs it.
    ticket_aids: set[int] = set()
    for r in zd_raw:
        try:
            ticket_aids.add(int(r["AID"]))
        except (TypeError, ValueError, KeyError):
            continue
    for r in (*rd_first_raw, *bday_raw):
        try:
            ticket_aids.add(int(r["AID"]))
        except (TypeError, ValueError, KeyError):
            continue
    shared_enrich: dict[int, dict] = {}
    if ticket_aids:
        print(f"  Enriching metrics for {len(ticket_aids)} AIDs (Open Tickets, RD, Birthdays)...")
        shared_enrich = {
            int(e["AID"]): e
            for e in run_query(client, enrich_aids_sql(sorted(ticket_aids), report_date))
        }
    zd = build_zd_section(zd_raw, shared_enrich)
    locks_raw = run_query(client, am_queries.locked_players_sql())
    print(f"  Locked players (raw): {len(locks_raw)}")
    purchase_raw = run_query(client, am_queries.agent_day_purchase_sql(report_date))
    purchase_by_tag = {r["agent"]: r for r in purchase_raw}
    book_raw = run_query(client, am_queries.agent_book_size_sql())
    book_by_tag = {r["agent"]: int(r.get("total_players") or 0) for r in book_raw}
    print(f"  AM book sizes: {len(book_by_tag)} agents")

    goals_by_display = build_goals_blocks(report_date, client)

    print("  Fetching Elite / Jackpota weekday summary...")
    sql = build_sql(report_date)
    day_rows = run_query(client, sql["weekday_compare"])
    overall_rows = run_query(client, sql["overall_weekday_compare"])
    decline_report = build_report(report_date, day_rows, overall_rows)
    prior_day = report_date - timedelta(days=7)
    elite_this = day_row(day_rows, report_date)
    elite_prior = day_row(day_rows, prior_day)
    elite_wow_drop = max(
        0.0,
        float(elite_prior.get("revenue") or 0) - float(elite_this.get("revenue") or 0),
    )
    elite_rev = float(elite_this.get("revenue") or 0)
    elite_ply = int(elite_this.get("players") or 0)

    print("  Fetching Top 20 same-day decline per AM (Daily Elite logic)...")
    decline_by_am_raw = fetch_top_same_day_by_agent(
        client,
        report_date,
        AM_ORDER,
        elite_wow_drop=elite_wow_drop,
    )
    decline_by_am = {
        name: soften_decline_rows(build_top10_rows(raw), raw)
        for name, raw in decline_by_am_raw.items()
    }
    for name, rows in decline_by_am.items():
        print(f"    {name}: {len(rows)} Top 20 rows")

    top10 = build_top10_section(top10_raw)
    rd5k = build_rd_section(
        rd5k_raw, report_date, aging_threshold_days=PENDING_RD_LOOKBACK_DAYS - 1
    )
    rd_first = build_rd_section(rd_first_raw, ticket_enrich=shared_enrich)
    birthdays = build_birthday_section(bday_raw, ticket_enrich=shared_enrich)
    locks = build_lock_section(locks_raw, report_date)
    print(f"  Locked after past-day window filter: {len(locks)}")

    weekday = weekday_label(report_date)
    subtitle = f"{weekday} {report_date.strftime('%d %b %Y')}"
    day_short = weekday[:3]

    agents = []
    for name in AM_ORDER:
        purchase = None
        total_players = 0
        for tag, row in purchase_by_tag.items():
            if agent_display(tag) == name:
                purchase = row
                break
        for tag, n in book_by_tag.items():
            if agent_display(tag) == name:
                total_players = n
                break
        agents.append(
            focus_for_agent(
                name,
                weekday,
                top10=top10,
                decline=decline_by_am.get(name, []),
                rd5k=rd5k,
                rd_first=rd_first,
                birthdays=birthdays,
                zd=zd,
                locks=locks,
                purchase=purchase,
                total_players=total_players,
                elite_rev=elite_rev,
                elite_ply=elite_ply,
                goals=goals_by_display.get(name),
            )
        )

    am_shares = []
    for a in agents:
        am_shares.append(
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
        )

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

    return {
        "report": {
            "date": report_date.isoformat(),
            "weekday": weekday,
            "dayShort": day_short,
            "subtitle": subtitle,
            "title": "Elite AM Brief",
            "headline": decline_report.get("headline") or "",
            "segmentTitle": f"{weekday} vs last {weekday} · Elite & Jackpota",
            "overviewGreetingLines": [
                "Good morning.",
                f"Here is your {weekday} summary.",
                "Good luck 🚀",
            ],
            "segments": decline_report.get("segments") or [],
        },
        "amShares": am_shares,
        "overview": overview,
        "agents": agents,
        "amOrder": AM_ORDER,
        "goalsMeta": {
            "includedWeightTotal": INCLUDED_WEIGHT_TOTAL,
            "upgradesNote": UPGRADES_NOTE,
            "asOf": report_date.isoformat(),
            "goalsAmOrder": GOALS_AM_ORDER,
        },
        # Manager-only. strip_payload_for_am rebuilds the payload from a fixed
        # key list, so this never reaches a per-AM file.
        "managerGate": manager_gate_token(),
    }


def write_outputs(
    payload: dict, canvas_dir: Path, *, publish: bool = False
) -> tuple[Path, Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    canvas_dir.mkdir(parents=True, exist_ok=True)
    d = payload["report"]["date"]
    canvas_path = canvas_dir / f"elite-am-brief-{d}.canvas.tsx"
    canvas_path.write_text(render_am_brief_canvas(payload), encoding="utf-8")
    html_path = OUTPUT_DIR / f"{d}_elite_am_brief.html"
    write_am_brief_html(payload, html_path)
    json_path = OUTPUT_DIR / f"{d}_elite_am_brief.json"
    json_path.write_text(
        json.dumps(payload, indent=2, default=str),
        encoding="utf-8",
    )
    # Clean prior Focus slug artifacts for same date if present
    old_canvas = canvas_dir / f"elite-am-focus-{d}.canvas.tsx"
    if old_canvas.exists():
        old_canvas.unlink()

    per_am_paths: list[Path] = []
    for name in GOALS_AM_ORDER:
        slug = name.lower()
        am_payload = strip_payload_for_am(payload, name)
        am_html = OUTPUT_DIR / f"{d}_elite_am_brief_{slug}.html"
        am_json = OUTPUT_DIR / f"{d}_elite_am_brief_{slug}.json"
        write_am_brief_html(am_payload, am_html)
        am_json.write_text(
            json.dumps(am_payload, indent=2, default=str),
            encoding="utf-8",
        )
        am_canvas = canvas_dir / f"elite-am-brief-{d}-{slug}.canvas.tsx"
        am_canvas.write_text(render_am_brief_canvas(am_payload), encoding="utf-8")
        per_am_paths.extend([am_html, am_json])
        print(f"  Per-AM: {am_html.name}")

    if publish:
        publish_am_brief(html_path)
    mirror_to_cursor("am_brief", html_path, json_path, *per_am_paths)
    return canvas_path, html_path


def print_goals_audit(payload: dict) -> None:
    """Compact audit table for verification against external Goals sheet.

    Adds Yours / Gap columns for any AM and as-of date present in
    data/elite_goals_reference.tsv, so a drift against the AM's own table shows up
    in the audit itself rather than in a manual read-out. See goals_reference.py.
    """
    reference = load_reference_tsv()
    print("\n=== Goals audit (as of report date) ===")
    has_ref = bool(reference)
    header = (
        f"{'AM':<10} {'KPI':<28} {'Goal':>12} {'Actual':>12} {'Pace':>12} "
        f"{'Status':<10}"
    )
    if has_ref:
        header += f" {'Yours':>12} {'Gap':>16}"
    print(header)
    print("-" * len(header))
    for a in payload.get("agents") or []:
        goals = a.get("goals")
        if not goals or not goals.get("available"):
            continue
        theirs = (
            reference_for(reference, goals.get("agent") or "", goals.get("asOf") or "")
            if has_ref
            else {}
        )
        for k in goals.get("kpis") or []:
            line = (
                f"{a['agentName']:<10} {k['label']:<28} "
                f"{k.get('goalDisplay') or '—':>12} "
                f"{k.get('actualDisplay') or '—':>12} "
                f"{k.get('paceDisplay') or '—':>12} "
                f"{k.get('status') or '—':<10}"
            )
            if has_ref:
                mine, gap = gap_text(
                    k["label"], k.get("actual"), theirs.get(k["label"])
                )
                line += f" {mine:>12} {gap:>16}"
            print(line)
        tracked = goals.get("weightedTrackedDisplay") or "—"
        print(f"{a['agentName']:<10} {'(weighted tracked)':<28} {'':>12} {'':>12} {tracked:>12}")
        shapes = (
            f"purchasers {goals.get('purchasersShape') or 0:.3f} / "
            f"upgrades {goals.get('upgradesShape') or 0:.3f}"
        )
        print(f"{a['agentName']:<10} {'(month-shape divisors)':<28} {shapes}")
        print(
            f"{a['agentName']:<10} {'(net if paid-redeem instead)':<28} "
            f"{'':>12} ${goals.get('dailyNetPaidRedeem') or 0:>11,.0f}"
        )
        print(
            f"{a['agentName']:<10} {'(portfolio: tagged book)':<28} "
            f"{goals.get('portfolioSize') or 0:>12,} "
            f"{'':>11}"
            f"   ({goals.get('portfolioLocked') or 0} locked, still counted)"
        )
        snap = goals.get("bookSnapshotDate") or ""
        as_of = goals.get("asOf") or ""
        drift = "" if snap == as_of else "  <-- DRIFTED, book is not the report date"
        print(
            f"{a['agentName']:<10} {'(book tag snapshot)':<28} "
            f"{snap or '—':>12}{drift}"
        )
        print("-" * len(header))



def main() -> None:
    parser = argparse.ArgumentParser(description="Elite AM Brief morning board")
    parser.add_argument("--date", help="Report date YYYY-MM-DD (default: yesterday)")
    parser.add_argument(
        "--canvas-dir",
        type=Path,
        default=DEFAULT_CANVAS_DIR,
        help="Canvas output directory",
    )
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Copy HTML into docs/ for GitHub Pages (off by default; local review only)",
    )
    parser.add_argument(
        "--goals-only",
        action="store_true",
        help="Print the Goals audit from one query and exit; writes no files. "
        "Use to check Goal/MTD/Pace against an external sheet.",
    )
    args = parser.parse_args()
    report_date = resolve_report_date(args.date)
    client = get_client()
    if args.goals_only:
        goals = build_goals_blocks(report_date, client)
        print_goals_audit(
            {
                "agents": [
                    {"agentName": name, "goals": block}
                    for name, block in goals.items()
                    if block
                ]
            }
        )
        return
    payload = build_payload(report_date, client)
    canvas_path, html_path = write_outputs(
        payload, args.canvas_dir, publish=args.publish
    )
    print_goals_audit(payload)
    print(f"Wrote {canvas_path}")
    print(f"Wrote {html_path}")


if __name__ == "__main__":
    main()
