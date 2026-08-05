"""
60 Days No Purchase Last Push — quarterly Elite export.

Managed Elite with no purchase in the past 60 days; locked/closed accounts excluded.

Run from project root:
  python last_push_60d/generate_60_days_no_purchase_last_push.py
  python last_push_60d/generate_60_days_no_purchase_last_push.py --date YYYY-MM-DD

Output: last_push_60d/exports/YYYY-MM-DD_60_days_no_purchase_last_push.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = Path(__file__).resolve().parent / "exports"
sys.path.insert(0, str(PROJECT_ROOT))

from elite_lib import PROJECT_ID, dashboard_elite_ctes, get_client, run_query  # noqa: E402
from wow_drop_analysis.wow_drop_reason import format_agent_name  # noqa: E402

EXPORT_BASENAME = "60_days_no_purchase_last_push"

COLUMNS = [
    ("AID", "AID"),
    ("Account Manager", "account_manager"),
    ("First Name", "first_name"),
    ("Last Name", "last_name"),
    ("Name", "name"),
    ("Email", "email"),
    ("Last Purchase Date", "last_purchase_date"),
    ("Last Purchase Amount", "last_purchase_amount"),
    ("LT Purchase", "lt_purchase"),
    ("Net Purchase", "lt_net_purchase"),
]


def build_sql(report_date: date) -> str:
    d60_start = (report_date - timedelta(days=59)).isoformat()
    rd = report_date.isoformat()
    elite_ctes = dashboard_elite_ctes(
        latest_name="latest",
        elite_name="elite",
        aid_alias="AID",
        agent_alias="agent_tag",
    )
    return f"""
WITH {elite_ctes},
daily AS (
  SELECT
    account_id AS AID,
    date,
    SUM(CAST(purchased AS FLOAT64)) AS purchased,
    SUM(
      CAST(purchased AS FLOAT64)
      - CAST(COALESCE(redeemed, 0) AS FLOAT64)
      - CAST(COALESCE(chargeback, 0) AS FLOAT64)
      - CAST(COALESCE(refunds, 0) AS FLOAT64)
    ) AS net_purchases
  FROM `{PROJECT_ID}.jackpota_agg.daily_player_revenue_kpis`
  WHERE account_id IN (SELECT AID FROM elite)
  GROUP BY 1, 2
),
lt AS (
  SELECT
    AID,
    ROUND(SUM(purchased), 2) AS lt_purchase,
    ROUND(SUM(net_purchases), 2) AS lt_net_purchase,
    MAX(IF(purchased > 0, date, NULL)) AS last_purchase_date
  FROM daily
  GROUP BY 1
),
last_amt AS (
  SELECT d.AID, ROUND(d.purchased, 2) AS last_purchase_amount
  FROM daily d
  INNER JOIN lt ON d.AID = lt.AID AND d.date = lt.last_purchase_date
),
recent AS (
  SELECT AID, SUM(IF(purchased > 0, 1, 0)) AS purchase_days_60d
  FROM daily
  WHERE date BETWEEN DATE '{d60_start}' AND DATE '{rd}'
  GROUP BY 1
),
pii AS (
  SELECT DISTINCT
    ua.id AS AID,
    ua.email,
    ua.locked,
    p.first_name,
    p.last_name,
    COALESCE(CONCAT(p.first_name, ' ', p.last_name), ua.name) AS name
  FROM `{PROJECT_ID}.transactional_data.uam_accounts` ua
  LEFT JOIN `{PROJECT_ID}.transactional_data.uam_persons` p ON ua.person_id = p.id
)
SELECT
  e.AID,
  e.agent_tag,
  pi.first_name,
  pi.last_name,
  COALESCE(eu.name, pi.name) AS name,
  pi.email,
  lt.last_purchase_date,
  la.last_purchase_amount,
  lt.lt_purchase,
  lt.lt_net_purchase
FROM elite e
LEFT JOIN lt ON e.AID = lt.AID
LEFT JOIN last_amt la ON e.AID = la.AID
LEFT JOIN recent r ON e.AID = r.AID
LEFT JOIN pii pi ON e.AID = pi.AID
LEFT JOIN `{PROJECT_ID}.dbt_dashboards_mart.elite_users` eu
  ON e.AID = eu.account_id AND eu.report_date = DATE '{rd}'
WHERE COALESCE(r.purchase_days_60d, 0) = 0
  AND COALESCE(pi.locked, FALSE) = FALSE
ORDER BY lt.lt_purchase DESC NULLS LAST, e.AID
"""


def row_for_export(raw: dict) -> dict:
    return {
        "AID": raw.get("AID"),
        "account_manager": format_agent_name({"agent": raw.get("agent_tag")}),
        "first_name": raw.get("first_name") or "",
        "last_name": raw.get("last_name") or "",
        "name": raw.get("name") or "",
        "email": raw.get("email") or "",
        "last_purchase_date": raw.get("last_purchase_date") or "",
        "last_purchase_amount": raw.get("last_purchase_amount")
        if raw.get("last_purchase_amount") is not None
        else "",
        "lt_purchase": raw.get("lt_purchase") if raw.get("lt_purchase") is not None else "",
        "lt_net_purchase": raw.get("lt_net_purchase")
        if raw.get("lt_net_purchase") is not None
        else "",
    }


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    headers = [h for h, _ in COLUMNS]
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        for raw in rows:
            mapped = row_for_export(raw)
            w.writerow({h: mapped[k] for h, k in COLUMNS})


def parse_report_date(value: str | None) -> date:
    if value:
        return datetime.strptime(value, "%Y-%m-%d").date()
    return date.today()


def run_export(report_date: date) -> Path:
    rows = run_query(get_client(), build_sql(report_date))
    out = OUTPUT_DIR / f"{report_date.isoformat()}_{EXPORT_BASENAME}.csv"
    write_csv(out, rows)
    never = sum(1 for r in rows if not r.get("last_purchase_date"))
    print(f"60 Days No Purchase Last Push — {report_date.isoformat()}")
    print(f"  Players: {len(rows)} (active Elite, no purchase in 60d)")
    print(f"  Never purchased (lifetime): {never}")
    print(f"  Saved: {out}")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="60 Days No Purchase Last Push export")
    parser.add_argument(
        "--date",
        metavar="YYYY-MM-DD",
        help="Report / as-of date (default: today)",
    )
    args = parser.parse_args()
    run_export(parse_report_date(args.date))


if __name__ == "__main__":
    main()
