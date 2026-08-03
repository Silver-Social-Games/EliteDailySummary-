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
sys.path.insert(0, str(PROJECT_ROOT / "decline_check"))

from elite_lib.bigquery import get_client, run_query  # noqa: E402

import queries as am_queries  # noqa: E402
from am_brief_canvas import render_am_brief_canvas  # noqa: E402
from canvas_to_html import publish_am_brief, write_am_brief_html  # noqa: E402
from generate_daily_elite_canvas import build_report, build_top10_rows, fmt_money_short  # noqa: E402
from generate_daily_elite_summary import (  # noqa: E402
    build_sql,
    day_row,
    looker_account_portal_url,
    weekday_label,
    zendesk_ticket_url,
)
from wow_drop_reason import (  # noqa: E402
    AGENT_TAG_LABELS,
    _take_a_break_days,
    enrich_aids_sql,
    fetch_top_same_day_by_agent,
    format_agent_name,
    format_lifetime_hold,
    format_lifetime_purchased,
)

OUTPUT_DIR = Path(__file__).resolve().parent / "exports"
DEFAULT_CANVAS_DIR = Path(
    r"C:\Users\Owner\.cursor\projects\c-Users-Owner-Downloads-Elite\canvases"
)

AM_ORDER = ["Coral", "Gabriel", "Lee", "Rachel", "Alon"]

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


def unlock_line(
    lock_reason: str,
    lock_comment: str,
    locked_at: date | None,
    report_date: date,
) -> str:
    days = _take_a_break_days(lock_reason or "") or _take_a_break_days(lock_comment or "")
    if not days:
        return ""
    if not locked_at:
        return f"Take a break {days} days"
    unlock = locked_at + timedelta(days=days)
    remaining = (unlock - report_date).days
    if remaining > 0:
        return f"{remaining}d left · unlock {unlock.isoformat()}"
    if remaining == 0:
        return "Unlock today — remove restriction"
    return f"Ended {unlock.isoformat()} — remove restriction"


def parse_date_val(val) -> date | None:
    if val is None or val == "":
        return None
    if hasattr(val, "isoformat") and not isinstance(val, str):
        return val if isinstance(val, date) else val.date()  # type: ignore[attr-defined]
    return date.fromisoformat(str(val)[:10])


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


def build_rd_section(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        out.append(
            aid_row(
                r.get("AID"),
                r.get("name") or "n/a",
                agent=r.get("agent") or "",
                agentName=agent_display(r.get("agent") or ""),
                redeemId=str(r.get("redeem_id") or ""),
                amount=fmt_money_short(r.get("amount")),
                amountNum=float(r.get("amount") or 0),
                status=r.get("status") or "locked",
                created=str(r.get("created_date") or ""),
                tone="warning",
            )
        )
    return out


def build_birthday_section(rows: list[dict]) -> list[dict]:
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
        out.append(
            aid_row(
                r.get("AID"),
                r.get("name") or "n/a",
                agent=r.get("agent") or "",
                agentName=agent_display(r.get("agent") or ""),
                email=r.get("email") or "",
                dob=dob_fmt,
                age=age_i,
                tone="success",
            )
        )
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
    """Still locked and first locked/updated on report_date (past day), any reason."""
    out = []
    for r in rows:
        locked_at_d = parse_date_val(r.get("locked_at"))
        if locked_at_d != report_date:
            continue
        bucket, tone = lock_bucket(
            r.get("lock_reason") or "",
            r.get("lock_reason_comment") or "",
        )
        unlock = unlock_line(
            r.get("lock_reason") or "",
            r.get("lock_reason_comment") or "",
            locked_at_d,
            report_date,
        )
        out.append(
            aid_row(
                r.get("AID"),
                r.get("name") or "n/a",
                agent=r.get("agent") or "",
                agentName=agent_display(r.get("agent") or ""),
                bucket=bucket,
                lockReason=r.get("lock_reason") or "",
                unlockDetail=unlock,
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
    }


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
    zd_enrich: dict[int, dict] = {}
    zd_aids = []
    for r in zd_raw:
        try:
            zd_aids.append(int(r["AID"]))
        except (TypeError, ValueError, KeyError):
            continue
    if zd_aids:
        print(f"  Enriching Open Tickets metrics for {len(zd_aids)} AIDs...")
        zd_enrich = {
            int(e["AID"]): e
            for e in run_query(client, enrich_aids_sql(zd_aids, report_date))
        }
    zd = build_zd_section(zd_raw, zd_enrich)
    locks_raw = run_query(client, am_queries.locked_players_sql())
    print(f"  Locked players (raw): {len(locks_raw)}")
    purchase_raw = run_query(client, am_queries.agent_day_purchase_sql(report_date))
    purchase_by_tag = {r["agent"]: r for r in purchase_raw}
    book_raw = run_query(client, am_queries.agent_book_size_sql())
    book_by_tag = {r["agent"]: int(r.get("total_players") or 0) for r in book_raw}
    print(f"  AM book sizes: {len(book_by_tag)} agents")

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
    rd5k = build_rd_section(rd5k_raw)
    rd_first = build_rd_section(rd_first_raw)
    birthdays = build_birthday_section(bday_raw)
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
    (OUTPUT_DIR / f"{d}_elite_am_brief.json").write_text(
        json.dumps(payload, indent=2, default=str),
        encoding="utf-8",
    )
    # Clean prior Focus slug artifacts for same date if present
    old_canvas = canvas_dir / f"elite-am-focus-{d}.canvas.tsx"
    if old_canvas.exists():
        old_canvas.unlink()
    if publish:
        publish_am_brief(html_path)
    return canvas_path, html_path


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
    args = parser.parse_args()
    report_date = resolve_report_date(args.date)
    client = get_client()
    payload = build_payload(report_date, client)
    canvas_path, html_path = write_outputs(
        payload, args.canvas_dir, publish=args.publish
    )
    print(f"Wrote {canvas_path}")
    print(f"Wrote {html_path}")


if __name__ == "__main__":
    main()
