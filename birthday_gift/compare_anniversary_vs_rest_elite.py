"""Compare unlocked anniversary cohort (74) vs rest of Elite across all metrics."""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from elite_lib import PROJECT_ID, get_client, run_query  # noqa: E402

AIDS_FILE = (
    PROJECT_ROOT
    / "birthday_gift"
    / "cohorts"
    / "jackpota_anniversary_batch2_unlocked_aids.txt"
)
OUT_JSON = (
    PROJECT_ROOT
    / "birthday_gift"
    / "exports"
    / "jackpota_anniversary_vs_rest_elite.json"
)
BEFORE_FROM = "2026-06-23"
BEFORE_TO = "2026-07-06"
AFTER_FROM = "2026-07-08"
AFTER_TO = "2026-07-21"


def load_aids(path: Path) -> list[int]:
    aids = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            aids.append(int(line))
    return aids


def main() -> None:
    aids = load_aids(AIDS_FILE)
    aid_list = ", ".join(str(a) for a in aids)
    print(f"Unlocked cohort AIDs: {len(aids)}")

    sql = f"""
WITH cohort AS (
  SELECT AID FROM UNNEST([{aid_list}]) AS AID
),
elite AS (
  SELECT DISTINCT account_id AS AID
  FROM `{PROJECT_ID}.dbt_aninditac.elite`
),
book_full AS (
  SELECT AID, 'anniversary_74' AS grp FROM cohort
  UNION DISTINCT
  SELECT e.AID, 'rest_elite' AS grp
  FROM elite e
  LEFT JOIN cohort c ON c.AID = e.AID
  WHERE c.AID IS NULL
),
daily AS (
  SELECT
    b.AID,
    b.grp,
    k.date,
    SUM(CAST(k.purchased AS FLOAT64)) AS purchased,
    SUM(CAST(COALESCE(k.purchased_num, 0) AS FLOAT64)) AS purchase_count,
    SUM(CAST(COALESCE(k.profit, 0) AS FLOAT64)) AS sc_bets,
    MAX(CASE WHEN COALESCE(k.spins, 0) > 0 THEN 1 ELSE 0 END) AS active_day
  FROM `{PROJECT_ID}.jackpota_agg.daily_player_revenue_kpis` k
  INNER JOIN book_full b ON b.AID = k.account_id
  WHERE k.date BETWEEN DATE '{BEFORE_FROM}' AND DATE '{AFTER_TO}'
  GROUP BY 1, 2, 3
),
player_window AS (
  SELECT
    b.AID,
    b.grp,
    w.window_name,
    DATE_DIFF(w.win_to, w.win_from, DAY) + 1 AS window_days,
    w.win_from,
    w.win_to
  FROM book_full b
  CROSS JOIN UNNEST([
    STRUCT('before' AS window_name, DATE '{BEFORE_FROM}' AS win_from, DATE '{BEFORE_TO}' AS win_to),
    STRUCT('after' AS window_name, DATE '{AFTER_FROM}' AS win_from, DATE '{AFTER_TO}' AS win_to)
  ]) w
),
player_daily_rate AS (
  SELECT
    pw.AID,
    pw.grp,
    pw.window_name,
    pw.window_days,
    COALESCE(SUM(d.purchased), 0) / pw.window_days AS daily_purchase,
    COALESCE(SUM(d.purchase_count), 0) / pw.window_days AS daily_purchases,
    COALESCE(SUM(d.active_day), 0) / pw.window_days AS daily_active,
    COALESCE(SUM(d.sc_bets), 0) / pw.window_days AS daily_sc_bets,
    COALESCE(SUM(d.purchased), 0) AS window_purchase,
    COALESCE(SUM(d.purchase_count), 0) AS window_purchases,
    COALESCE(SUM(d.active_day), 0) AS window_active,
    COALESCE(SUM(d.sc_bets), 0) AS window_sc_bets
  FROM player_window pw
  LEFT JOIN daily d
    ON d.AID = pw.AID AND d.grp = pw.grp
   AND d.date BETWEEN pw.win_from AND pw.win_to
  GROUP BY 1, 2, 3, 4
)
SELECT
  grp,
  window_name,
  COUNT(*) AS n_players,
  ROUND(AVG(daily_purchase), 4) AS mean_daily_purchase,
  ROUND(APPROX_QUANTILES(daily_purchase, 100)[OFFSET(50)], 4) AS median_daily_purchase,
  ROUND(AVG(daily_purchases), 4) AS mean_daily_purchases,
  ROUND(APPROX_QUANTILES(daily_purchases, 100)[OFFSET(50)], 4) AS median_daily_purchases,
  ROUND(AVG(daily_active), 4) AS mean_daily_active,
  ROUND(APPROX_QUANTILES(daily_active, 100)[OFFSET(50)], 4) AS median_daily_active,
  ROUND(AVG(daily_sc_bets), 4) AS mean_daily_sc_bets,
  ROUND(APPROX_QUANTILES(daily_sc_bets, 100)[OFFSET(50)], 4) AS median_daily_sc_bets,
  ROUND(AVG(window_purchase), 2) AS mean_window_purchase,
  ROUND(AVG(window_purchases), 2) AS mean_window_purchases,
  ROUND(AVG(window_active), 2) AS mean_window_active,
  ROUND(AVG(window_sc_bets), 2) AS mean_window_sc_bets,
  ROUND(SUM(window_purchase), 2) AS total_window_purchase
FROM player_daily_rate
GROUP BY 1, 2
ORDER BY grp, window_name
"""
    rows = [dict(r) for r in run_query(get_client(), sql)]
    by = {(r["grp"], r["window_name"]): r for r in rows}

    metrics = [
        ("purchase", "mean_daily_purchase", "median_daily_purchase", "Purchase ($)/day"),
        ("purchases", "mean_daily_purchases", "median_daily_purchases", "Purchases/day"),
        ("active", "mean_daily_active", "median_daily_active", "Active rate/day"),
        ("sc_bets", "mean_daily_sc_bets", "median_daily_sc_bets", "SC bets/day"),
    ]

    payload = {
        "beforeFrom": BEFORE_FROM,
        "beforeTo": BEFORE_TO,
        "afterFrom": AFTER_FROM,
        "afterTo": AFTER_TO,
        "cohortSize": len(aids),
        "restSize": int(by[("rest_elite", "before")]["n_players"]),
        "groups": rows,
        "metrics": [],
    }

    print("\n=== Unlocked 74 vs rest Elite (daily per-player rates) ===")
    for key, mean_col, med_col, label in metrics:
        cb, ca = by[("anniversary_74", "before")], by[("anniversary_74", "after")]
        rb, ra = by[("rest_elite", "before")], by[("rest_elite", "after")]
        c_d_mean = ca[mean_col] - cb[mean_col]
        r_d_mean = ra[mean_col] - rb[mean_col]
        c_d_med = ca[med_col] - cb[med_col]
        r_d_med = ra[med_col] - rb[med_col]
        did_mean = c_d_mean - r_d_mean
        did_med = c_d_med - r_d_med
        entry = {
            "key": key,
            "label": label,
            "cohort": {
                "beforeMean": cb[mean_col],
                "afterMean": ca[mean_col],
                "deltaMean": round(c_d_mean, 4),
                "beforeMedian": cb[med_col],
                "afterMedian": ca[med_col],
                "deltaMedian": round(c_d_med, 4),
            },
            "rest": {
                "beforeMean": rb[mean_col],
                "afterMean": ra[mean_col],
                "deltaMean": round(r_d_mean, 4),
                "beforeMedian": rb[med_col],
                "afterMedian": ra[med_col],
                "deltaMedian": round(r_d_med, 4),
            },
            "didMean": round(did_mean, 4),
            "didMedian": round(did_med, 4),
        }
        payload["metrics"].append(entry)
        print(
            f"{label}: cohort {cb[mean_col]:.2f}->{ca[mean_col]:.2f} (Δ{c_d_mean:+.2f}) | "
            f"rest {rb[mean_col]:.2f}->{ra[mean_col]:.2f} (Δ{r_d_mean:+.2f}) | "
            f"DiD mean {did_mean:+.2f} | DiD median {did_med:+.2f}"
        )

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nWrote {OUT_JSON}")


if __name__ == "__main__":
    main()
