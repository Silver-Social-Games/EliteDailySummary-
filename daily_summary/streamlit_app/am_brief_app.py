"""Streamlit view of an existing Elite AM Brief JSON export (no BigQuery regen)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
import streamlit as st

EXPORTS = Path(__file__).resolve().parent.parent.parent / "am_daily_dashboard" / "exports"


def _wow_color(value: str) -> str:
    v = str(value or "").strip()
    pct = re.search(r"\(([+-]?\d+(?:\.\d+)?)%\)", v)
    n = float(pct.group(1)) if pct else None
    up = (n is not None and n > 0) or (v.startswith("+") and not v.startswith("+$0"))
    down = (n is not None and n < 0) or v.startswith("-") or v.startswith("$-")
    if up:
        return "color:#1F8A65;font-weight:600"
    if down:
        return "color:#CF2D56;font-weight:600"
    return ""


def _style_wow(series: pd.Series) -> list[str]:
    return [f"{_wow_color(v)}" if _wow_color(v) else "" for v in series]


def _sort_by_num(rows: list[dict], key: str, desc: bool = True) -> list[dict]:
    """Mirrors sortByNumKey() in canvas_parts/cells.py: missing/NaN values
    always sort last regardless of direction."""

    def sort_key(r: dict):
        v = r.get(key)
        try:
            v = float(v)
            is_nan = False
        except (TypeError, ValueError):
            v = 0.0
            is_nan = True
        return (1 if is_nan else 0, (-v if desc else v))

    return sorted(rows, key=sort_key)


def _sort_locks_by_soonest_unlock(rows: list[dict]) -> list[dict]:
    """Mirrors sortBySoonestUnlock() in canvas_parts/cells.py: rows with no
    calculable unlock (self-exclusion, other locked) sort last, always."""

    def sort_key(r: dict):
        v = r.get("unlockRemainingDays")
        return (1, 0) if v is None else (0, v)

    return sorted(rows, key=sort_key)


def _format_created_with_aging(row: dict) -> str:
    created = row.get("created") or ""
    days = row.get("daysPending")
    if isinstance(days, (int, float)):
        return f"{created} ({int(days)}d ago)"
    return created


def _style_flagged(series: pd.Series, flags: list[bool]) -> list[str]:
    return ["color:#CF2D56;font-weight:600" if f else "" for f in flags]


def _ticket_preview(row: dict) -> str:
    if row.get("ticketEnabled"):
        subject = row.get("ticketSubject") or "Draft"
        return f"\U0001F4DD {subject}"
    reason = row.get("ticketDisabledReason")
    return reason if reason else "\u2014"


def render_ticket_draft_picker(rows: list[dict], key: str, empty_msg: str = "No rows to show.") -> None:
    """Review-only Zendesk ticket draft viewer (subject/body/open link), same
    policy as the canvas TicketDraftModal: agent edits, copies, opens
    Zendesk, and sends manually. Nothing here is auto-created or auto-sent."""
    if not rows:
        st.caption(empty_msg)
        return
    labels = [f"{r.get('name') or 'Unknown'} (AID {r.get('aid')})" for r in rows]
    idx = st.selectbox(
        "Select a row",
        options=list(range(len(rows))),
        format_func=lambda i: labels[i],
        key=key,
    )
    row = rows[idx]
    if row.get("ticketEnabled"):
        st.text_input("Subject", value=row.get("ticketSubject") or "", disabled=True, key=f"{key}_subject")
        st.text_area("Message", value=row.get("ticketBody") or "", height=220, disabled=True, key=f"{key}_body")
        if row.get("zendeskUrl"):
            st.link_button("Open Zendesk", row["zendeskUrl"])
    else:
        st.caption(f"Ticket disabled \u2014 {row.get('ticketDisabledReason') or 'not eligible for outreach'}")


def list_brief_jsons() -> list[Path]:
    files = sorted(EXPORTS.glob("*_elite_am_brief.json"), reverse=True)
    return files


@st.cache_data(show_spinner=False)
def load_payload(path_str: str) -> dict:
    return json.loads(Path(path_str).read_text(encoding="utf-8"))


def render_segments(report: dict) -> None:
    segments = report.get("segments") or []
    day = report.get("weekday") or ""
    day_short = report.get("dayShort") or day[:3]
    st.subheader(report.get("segmentTitle") or f"{day} vs last {day} · Elite & Jackpota")
    if report.get("headline"):
        st.caption(report["headline"])
    if not segments:
        st.write("No segment data.")
        return
    df = pd.DataFrame(
        [
            {
                "Segment": s.get("label"),
                f"This {day_short} Purchase": s.get("revThis"),
                f"Prior {day_short} Purchase": s.get("revPrior"),
                "Purchase WoW": s.get("revWow"),
                f"This {day_short} Purchased Players": s.get("plyThis"),
                f"Prior {day_short} Purchased Players": s.get("plyPrior"),
                "Purchased Players WoW": s.get("plyWow"),
                "Share": s.get("share") or "",
            }
            for s in segments
        ]
    )
    styled = df.style.apply(_style_wow, subset=["Purchase WoW"]).apply(
        _style_wow, subset=["Purchased Players WoW"]
    )
    st.dataframe(styled, use_container_width=True, hide_index=True)


def render_overview(payload: dict) -> None:
    report = payload.get("report") or {}
    for line in report.get("overviewGreetingLines") or []:
        st.markdown(str(line).replace("**", ""))

    left, right = st.columns([1.4, 1])
    with left:
        render_segments(report)
    with right:
        st.subheader("AM Share Of Elite")
        shares = payload.get("amShares") or []
        if shares:
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "AM": r.get("agentName"),
                            "Purchase $": r.get("purchase"),
                            "Share": r.get("purchaseShare"),
                            "Purchased Of Portfolio": r.get("purchasedOfBook")
                            or r.get("purchasedPlayers"),
                        }
                        for r in shares
                    ]
                ),
                use_container_width=True,
                hide_index=True,
            )

    st.subheader("AM Overview")
    ov = payload.get("overview") or []
    if ov:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "AM": r.get("agentName"),
                        "Purchase $": r.get("purchase"),
                        "Purchased Of Portfolio": r.get("purchasedOfBook")
                        or r.get("purchasedPlayers"),
                        "Open Tickets": r.get("openZd"),
                        "Take A Break": r.get("takeABreak"),
                        "Locked": r.get("locked"),
                        "Pending RD": r.get("rdOver5k"),
                        "Birthdays": r.get("birthdays"),
                        "Top 20 Decline": r.get("declineCount"),
                    }
                    for r in ov
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )


def checklist_board(focus: dict) -> None:
    st.subheader("Morning Checklist")
    items = [
        ("Open Tickets", focus.get("openZd", 0)),
        ("Take A Break (Past Day)", focus.get("takeABreak", 0)),
        ("Other Locked", focus.get("otherLocked", 0)),
        ("Self-Exclusion", focus.get("selfExclusion", 0)),
        ("Pending Redemptions", focus.get("rdOver5k", 0)),
        ("Birthdays (3d)", focus.get("birthdays", 0)),
        ("Top 20 Decline", focus.get("declineCount", 0)),
    ]
    cols = st.columns(len(items))
    for col, (label, count) in zip(cols, items):
        n = int(count or 0)
        col.metric(label, n)


def render_agent(block: dict, day: str) -> None:
    for i, line in enumerate(block.get("greetingLines") or []):
        text = str(line).replace("**", "")
        if i == 0:
            st.markdown(f"**{text}**")
        else:
            st.markdown(text)

    checklist_board(block.get("focus") or {})

    st.subheader("Top 10 Purchasers")
    top10 = block.get("top10") or []
    if top10:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "#": p.get("rank"),
                        "AID": p.get("aid"),
                        "Name": p.get("name"),
                        "Purchased $": p.get("purchased"),
                        "Purchases (#)": p.get("orderCount"),
                        "Top Offer": p.get("offerCode"),
                        "Price": p.get("offerPrice"),
                        "Usual → Ceiling (30D)": p.get("packageFit"),
                    }
                    for p in top10
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.caption("No top purchasers.")

    st.subheader("Top 20 · WoW Purchase Gaps")
    decline = block.get("decline") or []
    search = st.text_input("Search Top 20", "", key=f"search_{block.get('agentName')}")
    rows = decline
    q = search.strip().lower()
    if q:
        rows = [
            p
            for p in rows
            if q
            in " ".join(
                [
                    str(p.get("name") or ""),
                    str(p.get("aid") or ""),
                    str(p.get("reason") or ""),
                    str(p.get("reasonTable") or ""),
                    str(p.get("recommendation") or ""),
                ]
            ).lower()
        ]
    st.caption(f"Showing {len(rows)} of {len(decline)}")
    if rows:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "#": i + 1,
                        "AID": p.get("aid"),
                        "Name": p.get("name"),
                        "LT Purchase": p.get("lifetimePurchase"),
                        "Hold": p.get("lifetimeHold"),
                        f"This {day}": p.get("thisDay"),
                        f"Prior {day}": p.get("priorDay"),
                        "7D Purchase": p.get("purchase7d"),
                        "Urgency": p.get("urgency"),
                        "Reason": p.get("reasonTable") or p.get("reason"),
                        "Recommendation": p.get("recommendation"),
                    }
                    for i, p in enumerate(rows)
                ]
            ),
            use_container_width=True,
            hide_index=True,
            height=420,
        )
    with st.expander("Zendesk ticket draft \u2014 Top 20 \u00b7 WoW Purchase Gaps"):
        render_ticket_draft_picker(
            rows,
            key=f"dec_draft_{block.get('agentName')}",
            empty_msg="No rows match the current search.",
        )

    render_pending_rd(block.get("rdOver5k") or [], block.get("agentName") or "")
    render_first_time_rd(block.get("rdFirstTime") or [], block.get("agentName") or "")
    render_birthdays(block.get("birthdays") or [], block.get("agentName") or "")
    render_open_tickets(block.get("zendesk") or [], block.get("agentName") or "")
    render_locks(block.get("locks") or [], block.get("agentName") or "")


def render_pending_rd(rows: list[dict], agent_name: str) -> None:
    st.subheader("Pending Redemptions")
    if not rows:
        st.caption("All clear — none for this section.")
        return
    sort_choice = st.selectbox(
        "Sort",
        ["Amount ↓", "Won Yesterday ↓", "Oldest first"],
        key=f"sort_rd5_{agent_name}",
    )
    if sort_choice == "Oldest first":
        sorted_rows = _sort_by_num(rows, "daysPending", desc=True)
    elif sort_choice == "Won Yesterday ↓":
        sorted_rows = _sort_by_num(rows, "wonYesterdayNum", desc=True)
    else:
        sorted_rows = _sort_by_num(rows, "amountNum", desc=True)
    df = pd.DataFrame(
        [
            {
                "AID": r.get("aid"),
                "Name": r.get("name"),
                "RD ID": r.get("redeemId"),
                "Amount": r.get("amount"),
                "Status": r.get("status"),
                "Created": _format_created_with_aging(r),
                "Won Yesterday": (
                    f"{r.get('wonYesterday')} · Big Winner"
                    if r.get("bigWinner")
                    else (r.get("wonYesterday") or "—")
                ),
                "Docs": r.get("docsStatus") or "—",
                "LTP": r.get("lifetimePurchase") or "—",
                "Hold": r.get("lifetimeHold") or "—",
                "7D Purchase": r.get("purchase7d") or "—",
            }
            for r in sorted_rows
        ]
    )
    aging_flags = [bool(r.get("agingFlag")) for r in sorted_rows]
    styled = df.style.apply(lambda s: _style_flagged(s, aging_flags), subset=["Created"])
    st.dataframe(styled, use_container_width=True, hide_index=True)


def render_first_time_rd(rows: list[dict], agent_name: str) -> None:
    st.subheader("First-Time Locked RD")
    if not rows:
        st.caption("All clear — none for this section.")
        return
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "AID": r.get("aid"),
                    "Name": r.get("name"),
                    "RD ID": r.get("redeemId"),
                    "Amount": r.get("amount"),
                    "Status": r.get("status"),
                    "Created": r.get("created"),
                    "Ticket": _ticket_preview(r),
                }
                for r in rows
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )
    with st.expander("Zendesk ticket draft \u2014 First-Time Locked RD"):
        render_ticket_draft_picker(rows, key=f"rdf_draft_{agent_name}")


def render_birthdays(rows: list[dict], agent_name: str) -> None:
    st.subheader("Birthdays · Last 3 Days")
    if not rows:
        st.caption("All clear — none for this section.")
        return
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "AID": r.get("aid"),
                    "Name": r.get("name"),
                    "Email": r.get("email"),
                    "DOB": r.get("dob"),
                    "Age": r.get("age"),
                    "Ticket": _ticket_preview(r),
                }
                for r in rows
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )
    with st.expander("Zendesk ticket draft \u2014 Birthdays"):
        render_ticket_draft_picker(rows, key=f"bd_draft_{agent_name}")


def render_open_tickets(rows: list[dict], agent_name: str) -> None:
    st.subheader("Open Tickets")
    if not rows:
        st.caption("All clear — none for this section.")
        return
    sort_choice = st.selectbox(
        "Sort",
        ["LTP ↓", "Open Tickets ↓", "7D Purchase ↓"],
        key=f"sort_zd_{agent_name}",
    )
    if sort_choice == "Open Tickets ↓":
        sorted_rows = _sort_by_num(rows, "openTickets", desc=True)
    elif sort_choice == "7D Purchase ↓":
        sorted_rows = _sort_by_num(rows, "purchase7dNum", desc=True)
    else:
        sorted_rows = _sort_by_num(rows, "lifetimePurchasedNum", desc=True)
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "AID": r.get("aid"),
                    "Name": r.get("name"),
                    "LTP": r.get("lifetimePurchase"),
                    "Hold": r.get("lifetimeHold"),
                    "7D Purchase": r.get("purchase7d"),
                    "Open Tickets": r.get("openTickets"),
                    "Ticket TIDs": r.get("ticketIds"),
                }
                for r in sorted_rows
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )


def render_locks(rows: list[dict], agent_name: str) -> None:
    st.subheader("Locked And Take A Break")
    if not rows:
        st.caption("All clear — none for this section.")
        return
    sorted_rows = _sort_locks_by_soonest_unlock(rows)
    df = pd.DataFrame(
        [
            {
                "AID": r.get("aid"),
                "Name": r.get("name"),
                "Lock Reason": r.get("lockReason"),
                "Days Remaining / Unlock": r.get("unlockDetail") or "—",
            }
            for r in sorted_rows
        ]
    )
    # Ended take-a-break rows carry tone "danger" server-side (generate_am_daily_dashboard.py
    # lock_bucket/build_lock_section); fall back to unlockRemainingDays <= 0 for safety.
    danger_flags = [
        bool(r.get("tone") == "danger")
        or (isinstance(r.get("unlockRemainingDays"), (int, float)) and r.get("unlockRemainingDays") <= 0)
        for r in sorted_rows
    ]
    styled = df.style.apply(
        lambda s: _style_flagged(s, danger_flags), subset=["Lock Reason", "Days Remaining / Unlock"]
    )
    st.dataframe(styled, use_container_width=True, hide_index=True)


def main() -> None:
    st.set_page_config(
        page_title="Elite AM Brief",
        page_icon="📋",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    files = list_brief_jsons()
    if not files:
        st.error(f"No AM Brief JSON found in {EXPORTS}")
        return

    labels = [f.stem.replace("_elite_am_brief", "") for f in files]
    st.sidebar.title("Elite AM Brief")
    choice = st.sidebar.selectbox("Report date", options=list(range(len(files))), format_func=lambda i: labels[i])
    path = files[choice]
    payload = load_payload(str(path))
    report = payload.get("report") or {}
    am_order = payload.get("amOrder") or [
        a.get("agentName") for a in (payload.get("agents") or []) if a.get("agentName")
    ]

    st.title(report.get("title") or "Elite AM Brief")
    st.caption(report.get("subtitle") or report.get("date") or "")
    st.sidebar.caption(f"Loaded `{path.name}` (existing export)")

    tabs = ["Overview", *am_order]
    tab_objs = st.tabs(tabs)

    with tab_objs[0]:
        render_overview(payload)

    agents_by_name = {a.get("agentName"): a for a in (payload.get("agents") or [])}
    day = report.get("weekday") or ""
    for tab, name in zip(tab_objs[1:], am_order):
        with tab:
            block = agents_by_name.get(name)
            if not block:
                st.write("No data for this AM.")
                continue
            render_agent(block, day)


if __name__ == "__main__":
    main()
