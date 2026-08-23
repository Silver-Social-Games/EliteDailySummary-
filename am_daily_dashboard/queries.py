"""SQL builders for Elite AM Brief dashboard."""

from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta

from elite_lib.bigquery import PROJECT_ID, dashboard_elite_ctes
from goals import TEAM_AGENT_TAG
from config import (
    BIG_LOSER_SECTION_MIN,
    BIG_WINNER_MIN_PLAYER_WIN,
    BIG_WINNER_SECTION_MIN,
    BIRTHDAYS_LOOKBACK_DAYS,
    GOALS_ACTIVE_LOOKBACK_DAYS,
    GOALS_REACTIVATION_GAP_DAYS,
    PENDING_RD_LOOKBACK_DAYS,
    PENDING_RD_MIN_AMOUNT,
)


def _iso(d: date) -> str:
    """Return the ISO 8601 date string for a date literal in SQL.

    Accepts only `datetime.date` objects so a raw string can never be
    interpolated into a query — guards the f-string DATE '{_iso(d)}' pattern
    used throughout this module against accidental string pass-through.
    """
    if not isinstance(d, date):
        raise TypeError(f"Expected datetime.date, got {type(d).__name__!r}")
    return d.isoformat()

# Only these AMs appear on the board (tag_agent_1 values).
ALLOWED_AGENT_TAGS = (
    "coral_s",
    "lee_t",
    "alon_tish",
    "gabriel_e",
    "gabriel",
    "rachel_a",
)

ALLOWED_TAGS_SQL = ", ".join(f"'{t}'" for t in ALLOWED_AGENT_TAGS)


def _elite_am_book_ctes(as_of: date | None = None) -> str:
    """Dashboard Elite book + agent, restricted to named AMs.

    `as_of` pins the tag snapshot to that report date — required for the scored
    Goals block so a re-run of an old date reproduces its numbers. Live
    operational sections (locks, pending RD) deliberately leave it unset.
    """
    base = dashboard_elite_ctes(
        latest_name="latest_elite_tag_snapshot",
        elite_name="elite_book_raw",
        aid_alias="account_id",
        agent_alias="agent",
        as_of=_iso(as_of) if as_of else None,
    )
    return f"""
{base},
elite_am AS (
  SELECT account_id, agent
  FROM elite_book_raw
  WHERE agent IN ({ALLOWED_TAGS_SQL})
)
""".strip()


def top10_purchasers_sql(report_date: date) -> str:
    """Top 10 purchasers per AM for report_date, with leading offer code/qty/$.

    Also returns the player's 30-day **price ladder** so an AM can see which
    package to pitch: `usual_price` (the price point bought most often, with
    `usual_price_orders`) and `ceiling_price` (the highest price paid at least
    twice). An average was asked for first and rejected — these players buy at
    15–25 distinct price points a month, mixing small top-ups with occasional
    big offers, so a mean lands between the two and names no sellable package.
    One player averaged $33/order while habitually buying $20 and repeatedly
    buying $300. The twice-paid rule on the ceiling keeps a one-off purchase
    from setting an upsell target nobody will repeat.

    The 30-day window ends on report_date inclusive.
    """
    d = _iso(report_date)
    return f"""
WITH
{_elite_am_book_ctes()},
day_kpi AS (
  SELECT
    k.account_id,
    SUM(CAST(k.purchased AS FLOAT64)) AS purchased,
    SUM(CAST(k.purchased_num AS FLOAT64)) AS order_count_kpi
  FROM `{PROJECT_ID}.jackpota_agg.daily_player_revenue_kpis` k
  INNER JOIN elite_am e ON e.account_id = k.account_id
  WHERE k.date = DATE '{d}'
  GROUP BY k.account_id
  HAVING SUM(CAST(k.purchased AS FLOAT64)) > 0
),
ranked AS (
  SELECT
    e.agent,
    k.account_id,
    k.purchased,
    k.order_count_kpi,
    ROW_NUMBER() OVER (PARTITION BY e.agent ORDER BY k.purchased DESC) AS rn
  FROM day_kpi k
  INNER JOIN elite_am e ON e.account_id = k.account_id
),
top10 AS (
  SELECT * FROM ranked WHERE rn <= 10
),
orders AS (
  SELECT
    p.account_id,
    COALESCE(h.code, CAST(p.offer_id AS STRING)) AS offer_code,
    h.title AS offer_title,
    CAST(p.amount AS FLOAT64) AS amount
  FROM `{PROJECT_ID}.transactional_data.payment_payment_orders` p
  LEFT JOIN `{PROJECT_ID}.transactional_data.payment_offer_templates` h
    ON h.id = p.offer_id
  INNER JOIN top10 t ON t.account_id = p.account_id
  WHERE DATE(p.created_at) = DATE '{d}'
    AND p.status = 'succeeded'
    AND COALESCE(p.refunded, FALSE) = FALSE
),
offer_agg AS (
  SELECT
    account_id,
    offer_code,
    ANY_VALUE(offer_title) AS offer_title,
    COUNT(*) AS offer_qty,
    SUM(amount) AS offer_amount,
    -- Price the player actually paid for one unit of this offer. Averaged
    -- because the same offer can be sold at different amounts; min/max come
    -- along so a genuinely varying price can be spotted rather than hidden.
    SUM(amount) / COUNT(*) AS offer_unit_amount,
    MIN(amount) AS offer_unit_min,
    MAX(amount) AS offer_unit_max
  FROM orders
  GROUP BY account_id, offer_code
),
top_offer AS (
  SELECT
    account_id,
    offer_code,
    offer_title,
    offer_qty,
    offer_amount,
    offer_unit_amount,
    offer_unit_min,
    offer_unit_max,
    ROW_NUMBER() OVER (
      PARTITION BY account_id
      ORDER BY offer_qty DESC, offer_amount DESC
    ) AS orn
  FROM offer_agg
),
-- 30-day price ladder. Order level on purpose: the KPI view has no per-order
-- amount, and the whole point is which individual price points recur.
ladder_orders AS (
  SELECT
    p.account_id,
    CAST(p.amount AS FLOAT64) AS amount
  FROM `{PROJECT_ID}.transactional_data.payment_payment_orders` p
  INNER JOIN top10 t ON t.account_id = p.account_id
  WHERE DATE(p.created_at) BETWEEN DATE_SUB(DATE '{d}', INTERVAL 29 DAY) AND DATE '{d}'
    AND p.status = 'succeeded'
    AND COALESCE(p.refunded, FALSE) = FALSE
),
price_counts AS (
  SELECT account_id, amount, COUNT(*) AS orders_at_price
  FROM ladder_orders
  GROUP BY account_id, amount
),
usual_price AS (
  SELECT
    account_id,
    amount AS usual_price,
    orders_at_price AS usual_price_orders,
    -- Tie on frequency goes to the higher price: pitching the dearer of two
    -- equally habitual packages is the recoverable error.
    ROW_NUMBER() OVER (
      PARTITION BY account_id
      ORDER BY orders_at_price DESC, amount DESC
    ) AS prn
  FROM price_counts
),
ceiling_price AS (
  SELECT account_id, MAX(amount) AS ceiling_price
  FROM price_counts
  WHERE orders_at_price >= 2
  GROUP BY account_id
),
max_purchase_30d AS (
  SELECT account_id, MAX(amount) AS max_purchase_30d
  FROM ladder_orders
  GROUP BY account_id
)
SELECT
  t.agent,
  t.rn AS rank_in_agent,
  t.account_id AS AID,
  COALESCE(
    NULLIF(TRIM(CONCAT(IFNULL(per.first_name, ''), ' ', IFNULL(per.last_name, ''))), ''),
    ua.name,
    ua.email,
    CAST(t.account_id AS STRING)
  ) AS name,
  t.purchased,
  COALESCE(t.order_count_kpi, 0) AS order_count,
  o.offer_code,
  o.offer_title,
  o.offer_qty,
  o.offer_amount,
  o.offer_unit_amount,
  o.offer_unit_min,
  o.offer_unit_max,
  u.usual_price,
  u.usual_price_orders,
  cp.ceiling_price,
  mp.max_purchase_30d
FROM top10 t
LEFT JOIN top_offer o ON o.account_id = t.account_id AND o.orn = 1
LEFT JOIN usual_price u ON u.account_id = t.account_id AND u.prn = 1
LEFT JOIN ceiling_price cp ON cp.account_id = t.account_id
LEFT JOIN max_purchase_30d mp ON mp.account_id = t.account_id
LEFT JOIN `{PROJECT_ID}.transactional_data.uam_accounts` ua ON ua.id = t.account_id
LEFT JOIN `{PROJECT_ID}.transactional_data.uam_persons` per ON per.id = ua.person_id
ORDER BY t.agent, t.rn
""".strip()


