"""Parameterized BigQuery lookups for reward verification."""

from __future__ import annotations

from datetime import date

from google.cloud import bigquery

from elite_lib import PROJECT_ID, run_query_params

TOURNAMENT_SCAN_LIMIT = 5_000_000_000
HEAVY_SCAN_LIMIT = 10_000_000_000


def _scalar(name: str, type_: str, value: object) -> bigquery.ScalarQueryParameter:
    return bigquery.ScalarQueryParameter(name, type_, value)


def resolve_players(client: bigquery.Client, search: str) -> list[dict]:
    """Resolve an exact AID or normalized email to account records."""
    value = search.strip()
    if not value:
        return []

    latest_tags = f"""
    WITH latest_tags AS (
      SELECT account_id, tag_agent_1
      FROM `{PROJECT_ID}.dbt_utils.elite_account_tags`
      WHERE snapshot_date = (
        SELECT MAX(snapshot_date)
        FROM `{PROJECT_ID}.dbt_utils.elite_account_tags`
      )
        AND category = 'Elite'
    )
    """
    select_sql = f"""
    SELECT
      ua.id AS aid,
      COALESCE(
        NULLIF(ua.real_email, ''),
        NULLIF(ua.email, ''),
        NULLIF(ua.auth_email, ''),
        NULLIF(ua.normalized_email, '')
      ) AS email,
      ua.name,
      ua.locked,
      ua.lock_reason,
      ua.status,
      ua.email_verified,
      tags.tag_agent_1 AS agent
    FROM `{PROJECT_ID}.transactional_data.uam_accounts` ua
    LEFT JOIN latest_tags tags ON tags.account_id = ua.id
    """

    if value.isdigit():
        sql = f"{latest_tags}{select_sql} WHERE ua.id = @aid LIMIT 10"
        params = [_scalar("aid", "INT64", int(value))]
    else:
        normalized = value.casefold()
        sql = f"""
        {latest_tags}
        {select_sql}
        WHERE LOWER(TRIM(COALESCE(ua.normalized_email, ''))) = @email
           OR LOWER(TRIM(COALESCE(ua.real_email, ''))) = @email
           OR LOWER(TRIM(COALESCE(ua.email, ''))) = @email
           OR LOWER(TRIM(COALESCE(ua.auth_email, ''))) = @email
        ORDER BY ua.id
        LIMIT 20
        """
        params = [_scalar("email", "STRING", normalized)]

    return run_query_params(client, sql, params)


def lookup_orders(
    client: bigquery.Client,
    aid: int,
    date_from: date,
    date_to: date,
    offer_code: str = "",
) -> list[dict]:
    """Return purchase orders in the requested window."""
    sql = f"""
    SELECT
      p.id AS order_id,
      p.account_id AS aid,
      DATE(p.created_at) AS purchase_date,
      p.created_at AS purchase_ts,
      p.status,
      COALESCE(p.refunded, FALSE) AS refunded,
      ROUND(p.amount, 2) AS amount_usd,
      ROUND(p.sc_amount, 2) AS sc_amount,
      ROUND(GREATEST(p.sc_amount - p.amount, 0), 2) AS sc_bonus,
      ROUND(p.gc_amount, 2) AS gc_amount,
      p.code AS charge_code,
      p.transaction_id,
      t.code AS offer_code,
      t.title AS offer_title
    FROM `{PROJECT_ID}.transactional_data.payment_payment_orders` p
    LEFT JOIN `{PROJECT_ID}.transactional_data.payment_offer_templates` t
      ON t.id = p.offer_id
    WHERE p.account_id = @aid
      AND DATE(p.created_at) BETWEEN @date_from AND @date_to
      AND (
        @offer_code = ''
        OR LOWER(COALESCE(t.code, '')) = LOWER(@offer_code)
      )
    ORDER BY p.created_at DESC
    LIMIT 100
    """
    return run_query_params(
        client,
        sql,
        [
            _scalar("aid", "INT64", aid),
            _scalar("date_from", "DATE", date_from),
            _scalar("date_to", "DATE", date_to),
            _scalar("offer_code", "STRING", offer_code.strip()),
        ],
    )


def lookup_fs_wallet(
    client: bigquery.Client,
    aid: int,
    date_from: date,
    date_to: date,
    offer_code: str = "",
) -> list[dict]:
    """Return wallet grants that overlap the window or match the offer."""
    sql = f"""
    SELECT
      afs.id AS account_fs_id,
      afs.account_id AS aid,
      c.id AS campaign_id,
      c.code AS campaign_code,
      c.total_spins,
      c.bet_value,
      c.currency,
      c.status AS campaign_status,
      c.start_date,
      c.end_date,
      c.product_id,
      p.code AS game_code,
      p.title AS game_title,
      afs.left_spins,
      afs.credited,
      afs.used,
      afs.expired,
      afs.status,
      afs.created_at,
      afs.modified_at,
      afs.free_spin_id,
      afs.request_id
    FROM `{PROJECT_ID}.transactional_data.uam_account_free_spins` afs
    LEFT JOIN `{PROJECT_ID}.transactional_data.uam_free_spin_campaigns` c
      ON c.id = afs.free_spin_campaign_id
    LEFT JOIN `{PROJECT_ID}.transactional_data.core_products` p
      ON p.id = c.product_id
    WHERE afs.account_id = @aid
      AND (
        (
          @offer_code != ''
          AND CONTAINS_SUBSTR(LOWER(COALESCE(c.code, '')), LOWER(@offer_code))
        )
        OR DATE(afs.credited) BETWEEN DATE_SUB(@date_from, INTERVAL 1 DAY)
          AND DATE_ADD(@date_to, INTERVAL 5 DAY)
        OR DATE(afs.created_at) BETWEEN DATE_SUB(@date_from, INTERVAL 1 DAY)
          AND DATE_ADD(@date_to, INTERVAL 5 DAY)
        OR DATE(afs.used) BETWEEN DATE_SUB(@date_from, INTERVAL 1 DAY)
          AND DATE_ADD(@date_to, INTERVAL 5 DAY)
      )
    ORDER BY COALESCE(afs.credited, afs.created_at) DESC
    LIMIT 200
    """
    return run_query_params(
        client,
        sql,
        [
            _scalar("aid", "INT64", aid),
            _scalar("date_from", "DATE", date_from),
            _scalar("date_to", "DATE", date_to),
            _scalar("offer_code", "STRING", offer_code.strip()),
        ],
    )


