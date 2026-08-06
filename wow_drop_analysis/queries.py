"""BigQuery SQL builders and candidate selection for same-weekday drops.

Split out of wow_drop_reason.py: these functions only build SQL strings
and shape/rank the rows that come back - no classification, no markdown
or canvas formatting, no Zendesk ticket copy.
"""

from __future__ import annotations

from datetime import date, timedelta

from elite_lib import PROJECT_ID, fmt_money, sql_int_list

from wow_drop_analysis.taxonomy import (
    SAME_DAY_CANDIDATE_LIMIT,
    TOP_SAME_DAY_LIMIT,
    ZERO_DAY_DROP_SHARE,
)


def top_same_day_sql(report_date: date) -> str:
    """Candidates for same-weekday comparison (prior > this); capped for scan size."""
    this_day = report_date.isoformat()
    prior_day = (report_date - timedelta(days=7)).isoformat()
    w0_start = (report_date - timedelta(days=6)).isoformat()
    return f"""
    WITH latest AS (
      SELECT MAX(snapshot_date) AS snap
      FROM `{PROJECT_ID}.dbt_utils.elite_account_tags`
    ),
    elite AS (
      SELECT DISTINCT
        e.account_id AS AID,
        COALESCE(t.tag_agent_1, e.agent_name) AS agent,
        e.agent_name AS agent_display
      FROM `{PROJECT_ID}.dbt_aninditac.elite` e
      CROSS JOIN latest l
      LEFT JOIN `{PROJECT_ID}.dbt_utils.elite_account_tags` t
        ON e.account_id = t.account_id AND t.snapshot_date = l.snap
        AND t.category = 'Elite' AND t.tag_agent_1 IS NOT NULL
    ),
    day_p AS (
      SELECT k.account_id AS AID,
        SUM(IF(k.date = DATE '{this_day}', CAST(k.purchased AS FLOAT64), 0)) AS this_day,
        SUM(IF(k.date = DATE '{prior_day}', CAST(k.purchased AS FLOAT64), 0)) AS prior_day
      FROM `{PROJECT_ID}.jackpota_agg.daily_player_revenue_kpis` k
      INNER JOIN elite e ON k.account_id = e.AID
      WHERE k.date IN (DATE '{this_day}', DATE '{prior_day}')
      GROUP BY 1
    ),
    w7 AS (
      SELECT k.account_id AS AID, SUM(CAST(k.purchased AS FLOAT64)) AS purchased_7d
      FROM `{PROJECT_ID}.jackpota_agg.daily_player_revenue_kpis` k
      WHERE k.date BETWEEN DATE '{w0_start}' AND DATE '{this_day}'
      GROUP BY 1
    ),
    pii AS (
      SELECT
        ua.id AS AID,
        COALESCE(CONCAT(p.first_name, ' ', p.last_name), ua.name) AS person_name
      FROM `{PROJECT_ID}.transactional_data.uam_accounts` ua
      LEFT JOIN `{PROJECT_ID}.transactional_data.uam_persons` p ON ua.person_id = p.id
    ),
    scored AS (
      SELECT e.AID, e.agent, e.agent_display,
        COALESCE(NULLIF(TRIM(eu.name), ''), NULLIF(TRIM(pi.person_name), ''), 'n/a') AS name,
        ROUND(d.prior_day, 2) AS prior_weekday,
        ROUND(d.this_day, 2) AS this_weekday,
        ROUND(d.prior_day - d.this_day, 2) AS delta,
        ROUND(COALESCE(w.purchased_7d, 0), 2) AS purchased_7d
      FROM elite e
      INNER JOIN day_p d ON e.AID = d.AID
      LEFT JOIN w7 w ON e.AID = w.AID
      LEFT JOIN pii pi ON e.AID = pi.AID
      LEFT JOIN `{PROJECT_ID}.dbt_dashboards_mart.elite_users` eu
        ON e.AID = eu.account_id AND eu.report_date = DATE '{this_day}'
      WHERE d.prior_day > d.this_day
    )
    SELECT * FROM scored ORDER BY delta DESC LIMIT {SAME_DAY_CANDIDATE_LIMIT}
    """


def top10_delta_sql(report_date: date) -> str:
    """Backward-compatible alias."""
    return top_same_day_sql(report_date)


