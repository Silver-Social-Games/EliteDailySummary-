"""Elite players who bought prior Monday but not this Monday."""
from datetime import date
from pathlib import Path
import csv
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from elite_lib import PROJECT_ID, get_client, run_query  # noqa: E402

THIS = date(2026, 6, 8)
PRIOR = date(2026, 6, 1)

sql = f"""
WITH latest AS (
  SELECT MAX(snapshot_date) AS snap
  FROM `{PROJECT_ID}.dbt_utils.elite_account_tags`
),
elite AS (
  SELECT DISTINCT
    e.account_id AS AID,
    COALESCE(t.tag_agent_1, e.agent_name) AS agent_tag,
    e.agent_name AS account_manager
  FROM `{PROJECT_ID}.dbt_aninditac.elite` e
  CROSS JOIN latest l
  LEFT JOIN `{PROJECT_ID}.dbt_utils.elite_account_tags` t
    ON e.account_id = t.account_id
    AND t.snapshot_date = l.snap
    AND t.category = 'Elite'
    AND t.tag_agent_1 IS NOT NULL
),
day AS (
  SELECT account_id AS AID, date,
    SUM(CAST(purchased AS FLOAT64)) AS bought
  FROM `{PROJECT_ID}.jackpota_agg.daily_player_revenue_kpis`
  WHERE date IN (DATE '{PRIOR.isoformat()}', DATE '{THIS.isoformat()}')
  GROUP BY 1, 2
),
player AS (
  SELECT e.AID, e.agent_tag, e.account_manager,
    MAX(IF(d.date = DATE '{THIS.isoformat()}', d.bought, 0)) AS bought_this_monday,
    MAX(IF(d.date = DATE '{PRIOR.isoformat()}', d.bought, 0)) AS bought_prior_monday
  FROM elite e
  LEFT JOIN day d ON e.AID = d.AID
  GROUP BY 1, 2, 3
),
pii AS (
  SELECT DISTINCT
    ua.id AS AID,
    ua.email,
    COALESCE(CONCAT(p.first_name, ' ', p.last_name), ua.name) AS name
  FROM `{PROJECT_ID}.transactional_data.uam_accounts` ua
  LEFT JOIN `{PROJECT_ID}.transactional_data.uam_persons` p ON ua.person_id = p.id
)
SELECT
  p.AID,
  COALESCE(eu.name, pi.name) AS name,
  pi.email,
  p.account_manager,
  ROUND(p.bought_prior_monday, 2) AS bought_prior_monday,
  ROUND(p.bought_this_monday, 2) AS bought_this_monday,
  ROUND(p.bought_prior_monday - p.bought_this_monday, 2) AS amount_gap
FROM player p
LEFT JOIN pii pi ON p.AID = pi.AID
LEFT JOIN `{PROJECT_ID}.dbt_dashboards_mart.elite_users` eu
  ON p.AID = eu.account_id AND eu.report_date = DATE '{THIS.isoformat()}'
WHERE p.bought_prior_monday > 0
  AND COALESCE(p.bought_this_monday, 0) = 0
ORDER BY amount_gap DESC
"""


def main() -> None:
    rows = run_query(get_client(), sql)
    out = Path(__file__).parent / "exports" / f"monday_skip_{THIS.isoformat()}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    fields = ["AID", "name", "email", "account_manager", "amount_gap",
              "bought_prior_monday", "bought_this_monday"]
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in fields})

    total_gap = sum(float(r.get("amount_gap") or 0) for r in rows)
    print(f"Players: {len(rows)}")
    print(f"Total amount gap: ${total_gap:,.2f}")
    print(f"CSV: {out}")


if __name__ == "__main__":
    main()
