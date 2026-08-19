"""Pure-Python AM Brief payload fixtures for render tests.

Every fixture is assembled by calling the SAME production section builders
the real generator uses (goals.py, generate_am_daily_dashboard.py) with small
hand-written rows shaped like BigQuery results. There is no BigQuery call
and nothing is ever read from a generated export or checked into git as a
giant JSON blob — see the elite-am-brief Skill's "Cost discipline" section
and AM_DAILY_DASHBOARD.md for why generated files are never opened directly.

If a builder's output shape changes, importing it here breaks loudly (an
ImportError or a TypeError from a changed signature) instead of a fixture
silently drifting from the real payload, which is the failure mode a
hand-written JSON fixture would have.

NOTE: the amShares/overview construction below intentionally mirrors the
~15-line inline block inside generate_am_daily_dashboard.build_payload
(there is no standalone function to import yet). Phase 3 of the AM Brief
foundation plan extracts that block into a shared function — when that
lands, replace the local copy here with the import so this cannot drift.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from typing import Any

PACKAGE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = PACKAGE_DIR.parent
for _p in (PROJECT_ROOT, PACKAGE_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from config import manager_gate_token  # noqa: E402
from goals import (  # noqa: E402
    GoalsTarget,
    build_agent_goals_block,
    build_team_goals_block,
    strip_payload_for_am,
)
from generate_am_daily_dashboard import (  # noqa: E402
    agent_display,
    build_birthday_section,
    build_lock_section,
    build_rd_section,
    build_top10_section,
    build_zd_section,
    focus_for_agent,
    soften_decline_rows,
)
from daily_summary.generate_daily_elite_canvas import build_top10_rows  # noqa: E402

REPORT_DATE = date(2026, 8, 17)
WEEKDAY = REPORT_DATE.strftime("%A")
DAY_SHORT = WEEKDAY[:3]

AGENT_TAGS = {"Coral": "coral_s", "Gabriel": "gabriel_e", "Alon": "alon_tish"}
AM_ORDER = ["Coral", "Gabriel", "Alon"]
GOALS_AM_ORDER = ["Coral", "Gabriel"]

CORAL_TARGET = GoalsTarget(
    agent="coral_s", year=2026, month=8, quarter=3,
    daily_avg_purchase=51_000, daily_avg_net_purchase=30_000,
    monthly_purchasers=546, reactivations=53, upgrades=49,
    pct_active=96, arppu=2_900,
)
GABRIEL_TARGET = GoalsTarget(
    agent="gabriel_e", year=2026, month=8, quarter=3,
    daily_avg_purchase=45_000, daily_avg_net_purchase=26_000,
    monthly_purchasers=520, reactivations=48, upgrades=40,
    pct_active=90, arppu=2_400,
)
TEAM_TARGET = GoalsTarget(
    agent="team", year=2026, month=8, quarter=3,
    daily_avg_purchase=96_000, daily_avg_net_purchase=56_000,
    monthly_purchasers=1_066, reactivations=101, upgrades=89,
    pct_active=93, arppu=2_650,
)

# Coral: every KPI on track, and scored by the manager (exercises the scored
# meter + leaderboard branch).
CORAL_ACTUALS = {
    "mtd_purchase": 51_200 * 16, "mtd_net_purchase": 30_000 * 16,
    "monthly_purchasers": 546 * 0.93, "reactivations": 53 * 16 / 31,
    "upgrades": 49 * 0.87, "portfolio_size": 560, "active_players": 545,
    "purchasers_shape": 0.93, "upgrades_shape": 0.87,
}
CORAL_APPRECIATION = {"points": 18.0, "note": "Owned the Top 20 gaps early."}

# Gabriel: intentionally behind on purpose (missing shape + lower actuals) so
# the fixture also exercises the "Manager Pending" / unscored leaderboard
# branch and a non-success status tone.
GABRIEL_ACTUALS = {
    "mtd_purchase": 620_000, "mtd_net_purchase": 360_000,
    "monthly_purchasers": 410, "reactivations": 20, "upgrades": 18,
    "portfolio_size": 646, "active_players": 480,
}

TEAM_ACTUALS = {
    "mtd_purchase": 1_600_000.0, "mtd_net_purchase": 940_000.0,
    "monthly_purchasers": 980, "reactivations": 70, "upgrades": 60,
    "portfolio_size": 1_326, "active_players": 1_050,
    "purchasers_shape": 0.92, "upgrades_shape": 0.86,
}

UPGRADES_NOTE = "Fixture note — see AM_DAILY_DASHBOARD.md for the real caveat."


def _top10_row(agent_tag: str, aid: int, name: str, *, purchased: float = 500.0, **extra: Any) -> dict:
    row = {
        "AID": aid, "name": name, "agent": agent_tag, "rank_in_agent": 1,
        "purchased": purchased, "order_count": 3, "offer_code": "OFF10",
        "offer_title": "Weekend Boost", "offer_qty": 1, "offer_amount": 500,
        "offer_unit_amount": 199.99, "offer_unit_min": 199.99, "offer_unit_max": 199.99,
        "usual_price": 199.99, "usual_price_orders": 2, "ceiling_price": 299.99,
    }
    row.update(extra)
    return row


def _rd_row(agent_tag: str, aid: int, name: str, *, amount: float = 6000.0, **extra: Any) -> dict:
    row = {
        "AID": aid, "name": name, "agent": agent_tag, "redeem_id": f"RD{aid}",
        "amount": amount, "status": "locked",
        "created_date": REPORT_DATE.isoformat(), "big_winner": False,
        "player_win_day": 0, "locked": False, "lock_reason": "", "lock_reason_comment": "",
    }
    row.update(extra)
    return row


def _birthday_row(agent_tag: str, aid: int, name: str, **extra: Any) -> dict:
    row = {
        "AID": aid, "name": name, "agent": agent_tag, "email": f"{name.lower()}@example.com",
        "dob": REPORT_DATE.isoformat(), "age": 34, "locked": False,
        "lock_reason": "", "lock_reason_comment": "",
    }
    row.update(extra)
    return row


def _zd_row(agent_tag: str, aid: int, name: str, *, open_tickets: int = 1, **extra: Any) -> dict:
    row = {
        "AID": aid, "name": name, "agent": agent_tag, "open_tickets": open_tickets,
        "ticket_ids": f"{100000 + aid}",
    }
    row.update(extra)
    return row


def _lock_row(agent_tag: str, aid: int, name: str, *, lock_reason: str = "Take a break", days_ago: int = 0, **extra: Any) -> dict:
    row = {
        "AID": aid, "name": name, "agent": agent_tag, "lock_reason": lock_reason,
        "lock_reason_comment": "14 days" if lock_reason == "Take a break" else "",
        "locked_at": (REPORT_DATE - _days(days_ago)).isoformat(),
    }
    row.update(extra)
    return row


def _days(n: int):
    from datetime import timedelta
    return timedelta(days=n)


def _decline_row(
    agent_tag: str, aid: int, name: str, *,
    this_weekday: float = 0.0, prior_weekday: float = 800.0,
    urgency: str = "Today", reason: str = "No Purchases",
    reason_code: str = "churn_lapsed", recommendation: str = "Call to re-engage.",
    ticket_enabled: bool = True,
) -> dict:
    return {
        "AID": aid, "name": name, "agent": agent_tag,
        "this_weekday": this_weekday, "prior_weekday": prior_weekday,
        "delta": prior_weekday - this_weekday,
        "purchase_7d_combined": "None In 7D",
        "lifetime_purchased": 12_000.0, "favourite_game_7d": "Fortune Tiger",
        "urgency": urgency, "reason": reason, "reason_table": reason,
        "reason_code": reason_code, "recommendation": recommendation,
        "ticketEnabled": ticket_enabled,
    }


def _decline_rows(raw: list[dict]) -> list[dict]:
    return soften_decline_rows(build_top10_rows(raw), raw)


def _am_shares_and_overview(agents: list[dict]) -> tuple[list[dict], list[dict]]:
    """Mirrors build_payload's amShares/overview loop — see module docstring."""
    am_shares = [
        {
            "agentName": a["agentName"], "purchase": a["purchase"],
            "purchasedPlayers": a["purchasedPlayers"], "totalPlayers": a["totalPlayers"],
            "purchasedOfBook": a["purchasedOfBook"], "bookPurchaseRate": a["bookPurchaseRate"],
            "purchaseShare": a["purchaseShare"], "playerShare": a["playerShare"],
            "tone": "success",
        }
        for a in agents
    ]
    overview = [
        {
            "agentName": a["agentName"], "purchase": a["purchase"],
            "purchasedPlayers": a["purchasedPlayers"], "totalPlayers": a["totalPlayers"],
            "purchasedOfBook": a["purchasedOfBook"], **a["focus"], "tone": "success",
        }
        for a in agents
    ]
    return am_shares, overview


