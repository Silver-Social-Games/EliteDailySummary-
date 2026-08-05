"""Streamlit view of the latest Elite Daily Summary (reads canvas payload)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DAILY_SUMMARY_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(DAILY_SUMMARY_DIR))

from canvas_to_html import build_payload, latest_canvas  # noqa: E402


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
    return [f"color: inherit; {_wow_color(v)}" if _wow_color(v) else "" for v in series]


@st.cache_data(show_spinner=False)
def load_latest_payload() -> tuple[str, dict]:
    canvas = latest_canvas()
    return str(canvas), build_payload(canvas)


def main() -> None:
    st.set_page_config(
        page_title="Elite Daily Summary",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    canvas_path, payload = load_latest_payload()
    report = payload["report"]
    segments = payload.get("segments") or report.get("segments") or []
    players = payload.get("players") or []
    titles = payload.get("titles") or {}
    agents = payload.get("agents") or sorted({p.get("agent") for p in players if p.get("agent")})
    day = report.get("weekday") or ""
    date_key = report.get("date") or ""

    st.sidebar.title("Elite Daily")
    st.sidebar.caption(f"Source: `{Path(canvas_path).name}`")
    st.sidebar.markdown(f"**Report date:** {date_key}")
    search = st.sidebar.text_input("Search name / AID / reason", "")
    agent_filter = st.sidebar.selectbox(
        "Agent",
        options=["All"] + list(agents),
        index=0,
    )
    sort_by = st.sidebar.selectbox(
        "Sort Top 20",
        options=["Urgency + gap", "Prior purchase ↓", "Lifetime purchase ↓", "WoW gap ↓"],
        index=0,
    )

    st.title("Elite Daily Summary")
    st.caption(f"{day} {date_key} · vs prior {report.get('priorDate', '')}")
    if report.get("headline"):
        st.info(report["headline"])

    # Metrics from Elite + Jackpota segment rows
    by_label = {s.get("label"): s for s in segments}
    elite = by_label.get("Elite") or {}
    jack = by_label.get("Jackpota") or {}
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Elite purchase", elite.get("revThis", "—"), elite.get("revWow", None))
    c2.metric("Elite purchased players", elite.get("plyThis", "—"), elite.get("plyWow", None))
    c3.metric("Jackpota purchase", jack.get("revThis", "—"), jack.get("revWow", None))
    c4.metric("Elite share", elite.get("share") or "—")

    st.subheader(f"{day} vs last {day} · Elite & Jackpota")
    seg_df = pd.DataFrame(
        [
            {
                "Segment": s.get("label"),
                f"This {day[:3]} Purchase": s.get("revThis"),
                f"Prior {day[:3]} Purchase": s.get("revPrior"),
                "Purchase WoW": s.get("revWow"),
                f"This {day[:3]} Purchased Players": s.get("plyThis"),
                f"Prior {day[:3]} Purchased Players": s.get("plyPrior"),
                "Purchased Players WoW": s.get("plyWow"),
                "Share": s.get("share") or "",
            }
            for s in segments
        ]
    )
    if not seg_df.empty:
        styled = seg_df.style.apply(_style_wow, subset=["Purchase WoW"]).apply(
            _style_wow, subset=["Purchased Players WoW"]
        )
        st.dataframe(styled, use_container_width=True, hide_index=True)

    st.subheader("Top 20 Same Day Comparison")
    if payload.get("urgencyLegend"):
        st.caption(payload["urgencyLegend"])

    rows = list(players)
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
                    str(p.get("agent") or ""),
                    str(p.get("agentName") or ""),
                    str(p.get("reason") or ""),
                    str(p.get("reasonTable") or ""),
                ]
            ).lower()
        ]
    if agent_filter != "All":
        rows = [p for p in rows if p.get("agent") == agent_filter]

    urgency_rank = {"Today": 0, "48h": 1, "Watch": 2, "None": 3}
    if sort_by == "Prior purchase ↓":
        rows.sort(key=lambda p: float(p.get("priorPriorNum") or 0), reverse=True)
    elif sort_by == "Lifetime purchase ↓":
        rows.sort(key=lambda p: float(p.get("lifetimePurchasedNum") or 0), reverse=True)
    elif sort_by == "WoW gap ↓":
        rows.sort(key=lambda p: float(p.get("sortGap") or 0), reverse=True)
    else:
        rows.sort(
            key=lambda p: (
                urgency_rank.get(str(p.get("urgency") or ""), 9),
                -float(p.get("sortGap") or 0),
            )
        )

    this_col = titles.get("thisPurchase") or f"This {day} Purchase"
    prior_col = titles.get("priorPurchase") or f"Prior {day} Purchase"
    lt_col = titles.get("lifetimePurchase") or "LT Purchase"
    hold_col = titles.get("lifetimeHold") or "Lifetime Hold"
    p7_col = titles.get("purchase7d") or "7D Purchase"

    top_df = pd.DataFrame(
        [
            {
                "#": i + 1,
                "AID": p.get("aid"),
                "Name": p.get("name"),
                "Agent": p.get("agentName") or p.get("agent"),
                lt_col: p.get("lifetimePurchase"),
                hold_col: p.get("lifetimeHold"),
                this_col: p.get("thisDay"),
                prior_col: p.get("priorDay"),
                p7_col: p.get("purchase7d"),
                "Urgency": p.get("urgency"),
                "Reason": p.get("reasonTable") or p.get("reason"),
                "Recommendation": p.get("recommendation"),
            }
            for i, p in enumerate(rows)
        ]
    )
    st.caption(f"Showing {len(rows)} of {len(players)} players")
    st.dataframe(top_df, use_container_width=True, hide_index=True, height=520)

    st.subheader("Player detail")
    if not rows:
        st.write("No players match the current filters.")
        return

    labels = [f"{p.get('name')} ({p.get('aid')}) · {p.get('urgency')}" for p in rows]
    pick = st.selectbox("Select player", options=list(range(len(rows))), format_func=lambda i: labels[i])
    p = rows[pick]
    left, right = st.columns(2)
    with left:
        st.markdown(f"**AID:** [{p.get('aid')}]({p.get('aidUrl')})" if p.get("aidUrl") else f"**AID:** {p.get('aid')}")
        st.markdown(f"**Agent:** {p.get('agentName') or p.get('agent')}")
        st.markdown(f"**Urgency:** {p.get('urgency')}")
        st.markdown(f"**{this_col}:** {p.get('thisDay')} · **{prior_col}:** {p.get('priorDay')}")
    with right:
        st.markdown("**Reason**")
        st.write(p.get("reasonTable") or p.get("reason") or "—")
        st.markdown("**Recommendation**")
        st.write(p.get("recommendation") or "—")
        if p.get("ticketEnabled"):
            with st.expander("Zendesk ticket draft"):
                st.text_input("Subject", value=p.get("ticketSubject") or "", disabled=True)
                st.text_area("Body", value=p.get("ticketBody") or "", height=180, disabled=True)
                if p.get("zendeskUrl"):
                    st.link_button("Open Zendesk", p["zendeskUrl"])


if __name__ == "__main__":
    main()
