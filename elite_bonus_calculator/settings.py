"""Elite Bonus Calculator settings — CS Free SC matrix, Slack IDs, runtime paths.

Named `settings` rather than `config` so importing this package can never
collide with `am_daily_dashboard/config.py`, which is also imported as a
top-level `config` module.
"""

from __future__ import annotations

from pathlib import Path

APP_DISPLAY_NAME = "Elite Bonus Calculator"

# Last 14 days purchase ($) — upper bounds exclusive except the last bucket.
PURCHASE_TIER_LABELS = ("0–200", "200–500", "500–1,000", "1,000+")
PURCHASE_TIER_BOUNDS = (200.0, 500.0, 1000.0)

# Days since last manual / CS free SC grant.
DAYS_TIER_LABELS = ("0–3", "3–7", "7–14", "14+")
DAYS_TIER_BOUNDS = (3, 7, 14)

# Matrix[row][col] — rows = days tier, cols = purchase tier (CS sheet).
FREE_SC_MATRIX: tuple[tuple[int, ...], ...] = (
    (0, 0, 0, 5),
    (0, 5, 5, 10),
    (5, 5, 10, 20),
    (5, 15, 20, 30),
)

LOOKUP_WINDOW_DAYS = 14

# How far back to search for a previous manual grant.
GRANT_LOOKBACK_DAYS = 730

# Per-query BQ scan cap (~50 MB) — cheap per click, predictable cost.
LOOKUP_MAX_BYTES = 50_000_000

# BigQuery rows are reused for this long, so a channel re-checking the same
# player does not pay for a new query each time.
RESULT_CACHE_TTL_SECONDS = 600
RESULT_CACHE_MAX_ENTRIES = 512

# fact_rewards rows counted as manual / CS free SC (tune if Tableau differs).
MANUAL_FREE_SC_REWARD_FILTER = """
  COALESCE(r.sweepstake_reward_amount, 0) > 0
  AND LOWER(COALESCE(r.product_type, '')) NOT IN ('freespin')
  AND LOWER(COALESCE(r.product_title, '')) NOT IN ('freespin', 'offer discount reward')
  AND (
    LOWER(COALESCE(r.product_type, '')) IN ('manual', 'reward')
    OR REGEXP_CONTAINS(LOWER(CONCAT(
         COALESCE(r.product_title, ''), ' ',
         COALESCE(r.campaign_title, ''), ' ',
         COALESCE(r.product_code, '')
       )), r'(manual|support|comp|customer service|cs grant|goodwill)')
  )
"""

# Slack identifiers — must match slack_app_manifest.yml.
SLASH_COMMAND = "/bonus"
SHORTCUT_CALLBACK_ID = "elite_bonus_calc"
MODAL_CALLBACK_ID = "elite_bonus_calc_modal"
ADJUST_DAYS_ACTION_ID = "elite_bonus_adjust_days"
AID_BLOCK_ID = "aid_block"
AID_ACTION_ID = "aid_input"
DAYS_BLOCK_ID = "days_block"
DAYS_ACTION_ID = "days_input"

LOOKER_ACCOUNT_PORTAL = (
    "https://lookerpatrianna.cloud.looker.com/dashboards/5207?"
    "Account+ID+={aid}&Purchase+filter+date=30+day"
)

PACKAGE_DIR = Path(__file__).resolve().parent
LOG_DIR = PACKAGE_DIR / "logs"
LOG_FILE = LOG_DIR / "bot.log"
DATA_DIR = PACKAGE_DIR / "data"
AUDIT_LOG = DATA_DIR / "lookup_audit.jsonl"
