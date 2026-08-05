"""Streamlit UI for CRM and Elite reward verification."""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from elite_lib import get_client  # noqa: E402
from reward_check.decision import (  # noqa: E402
    account_warning,
    display_rows,
    mask_email,
    reconcile_free_spins_from_rewards,
    slack_summary,
    verify_free_spins,
    verify_purchase_credit,
    verify_tournament_prize,
)
from reward_check.queries import (  # noqa: E402
    lookup_fact_rewards,
    lookup_fs_wallet,
    lookup_gameplay,
    lookup_orders,
    lookup_tournament_rewards,
    resolve_players,
)


@st.cache_resource
def bigquery_client():
    return get_client()


@st.cache_data(ttl=300, show_spinner=False)
def cached_players(search: str) -> list[dict]:
    return resolve_players(bigquery_client(), search)


@st.cache_data(ttl=300, show_spinner=False)
def cached_orders(
    aid: int,
    date_from: date,
    date_to: date,
    offer_code: str,
) -> list[dict]:
    return lookup_orders(bigquery_client(), aid, date_from, date_to, offer_code)


@st.cache_data(ttl=300, show_spinner=False)
def cached_wallet(
    aid: int,
    date_from: date,
    date_to: date,
    offer_code: str,
) -> list[dict]:
    return lookup_fs_wallet(bigquery_client(), aid, date_from, date_to, offer_code)


@st.cache_data(ttl=300, show_spinner=False)
def cached_fact_rewards(
    aid: int,
    date_from: date,
    date_to: date,
    offer_code: str,
) -> list[dict]:
    return lookup_fact_rewards(bigquery_client(), aid, date_from, date_to, offer_code)


@st.cache_data(ttl=300, show_spinner=False)
def cached_tournaments(
    aid: int,
    date_from: date,
    date_to: date,
) -> list[dict]:
    return lookup_tournament_rewards(bigquery_client(), aid, date_from, date_to)


@st.cache_data(ttl=300, show_spinner=False)
def cached_gameplay(
    aid: int,
    date_from: date,
    date_to: date,
    game_name: str,
) -> list[dict]:
    return lookup_gameplay(bigquery_client(), aid, date_from, date_to, game_name)


def optional_number(label: str, *, key: str, step: float = 1.0) -> float | None:
    value = st.number_input(label, min_value=0.0, value=0.0, step=step, key=key)
    return None if value == 0 else float(value)


def show_verdict(status: str, headline: str, detail: str) -> None:
    message = f"**{headline}**\n\n{detail}"
    if status in {"received", "received_used", "received_unused"}:
        st.success(message)
    elif status in {"partial", "amount_mismatch", "received_expired"}:
        st.warning(message)
    elif status in {"missing", "not_paid"}:
        st.error(message)
    else:
        st.info(message)


def player_label(player: dict) -> str:
    email = mask_email(str(player.get("email") or ""))
    return f"AID {player['aid']} · {email or 'no email'}"


st.set_page_config(
    page_title="Elite Reward Checker",
    page_icon="✓",
    layout="wide",
)

st.title("Elite Reward Checker")
st.caption(
    "Verify Free Spins, purchase SC/GC, and Platform Tournament payouts. "
    "TID always means Zendesk ticket ID."
)

search = st.text_input(
    "Search by AID or email",
    placeholder="253808059 or player@example.com",
)

if not search.strip():
    st.info("Enter an exact AID or email to begin.")
    st.stop()

try:
    players = cached_players(search)
except Exception as exc:
    st.error(f"Player lookup failed: {exc}")
    st.stop()

if not players:
    st.error("No account matched that exact AID or email.")
    st.stop()

if len(players) > 1:
    selected_index = st.selectbox(
        "Multiple accounts matched. Select the correct AID.",
        options=range(len(players)),
        format_func=lambda index: player_label(players[index]),
    )
    player = players[selected_index]
else:
    player = players[0]

aid = int(player["aid"])
masked_email = mask_email(str(player.get("email") or ""))

identity_cols = st.columns(4)
identity_cols[0].metric("AID", str(aid))
identity_cols[1].metric("Email", masked_email or "—")
identity_cols[2].metric("Agent", str(player.get("agent") or "Unassigned"))
identity_cols[3].metric("Account status", str(player.get("status") or "—"))

warning = account_warning(player)
if warning:
    st.error(warning)

st.divider()

reward_type = st.selectbox(
    "Reward type",
    options=("Free Spins", "Purchase SC / GC", "Tournament Prize"),
)

default_to = date.today()
default_from = default_to - timedelta(days=6)
date_cols = st.columns(2)
date_from = date_cols[0].date_input("From", value=default_from)
date_to = date_cols[1].date_input("To", value=default_to)
if date_from > date_to:
    st.error("From date must be before or equal to To date.")
    st.stop()

zendesk_tid = st.text_input(
    "Zendesk TID (optional)",
    placeholder="608022",
    help="Reference only. This is never treated as an Order ID.",
)

