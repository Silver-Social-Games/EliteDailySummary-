"""Shared constants for WoW drop reason codes, urgency, and message labels.

Pure data - no imports, no BigQuery, no formatting logic. Split out of
wow_drop_reason.py so classification/query/presentation code can each
depend on the taxonomy without depending on each other.
"""

from __future__ import annotations

DAY_DROP_LABELS = {
    "self_exclusion": "Self-exclusion",
    "account_locked": "Account locked",
    "redemption_in_progress": "Redemption in progress",
    "payment_failed": "Payment failed",
    "big_win_day_before": "Big win (day before)",
    "same_weekday_skip": "Same weekday skip",
    "churn_lapsed": "Churn - needs reactivation",
    "red_flag": "Red flag",
    "general_spend_softening": "General spend softening",
}

URGENCY_BY_CODE = {
    "self_exclusion": "None",
    "account_locked": "Today",
    "redemption_in_progress": "Today",
    "payment_failed": "Today",
    "big_win_day_before": "Watch",
    "churn_lapsed": "48h",
    "same_weekday_skip": "Watch",
    "red_flag": "Today",
    "general_spend_softening": "48h",
}

URGENCY_SORT = {"Today": 0, "48h": 1, "Watch": 2, "None": 3}

URGENCY_OPTIONS = [
    ("Today", "Redeem pending, payment failed, account lock, or red flag"),
    ("48h", "Churn, spend slowing, or 2+ days without purchase"),
    ("Watch", "Skipped purchase day or post-win"),
    ("None", "Self-exclusion"),
]

# User-facing metric labels (Title Case; day windows as 7D / 14D / 30D)
M_NONE_IN_7D = "None In 7D"
M_LAST_PURCHASE_30D = "Last Purchase 30D"
M_LAST_PLAY_14D = "Last Play 14D"
M_7D_PURCHASE = "7D Purchase"
M_NO_PLAY_7D = "No Play In 7D"
M_NO_PURCHASES_7D = "No Purchases In 7D"
M_NO_PLAY_OR_PURCHASE_SINCE = "No Play Or Purchase Since"
M_REPORT_DAY = "Report Day"
M_PENDING_REDEEM = "Pending Redeem"
# Open withdraw rows — not terminal (confirmed/cancelled/declined/failed).
PENDING_REDEEM_STATUSES = ("pre_authorized", "locked")
M_FAILED_CHECKOUT = "Failed Checkout"
M_ZENDESK_14D = "Zendesk 14D"
M_NO_REPORT_DAY_PLAY = "No Report Day Play"
M_ACCOUNT_RESTRICTED_LEGAL = "Account Restricted - Legal Action"
M_ACCOUNT_SUSPENDED = "Account Suspended"
M_ACCOUNT_RESTRICTED = "Account Restricted"

REASON_SEP = "  ●  "
TOP_SAME_DAY_LIMIT = 20
ZERO_DAY_DROP_SHARE = 0.51
SAME_DAY_CANDIDATE_LIMIT = 500

# Reason segments bolded in markdown / semibold in canvas when they start with these.
REASON_EMPHASIS_PREFIXES = (
    "Redemption Blocked",
    "Redemption in progress",
    "Red flag",
    "Needs ",
    "Same weekday skip",
    "Spend Softening",
    "Offline Since",
    "Pending RD",
    "RD $",
    "Redeem Status ",
    "Take a break",
    "Account Closure",
    "Restriction Lift",
    "Break Requested",
    "Break / Timeout",
    "No Purchases",
    "Played Today",
    "Account locked",
)
MAX_ZD_SUBJECT = 24


CLASSIFICATION_RULES = [
    ("self_exclusion", "locked AND lock_reason = Exclusion"),
    ("account_locked", "locked AND lock_reason != Exclusion"),
    ("redemption_in_progress", "open withdraw (pre_authorized or locked) > 0"),
    ("payment_failed", "failed purchase orders on report day AND report-day purchased = 0"),
    ("big_win_day_before", "day-before NGR <= -$5,000 (player up)"),
    ("churn_lapsed", "rolling 7d purchased = 0"),
    ("same_weekday_skip", "report-day purchased = 0 AND purchased on other days in 7d window > 0"),
    ("red_flag", "elite_users.red_flag = true"),
    ("general_spend_softening", "report-day purchased < prior same weekday (default)"),
]


AGENT_TAG_LABELS = {
    "coral_s": "Coral",
    "lee_t": "Lee",
    "alon_tish": "Alon",
    "gabriel_e": "Gabriel",
    "gabriel": "Gabriel",
    "rachel_a": "Rachel",
}