def locked_rd_over_5k_sql(report_date: date) -> str:
    """Pending locked redemptions >= PENDING_RD_MIN_AMOUNT created within the
    trailing PENDING_RD_LOOKBACK_DAYS ending report_date (config.py).

    Also returns the player's **report-day win** so the Big Winner flag can be
    raised on a pending redemption. GGR is house-side (`profit - loss`), so a
    player win is a negative GGR day; `player_win_day` flips the sign to be
    positive-when-the-player-won, and only a genuine win is reported (a losing
    day comes back as 0, not a negative win).
    """
    d = _iso(report_date)
    lookback_interval = PENDING_RD_LOOKBACK_DAYS - 1
    return f"""
WITH
{_elite_am_book_ctes()},
locked_rd AS (
  SELECT
    w.account_id,
    w.id AS redeem_id,
    CAST(w.amount AS FLOAT64) AS amount,
    w.status,
    DATE(w.created_at) AS created_date,
    w.created_at
  FROM `{PROJECT_ID}.transactional_data.payment_withdraw_money_requests` w
  INNER JOIN elite_am e ON e.account_id = w.account_id
  WHERE w.status = 'locked'
    AND CAST(w.amount AS FLOAT64) >= {PENDING_RD_MIN_AMOUNT}
    AND DATE(w.created_at) BETWEEN DATE_SUB(DATE '{d}', INTERVAL {lookback_interval} DAY) AND DATE '{d}'
),
day_ggr AS (
  SELECT
    k.account_id,
    SUM(CAST(k.profit AS FLOAT64) - CAST(k.loss AS FLOAT64)) AS ggr_day
  FROM `{PROJECT_ID}.jackpota_agg.daily_player_revenue_kpis` k
  INNER JOIN locked_rd r ON r.account_id = k.account_id
  WHERE k.date = DATE '{d}'
  GROUP BY k.account_id
)
SELECT
  e.agent,
  r.account_id AS AID,
  COALESCE(
    NULLIF(TRIM(CONCAT(IFNULL(per.first_name, ''), ' ', IFNULL(per.last_name, ''))), ''),
    ua.name,
    ua.email,
    CAST(r.account_id AS STRING)
  ) AS name,
  r.redeem_id,
  r.amount,
  r.status,
  r.created_date,
  ROUND(COALESCE(g.ggr_day, 0), 2) AS ggr_day,
  ROUND(GREATEST(-COALESCE(g.ggr_day, 0), 0), 2) AS player_win_day,
  COALESCE(g.ggr_day, 0) <= -{BIG_WINNER_MIN_PLAYER_WIN} AS big_winner
FROM locked_rd r
INNER JOIN elite_am e ON e.account_id = r.account_id
LEFT JOIN day_ggr g ON g.account_id = r.account_id
LEFT JOIN `{PROJECT_ID}.transactional_data.uam_accounts` ua ON ua.id = r.account_id
LEFT JOIN `{PROJECT_ID}.transactional_data.uam_persons` per ON per.id = ua.person_id
ORDER BY e.agent, r.amount DESC
""".strip()