offer_code = ""
campaign_code = ""
game_name = ""
expected_fs: int | None = None
expected_sc: float | None = None
expected_gc: float | None = None
tournament_id = ""
deep_reconciliation = False
include_gameplay = False

if reward_type == "Free Spins":
    fs_cols = st.columns(2)
    offer_code = fs_cols[0].text_input(
        "Offer code (optional)",
        placeholder="conv_20kg_10s_9_99",
    )
    campaign_code = fs_cols[1].text_input(
        "FS campaign code (optional)",
        placeholder="20260714_conv_20kg_10s_9_99_125",
    )
    details_cols = st.columns(2)
    expected_value = details_cols[0].number_input(
        "Expected FS (0 = unknown)",
        min_value=0,
        value=0,
        step=1,
    )
    expected_fs = int(expected_value) or None
    game_name = details_cols[1].text_input(
        "Game name/code (optional)",
        placeholder="BonanzaTrillion",
    )
    deep_reconciliation = st.checkbox(
        "If the wallet is inconclusive, check the heavy rewards ledger",
        value=True,
        help="This can take longer because fact_rewards is a large table.",
    )
    include_gameplay = st.checkbox(
        "Include game usage evidence",
        value=False,
    )
elif reward_type == "Purchase SC / GC":
    offer_code = st.text_input(
        "Offer code (optional)",
        placeholder="conv_20kg_10s_9_99",
    )
    purchase_cols = st.columns(2)
    with purchase_cols[0]:
        expected_sc = optional_number("Expected total SC (0 = unknown)", key="purchase_sc")
    with purchase_cols[1]:
        expected_gc = optional_number("Expected total GC (0 = unknown)", key="purchase_gc")
else:
    tournament_cols = st.columns(3)
    with tournament_cols[0]:
        expected_sc = optional_number("Expected prize SC (0 = unknown)", key="tournament_sc")
    with tournament_cols[1]:
        expected_gc = optional_number("Expected prize GC (0 = unknown)", key="tournament_gc")
    tournament_id = tournament_cols[2].text_input(
        "Tournament ID (reference only)",
        help="BigQuery does not expose tournament ID/name/position.",
    )

if st.button("Check reward", type="primary", width="stretch"):
    try:
        with st.spinner("Checking reward evidence…"):
            result = None
            orders: list[dict] = []
            wallet_rows: list[dict] = []
            fact_rows: list[dict] = []
            gameplay_rows: list[dict] = []
            tournament_rows: list[dict] = []

            if reward_type == "Free Spins":
                if offer_code:
                    orders = cached_orders(aid, date_from, date_to, offer_code)
                wallet_rows = cached_wallet(aid, date_from, date_to, offer_code)
                result = verify_free_spins(
                    orders,
                    wallet_rows,
                    expected_fs=expected_fs,
                    offer_code=offer_code,
                    campaign_code=campaign_code,
                )
                if deep_reconciliation and result.status in {"missing", "inconclusive"}:
                    fact_rows = cached_fact_rewards(aid, date_from, date_to, offer_code)
                    result = reconcile_free_spins_from_rewards(
                        result,
                        fact_rows,
                        expected_fs=expected_fs,
                        offer_code=offer_code,
                        campaign_code=campaign_code,
                    )
                if include_gameplay:
                    gameplay_rows = cached_gameplay(
                        aid,
                        date_from,
                        date_to + timedelta(days=5),
                        game_name,
                    )
            elif reward_type == "Purchase SC / GC":
                orders = cached_orders(aid, date_from, date_to, offer_code)
                result = verify_purchase_credit(
                    orders,
                    expected_sc=expected_sc,
                    expected_gc=expected_gc,
                )
            else:
                tournament_rows = cached_tournaments(aid, date_from, date_to)
                result = verify_tournament_prize(
                    tournament_rows,
                    expected_sc=expected_sc,
                    expected_gc=expected_gc,
                )

        assert result is not None
        show_verdict(result.status, result.headline, result.detail)
        st.write(f"**Recommended action:** {result.action}")

        if result.evidence:
            st.subheader("Evidence")
            st.dataframe(display_rows(result.evidence), width="stretch")

        if orders and reward_type == "Free Spins":
            with st.expander("Matching purchase"):
                st.dataframe(display_rows(orders), width="stretch")
        if fact_rows:
            with st.expander("Rewards-ledger reconciliation"):
                st.dataframe(display_rows(fact_rows), width="stretch")
        if gameplay_rows:
            with st.expander("Gameplay evidence"):
                st.dataframe(display_rows(gameplay_rows), width="stretch")

        reward_label = reward_type
        if reward_type == "Tournament Prize" and tournament_id:
            reward_label += f" · Tournament ID {tournament_id}"
        summary = slack_summary(
            player,
            reward_label,
            result,
            zendesk_tid=zendesk_tid,
        )
        st.subheader("Slack-ready summary")
        st.code(summary, language=None)

        if reward_type == "Tournament Prize":
            st.caption(
                "Tournament ID, name, and leaderboard position are not available "
                "in the current BigQuery reward tables."
            )
    except Exception as exc:
        st.error(f"Reward check failed: {exc}")
