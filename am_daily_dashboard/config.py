"""Elite AM Brief — tunable thresholds.

Single place to look before changing a cutoff. Previously these lived
inside embedded SQL strings (queries.py) or inline comparisons
(generate_am_daily_dashboard.py) with no single home — see the "Known
threshold debt" section of the Batch 1 canvas / AM_DAILY_DASHBOARD.md
Roadmap for context.
"""
from __future__ import annotations

import os

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


# Pending Redemptions section: locked withdraw requests at or above this
# amount, created within the trailing window (inclusive of report_date).
PENDING_RD_MIN_AMOUNT = 5000
PENDING_RD_LOOKBACK_DAYS = 3

# Big Winner flag on Pending Redemptions: the player won at least this much on
# the report day. Stated as a positive player win. GGR is house-side
# (`profit - loss`, Elite.MD), so a player win is a *negative* GGR day and the
# SQL compares `ggr <= -BIG_WINNER_MIN_PLAYER_WIN`. Read the sign backwards and
# the flag lands on the biggest losers instead.
BIG_WINNER_MIN_PLAYER_WIN = 5000

# Big Losers section: house-side GGR ≥ this on report_date (player lost at least
# this much). Uses the same $5K floor as the Pending RD Big Winner flag.
BIG_LOSER_SECTION_MIN = BIG_WINNER_MIN_PLAYER_WIN

# Big Winners section threshold: players at or above this player win on
# report_date get their own dedicated section. Separate from the Pending RD
# flag above — that one raises an alert inside the RD row; this one is a
# stand-alone section that includes non-Elite players. Same GGR sign rule:
# player win = negative GGR day, SQL uses `ggr <= -BIG_WINNER_SECTION_MIN`.
BIG_WINNER_SECTION_MIN = 20_000

# Birthdays section: calendar birthdays (MM-DD match) within the trailing
# window (inclusive of report_date).
BIRTHDAYS_LOOKBACK_DAYS = 3

# Locked / Take A Break section: surface accounts whose lock started within
# this trailing window (inclusive of report_date). 1 = today only. This is
# the "what just happened" feed — applies to every lock reason.
LOCKS_WINDOW_DAYS = 1

# Take-a-break locks *also* surface once their unlock date is within this
# many days (or already passed), regardless of how long ago the lock
# started — so an overdue break is never missed just because it's no longer
# "new." Self-exclusion / other locked reasons have no unlock date and are
# not affected by this window.
LOCKS_REVIEW_WINDOW_DAYS = 3

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
# GOALS_ACTIVE_LOOKBACK_DAYS is the inactivity threshold behind % Active — a
# player counts as active while their last successful purchase is inside this
# many days of the as-of date. 30 reproduces Coral's 85%.
#
# If the Tableau query is re-exported, re-check both against it before trusting
# a mismatch report.
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
        "Withdrawal / Security",
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
