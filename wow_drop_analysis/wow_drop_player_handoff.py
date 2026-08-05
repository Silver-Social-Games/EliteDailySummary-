"""
WoW Drop Reason — fetch player handoff metrics for canvas/agent brief.
Usage:
  python wow_drop_analysis/wow_drop_player_handoff.py --aid 277467539
  python wow_drop_analysis/wow_drop_player_handoff.py --aid 277467539 --date 2026-06-08
"""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from daily_summary.generate_daily_elite_summary import PROJECT_ID, get_client, run_query  # noqa: E402


def fmt_money(v: float | None) -> str:
    if v is None:
        return "$0"
    return f"${v:,.0f}" if abs(v) >= 100 else f"${v:,.2f}"


def fmt_pct(num: float, den: float) -> str:
    if not den:
        return "0.0%"
    return f"{100 * num / den:.1f}%"


def fmt_day(d: date) -> str:
    return f"{d.strftime('%A')}, {d.day} {d.strftime('%b %Y')}"


def build_sql(aid: int, report_date: date) -> str:
    prior = report_date - timedelta(days=7)
    tue_start = report_date - timedelta(days=6)
    d14 = (report_date - timedelta(days=13)).isoformat()
    d30 = (report_date - timedelta(days=29)).isoformat()
    redeem_start = (report_date - timedelta(days=3)).isoformat()
    rd = report_date.isoformat()
    ps = prior.isoformat()
    ts = tue_start.isoformat()
    sun = (report_date - timedelta(days=1)).isoformat()

    return f"""
WITH kpi AS (
  SELECT date,
    SUM(CAST(purchased AS FLOAT64)) AS purchased,
    SUM(CAST(purchased AS FLOAT64) - CAST(redeemed AS FLOAT64)
      - CAST(chargeback AS FLOAT64) - CAST(refunds AS FLOAT64)) AS net_purchase,
    SUM(COALESCE(sc_reward_amount, 0) + COALESCE(sc_envelopes_amount, 0)) AS bonuses,
    SUM(CAST(profit AS FLOAT64) - CAST(loss AS FLOAT64)
      - COALESCE(sc_reward_amount, 0)) AS ngr
  FROM `{PROJECT_ID}.jackpota_agg.daily_player_revenue_kpis`
  WHERE account_id = {aid}
  GROUP BY date
),
lt AS (
  SELECT
    SUM(purchased) AS lifetime_purchased,
    SUM(net_purchase) AS lifetime_net_purchase,
    SUM(bonuses) AS lifetime_bonuses
  FROM kpi
),
windows AS (
  SELECT
    SUM(IF(date BETWEEN DATE '{ts}' AND DATE '{rd}', purchased, 0)) AS purchased_7d,
    SUM(IF(date BETWEEN DATE '{d14}' AND DATE '{rd}', purchased, 0)) AS purchased_14d,
    SUM(IF(date BETWEEN DATE '{d30}' AND DATE '{rd}', purchased, 0)) AS purchased_30d,
    MAX(IF(date = DATE '{ps}', purchased, 0)) AS prior_weekday_purchased,
    MAX(IF(date = DATE '{rd}', purchased, 0)) AS this_weekday_purchased,
    SUM(IF(date BETWEEN DATE '{ts}' AND DATE '{report_date - timedelta(days=1)}', purchased, 0)) AS rest_of_week_purchased
  FROM kpi
),
redeemed AS (
  SELECT
    ROUND(SUM(IF(status = 'confirmed', amount, 0)), 2) AS total_redeemed,
    MAX(IF(status = 'confirmed', DATE(created_at), NULL)) AS last_confirmed_date
  FROM `{PROJECT_ID}.transactional_data.payment_withdraw_money_requests`
  WHERE account_id = {aid}
),
pending AS (
  SELECT CAST(id AS STRING) AS redeem_id, ROUND(amount, 2) AS amount,
    DATETIME(created_at) AS submitted_at
  FROM `{PROJECT_ID}.transactional_data.payment_withdraw_money_requests`
  WHERE account_id = {aid} AND status IN ('pre_authorized', 'locked')
  ORDER BY created_at DESC LIMIT 1
),
pii AS (
  SELECT ua.id AS aid, ua.email,
    COALESCE(CONCAT(p.first_name, ' ', p.last_name), ua.name) AS name,
    COALESCE(e.agent_name, t.tag_agent_1) AS agent,
    (ua.locked OR COALESCE(eu.locked, FALSE)) AS account_locked,
    ua.locked_at,
    COALESCE(ua.lock_reason, eu.lock_reason) AS lock_reason,
    COALESCE(ua.lock_reason_comment, eu.lock_reason_comment) AS lock_reason_comment,
    ua.status AS redeem_workflow_status
  FROM `{PROJECT_ID}.transactional_data.uam_accounts` ua
  LEFT JOIN `{PROJECT_ID}.transactional_data.uam_persons` p ON ua.person_id = p.id
  LEFT JOIN `{PROJECT_ID}.dbt_aninditac.elite` e ON e.account_id = ua.id
  LEFT JOIN `{PROJECT_ID}.dbt_utils.elite_account_tags` t
    ON t.account_id = ua.id AND t.category = 'Elite'
  LEFT JOIN `{PROJECT_ID}.dbt_dashboards_mart.elite_users` eu
    ON ua.id = eu.account_id AND eu.report_date = DATE '{rd}'
  WHERE ua.id = {aid}
  LIMIT 1
),
sun AS (
  SELECT purchased, ngr FROM kpi WHERE date = DATE '{sun}'
),
failed_orders AS (
  SELECT COUNT(*) AS n
  FROM `{PROJECT_ID}.transactional_data.payment_payment_orders`
  WHERE account_id = {aid} AND DATE(created_at) = DATE '{rd}'
    AND status = 'created'
),
redeems_recent AS (
  SELECT DATETIME(created_at) AS ts, ROUND(amount, 2) AS amount, status
  FROM `{PROJECT_ID}.transactional_data.payment_withdraw_money_requests`
  WHERE account_id = {aid}
    AND DATE(created_at) BETWEEN DATE '{redeem_start}' AND DATE '{rd}'
  ORDER BY created_at DESC LIMIT 4
)
SELECT
  p.name, p.email, p.agent,
  p.account_locked, p.locked_at, p.lock_reason, p.lock_reason_comment, p.redeem_workflow_status,
  lt.lifetime_purchased, lt.lifetime_net_purchase, lt.lifetime_bonuses,
  w.purchased_7d, w.purchased_14d, w.purchased_30d,
  w.prior_weekday_purchased, w.this_weekday_purchased, w.rest_of_week_purchased,
  r.total_redeemed, r.last_confirmed_date,
  pd.redeem_id, pd.amount AS pending_redeem, pd.submitted_at,
  s.purchased AS sun_purchased, s.ngr AS sun_ngr,
  fo.n AS failed_order_attempts
FROM lt
CROSS JOIN windows w
CROSS JOIN pii p
LEFT JOIN redeemed r ON TRUE
LEFT JOIN pending pd ON TRUE
LEFT JOIN sun s ON TRUE
CROSS JOIN failed_orders fo
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--aid", type=int, required=True)
    parser.add_argument("--date", type=lambda s: date.fromisoformat(s),
                        default=date.today() - timedelta(days=1))
    args = parser.parse_args()

    report_date: date = args.date
    prior_date = report_date - timedelta(days=7)
    row = run_query(get_client(), build_sql(args.aid, report_date))[0]

    lp = float(row["lifetime_purchased"] or 0)
    delta = float(row["prior_weekday_purchased"] or 0) - float(row["this_weekday_purchased"] or 0)

    last_redeem = row.get("last_confirmed_date")
    if isinstance(last_redeem, date):
        last_redeem_str = f"{last_redeem.day} {last_redeem.strftime('%b %Y')}"
    else:
        last_redeem_str = "n/a"

    pending_ts = row.get("submitted_at")
    pending_when = ""
    if isinstance(pending_ts, datetime):
        pending_when = f"{pending_ts.strftime('%A')}, {pending_ts.day} {pending_ts.strftime('%b %Y %H:%M')}"

    locked_at = row.get("locked_at")
    locked_at_str = ""
    if isinstance(locked_at, datetime):
        locked_at_str = f"{locked_at.strftime('%A')}, {locked_at.day} {locked_at.strftime('%b %Y %H:%M')} UTC"

    account_locked = bool(row.get("account_locked"))
    lock_reason = row.get("lock_reason") or ""
    if account_locked and lock_reason == "Exclusion":
        primary_reason = "self_exclusion"
    elif account_locked:
        primary_reason = "account_locked"
    elif row.get("pending_redeem"):
        primary_reason = "redemption_in_progress"
    else:
        primary_reason = "investigate"

    out = {
        "aid": str(args.aid),
        "name": row.get("name"),
        "email": row.get("email"),
        "agent": row.get("agent"),
        "accountLocked": account_locked,
        "lockReason": lock_reason or None,
        "lockedAt": locked_at_str or None,
        "lockReasonComment": row.get("lock_reason_comment"),
        "redeemWorkflowStatus": row.get("redeem_workflow_status"),
        "primaryReason": primary_reason,
        "reportDate": report_date.isoformat(),
        "weekday": report_date.strftime("%A"),
        "mondayDelta": fmt_money(delta),
        "pendingRedeem": fmt_money(float(row["pending_redeem"])) if row.get("pending_redeem") else None,
        "redeemId": row.get("redeem_id"),
        "pendingSubmitted": pending_when,
        "lifetimePurchased": fmt_money(lp),
        "totalRedeemed": fmt_money(float(row["total_redeemed"] or 0)),
        "totalRedeemedDate": last_redeem_str,
        "holdPct": fmt_pct(float(row["lifetime_net_purchase"] or 0), lp),
        "bonusesPct": fmt_pct(float(row["lifetime_bonuses"] or 0), lp),
        "purchased7d": fmt_money(float(row["purchased_7d"] or 0)),
        "purchased14d": fmt_money(float(row["purchased_14d"] or 0)),
        "purchased30d": fmt_money(float(row["purchased_30d"] or 0)),
        "priorWeekday": fmt_money(float(row["prior_weekday_purchased"] or 0)),
        "thisWeekday": fmt_money(float(row["this_weekday_purchased"] or 0)),
        "restOfWeek": fmt_money(float(row["rest_of_week_purchased"] or 0)),
        "priorWeekdayLabel": fmt_day(prior_date),
        "thisWeekdayLabel": fmt_day(report_date),
        "failedOrderAttempts": int(row.get("failed_order_attempts") or 0),
        "sunPurchased": fmt_money(float(row["sun_purchased"])) if row.get("sun_purchased") else None,
        "sunNgr": fmt_money(float(row["sun_ngr"])) if row.get("sun_ngr") is not None else None,
    }

    out_path = Path(__file__).parent / "handoffs" / f"{report_date.isoformat()}_{args.aid}_handoff.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