def lookup_fact_rewards(
    client: bigquery.Client,
    aid: int,
    date_from: date,
    date_to: date,
    offer_code: str = "",
) -> list[dict]:
    """Return grouped FS reward rows for optional deep reconciliation."""
    sql = f"""
    SELECT
      r.account_id AS aid,
      r.reward_date,
      MIN(r.reward_datetime) AS first_reward_ts,
      MAX(r.reward_datetime) AS last_reward_ts,
      r.campaign_code,
      r.campaign_title,
      r.product_code,
      COUNT(*) AS raw_rows,
      COUNT(DISTINCT r.reward_id) AS distinct_rewards,
      SUM(COALESCE(r.reward_count, 1)) AS reward_count,
      MAX(COALESCE(r.total_spins, 0)) AS total_spins
    FROM `{PROJECT_ID}.jackpota_agg.fact_rewards` r
    WHERE r.account_id = @aid
      AND r.reward_date BETWEEN DATE_SUB(@date_from, INTERVAL 1 DAY)
        AND DATE_ADD(@date_to, INTERVAL 5 DAY)
      AND (
        LOWER(COALESCE(r.product_title, '')) = 'freespin'
        OR LOWER(COALESCE(r.product_type, '')) = 'freespin'
      )
      AND (
        @offer_code = ''
        OR CONTAINS_SUBSTR(LOWER(COALESCE(r.campaign_code, '')), LOWER(@offer_code))
      )
    GROUP BY
      r.account_id,
      r.reward_date,
      r.campaign_code,
      r.campaign_title,
      r.product_code
    ORDER BY r.reward_date DESC, r.campaign_code
    LIMIT 200
    """
    return run_query_params(
        client,
        sql,
        [
            _scalar("aid", "INT64", aid),
            _scalar("date_from", "DATE", date_from),
            _scalar("date_to", "DATE", date_to),
            _scalar("offer_code", "STRING", offer_code.strip()),
        ],
        maximum_bytes_billed=HEAVY_SCAN_LIMIT,
        timeout=120,
    )


def lookup_tournament_rewards(
    client: bigquery.Client,
    aid: int,
    date_from: date,
    date_to: date,
) -> list[dict]:
    """Return Platform Tournament bonus payouts."""
    sql = f"""
    SELECT
      br.id AS bonus_reward_id,
      br.account_id AS aid,
      DATE(br.created_at) AS payout_date,
      br.created_at AS credited_ts,
      br.sweepstake_amount AS sc_amount,
      br.gold_amount AS gc_amount,
      br.accepted,
      br.accepted_at,
      br.campaign_id,
      br.code AS reward_code,
      br.reference,
      br.product_id,
      p.code AS product_code,
      p.title AS product_title
    FROM `{PROJECT_ID}.transactional_data.uam_bonus_rewards` br
    LEFT JOIN `{PROJECT_ID}.transactional_data.core_products` p
      ON p.id = br.product_id
    WHERE br.account_id = @aid
      AND br.product_id = 8990
      AND DATE(br.created_at) BETWEEN @date_from AND @date_to
    ORDER BY br.created_at DESC
    LIMIT 100
    """
    return run_query_params(
        client,
        sql,
        [
            _scalar("aid", "INT64", aid),
            _scalar("date_from", "DATE", date_from),
            _scalar("date_to", "DATE", date_to),
        ],
        maximum_bytes_billed=TOURNAMENT_SCAN_LIMIT,
    )


def lookup_gameplay(
    client: bigquery.Client,
    aid: int,
    date_from: date,
    date_to: date,
    game_name: str = "",
) -> list[dict]:
    """Return game-level activity for optional usage evidence."""
    sql = f"""
    SELECT
      DATE(g.at) AS play_date,
      g.product_code AS game_code,
      g.product_title AS game_title,
      g.currency,
      g.freespin_flag,
      SUM(g.nrows) AS spins,
      SUM(g.profit) AS win,
      SUM(g.loss) AS wagered,
      SUM(g.ggr) AS ggr
    FROM `{PROJECT_ID}.jackpota_agg.fact_gameplay_daily` g
    WHERE g.account_id = @aid
      AND DATE(g.at) BETWEEN @date_from AND @date_to
      AND (
        @game_name = ''
        OR CONTAINS_SUBSTR(LOWER(COALESCE(g.product_title, '')), LOWER(@game_name))
        OR CONTAINS_SUBSTR(LOWER(COALESCE(g.product_code, '')), LOWER(@game_name))
      )
    GROUP BY
      play_date,
      game_code,
      game_title,
      g.currency,
      g.freespin_flag
    ORDER BY play_date DESC, spins DESC
    LIMIT 200
    """
    return run_query_params(
        client,
        sql,
        [
            _scalar("aid", "INT64", aid),
            _scalar("date_from", "DATE", date_from),
            _scalar("date_to", "DATE", date_to),
            _scalar("game_name", "STRING", game_name.strip()),
        ],
        maximum_bytes_billed=HEAVY_SCAN_LIMIT,
        timeout=120,
    )