def _archive(slug: str = "") -> list[dict]:
    """Hand-written, deterministic archive list (3 days across 2 months) —
    unlike canvas_to_html.archive_entries(), this never touches the real
    exports/ folder, so fixtures stay hermetic."""
    suffix = f"_{slug}" if slug else ""
    return [
        {"d": "2026-07-30", "f": f"2026-07-30_elite_am_brief{suffix}.html"},
        {"d": "2026-08-14", "f": f"2026-08-14_elite_am_brief{suffix}.html"},
        {"d": REPORT_DATE.isoformat(), "f": f"{REPORT_DATE.isoformat()}_elite_am_brief{suffix}.html"},
    ]


def build_manager_payload(*, ticket_count_for_coral: int = 1) -> dict:
    """Full manager payload: Coral (scored), Gabriel (unscored, behind),
    Alon (no Goals — the one AM the board deliberately excludes).

    ticket_count_for_coral: bump to 30+ to build the large-N fixture that
    exercises search / sort / pagination on Open Tickets without touching
    any other section.
    """
    top10_raw = [
        _top10_row("coral_s", 501, "Coral Purchaser One", purchased=1200.0, rank_in_agent=1),
        _top10_row("gabriel_e", 601, "Gabriel Purchaser One", purchased=900.0, rank_in_agent=1),
    ]
    rd_raw = [
        _rd_row("coral_s", 502, "Coral RD Player", amount=7500.0, big_winner=True, player_win_day=6200.0),
        _rd_row("gabriel_e", 602, "Gabriel RD Player", amount=5200.0,
                created_date=(REPORT_DATE - _days(2)).isoformat()),
    ]
    rd_first_raw = [
        _rd_row("coral_s", 503, "Coral First RD", amount=1200.0),
    ]
    birthday_raw = [
        _birthday_row("coral_s", 504, "Coral Birthday Player"),
        _birthday_row("gabriel_e", 604, "Gabriel Birthday Player"),
    ]
    zd_raw = [
        _zd_row("coral_s", 500 + i, f"Coral Ticket Player {i}")
        for i in range(1, ticket_count_for_coral + 1)
    ] + [
        _zd_row("gabriel_e", 605, "Gabriel Ticket Player"),
    ]
    lock_raw = [
        _lock_row("coral_s", 505, "Coral Locked Player", lock_reason="Take a break"),
        _lock_row("gabriel_e", 606, "Gabriel Self Exclusion", lock_reason="Exclusion"),
    ]
    decline_raw = {
        "Coral": [_decline_row("coral_s", 507, "Coral Decline Player", urgency="Today")],
        "Gabriel": [_decline_row("gabriel_e", 607, "Gabriel Decline Player", urgency="48h",
                                  reason_code="general_spend_softening")],
        "Alon": [],
    }

    top10 = build_top10_section(top10_raw)
    rd5k = build_rd_section(rd_raw, REPORT_DATE, aging_threshold_days=1, metrics_enrich={})
    rd_first = build_rd_section(rd_first_raw, ticket_enrich={})
    birthdays = build_birthday_section(birthday_raw, ticket_enrich={})
    zd = build_zd_section(zd_raw, enrich_map={})
    locks = build_lock_section(lock_raw, REPORT_DATE)
    decline_by_am = {name: _decline_rows(raw) for name, raw in decline_raw.items()}

    purchase_by_agent = {
        "Coral": {"purchased": 12_000.0, "purchased_players": 40},
        "Gabriel": {"purchased": 9_000.0, "purchased_players": 35},
        "Alon": {"purchased": 3_000.0, "purchased_players": 10},
    }
    total_players_by_agent = {"Coral": 560, "Gabriel": 646, "Alon": 120}
    elite_rev = sum(p["purchased"] for p in purchase_by_agent.values())
    elite_ply = sum(p["purchased_players"] for p in purchase_by_agent.values())

    goals_blocks = {
        "Coral": build_agent_goals_block(
            "coral_s", CORAL_TARGET, CORAL_ACTUALS, REPORT_DATE,
            upgrades_available=True, upgrades_note=UPGRADES_NOTE,
            appreciation=CORAL_APPRECIATION,
        ),
        "Gabriel": build_agent_goals_block(
            "gabriel_e", GABRIEL_TARGET, GABRIEL_ACTUALS, REPORT_DATE,
            upgrades_available=True, upgrades_note=UPGRADES_NOTE,
        ),
        "Alon": None,
    }

    agents = [
        focus_for_agent(
            name, WEEKDAY,
            top10=top10, decline=decline_by_am.get(name, []), rd5k=rd5k,
            rd_first=rd_first, birthdays=birthdays, zd=zd, locks=locks,
            purchase=purchase_by_agent[name], total_players=total_players_by_agent[name],
            elite_rev=elite_rev, elite_ply=elite_ply, goals=goals_blocks.get(name),
        )
        for name in AM_ORDER
    ]
    am_shares, overview = _am_shares_and_overview(agents)

    team_goals = build_team_goals_block(
        TEAM_TARGET, TEAM_ACTUALS, REPORT_DATE,
        upgrades_available=True, upgrades_note=UPGRADES_NOTE,
    )

    return {
        "report": {
            "date": REPORT_DATE.isoformat(), "weekday": WEEKDAY, "dayShort": DAY_SHORT,
            "subtitle": f"{WEEKDAY} {REPORT_DATE.strftime('%d %b %Y')}", "title": "Elite AM Brief",
            "headline": "Fixture headline — Elite steady vs last week.",
            "segmentTitle": f"{WEEKDAY} vs last {WEEKDAY} \u00b7 Elite & Jackpota",
            "overviewGreetingLines": ["Good morning.", f"Here is your {WEEKDAY} summary.", "Good luck \U0001f680"],
            "segments": [
                {"label": "Jackpota", "revThis": "$41K", "revPrior": "$39K", "revWow": "+5.1%",
                 "plyThis": "812", "plyPrior": "790", "plyWow": "+2.8%", "share": "", "tone": "success"},
                {"label": "Elite", "revThis": "$24K", "revPrior": "$23K", "revWow": "+4.3%",
                 "plyThis": "88", "plyPrior": "85", "plyWow": "+3.5%", "share": "58.5% of Jackpota", "tone": "success"},
            ],
            "archive": _archive(),
        },
        "amShares": am_shares,
        "overview": overview,
        "agents": agents,
        "amOrder": AM_ORDER,
        "goalsMeta": {
            "includedWeightTotal": 80.0, "managerAppreciationMax": 20.0,
            "upgradesNote": UPGRADES_NOTE, "asOf": REPORT_DATE.isoformat(),
            "goalsAmOrder": GOALS_AM_ORDER,
        },
        "teamGoals": team_goals,
        "managerGate": manager_gate_token(),
    }


def build_single_am_payload(agent_name: str = "Coral") -> dict:
    manager = build_manager_payload()
    payload = strip_payload_for_am(manager, agent_name)
    report = dict(payload["report"])
    report["archive"] = _archive(agent_name.lower())
    payload["report"] = report
    return payload


def build_empty_sections_payload(agent_name: str = "Alon") -> dict:
    """Alon already has no goals block and, by construction, no rows in any
    section here — hits every table's `empty:` string in one fixture."""
    manager = build_manager_payload()
    return strip_payload_for_am(manager, agent_name)


def build_large_tickets_payload() -> dict:
    """Coral's Open Tickets list is pumped to 30 rows to exercise search,
    sort and pagination (`PAGINATE_ABOVE = 25` in the shell)."""
    return build_manager_payload(ticket_count_for_coral=30)