def first_time_locked_rd_sql() -> str:
    """Accounts whose first-ever withdraw request is currently status=locked."""
    return f"""
WITH
{_elite_am_book_ctes()},
ordered AS (
  SELECT
    w.account_id,
    w.id AS redeem_id,
    CAST(w.amount AS FLOAT64) AS amount,
    w.status,
    DATE(w.created_at) AS created_date,
    ROW_NUMBER() OVER (PARTITION BY w.account_id ORDER BY w.created_at ASC, w.id ASC) AS rn
  FROM `{PROJECT_ID}.transactional_data.payment_withdraw_money_requests` w
  INNER JOIN elite_am e ON e.account_id = w.account_id
),
first_locked AS (
  SELECT *
  FROM ordered
  WHERE rn = 1 AND status = 'locked'
)
SELECT
  e.agent,
  f.account_id AS AID,
  COALESCE(
    NULLIF(TRIM(CONCAT(IFNULL(per.first_name, ''), ' ', IFNULL(per.last_name, ''))), ''),
    ua.name,
    ua.email,
    CAST(f.account_id AS STRING)
  ) AS name,
  f.redeem_id,
  f.amount,
  f.status,
  f.created_date,
  COALESCE(ua.locked, FALSE) AS locked,
  COALESCE(ua.lock_reason, '') AS lock_reason,
  COALESCE(ua.lock_reason_comment, '') AS lock_reason_comment
FROM first_locked f
INNER JOIN elite_am e ON e.account_id = f.account_id
LEFT JOIN `{PROJECT_ID}.transactional_data.uam_accounts` ua ON ua.id = f.account_id
LEFT JOIN `{PROJECT_ID}.transactional_data.uam_persons` per ON per.id = ua.person_id
ORDER BY e.agent, f.amount DESC
""".strip()


def birthdays_last_3d_sql(report_date: date) -> str:
    """Calendar birthdays within the trailing BIRTHDAYS_LOOKBACK_DAYS ending
    on report_date (MM-DD match), config.py."""
    d = _iso(report_date)
    days_back_clauses = "\n  ".join(
        f"UNION ALL SELECT DATE_SUB(report_date, INTERVAL {n} DAY) FROM params"
        for n in range(1, BIRTHDAYS_LOOKBACK_DAYS)
    )
    return f"""
WITH
{_elite_am_book_ctes()},
params AS (
  SELECT DATE '{d}' AS report_date
),
days AS (
  SELECT report_date AS d FROM params
  {days_back_clauses}
),
birth AS (
  SELECT DISTINCT id AS account_id, date_of_birth
  FROM `{PROJECT_ID}.transactional_data.uam_account_personal_info`
  WHERE date_of_birth IS NOT NULL
    AND date_of_birth != DATE '1900-01-01'
)
SELECT
  e.agent,
  e.account_id AS AID,
  COALESCE(
    NULLIF(TRIM(CONCAT(IFNULL(per.first_name, ''), ' ', IFNULL(per.last_name, ''))), ''),
    ua.name,
    ua.email,
    CAST(e.account_id AS STRING)
  ) AS name,
  ua.email,
  b.date_of_birth AS dob,
  FORMAT_DATE('%m-%d', b.date_of_birth) AS dob_mmdd,
  DATE_DIFF((SELECT report_date FROM params), b.date_of_birth, YEAR) AS age,
  COALESCE(ua.locked, FALSE) AS locked,
  COALESCE(ua.lock_reason, '') AS lock_reason,
  COALESCE(ua.lock_reason_comment, '') AS lock_reason_comment
FROM birth b
INNER JOIN elite_am e ON e.account_id = b.account_id
INNER JOIN days dy ON FORMAT_DATE('%m-%d', b.date_of_birth) = FORMAT_DATE('%m-%d', dy.d)
LEFT JOIN `{PROJECT_ID}.transactional_data.uam_accounts` ua ON ua.id = e.account_id
LEFT JOIN `{PROJECT_ID}.transactional_data.uam_persons` per ON per.id = ua.person_id
ORDER BY e.agent, b.date_of_birth, name
""".strip()


def open_zendesk_sql() -> str:
    """Open Zendesk tickets for Elite AM players (include promo); return TIDs."""
    return f"""
WITH
{_elite_am_book_ctes()},
ticket_aid AS (
  SELECT
    e.agent,
    e.account_id,
    t.id AS ticket_id,
    t.created_at AS ticket_created_at,
    t.updated_at AS ticket_updated_at,
    LOWER(CAST(t.status AS STRING)) AS status,
    LOWER(COALESCE(CAST(t.subject AS STRING), '')) AS subject
  FROM `{PROJECT_ID}.zendesk.ticket` t
  LEFT JOIN `{PROJECT_ID}.zendesk.user` r ON t.requester_id = r.id
  INNER JOIN `{PROJECT_ID}.transactional_data.uam_accounts` ua
    ON CAST(r.external_id AS STRING) = CAST(ua.id AS STRING)
    OR (r.email IS NOT NULL AND ua.email IS NOT NULL AND LOWER(r.email) = LOWER(ua.email))
  INNER JOIN elite_am e ON e.account_id = ua.id
  WHERE LOWER(CAST(t.status AS STRING)) NOT IN ('solved', 'closed', 'deleted')
)
SELECT
  agent,
  account_id AS AID,
  COALESCE(
    NULLIF(TRIM(CONCAT(IFNULL(per.first_name, ''), ' ', IFNULL(per.last_name, ''))), ''),
    ua.name,
    ua.email,
    CAST(account_id AS STRING)
  ) AS name,
  COUNT(DISTINCT ticket_id) AS open_tickets,
  MIN(ticket_created_at) AS oldest_ticket_at,
  MAX(ticket_updated_at) AS latest_ticket_at,
  ARRAY_AGG(DISTINCT CAST(ticket_id AS STRING) ORDER BY CAST(ticket_id AS STRING) LIMIT 8) AS ticket_ids,
  ARRAY_AGG(DISTINCT subject ORDER BY subject LIMIT 8) AS subjects
FROM ticket_aid ta
LEFT JOIN `{PROJECT_ID}.transactional_data.uam_accounts` ua ON ua.id = ta.account_id
LEFT JOIN `{PROJECT_ID}.transactional_data.uam_persons` per ON per.id = ua.person_id
GROUP BY agent, account_id, name, ua.email
ORDER BY agent, open_tickets DESC
""".strip()


