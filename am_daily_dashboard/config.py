"""Elite Dashboard — tunable thresholds.

Single place to look before changing a cutoff. Previously these lived
inside embedded SQL strings (queries.py) or inline comparisons
(generate_am_daily_dashboard.py) with no single home — see the "Known
threshold debt" section of the Batch 1 canvas / AM_DAILY_DASHBOARD.md
Roadmap for context.
"""
from __future__ import annotations

import os

# User-facing product name (browser title, sidebar brand, Slack DM text).
PRODUCT_TITLE = "Elite Dashboard"

# Manager Dashboard gate. The Dashboard view carries the cross-AM roll-up
# numbers and only exists in the manager HTML — strip_payload_for_am never
# copies it into a per-AM file, so an AM's own file has no trace of it.
#
# The passcode on top of that is a soft gate, not security: the brief is a
# static HTML file, so anyone determined can read the payload in view-source.
# It exists to stop the numbers appearing over a shoulder or on a shared
# screen. Override with ELITE_AM_BRIEF_PASSCODE to change it without editing
# the repo; only the hashed token is written into the HTML.
MANAGER_DASHBOARD_PASSCODE = os.environ.get("ELITE_AM_BRIEF_PASSCODE", "elite")


def manager_gate_token(passcode: str = "") -> str:
    """djb2 hash of the passcode. Mirrored byte-for-byte by gateToken() in
    handoffs/elite_am_brief_web.html so the plaintext never lands in the file."""
    h = 5381
    for ch in passcode or MANAGER_DASHBOARD_PASSCODE:
        h = ((h * 33) ^ ord(ch)) & 0xFFFFFFFF
    return f"{h:08x}"


# --- Big win / big loss definitions (GGR is house-side: profit - loss) ---
#
# Player win on a day = max(-GGR, 0). Player loss on a day = max(GGR, 0).
#
# | Use | Threshold | Window | SQL sign |
# |-----|-----------|--------|----------|
# | Pending RD row (amount path) | locked amount >= $5k | any age, still open | — |
# | Pending RD row (win path) | player win >= $5k | last PENDING_RD_LOOKBACK_DAYS | ggr <= -5000 |
# | Pending RD "Big Winner" flag | player win >= $5k | report day only | ggr <= -5000 |
# | Big Winners section | player win >= $20k | last TRIGGER_LOOKBACK_DAYS | ggr <= -20000 |
# | Big Losers section | player loss >= $5k | last TRIGGER_LOOKBACK_DAYS | ggr >= +5000 |
#
# Pending RD: two inclusion paths (OR). Big Winner flag matches Won Yesterday.

PENDING_RD_MIN_AMOUNT = 5000
PENDING_RD_LOOKBACK_DAYS = 3

BIG_WINNER_MIN_PLAYER_WIN = 5000

BIG_LOSER_SECTION_MIN = BIG_WINNER_MIN_PLAYER_WIN

BIG_WINNER_SECTION_MIN = 20_000

# Birthdays section: calendar birthdays (MM-DD match) within the trailing
# window (inclusive of report_date).
BIRTHDAYS_LOOKBACK_DAYS = 3

# Trigger sections (first-time RD, Big Winners, Big Losers) show rows from this
# trailing window ending on report_date. Pending RD already uses
# PENDING_RD_LOOKBACK_DAYS (same value).
TRIGGER_LOOKBACK_DAYS = 3

# Locked / Take A Break section: surface accounts whose lock started within
# this trailing window (inclusive of report_date). Matches TRIGGER_LOOKBACK_DAYS
# so a missed day still surfaces recent locks — applies to every lock reason.
LOCKS_WINDOW_DAYS = TRIGGER_LOOKBACK_DAYS

# Take-a-break locks *also* surface once their unlock date is within this
# many days (or already passed), regardless of how long ago the lock
# started — so an overdue break is never missed just because it's no longer
# "new." Self-exclusion / other locked reasons have no unlock date and are
# not affected by this window.
LOCKS_REVIEW_WINDOW_DAYS = 3

# Take-a-break rows drop from the board once unlock ended more than this many
# calendar days before report_date (still locked but no longer actionable).
LOCKS_TAB_EXPIRE_DAYS = 7

# Churned, Active Decliners and Milestone Alerts were removed on 2026-08-18 at
# the user's request — they had been built despite an earlier instruction to
# exclude them, and each cost a BigQuery query on every run. Do not re-add them
# to this board without asking. Churn and Active decliner still live in
# daily_summary; Elite-core keeps their definitions.

# Elite Goals — these two must stay identical to the AMs' Tableau report, which
# is the number the team is measured on. Source of truth:
# elite_reference/Daily_Agg_Per_Player_Query_v1.sql.
#
# GOALS_REACTIVATION_GAP_DAYS mirrors that query's `params.churn_period_days`,
# which is **20**, not 30 (its inline comments still say 10 and are stale — trust
# the param). It powers is_reactivated_today: purchased today AND the gap from
# the previous purchase >= churn_period_days. Verified: 20 reproduces the
# Tableau figure for Coral Aug 1-16 2026 exactly (55); 30 returns 30.
#
# GOALS_ACTIVE_LOOKBACK_DAYS remains in goals_mtd_actuals_sql for legacy columns;
# % Active on the board is MTD purchasers / portfolio (see goals.py).
GOALS_REACTIVATION_GAP_DAYS = 20
GOALS_ACTIVE_LOOKBACK_DAYS = 30

