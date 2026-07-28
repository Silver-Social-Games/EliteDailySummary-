"""SQL builders for Elite AM Brief dashboard."""

from __future__ import annotations

from datetime import date

from elite_lib.bigquery import PROJECT_ID, dashboard_elite_ctes

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


def _elite_am_book_ctes() -> str:
    """Dashboard Elite book + latest agent, restricted to named AMs."""
    base = dashboard_elite_ctes(
        latest_name="latest_elite_tag_snapshot",
        elite_name="elite_book_raw",
        aid_alias="account_id",
        agent_alias="agent",
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
    """Top 10 purchasers per AM for report_date, with leading offer code/qty/$."""
    d = report_date.isoformat()
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
    SUM(amount) AS offer_amount
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
    ROW_NUMBER() OVER (
      PARTITION BY account_id
      ORDER BY offer_qty DESC, offer_amount DESC
    ) AS orn
  FROM offer_agg
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
  o.offer_amount
FROM top10 t
LEFT JOIN top_offer o ON o.account_id = t.account_id AND o.orn = 1
LEFT JOIN `{PROJECT_ID}.transactional_data.uam_accounts` ua ON ua.id = t.account_id
LEFT JOIN `{PROJECT_ID}.transactional_data.uam_persons` per ON per.id = ua.person_id
ORDER BY t.agent, t.rn
""".strip()


def locked_rd_over_5k_sql(report_date: date) -> str:
    """Pending locked redemptions ≥ $5k created in the last 3 days ending report_date."""
    d = report_date.isoformat()
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
    AND CAST(w.amount AS FLOAT64) >= 5000
    AND DATE(w.created_at) BETWEEN DATE_SUB(DATE '{d}', INTERVAL 2 DAY) AND DATE '{d}'
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
  r.created_date
FROM locked_rd r
INNER JOIN elite_am e ON e.account_id = r.account_id
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
  f.created_date
FROM first_locked f
INNER JOIN elite_am e ON e.account_id = f.account_id
LEFT JOIN `{PROJECT_ID}.transactional_data.uam_accounts` ua ON ua.id = f.account_id
LEFT JOIN `{PROJECT_ID}.transactional_data.uam_persons` per ON per.id = ua.person_id
ORDER BY e.agent, f.amount DESC
""".strip()


def birthdays_last_3d_sql(report_date: date) -> str:
    """Calendar birthdays in last 3 days ending on report_date (MM-DD match)."""
    d = report_date.isoformat()
    return f"""
WITH
{_elite_am_book_ctes()},
params AS (
  SELECT DATE '{d}' AS report_date
),
days AS (
  SELECT report_date AS d FROM params
  UNION ALL SELECT DATE_SUB(report_date, INTERVAL 1 DAY) FROM params
  UNION ALL SELECT DATE_SUB(report_date, INTERVAL 2 DAY) FROM params
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
  DATE_DIFF((SELECT report_date FROM params), b.date_of_birth, YEAR) AS age
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
    LOWER(CAST(t.status AS STRING)) AS status
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
  ARRAY_AGG(DISTINCT CAST(ticket_id AS STRING) ORDER BY CAST(ticket_id AS STRING) LIMIT 8) AS ticket_ids
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


def agent_day_purchase_sql(report_date: date) -> str:
    """Per-AM purchase $ and purchased-player count for report_date."""
    d = report_date.isoformat()
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