def locked_players_sql() -> str:
    """Locked Elite AM accounts with lock reason and locked_at."""
    return f"""
WITH
{_elite_am_book_ctes()}
SELECT
  e.agent,
  e.account_id AS AID,
  COALESCE(
    NULLIF(TRIM(CONCAT(IFNULL(per.first_name, ''), ' ', IFNULL(per.last_name, ''))), ''),
    ua.name,
    ua.email,
    CAST(e.account_id AS STRING)
  ) AS name,
  COALESCE(ua.locked, FALSE) AS locked,
  COALESCE(ua.lock_reason, '') AS lock_reason,
  COALESCE(ua.lock_reason_comment, '') AS lock_reason_comment,
  DATE(ua.locked_at) AS locked_at
FROM elite_am e
INNER JOIN `{PROJECT_ID}.transactional_data.uam_accounts` ua ON ua.id = e.account_id
LEFT JOIN `{PROJECT_ID}.transactional_data.uam_persons` per ON per.id = ua.person_id
WHERE COALESCE(ua.locked, FALSE) = TRUE
ORDER BY e.agent, name
""".strip()


def big_winners_sql(report_date: date) -> str:
    """Players whose net GGR was ≤ −BIG_WINNER_SECTION_MIN on report_date.

    GGR is house-side (`profit − loss`), so a player win is a *negative* GGR
    day — `SUM(profit - loss) <= -BIG_WINNER_SECTION_MIN` catches the big
    winners. Read the sign backwards and this selects the biggest losers.

    Includes **all** accounts on that day (not just Elite), because the Big
    Winners section deliberately reaches outside the Elite book. Elite rows
    carry their AM's agent tag; non-Elite rows have agent = NULL and
    is_elite = FALSE — every AM sees those rows in their own tab.

    Columns returned:
      agent, is_elite, AID, name, win_ggr, sc_turnover, sc_won, game,
      pending_rd_amount
    """
    d = _iso(report_date)
    return f"""
WITH
{_elite_am_book_ctes()},
day_ggr AS (
  SELECT
    k.account_id,
    SUM(CAST(k.profit AS FLOAT64)) AS sc_turnover,
    SUM(CAST(k.loss AS FLOAT64)) AS sc_won,
    SUM(CAST(k.profit AS FLOAT64) - CAST(k.loss AS FLOAT64)) AS ggr_day
  FROM `{PROJECT_ID}.jackpota_agg.daily_player_revenue_kpis` k
  WHERE k.date = DATE '{d}'
  GROUP BY k.account_id
  HAVING SUM(CAST(k.profit AS FLOAT64) - CAST(k.loss AS FLOAT64)) <= -{BIG_WINNER_SECTION_MIN}
),
top_game AS (
  SELECT account_id, product_title AS game
  FROM (
    SELECT g.account_id, g.product_title,
      ROW_NUMBER() OVER (
        PARTITION BY g.account_id
        ORDER BY SUM(g.nrows) DESC, g.product_title
      ) AS rn
    FROM `{PROJECT_ID}.jackpota_agg.fact_gameplay_daily` g
    INNER JOIN day_ggr dg ON dg.account_id = g.account_id
    WHERE DATE(g.at) = DATE '{d}'
      AND g.product_title IS NOT NULL AND g.product_title != 'Jackpot'
    GROUP BY g.account_id, g.product_title
  )
  WHERE rn = 1
),
pending_rd AS (
  SELECT
    account_id,
    SUM(CAST(amount AS FLOAT64)) AS pending_rd_amount
  FROM `{PROJECT_ID}.transactional_data.payment_withdraw_money_requests`
  WHERE status = 'locked'
    AND account_id IN (SELECT account_id FROM day_ggr)
  GROUP BY account_id
)
SELECT
  e.agent,
  (e.account_id IS NOT NULL) AS is_elite,
  g.account_id AS AID,
  COALESCE(
    NULLIF(TRIM(CONCAT(IFNULL(per.first_name, ''), ' ', IFNULL(per.last_name, ''))), ''),
    ua.name,
    ua.email,
    CAST(g.account_id AS STRING)
  ) AS name,
  ROUND(-g.ggr_day, 2) AS win_ggr,
  ROUND(g.sc_turnover, 2) AS sc_turnover,
  ROUND(g.sc_won, 2) AS sc_won,
  tg.game,
  ROUND(COALESCE(rd.pending_rd_amount, 0), 2) AS pending_rd_amount
FROM day_ggr g
LEFT JOIN elite_am e ON e.account_id = g.account_id
LEFT JOIN `{PROJECT_ID}.transactional_data.uam_accounts` ua ON ua.id = g.account_id
LEFT JOIN `{PROJECT_ID}.transactional_data.uam_persons` per ON per.id = ua.person_id
LEFT JOIN top_game tg ON tg.account_id = g.account_id
LEFT JOIN pending_rd rd ON rd.account_id = g.account_id
ORDER BY g.ggr_day ASC
""".strip()