# ---------------------------------------------------------------------------
# Open Tickets — weighted priority score
# ---------------------------------------------------------------------------
# Raw weights (sum to 90): lifetime hold 25, lifetime NGR 20, lifetime
# purchase 20, 30-day purchase 25. Normalised to 100 % by dividing by 90.
# Change any weight here; the normalisation is automatic.
_TICKET_RAW_WEIGHTS = (25.0, 20.0, 20.0, 25.0)
_TICKET_WEIGHT_SUM = sum(_TICKET_RAW_WEIGHTS)
TICKET_WEIGHT_LT_HOLD: float = _TICKET_RAW_WEIGHTS[0] / _TICKET_WEIGHT_SUM      # ~0.278
TICKET_WEIGHT_LT_NGR: float = _TICKET_RAW_WEIGHTS[1] / _TICKET_WEIGHT_SUM       # ~0.222
TICKET_WEIGHT_LT_PURCHASE: float = _TICKET_RAW_WEIGHTS[2] / _TICKET_WEIGHT_SUM  # ~0.222
TICKET_WEIGHT_30D_PURCHASE: float = _TICKET_RAW_WEIGHTS[3] / _TICKET_WEIGHT_SUM # ~0.278

# Topic tiers — list of (multiplier, label, regex_pattern).
# Ordered from highest to lowest urgency. The FIRST matching tier wins.
# Patterns are matched against the concatenation of LOWER(ticket.subject)
# values for all open tickets on the player. Raw strings; no re.IGNORECASE
# needed because subjects are already lowercased in the query.
TICKET_TOPIC_TIERS: list[tuple[float, str, str]] = [
    (
        2.0,
        "Redemption / Security",
        (
            r"withdraw|redeem|cash.?out|payout|redemption"
            r"|self.?exclu|stop.?gambl|close.?account|delete.?account"
            r"|chargeback|dispute|fraud|unauthori[sz]ed|stolen|hack|security"
            r"|refund(?!\s*(?:bonus|offer|promo))"
        ),
    ),
    (
        1.5,
        "Account / KYC / Promo",
        (
            r"lock|suspend|block|ban|restrict"
            r"|document|verif|kyc|proof|id.?upload|identity"
            r"|bonus|promo|offer|credit|reward|free.?spin|spin.?pack"
            r"|(?:not.?credit|missing|didn.?t.?receiv|not.?receiv|wrong|issue)"
            r"|login|password|reset.?password|can.?t.?log"
        ),
    ),
    (
        1.2,
        "Service Issue",
        (
            r"deposit|payment.?fail|card.?declin|declin"
            r"|error|crash|bug|not.?working|disconnect|lag|freeze"
            r"|balance|missing.?coin|coin.?missing|game.?issue|spin.?issue"
            r"|help|complaint|problem|support|assist"
        ),
    ),
]
TICKET_TOPIC_BASE_MULTIPLIER: float = 1.0
TICKET_TOPIC_BASE_LABEL: str = "General"

# Zendesk ABOUT / Player Safety dropdown values (custom_fields.value). Matched before
# subject regex — the board must follow the agent-set Topic, not only the subject line.
TICKET_ZENDESK_TIER1_FIELD_VALUES: frozenset[str] = frozenset({
    "self_exclusion",
    "rg__self_exclusion",
    "rg__indefinite_self_exclusion",
    "responsible_gameplay",
    "account_closure",
    "player_safety",
    "chargeback_dispute",
})
TICKET_ZENDESK_TIER2_FIELD_VALUES: frozenset[str] = frozenset({
    "login_issue_-_account_restricted",
    "request_additional_document",
})

# ---------------------------------------------------------------------------
# Responsiveness — 90-day no-ticket-activity (Phase E)
# ---------------------------------------------------------------------------
# Players with no Zendesk activity in this many calendar days.
# Source: last ticket created_at or updated_at for the account, whichever is
# more recent. Shown as a per-AM section so each AM sees their own silent book.
TICKET_INACTIVITY_DAYS: int = 90

# ---------------------------------------------------------------------------
# Birthday Gift Report — eligible players (Phase D)
# ---------------------------------------------------------------------------
# Eligible = Hold % >= threshold AND 30-day purchase >= floor.
# Refreshed weekly on Sunday so it does not churn daily.
# BIRTHDAY_GIFT_REFRESH_DOW: 6 = Sunday (Python weekday; matches Sun-Thu schedule)
BIRTHDAY_GIFT_MIN_HOLD_PCT: float = 0.50      # hold >= 50 %
BIRTHDAY_GIFT_MIN_30D_PURCHASE: float = 4_000  # 30-day purchase >= $4 000
BIRTHDAY_GIFT_REFRESH_DOW: int = 6            # Sunday

# ---------------------------------------------------------------------------
# One-month anniversary (Phase C)
# ---------------------------------------------------------------------------
# Days after agent_start_managed_date that count as the one-month anniversary
# window. Show players whose managed date + ANNIVERSARY_MANAGED_DAYS falls
# within ANNIVERSARY_WINDOW_DAYS of report_date (inclusive on both sides).
ANNIVERSARY_MANAGED_DAYS: int = 30
ANNIVERSARY_WINDOW_DAYS: int = 3

# ---------------------------------------------------------------------------
# Peer book mode — Phase F (coverage board, live default 2026-09-01)
# ---------------------------------------------------------------------------
# When True, strip_payload_for_am builds a coverage board: a tab for every AM
# who has a brief of their own (the measured AMs), so each AM can see all
# colleagues' triggers, past and present. Goals is present only for the home AM
# (personal). Overflow AMs with no snapshot of their own are left off the tabs.
# Set live so saved daily history accumulates as coverage boards. Pass
# --no-peer-mode to fall back to the isolated single-AM shape for one run.
PEER_BOOK_MODE: bool = True
