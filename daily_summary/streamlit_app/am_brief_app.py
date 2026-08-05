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
                            "Purchased / Book": r.get("purchasedOfBook")
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
                        "Purchased / Book": r.get("purchasedOfBook")
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

    for title, key, cols in [
        (
            "Pending Redemptions",
            "rdOver5k",
            ["aid", "name", "redeemId", "amount", "status", "created"],
        ),
        (
            "First-Time Locked RD",
            "rdFirstTime",
            ["aid", "name", "redeemId", "amount", "status", "created"],
        ),
        ("Birthdays · Last 3 Days", "birthdays", ["aid", "name", "email", "dob", "age"]),
        (
            "Open Tickets",
            "zendesk",
            ["aid", "name", "lifetimePurchase", "lifetimeHold", "purchase7d", "openTickets", "ticketIds"],
        ),
        ("Locked And Take A Break", "locks", ["aid", "name", "lockReason", "unlockDetail"]),
    ]:
        st.subheader(title)
        data = block.get(key) or []
        if not data:
            st.caption("All clear — none for this section.")
            continue
        st.dataframe(
            pd.DataFrame([{c: r.get(c) for c in cols} for r in data]),
            use_container_width=True,
            hide_index=True,
        )


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