def big_losers_sql(report_date: date) -> str:
    """Players whose net GGR was ≥ BIG_LOSER_SECTION_MIN on report_date (house win).

    Positive GGR is a player loss day. Default floor is $5,000, same as the
    Pending RD Big Winner flag threshold.
    """
    d = _iso(report_date)
    return f"""
WITH
{_elite_am_book_ctes()},
day_ggr AS (
  SELECT
    k.account_id,
    SUM(CAST(k.profit AS FLOAT64)) AS sc_turnover,
    SUM(CAST(k.loss AS FLOAT64)) AS sc_won,
    SUM(CAST(k.profit AS FLOAT64) - CAST(k.loss AS FLOAT64)) AS ggr_day
  FROM `{PROJECT_ID}.jackpota_agg.daily_player_revenue_kpis` k
  WHERE k.date = DATE '{d}'
  GROUP BY k.account_id
  HAVING SUM(CAST(k.profit AS FLOAT64) - CAST(k.loss AS FLOAT64)) >= {BIG_LOSER_SECTION_MIN}
),
top_game AS (
  SELECT account_id, product_title AS game
  FROM (
    SELECT g.account_id, g.product_title,
      ROW_NUMBER() OVER (
        PARTITION BY g.account_id
        ORDER BY SUM(g.nrows) DESC, g.product_title
      ) AS rn
    FROM `{PROJECT_ID}.jackpota_agg.fact_gameplay_daily` g
    INNER JOIN day_ggr dg ON dg.account_id = g.account_id
    WHERE DATE(g.at) = DATE '{d}'
      AND g.product_title IS NOT NULL AND g.product_title != 'Jackpot'
    GROUP BY g.account_id, g.product_title
  )
  WHERE rn = 1
),
pending_rd AS (
  SELECT
    account_id,
    SUM(CAST(amount AS FLOAT64)) AS pending_rd_amount
  FROM `{PROJECT_ID}.transactional_data.payment_withdraw_money_requests`
  WHERE status = 'locked'
    AND account_id IN (SELECT account_id FROM day_ggr)
  GROUP BY account_id
)
SELECT
  e.agent,
  (e.account_id IS NOT NULL) AS is_elite,
  g.account_id AS AID,
  COALESCE(
    NULLIF(TRIM(CONCAT(IFNULL(per.first_name, ''), ' ', IFNULL(per.last_name, ''))), ''),
    ua.name,
    ua.email,
    CAST(g.account_id AS STRING)
  ) AS name,
  ROUND(g.ggr_day, 2) AS loss_ggr,
  ROUND(g.sc_turnover, 2) AS sc_turnover,
  ROUND(g.sc_won, 2) AS sc_won,
  tg.game,
  ROUND(COALESCE(rd.pending_rd_amount, 0), 2) AS pending_rd_amount
FROM day_ggr g
LEFT JOIN elite_am e ON e.account_id = g.account_id
LEFT JOIN `{PROJECT_ID}.transactional_data.uam_accounts` ua ON ua.id = g.account_id
LEFT JOIN `{PROJECT_ID}.transactional_data.uam_persons` per ON per.id = ua.person_id
LEFT JOIN top_game tg ON tg.account_id = g.account_id
LEFT JOIN pending_rd rd ON rd.account_id = g.account_id
ORDER BY g.ggr_day DESC
""".strip()


def agent_day_purchase_sql(report_date: date) -> str:
    """Per-AM purchase $ and purchased-player count for report_date."""
    d = _iso(report_date)
    return f"""
WITH
{_elite_am_book_ctes()},
day_kpi AS (
  SELECT
    e.agent,
    k.account_id,
    SUM(CAST(k.purchased AS FLOAT64)) AS purchased
  FROM `{PROJECT_ID}.jackpota_agg.daily_player_revenue_kpis` k
  INNER JOIN elite_am e ON e.account_id = k.account_id
  WHERE k.date = DATE '{d}'
  GROUP BY e.agent, k.account_id
)
SELECT
  agent,
  SUM(purchased) AS purchased,
  COUNTIF(purchased > 0) AS purchased_players
FROM day_kpi
GROUP BY agent
ORDER BY agent
""".strip()


def agent_book_size_sql() -> str:
    """Total Elite AM book size (assigned players) per agent tag."""
    return f"""
WITH
{_elite_am_book_ctes()}
SELECT
  agent,
  COUNT(DISTINCT account_id) AS total_players
FROM elite_am
GROUP BY agent
ORDER BY agent
""".strip()


# The book this query reads. Alon is in it **only** for the manager's team
# rollup — the manager owns his portfolio too, and leaving him out understated
# their Daily Avg Purchase by ~$4,000/day. He has no targets, so
# `actuals_by_agent` drops his per-agent row and he still gets no Goals section.
GOALS_BOOK_TAGS_SQL = ", ".join(
    f"'{t}'"
    for t in ("coral_s", "gabriel_e", "lee_t", "rachel_a", "gabriel", "alon_tish")
)
# The four AMs who carry targets. The month-shape divisors are measured on these
# only, so adding Alon to the team rollup cannot move anybody's per-AM pace.
GOALS_SCORED_TAGS_SQL = ", ".join(
    f"'{t}'" for t in ("coral_s", "gabriel_e", "lee_t", "rachel_a", "gabriel")
)