def select_top_same_day_players(
    rows: list[dict],
    *,
    limit: int = TOP_SAME_DAY_LIMIT,
    elite_wow_drop: float | None = None,
) -> list[dict]:
    """Pick top N; prioritize $0 report-day players until majority of Elite WoW drop covered."""
    if not rows:
        return []

    ranked = sorted(rows, key=lambda r: float(r.get("delta") or 0), reverse=True)
    target = float(elite_wow_drop or 0) * ZERO_DAY_DROP_SHARE
    if target <= 0:
        target = sum(float(r.get("delta") or 0) for r in ranked[:limit]) * ZERO_DAY_DROP_SHARE

    zeros = [r for r in ranked if float(r.get("this_weekday") or 0) <= 0]
    partials = [r for r in ranked if float(r.get("this_weekday") or 0) > 0]

    picked: list[dict] = []
    seen: set[int] = set()
    cum = 0.0

    for r in zeros:
        if len(picked) >= limit:
            break
        aid = int(r["AID"])
        if aid in seen:
            continue
        picked.append(r)
        seen.add(aid)
        cum += float(r.get("delta") or 0)
        if cum >= target:
            break

    for pool in (zeros, partials):
        for r in pool:
            if len(picked) >= limit:
                break
            aid = int(r["AID"])
            if aid not in seen:
                picked.append(r)
                seen.add(aid)

    return picked[:limit]


def same_day_selection_summary(rows: list[dict], elite_wow_drop: float) -> str:
    """How the selected cohort is built — player-level gaps vs Elite WoW drop."""
    if not rows:
        return ""
    explained = sum(float(r.get("delta") or 0) for r in rows)
    zero_rows = [r for r in rows if float(r.get("this_weekday") or 0) <= 0]
    zero_drop = sum(float(r.get("delta") or 0) for r in zero_rows)
    pct_zero = 100 * zero_drop / explained if explained else 0
    return (
        f"_Top {len(rows)}: **{len(zero_rows)}** with **$0** report-day purchase · "
        f"**{pct_zero:.0f}%** of player-level gap from $0 days "
        f"({fmt_money(zero_drop)} of {fmt_money(explained)}) · "
        f"Elite WoW drop **{fmt_money(elite_wow_drop)}**._"
    )