def goals_mtd_actuals_sql(report_date: date) -> str:
    """MTD Goals actuals per AM through report_date (inclusive).

    Book + agent: dashboard Elite (`dbt_aninditac.elite`) with `tag_agent_1`
    from the newest tag snapshot **on or before report_date**, not the newest
    overall. Tags re-snapshot daily and books move fast — Rachel went 557 → 589
    tagged accounts between 2026-08-16 and 08-18 — so an unpinned book scores a
    date's activity against a later roster and makes re-runs irreproducible.

    Net Purchase: the **by requested redeem** variant (Elite.MD alternate),
    purchased − (requested redeem − cancelled) − chargeback − refunds after
    account/date aggregation. This is what the Goals sheet scores on. The
    paid-redeem canonical variant is returned alongside as
    `mtd_net_purchase_paid_redeem` for reconciliation only.

    Reactivation and % Active follow the AMs' Tableau report
    (`elite_reference/Daily_Agg_Per_Player_Query_v1.sql`) so the board shows the
    number the team is measured on:
      * purchases = `payment_payment_orders` WHERE success, by purchase day;
      * Reactivation = purchase after a gap >= that query's
        `params.churn_period_days`, which is 20 days, not 30 (its inline
        comments saying 10 are stale). Once per AID in the month. See
        `config.GOALS_REACTIVATION_GAP_DAYS`;
      * % Active = accounts whose last successful purchase is within
        `config.GOALS_ACTIVE_LOOKBACK_DAYS` (30) days of the as-of date, over
        the unlocked portfolio. Point-in-time, so it is not paced.

    Upgrade to Elite: first Elite tag snapshot in [month_start, report_date]
    for accounts that were *not* Elite on the last snapshot before month
    start. Source: daily `dbt_utils.elite_account_tags` (history from
    2026-04-08). Attributed to `tag_agent_1` on that first in-window snap.

    Also returns month-shape factors (`purchasers_shape`, `upgrades_shape`):
    the share of a full month's value already reached by the same relative
    day, averaged over the two complete prior months. Monthly Purchasers and
    Upgrades saturate instead of accruing linearly (measured Jun/Jul 2026:
    ~0.92 and ~0.87 by day 16), so a linear MTD/day x days_in_month pace
    badly over-projects both. Revenue and Reactivations do track linearly and
    need no shape factor. Book-wide across the four Goals AMs: two months per
    agent is too thin to fit a per-agent curve.
    """
    d = _iso(report_date)
    month_start = _iso(report_date.replace(day=1))
    # Look back far enough for 30d reactivation gaps (prior purchase date).
    lookback = _iso(report_date.replace(day=1) - timedelta(days=400))
    # Relative month position, so the reference day matches in shorter months.
    elapsed = (report_date - report_date.replace(day=1)).days + 1
    days_in_month = monthrange(report_date.year, report_date.month)[1]
    month_frac = elapsed / days_in_month
    return f"""
WITH
{_elite_am_book_ctes(report_date)},
elite_goals AS (
  SELECT
    account_id,
    CASE WHEN agent = 'gabriel' THEN 'gabriel_e' ELSE agent END AS agent
  FROM elite_am
  WHERE agent IN ({GOALS_BOOK_TAGS_SQL})
),
-- Only the four AMs who carry targets. Used for the month-shape reference so
-- the per-AM pace divisors stay exactly what they were before Alon joined the
-- team rollup.
scored_book AS (
  SELECT account_id FROM elite_goals WHERE agent != 'alon_tish'
),
day_kpi AS (
  SELECT
    k.account_id,
    k.date,
    SUM(CAST(k.purchased AS FLOAT64)) AS purchased,
    -- Net Purchase "by requested redeem" (Elite.MD alternate variant, the one
    -- the Goals sheet scores on): purchase - (requested redeem - cancelled)
    -- - chargeback - refund. `redeemed_amt_confirmed_locked_pre` is the daily
    -- precomputed confirmed + locked + pre_authorized request amount, i.e.
    -- requested redeems net of cancelled / declined / failed. Verified exactly
    -- equal to those status sums from
    -- transactional_data.payment_withdraw_money_requests for all four AMs on
    -- 2026-08-01..16. Preferred over rebuilding from request status because
    -- `status` is current-state: a request locked yesterday can be cancelled
    -- tomorrow, so a status rebuild silently rewrites history, while this
    -- column is fixed at its daily snapshot.
    SUM(
      CAST(k.purchased AS FLOAT64)
      - CAST(COALESCE(k.redeemed_amt_confirmed_locked_pre, 0) AS FLOAT64)
      - CAST(COALESCE(k.chargeback, 0) AS FLOAT64)
      - CAST(COALESCE(k.refunds, 0) AS FLOAT64)
    ) AS net_purchase,
    -- Kept for reconciliation: the paid-redeem canonical variant the board
    -- used before, so a gap against the Goals sheet is explainable.
    SUM(
      CAST(k.purchased AS FLOAT64)
      - CAST(COALESCE(k.redeemed, 0) AS FLOAT64)
      - CAST(COALESCE(k.chargeback, 0) AS FLOAT64)
      - CAST(COALESCE(k.refunds, 0) AS FLOAT64)
    ) AS net_purchase_paid_redeem
  FROM `{PROJECT_ID}.jackpota_agg.daily_player_revenue_kpis` k
  INNER JOIN elite_goals e ON e.account_id = k.account_id
  WHERE k.date BETWEEN DATE '{lookback}' AND DATE '{d}'
  GROUP BY k.account_id, k.date
),
-- Every per-agent aggregate below also rolls up to a '{TEAM_AGENT_TAG}' row: the
-- manager is measured on the four books as one, and ROLLUP computes that over
-- the *union* of accounts in the same pass, at no extra query cost. It must be
-- a rollup rather than a sum of the four rows, because Monthly Purchasers,
-- Reactivations and Active Players are distinct-account counts. ARPPU and
-- % Active are then rebuilt in Python from these team totals — averaging the
-- four AM ratios is the classic error and gives a different, wrong answer.
mtd_kpi AS (
  SELECT
    IFNULL(e.agent, '{TEAM_AGENT_TAG}') AS agent,
    SUM(k.purchased) AS mtd_purchase,
    SUM(k.net_purchase) AS mtd_net_purchase,
    SUM(k.net_purchase_paid_redeem) AS mtd_net_purchase_paid_redeem,
    COUNT(DISTINCT IF(k.purchased > 0, k.account_id, NULL)) AS monthly_purchasers
  FROM day_kpi k
  INNER JOIN elite_goals e ON e.account_id = k.account_id
  WHERE k.date BETWEEN DATE '{month_start}' AND DATE '{d}'
  GROUP BY ROLLUP(e.agent)
),
-- Reactivation and % Active come from the AMs' Tableau source, not the revenue
-- KPI view, so the board reports the same number the team is measured on.
-- Source: elite_reference/Daily_Agg_Per_Player_Query_v1.sql — successful rows
-- of transactional_data.payment_payment_orders, one row per account per
-- purchase day.
tableau_purchase_days AS (
  SELECT DISTINCT p.account_id, DATE(p.at) AS purchase_date
  FROM `{PROJECT_ID}.transactional_data.payment_payment_orders` p
  INNER JOIN elite_goals e ON e.account_id = p.account_id
  WHERE p.success = TRUE
    AND DATE(p.at) BETWEEN DATE '{lookback}' AND DATE '{d}'
),
purchase_days AS (
  SELECT
    account_id,
    purchase_date,
    LAG(purchase_date) OVER (
      PARTITION BY account_id ORDER BY purchase_date
    ) AS prev_purchase_date
  FROM tableau_purchase_days
),
-- Tableau's is_reactivated_today: purchased today AND the gap from the previous
-- purchase >= params.churn_period_days (20). Counted once per AID in the month.
reactivations AS (
  SELECT
    IFNULL(e.agent, '{TEAM_AGENT_TAG}') AS agent,
    COUNT(DISTINCT p.account_id) AS reactivations
  FROM purchase_days p
  INNER JOIN elite_goals e ON e.account_id = p.account_id
  WHERE p.purchase_date BETWEEN DATE '{month_start}' AND DATE '{d}'
    AND p.prev_purchase_date IS NOT NULL
    AND DATE_DIFF(p.purchase_date, p.prev_purchase_date, DAY)
        >= {GOALS_REACTIVATION_GAP_DAYS}
  GROUP BY ROLLUP(e.agent)
),
-- % Active numerator: still-active players as of the as-of date, i.e. last
-- successful purchase within GOALS_ACTIVE_LOOKBACK_DAYS. Point-in-time, so it
-- does not accumulate through the month and needs no pacing.
-- A locked player still counts toward every KPI as long as he is tagged (user
-- rule, 2026-08-18; denominator confirmed as the whole tagged book on the same
-- day after the AM's own figures were compared). So no Goals numerator or
-- denominator filters on `locked` at all — the earlier "eligible subset"
-- compromise inflated % Active by 4-5 points against the AM's table.
recent_buyers AS (
  SELECT DISTINCT account_id
  FROM tableau_purchase_days
  WHERE purchase_date > DATE_SUB(DATE '{d}',
                                 INTERVAL {GOALS_ACTIVE_LOOKBACK_DAYS} DAY)
),
active_players AS (
  SELECT
    IFNULL(e.agent, '{TEAM_AGENT_TAG}') AS agent,
    COUNT(DISTINCT r.account_id) AS active_players
  FROM elite_goals e
  INNER JOIN recent_buyers r ON r.account_id = e.account_id
  GROUP BY ROLLUP(e.agent)
),
portfolio AS (
  -- % Active denominator is the whole tagged book, locked included. Verified
  -- against the AM's table for Aug 1-17 2026: Gabriel 82.9% vs their 82.0,
  -- Rachel 84.4% vs 85.0. portfolio_locked stays exposed so the locked drag is
  -- still visible next to it.
  SELECT
    IFNULL(e.agent, '{TEAM_AGENT_TAG}') AS agent,
    COUNT(DISTINCT e.account_id) AS portfolio_size,
    COUNT(DISTINCT e.account_id) AS portfolio_size_all,
    COUNT(DISTINCT IF(COALESCE(ua.locked, FALSE), e.account_id, NULL))
      AS portfolio_locked
  FROM elite_goals e
  LEFT JOIN `{PROJECT_ID}.transactional_data.uam_accounts` ua
    ON ua.id = e.account_id
  GROUP BY ROLLUP(e.agent)
),
last_prior AS (
  SELECT MAX(snapshot_date) AS snap
  FROM `{PROJECT_ID}.dbt_utils.elite_account_tags`
  WHERE snapshot_date < DATE '{month_start}'
),
prior_elite AS (
  SELECT DISTINCT t.account_id
  FROM `{PROJECT_ID}.dbt_utils.elite_account_tags` t
  CROSS JOIN last_prior l
  WHERE t.snapshot_date = l.snap
    AND t.category = 'Elite'
),
mtd_elite AS (
  SELECT
    account_id,
    MIN(snapshot_date) AS first_in_window
  FROM `{PROJECT_ID}.dbt_utils.elite_account_tags`
  WHERE category = 'Elite'
    AND snapshot_date BETWEEN DATE '{month_start}' AND DATE '{d}'
    AND tag_agent_1 IS NOT NULL
  GROUP BY account_id
),
first_agent AS (
  SELECT
    t.account_id,
    CASE
      WHEN t.tag_agent_1 = 'gabriel' THEN 'gabriel_e'
      ELSE t.tag_agent_1
    END AS agent,
    ROW_NUMBER() OVER (
      PARTITION BY t.account_id
      ORDER BY t.snapshot_date, t.tag_agent_1
    ) AS rn
  FROM `{PROJECT_ID}.dbt_utils.elite_account_tags` t
  INNER JOIN mtd_elite m
    ON m.account_id = t.account_id
   AND m.first_in_window = t.snapshot_date
  WHERE t.category = 'Elite'
    AND t.tag_agent_1 IS NOT NULL
),
upgrades AS (
  SELECT
    IFNULL(f.agent, '{TEAM_AGENT_TAG}') AS agent,
    COUNT(*) AS upgrades
  FROM mtd_elite m
  INNER JOIN first_agent f
    ON f.account_id = m.account_id AND f.rn = 1
  LEFT JOIN prior_elite p ON p.account_id = m.account_id
  WHERE p.account_id IS NULL
    AND f.agent IN ({GOALS_BOOK_TAGS_SQL})
  GROUP BY ROLLUP(f.agent)
),
-- Month-shape reference: the two complete months before the report month.
ref_bounds AS (
  SELECT
    ms,
    LAST_DAY(ms) AS me,
    GREATEST(
      1,
      CAST(ROUND({month_frac} * EXTRACT(DAY FROM LAST_DAY(ms))) AS INT64)
    ) AS ref_day
  FROM UNNEST([
    DATE_SUB(DATE '{month_start}', INTERVAL 1 MONTH),
    DATE_SUB(DATE '{month_start}', INTERVAL 2 MONTH)
  ]) AS ms
),
ref_purchasers AS (
  SELECT
    b.ms,
    COUNT(DISTINCT IF(EXTRACT(DAY FROM k.date) <= b.ref_day,
                      k.account_id, NULL)) AS to_day,
    COUNT(DISTINCT k.account_id) AS full_month
  FROM day_kpi k
  INNER JOIN scored_book s ON s.account_id = k.account_id
  CROSS JOIN ref_bounds b
  WHERE k.purchased > 0
    AND k.date BETWEEN b.ms AND b.me
  GROUP BY b.ms
),
ref_prior_snap AS (
  SELECT b.ms, MAX(t.snapshot_date) AS snap
  FROM ref_bounds b
  INNER JOIN `{PROJECT_ID}.dbt_utils.elite_account_tags` t
    ON t.snapshot_date < b.ms
  GROUP BY b.ms
),
ref_prior_elite AS (
  SELECT DISTINCT s.ms, t.account_id
  FROM ref_prior_snap s
  INNER JOIN `{PROJECT_ID}.dbt_utils.elite_account_tags` t
    ON t.snapshot_date = s.snap
  WHERE t.category = 'Elite'
),
ref_month_elite AS (
  SELECT b.ms, t.account_id, MIN(t.snapshot_date) AS first_in_window
  FROM ref_bounds b
  INNER JOIN `{PROJECT_ID}.dbt_utils.elite_account_tags` t
    ON t.snapshot_date BETWEEN b.ms AND b.me
  WHERE t.category = 'Elite'
    AND t.tag_agent_1 IN ({GOALS_SCORED_TAGS_SQL})
  GROUP BY b.ms, t.account_id
),
ref_upgrades AS (
  SELECT
    m.ms,
    COUNTIF(EXTRACT(DAY FROM m.first_in_window) <= b.ref_day) AS to_day,
    COUNT(*) AS full_month
  FROM ref_month_elite m
  INNER JOIN ref_bounds b ON b.ms = m.ms
  LEFT JOIN ref_prior_elite p
    ON p.ms = m.ms AND p.account_id = m.account_id
  WHERE p.account_id IS NULL
  GROUP BY m.ms
),
shapes AS (
  SELECT
    (SELECT AVG(SAFE_DIVIDE(to_day, full_month))
     FROM ref_purchasers WHERE full_month > 0) AS purchasers_shape,
    (SELECT AVG(SAFE_DIVIDE(to_day, full_month))
     FROM ref_upgrades WHERE full_month > 0) AS upgrades_shape
)
SELECT
  p.agent,
  COALESCE(m.mtd_purchase, 0) AS mtd_purchase,
  COALESCE(m.mtd_net_purchase, 0) AS mtd_net_purchase,
  COALESCE(m.mtd_net_purchase_paid_redeem, 0) AS mtd_net_purchase_paid_redeem,
  COALESCE(m.monthly_purchasers, 0) AS monthly_purchasers,
  COALESCE(r.reactivations, 0) AS reactivations,
  COALESCE(u.upgrades, 0) AS upgrades,
  COALESCE(p.portfolio_size, 0) AS portfolio_size,
  COALESCE(p.portfolio_size_all, 0) AS portfolio_size_all,
  COALESCE(p.portfolio_locked, 0) AS portfolio_locked,
  COALESCE(ap.active_players, 0) AS active_players,
  s.purchasers_shape,
  s.upgrades_shape,
  -- Surfaced so a mismatch report is diagnosable without writing a diagnostic
  -- script: if this is not the report date, the book drifted and the numbers are
  -- being scored against a different roster than the activity window.
  snap.snapshot_date AS book_snapshot_date
FROM portfolio p
CROSS JOIN shapes s
CROSS JOIN latest_elite_tag_snapshot snap
LEFT JOIN mtd_kpi m ON m.agent = p.agent
LEFT JOIN reactivations r ON r.agent = p.agent
LEFT JOIN upgrades u ON u.agent = p.agent
LEFT JOIN active_players ap ON ap.agent = p.agent
ORDER BY p.agent
""".strip()