def enrich_aids_sql(aids: list[int], report_date: date) -> str:
    if not aids:
        return "SELECT 1 WHERE FALSE"
    id_list = sql_int_list(aids)
    rd = report_date.isoformat()
    day_before = (report_date - timedelta(days=1)).isoformat()
    w0_start = (report_date - timedelta(days=6)).isoformat()
    lp_start = (report_date - timedelta(days=30)).isoformat()
    play_start = (report_date - timedelta(days=13)).isoformat()
    zd_start = (report_date - timedelta(days=13)).isoformat()
    zd_doc_start = (report_date - timedelta(days=30)).isoformat()
    return f"""
    SELECT
      ua.id AS AID,
      ua.email AS player_email,
      (ua.locked OR COALESCE(eu.locked, FALSE)) AS account_locked,
      ua.locked_at,
      COALESCE(ua.lock_reason, eu.lock_reason) AS lock_reason,
      COALESCE(ua.lock_reason_comment, eu.lock_reason_comment) AS lock_reason_comment,
      eu.red_flag,
      eu.red_flag_state,
      eu.red_flag_chargeback,
      eu.red_flag_refunds,
      eu.red_flag_aml,
      eu.red_flag_redeemed_to_purchase,
      eu.red_flag_locked,
      eu.redeem_status,
      ua.status AS account_status,
      pd.amount AS pending_redeem,
      pd.pending_redeem_count,
      CAST(pd.id AS STRING) AS redeem_id,
      COALESCE(fo.n, 0) AS failed_orders,
      COALESCE(foslp.n, 0) AS failed_orders_since_last_purchase,
      ROUND(COALESCE(rest.rest_purchased, 0), 2) AS rest_of_week,
      ROUND(COALESCE(k7.purchased_7d, 0), 2) AS purchased_7d,
      ROUND(COALESCE(k7.net_purchases_7d, 0), 2) AS net_purchases_7d,
      ROUND(COALESCE(k7.bets_7d, 0), 2) AS bets_7d,
      ROUND(COALESCE(k7.ggr_7d, 0), 2) AS ggr_7d,
      ROUND(COALESCE(k7.ngr_7d, 0), 2) AS ngr_7d,
      COALESCE(gp.spins_7d, 0) AS spins_7d,
      ROUND(COALESCE(rd.purchased, 0), 2) AS report_day_purchased,
      ROUND(COALESCE(rd.bets, 0), 2) AS report_day_bets,
      ROUND(COALESCE(db.ngr, 0), 2) AS day_before_ngr,
      ROUND(COALESCE(db.purchased, 0), 2) AS day_before_purchased,
      pcal.purchase_calendar,
      COALESCE(streak.consecutive_no_purchase_days, 0) AS consecutive_no_purchase_days,
      lb.last_purchase_date,
      ROUND(COALESCE(lb.last_purchase_amt, 0), 2) AS last_purchase_amt,
      lplay.last_play_date,
      rz.restriction_zendesk,
      zd.recent_zendesk,
      zdoc.zendesk_missing_doc,
      zdoc.zendesk_missing_doc_at,
      zpoa.zendesk_poa_resolved,
      zpoa.zendesk_poa_resolved_at,
      zblock.zendesk_purchase_block,
      zblock.zendesk_block_subject,
      zblock.zendesk_block_ticket_tags,
      zblock.zendesk_block_created_at,
      fav.favourite_game_7d,
      COALESCE(rds.report_day_spins, 0) AS report_day_spins,
      ROUND(COALESCE(lt.lifetime_purchased, 0), 2) AS lifetime_purchased,
      ROUND(COALESCE(lt.lifetime_net_purchase, 0), 2) AS lifetime_net_purchase,
      zreq.zendesk_user_id
    FROM `{PROJECT_ID}.transactional_data.uam_accounts` ua
    LEFT JOIN `{PROJECT_ID}.dbt_dashboards_mart.elite_users` eu
      ON ua.id = eu.account_id AND eu.report_date = DATE '{rd}'
    LEFT JOIN (
      SELECT
        CAST(ua2.id AS INT64) AS account_id,
        ANY_VALUE(zu.id) AS zendesk_user_id
      FROM `{PROJECT_ID}.transactional_data.uam_accounts` ua2
      LEFT JOIN `{PROJECT_ID}.zendesk.user` zu
        ON CAST(zu.external_id AS STRING) = CAST(ua2.id AS STRING)
        OR zu.email = ua2.email
      WHERE ua2.id IN ({id_list})
      GROUP BY 1
    ) zreq ON ua.id = zreq.account_id
    LEFT JOIN (
      SELECT
        account_id,
        SUM(amount) AS amount,
        COUNT(*) AS pending_redeem_count,
        MAX_BY(id, created_at) AS id
      FROM `{PROJECT_ID}.transactional_data.payment_withdraw_money_requests`
      WHERE account_id IN ({id_list}) AND status IN ('pre_authorized', 'locked')
      GROUP BY account_id
    ) pd ON ua.id = pd.account_id
    LEFT JOIN (
      SELECT account_id, COUNT(*) AS n
      FROM `{PROJECT_ID}.transactional_data.payment_payment_orders`
      WHERE account_id IN ({id_list}) AND DATE(created_at) = DATE '{rd}' AND status = 'created'
      GROUP BY 1
    ) fo ON ua.id = fo.account_id
    LEFT JOIN (
      SELECT account_id, SUM(CAST(purchased AS FLOAT64)) AS rest_purchased
      FROM `{PROJECT_ID}.jackpota_agg.daily_player_revenue_kpis`
      WHERE account_id IN ({id_list})
        AND date BETWEEN DATE '{w0_start}' AND DATE '{day_before}'
      GROUP BY 1
    ) rest ON ua.id = rest.account_id
    LEFT JOIN (
      SELECT account_id,
        SUM(CAST(purchased AS FLOAT64)) AS purchased_7d,
        SUM(CAST(purchased AS FLOAT64) - CAST(redeemed AS FLOAT64)
          - CAST(chargeback AS FLOAT64) - CAST(refunds AS FLOAT64)) AS net_purchases_7d,
        SUM(CAST(profit AS FLOAT64)) AS bets_7d,
        SUM(CAST(profit AS FLOAT64) - CAST(loss AS FLOAT64)) AS ggr_7d,
        SUM(CAST(profit AS FLOAT64) - CAST(loss AS FLOAT64)
          - COALESCE(sc_reward_amount, 0)) AS ngr_7d
      FROM `{PROJECT_ID}.jackpota_agg.daily_player_revenue_kpis`
      WHERE account_id IN ({id_list})
        AND date BETWEEN DATE '{w0_start}' AND DATE '{rd}'
      GROUP BY 1
    ) k7 ON ua.id = k7.account_id
    LEFT JOIN (
      SELECT account_id,
        SUM(CAST(purchased AS FLOAT64)) AS purchased,
        SUM(CAST(profit AS FLOAT64)) AS bets
      FROM `{PROJECT_ID}.jackpota_agg.daily_player_revenue_kpis`
      WHERE account_id IN ({id_list}) AND date = DATE '{rd}'
      GROUP BY 1
    ) rd ON ua.id = rd.account_id
    LEFT JOIN (
      SELECT account_id,
        SUM(CAST(profit AS FLOAT64) - CAST(loss AS FLOAT64)
          - COALESCE(sc_reward_amount, 0)) AS ngr,
        SUM(CAST(purchased AS FLOAT64)) AS purchased
      FROM `{PROJECT_ID}.jackpota_agg.daily_player_revenue_kpis`
      WHERE account_id IN ({id_list}) AND date = DATE '{day_before}'
      GROUP BY 1
    ) db ON ua.id = db.account_id
    LEFT JOIN (
      SELECT g.account_id, SUM(g.nrows) AS spins_7d
      FROM `{PROJECT_ID}.jackpota_agg.fact_gameplay_daily` g
      WHERE g.account_id IN ({id_list})
        AND DATE(g.at) BETWEEN DATE '{w0_start}' AND DATE '{rd}'
        AND g.product_title IS NOT NULL AND g.product_title != 'Jackpot'
      GROUP BY 1
    ) gp ON ua.id = gp.account_id
    LEFT JOIN (
      SELECT account_id,
        STRING_AGG(day_label, ', ' ORDER BY date) AS purchase_calendar
      FROM (
        SELECT account_id, date,
          CONCAT(
            FORMAT_DATE('%A', date), ' $',
            CAST(CAST(ROUND(SUM(CAST(purchased AS FLOAT64))) AS INT64) AS STRING)
          ) AS day_label
        FROM `{PROJECT_ID}.jackpota_agg.daily_player_revenue_kpis`
        WHERE account_id IN ({id_list})
          AND date BETWEEN DATE '{w0_start}' AND DATE '{rd}'
        GROUP BY 1, 2
        HAVING SUM(CAST(purchased AS FLOAT64)) > 0
      )
      GROUP BY 1
    ) pcal ON ua.id = pcal.account_id
    LEFT JOIN (
      WITH daily AS (
        SELECT p.account_id, p.date,
          SUM(CAST(p.purchased AS FLOAT64)) AS purchased
        FROM `{PROJECT_ID}.jackpota_agg.daily_player_revenue_kpis` p
        WHERE p.account_id IN ({id_list})
          AND p.date BETWEEN DATE '{w0_start}' AND DATE '{rd}'
        GROUP BY 1, 2
      ),
      grid AS (
        SELECT ua2.id AS account_id, d AS date
        FROM `{PROJECT_ID}.transactional_data.uam_accounts` ua2
        CROSS JOIN UNNEST(GENERATE_DATE_ARRAY(DATE '{w0_start}', DATE '{rd}')) AS d
        WHERE ua2.id IN ({id_list})
      ),
      filled AS (
        SELECT g.account_id, g.date, COALESCE(d.purchased, 0) AS purchased
        FROM grid g
        LEFT JOIN daily d ON g.account_id = d.account_id AND g.date = d.date
      ),
      ranked AS (
        SELECT account_id, purchased,
          ROW_NUMBER() OVER (PARTITION BY account_id ORDER BY date DESC) AS days_back
        FROM filled
      )
      SELECT account_id,
        COALESCE(
          MIN(IF(purchased > 0, days_back - 1, NULL)),
          MAX(days_back)
        ) AS consecutive_no_purchase_days
      FROM ranked
      GROUP BY account_id
    ) streak ON ua.id = streak.account_id
    LEFT JOIN (
      SELECT account_id, last_purchase_date, last_purchase_amt
      FROM (
        SELECT account_id, date AS last_purchase_date,
          SUM(CAST(purchased AS FLOAT64)) AS last_purchase_amt
        FROM `{PROJECT_ID}.jackpota_agg.daily_player_revenue_kpis`
        WHERE account_id IN ({id_list})
          AND date BETWEEN DATE '{lp_start}' AND DATE '{rd}'
        GROUP BY 1, 2
        HAVING SUM(CAST(purchased AS FLOAT64)) > 0
      )
      QUALIFY ROW_NUMBER() OVER (PARTITION BY account_id ORDER BY last_purchase_date DESC) = 1
    ) lb ON ua.id = lb.account_id
    LEFT JOIN (
      SELECT lb.account_id, COUNT(*) AS n
      FROM (
        SELECT account_id, last_purchase_date
        FROM (
          SELECT account_id, date AS last_purchase_date,
            SUM(CAST(purchased AS FLOAT64)) AS last_purchase_amt
          FROM `{PROJECT_ID}.jackpota_agg.daily_player_revenue_kpis`
          WHERE account_id IN ({id_list})
            AND date BETWEEN DATE '{lp_start}' AND DATE '{rd}'
          GROUP BY 1, 2
          HAVING SUM(CAST(purchased AS FLOAT64)) > 0
        )
        QUALIFY ROW_NUMBER() OVER (PARTITION BY account_id ORDER BY last_purchase_date DESC) = 1
      ) lb
      INNER JOIN `{PROJECT_ID}.transactional_data.payment_payment_orders` po
        ON po.account_id = lb.account_id
       AND DATE(po.created_at) > lb.last_purchase_date
       AND DATE(po.created_at) <= DATE '{rd}'
       AND po.status = 'created'
      GROUP BY 1
    ) foslp ON ua.id = foslp.account_id
    LEFT JOIN (
      SELECT g.account_id, MAX(DATE(g.at)) AS last_play_date
      FROM `{PROJECT_ID}.jackpota_agg.fact_gameplay_daily` g
      WHERE g.account_id IN ({id_list})
        AND DATE(g.at) BETWEEN DATE '{play_start}' AND DATE '{rd}'
        AND g.product_title IS NOT NULL AND g.product_title != 'Jackpot'
      GROUP BY 1
    ) lplay ON ua.id = lplay.account_id
    LEFT JOIN (
      SELECT account_id, ticket_line AS restriction_zendesk
      FROM (
        SELECT account_id, ticket_line,
          ROW_NUMBER() OVER (PARTITION BY account_id ORDER BY ticket_pri, created_at DESC) AS rn
        FROM (
          SELECT ua.id AS account_id, t.created_at,
            CONCAT(
              FORMAT_DATE('%d %b', DATE(t.created_at)), ' "',
              REPLACE(COALESCE(t.subject, ''), '"', "'"), '"'
            ) AS ticket_line,
            CASE
              WHEN LOWER(COALESCE(t.subject, '')) LIKE '%legal%' THEN 1
              WHEN LOWER(COALESCE(t.subject, '')) LIKE '%suspend%' THEN 2
              WHEN LOWER(COALESCE(t.subject, '')) LIKE '%restrict%'
                   AND LOWER(COALESCE(t.subject, '')) NOT LIKE '%unrestrict%' THEN 3
              WHEN LOWER(COALESCE(t.subject, '')) LIKE '%unrestrict%' THEN 4
              ELSE 9
            END AS ticket_pri
          FROM `{PROJECT_ID}.zendesk.ticket` t
          LEFT JOIN `{PROJECT_ID}.zendesk.user` r ON t.requester_id = r.id
          INNER JOIN `{PROJECT_ID}.transactional_data.uam_accounts` ua
            ON CAST(r.external_id AS STRING) = CAST(ua.id AS STRING) OR r.email = ua.email
          WHERE ua.id IN ({id_list})
            AND DATE(t.created_at) BETWEEN DATE '{zd_start}' AND DATE '{rd}'
            AND (
              LOWER(COALESCE(t.subject, '')) LIKE '%legal%'
              OR LOWER(COALESCE(t.subject, '')) LIKE '%suspend%'
              OR LOWER(COALESCE(t.subject, '')) LIKE '%restrict%'
              OR LOWER(COALESCE(t.subject, '')) LIKE '%unrestrict%'
            )
        )
      )
      WHERE rn = 1
    ) rz ON ua.id = rz.account_id
    LEFT JOIN (
      SELECT account_id,
        STRING_AGG(ticket_line, ', ' ORDER BY ticket_pri, created_at DESC) AS recent_zendesk
      FROM (
        SELECT account_id, ticket_line, ticket_pri, created_at,
          ROW_NUMBER() OVER (PARTITION BY account_id ORDER BY ticket_pri, created_at DESC) AS rn
        FROM (
          SELECT ua.id AS account_id, t.created_at,
            CONCAT(
              FORMAT_DATE('%d %b', DATE(t.created_at)), ' "',
              REPLACE(COALESCE(t.subject, ''), '"', "'"), '"'
            ) AS ticket_line,
            CASE
              WHEN LOWER(COALESCE(t.subject, '')) LIKE '%legal%' THEN 1
              WHEN LOWER(COALESCE(t.subject, '')) LIKE '%suspend%' THEN 2
              WHEN LOWER(COALESCE(t.subject, '')) LIKE '%restrict%'
                   AND LOWER(COALESCE(t.subject, '')) NOT LIKE '%unrestrict%' THEN 3
              WHEN LOWER(COALESCE(t.subject, '')) LIKE '%unrestrict%' THEN 4
              WHEN LOWER(COALESCE(t.subject, '')) LIKE '%charge%' THEN 5
              ELSE 9
            END AS ticket_pri
          FROM `{PROJECT_ID}.zendesk.ticket` t
          LEFT JOIN `{PROJECT_ID}.zendesk.user` r ON t.requester_id = r.id
          INNER JOIN `{PROJECT_ID}.transactional_data.uam_accounts` ua
            ON CAST(r.external_id AS STRING) = CAST(ua.id AS STRING) OR r.email = ua.email
          WHERE ua.id IN ({id_list})
            AND DATE(t.created_at) BETWEEN DATE '{zd_start}' AND DATE '{rd}'
        )
      )
      WHERE rn <= 3
      GROUP BY 1
    ) zd ON ua.id = zd.account_id
    LEFT JOIN (
      SELECT account_id, doc_text AS zendesk_missing_doc, doc_at AS zendesk_missing_doc_at
      FROM (
        SELECT ua.id AS account_id,
          COALESCE(NULLIF(TRIM(t.description), ''), t.subject) AS doc_text,
          DATE(t.created_at) AS doc_at,
          ROW_NUMBER() OVER (
            PARTITION BY ua.id
            ORDER BY
              CASE
                WHEN LOWER(COALESCE(t.description, '')) LIKE '%invalid poa%'
                  OR LOWER(COALESCE(t.description, '')) LIKE '%poa declined%' THEN 1
                WHEN LOWER(COALESCE(t.subject, '')) LIKE '%poa declined%' THEN 2
                WHEN LOWER(COALESCE(t.subject, '')) LIKE '%poa%'
                  OR LOWER(COALESCE(t.description, '')) LIKE '%poa%' THEN 3
                WHEN 'kyc_follow_up' IN UNNEST(COALESCE(t.tags, [])) THEN 4
                WHEN 'verification' IN UNNEST(COALESCE(t.tags, [])) THEN 5
                WHEN 'ops_escalation_address_query' IN UNNEST(COALESCE(t.tags, [])) THEN 6
                ELSE 9
              END,
              t.created_at DESC
          ) AS rn
        FROM `{PROJECT_ID}.zendesk.ticket` t
        LEFT JOIN `{PROJECT_ID}.zendesk.user` r ON t.requester_id = r.id
        INNER JOIN `{PROJECT_ID}.transactional_data.uam_accounts` ua
          ON CAST(r.external_id AS STRING) = CAST(ua.id AS STRING) OR r.email = ua.email
        WHERE ua.id IN ({id_list})
          AND DATE(t.created_at) BETWEEN DATE '{zd_doc_start}'
            AND LEAST(DATE_ADD(DATE '{rd}', INTERVAL 7 DAY), CURRENT_DATE())
          AND (
            LOWER(COALESCE(t.subject, '')) LIKE '%poa%'
            OR LOWER(COALESCE(t.description, '')) LIKE '%poa%'
            OR LOWER(COALESCE(t.description, '')) LIKE '%proof%address%'
            OR LOWER(COALESCE(t.description, '')) LIKE '%utility bill%'
            OR LOWER(COALESCE(t.description, '')) LIKE '%kyc%'
            OR 'kyc_follow_up' IN UNNEST(COALESCE(t.tags, []))
            OR 'verification' IN UNNEST(COALESCE(t.tags, []))
            OR 'ops_escalation_address_query' IN UNNEST(COALESCE(t.tags, []))
          )
          AND LOWER(COALESCE(t.description, '')) NOT LIKE 'conversation with%'
          AND LENGTH(COALESCE(t.description, t.subject, '')) > 15
      )
      WHERE rn = 1
    ) zdoc ON ua.id = zdoc.account_id
    LEFT JOIN (
      SELECT account_id,
        LEFT(resolution_body, 240) AS zendesk_poa_resolved,
        resolution_at AS zendesk_poa_resolved_at
      FROM (
        SELECT ua.id AS account_id,
          tc.body AS resolution_body,
          DATE(tc.created) AS resolution_at,
          ROW_NUMBER() OVER (PARTITION BY ua.id ORDER BY tc.created DESC) AS rn
        FROM `{PROJECT_ID}.zendesk.ticket_comment` tc
        INNER JOIN `{PROJECT_ID}.zendesk.ticket` t ON tc.ticket_id = t.id
        LEFT JOIN `{PROJECT_ID}.zendesk.user` r ON t.requester_id = r.id
        INNER JOIN `{PROJECT_ID}.transactional_data.uam_accounts` ua
          ON CAST(r.external_id AS STRING) = CAST(ua.id AS STRING) OR r.email = ua.email
        WHERE ua.id IN ({id_list})
          AND DATE(tc.created) BETWEEN DATE '{zd_doc_start}'
            AND LEAST(DATE_ADD(DATE '{rd}', INTERVAL 7 DAY), CURRENT_DATE())
          AND (
            LOWER(tc.body) LIKE '%already provided a valid poa%'
            OR LOWER(tc.body) LIKE '%already received valid poa%'
            OR LOWER(tc.body) LIKE '%valid poa confirming%'
            OR (
              LOWER(tc.body) LIKE '%valid poa%'
              AND LOWER(tc.body) LIKE '%lifted the account restrictions%'
            )
            OR LOWER(tc.body) LIKE '%lifted the account restrictions and processed%'
            OR LOWER(tc.body) LIKE '%restrictions lifted and rd processed%'
            OR (
              LOWER(tc.body) LIKE '%account is now completely clear of any restrictions%'
              AND 'elite_ops_resolution' IN UNNEST(COALESCE(t.tags, []))
            )
            OR (
              'elite_ops_resolution' IN UNNEST(COALESCE(t.tags, []))
              AND LOWER(tc.body) LIKE '%valid poa%'
              AND LOWER(tc.body) NOT LIKE '%still awaited%'
              AND LOWER(tc.body) NOT LIKE '%outstanding%'
            )
          )
          AND LOWER(tc.body) NOT LIKE '%poa declined%'
          AND LOWER(tc.body) NOT LIKE '%invalid poa%'
          AND LOWER(tc.body) NOT LIKE '%valid alternative recent poa still awaited%'
      )
      WHERE rn = 1
    ) zpoa ON ua.id = zpoa.account_id
    LEFT JOIN (
      SELECT account_id, zendesk_purchase_block, zendesk_block_subject, zendesk_block_ticket_tags,
        zendesk_block_created_at
      FROM (
        SELECT ua.id AS account_id,
          COALESCE(NULLIF(TRIM(t.description), ''), t.subject) AS zendesk_purchase_block,
          COALESCE(t.subject, '') AS zendesk_block_subject,
          ARRAY_TO_STRING(COALESCE(t.tags, []), ',') AS zendesk_block_ticket_tags,
          DATE(t.created_at) AS zendesk_block_created_at,
          ROW_NUMBER() OVER (
            PARTITION BY ua.id
            ORDER BY
              CASE
                WHEN LOWER(COALESCE(t.description, '')) LIKE '%please close this account%' THEN 1
                WHEN LOWER(COALESCE(t.description, '')) LIKE '%close this account%' THEN 2
                WHEN LOWER(COALESCE(t.subject, '')) LIKE '%close account%'
                  AND LOWER(COALESCE(t.description, '')) NOT LIKE 'hi %' THEN 3
                WHEN 'self_exclusion' IN UNNEST(COALESCE(t.tags, [])) THEN 4
                WHEN LOWER(COALESCE(t.subject, '')) LIKE '%closure%' THEN 5
                WHEN LOWER(COALESCE(t.description, '')) LIKE '%close this account%' THEN 4
                WHEN LOWER(COALESCE(t.subject, '')) LIKE '%time%out%'
                  OR LOWER(COALESCE(t.subject, '')) LIKE '%time-out%' THEN 5
                WHEN LOWER(COALESCE(t.description, '')) LIKE '%take the restriction off%' THEN 6
                WHEN LOWER(COALESCE(t.subject, '')) LIKE '%restrict%' THEN 7
                WHEN LOWER(COALESCE(t.description, '')) LIKE '%invalid poa%'
                  OR LOWER(COALESCE(t.description, '')) LIKE '%poa declined%' THEN 8
                WHEN LOWER(COALESCE(t.subject, '')) LIKE '%poa%'
                  OR LOWER(COALESCE(t.description, '')) LIKE '%poa%' THEN 9
                WHEN 'kyc_follow_up' IN UNNEST(COALESCE(t.tags, [])) THEN 10
                ELSE 99
              END,
              t.created_at DESC
          ) AS rn
        FROM `{PROJECT_ID}.zendesk.ticket` t
        LEFT JOIN `{PROJECT_ID}.zendesk.user` r ON t.requester_id = r.id
        INNER JOIN `{PROJECT_ID}.transactional_data.uam_accounts` ua
          ON CAST(r.external_id AS STRING) = CAST(ua.id AS STRING) OR r.email = ua.email
        WHERE ua.id IN ({id_list})
          AND DATE(t.created_at) BETWEEN DATE '{zd_doc_start}' AND DATE '{rd}'
          AND NOT (
            'proactive_campaigns_ticket' IN UNNEST(COALESCE(t.tags, []))
            OR 'proactive_campaigns_email' IN UNNEST(COALESCE(t.tags, []))
          )
          AND (
            'self_exclusion' IN UNNEST(COALESCE(t.tags, []))
            OR LOWER(COALESCE(t.subject, '')) LIKE '%close%account%'
            OR LOWER(COALESCE(t.subject, '')) LIKE '%closure%'
            OR LOWER(COALESCE(t.subject, '')) LIKE '%time%out%'
            OR LOWER(COALESCE(t.subject, '')) LIKE '%time-out%'
            OR LOWER(COALESCE(t.subject, '')) LIKE '%restrict%'
            OR LOWER(COALESCE(t.description, '')) LIKE '%close%account%'
            OR LOWER(COALESCE(t.description, '')) LIKE '%close this account%'
            OR LOWER(COALESCE(t.description, '')) LIKE '%take the restriction off%'
            OR LOWER(COALESCE(t.description, '')) LIKE '%taking a break%'
            OR LOWER(COALESCE(t.description, '')) LIKE '%invalid poa%'
            OR LOWER(COALESCE(t.description, '')) LIKE '%poa%'
            OR 'kyc_follow_up' IN UNNEST(COALESCE(t.tags, []))
            OR 'verification' IN UNNEST(COALESCE(t.tags, []))
          )
          AND LOWER(COALESCE(t.description, '')) NOT LIKE 'conversation with%'
          AND LENGTH(COALESCE(t.description, t.subject, '')) > 15
      )
      WHERE rn = 1
    ) zblock ON ua.id = zblock.account_id
    LEFT JOIN (
      SELECT account_id, product_title AS favourite_game_7d
      FROM (
        SELECT g.account_id, g.product_title,
          ROW_NUMBER() OVER (
            PARTITION BY g.account_id
            ORDER BY SUM(g.nrows) DESC, g.product_title
          ) AS rn
        FROM `{PROJECT_ID}.jackpota_agg.fact_gameplay_daily` g
        WHERE g.account_id IN ({id_list})
          AND DATE(g.at) BETWEEN DATE '{w0_start}' AND DATE '{rd}'
          AND g.product_title IS NOT NULL AND g.product_title != 'Jackpot'
        GROUP BY 1, 2
      )
      WHERE rn = 1
    ) fav ON ua.id = fav.account_id
    LEFT JOIN (
      SELECT g.account_id, SUM(g.nrows) AS report_day_spins
      FROM `{PROJECT_ID}.jackpota_agg.fact_gameplay_daily` g
      WHERE g.account_id IN ({id_list}) AND DATE(g.at) = DATE '{rd}'
        AND g.product_title IS NOT NULL AND g.product_title != 'Jackpot'
      GROUP BY 1
    ) rds ON ua.id = rds.account_id
    LEFT JOIN (
      SELECT account_id,
        SUM(CAST(purchased AS FLOAT64)) AS lifetime_purchased,
        SUM(
          CAST(purchased AS FLOAT64) - CAST(redeemed AS FLOAT64)
          - CAST(chargeback AS FLOAT64) - CAST(refunds AS FLOAT64)
        ) AS lifetime_net_purchase
      FROM `{PROJECT_ID}.jackpota_agg.daily_player_revenue_kpis`
      WHERE account_id IN ({id_list})
      GROUP BY 1
    ) lt ON ua.id = lt.account_id
    WHERE ua.id IN ({id_list})
    """
