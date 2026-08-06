"""
Elite birthday gift — before/after activity comparison.

AID mode (skill default): you supply AIDs and explicit checking periods.
No month-15 anchor. Windows are exactly the dates you pass.

Run from project root:
  python birthday_gift/generate_birthday_gift_activity.py \\
    --aids-file birthday_gift/cohorts/july_2026_cohort_aids.txt \\
    --before-from 2026-06-01 --before-to 2026-06-30 \\
    --after-from 2026-07-01 --after-to 2026-07-31 \\
    --stem birthday_gift_activity_july_2026_cohort

  python birthday_gift/generate_birthday_gift_activity.py --cohort june_2026
  python birthday_gift/generate_birthday_gift_activity.py --start 2026-06-01 --end 2026-07-31

Output under birthday_gift/exports/
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = Path(__file__).resolve().parent / "exports"
COHORTS_DIR = Path(__file__).resolve().parent / "cohorts"
sys.path.insert(0, str(PROJECT_ROOT))

from elite_lib import PROJECT_ID, get_client, run_query, sql_int_list  # noqa: E402

BIRTHDAY_CAMPAIGN_ID = 1816
WINDOW_DAYS = 30
ANCHOR_DAY = 15

COHORT_CONFIG = {
    "june_2026": {
        "aids_file": COHORTS_DIR / "june_2026_aids.txt",
        "before_from": "2026-05-16",
        "before_to": "2026-06-14",
        "after_from": "2026-06-16",
        "after_to": "2026-07-15",
        "gift_month": "2026-06",
        "stem": "birthday_gift_activity_june_2026_cohort",
    },
}

METRICS = [
    ("purchase_amount", "Purchase amount ($)"),
    ("purchase_count", "Number of purchases"),
    ("active_days", "Active days"),
    ("sc_bets", "Total SC bets"),
]


def pct_change(before: float, after: float) -> float | None:
    if before == 0:
        return None if after == 0 else 100.0
    return round((after - before) / before * 100, 2)


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def load_aids(path: Path) -> list[int]:
    aids: list[int] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            aids.append(int(line))
    return aids


def build_cohort_sql(
    aids: list[int],
    before_from: date,
    before_to: date,
    after_from: date,
    after_to: date,
    gift_month: str | None = None,
) -> str:
    aid_list = sql_int_list(aids)
    bf, bt = before_from.isoformat(), before_to.isoformat()
    af, at = after_from.isoformat(), after_to.isoformat()
    label_month = gift_month or after_from.strftime("%Y-%m")

    if gift_month:
        gift_filter = f"AND FORMAT_DATE('%Y-%m', DATE(br.accepted_at)) = '{gift_month}'"
    else:
        gift_filter = (
            f"AND DATE(br.accepted_at) BETWEEN DATE '{bf}' AND DATE '{at}'"
        )

    return f"""
WITH cohort AS (
  SELECT AID FROM UNNEST([{aid_list}]) AS AID
),
gift_meta AS (
  SELECT
    br.account_id AS AID,
    DATE(br.accepted_at) AS gift_date,
    CAST(br.sweepstake_amount AS FLOAT64) AS gift_sc
  FROM `{PROJECT_ID}.transactional_data.uam_bonus_rewards` br
  WHERE br.campaign_id = {BIRTHDAY_CAMPAIGN_ID}
    AND br.accepted = TRUE
    AND br.account_id IN (SELECT AID FROM cohort)
    {gift_filter}
  QUALIFY ROW_NUMBER() OVER (PARTITION BY br.account_id ORDER BY br.accepted_at) = 1
),
agents AS (
  SELECT
    c.AID,
    '{label_month}' AS gift_month,
    DATE '{bf}' AS before_from,
    DATE '{bt}' AS before_to,
    DATE '{af}' AS after_from,
    DATE '{at}' AS after_to,
    gm.gift_date,
    gm.gift_sc,
    COALESCE(t.tag_agent_1, e.agent_name) AS agent
  FROM cohort c
  LEFT JOIN gift_meta gm ON gm.AID = c.AID
  LEFT JOIN `{PROJECT_ID}.dbt_aninditac.elite` e ON e.account_id = c.AID
  LEFT JOIN (
    SELECT account_id, tag_agent_1
    FROM `{PROJECT_ID}.dbt_utils.elite_account_tags`
    WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM `{PROJECT_ID}.dbt_utils.elite_account_tags`)
      AND category = 'Elite'
  ) t ON t.account_id = c.AID
),
lifetime AS (
  SELECT
    k.account_id AS AID,
    ROUND(SUM(CAST(k.purchased AS FLOAT64)), 2) AS lifetime_purchased,
    ROUND(SUM(
      CAST(k.purchased AS FLOAT64)
      - CAST(COALESCE(k.redeemed, 0) AS FLOAT64)
      - CAST(COALESCE(k.chargeback, 0) AS FLOAT64)
      - CAST(COALESCE(k.refunds, 0) AS FLOAT64)
    ), 2) AS lifetime_net_purchase
  FROM `{PROJECT_ID}.jackpota_agg.daily_player_revenue_kpis` k
  INNER JOIN cohort c ON c.AID = k.account_id
  GROUP BY 1
),
daily AS (
  SELECT
    k.account_id AS AID,
    k.date,
    SUM(CAST(k.purchased AS FLOAT64)) AS purchased,
    SUM(CAST(COALESCE(k.purchased_num, 0) AS FLOAT64)) AS purchase_count,
    SUM(CAST(COALESCE(k.profit, 0) AS FLOAT64)) AS sc_bets,
    MAX(CASE WHEN COALESCE(k.spins, 0) > 0 THEN 1 ELSE 0 END) AS active_day
  FROM `{PROJECT_ID}.jackpota_agg.daily_player_revenue_kpis` k
  INNER JOIN cohort c ON c.AID = k.account_id
  WHERE k.date BETWEEN DATE '{bf}' AND DATE '{at}'
  GROUP BY 1, 2
),
periods AS (
  SELECT
    a.AID,
    a.agent,
    a.gift_date,
    a.gift_month,
    a.before_from,
    a.before_to,
    a.after_from,
    a.after_to,
    a.gift_sc,
    ROUND(COALESCE(lt.lifetime_purchased, 0), 2) AS lifetime_purchased,
    ROUND(COALESCE(lt.lifetime_net_purchase, 0), 2) AS lifetime_net_purchase,
    ROUND(SUM(CASE WHEN d.date BETWEEN a.before_from AND a.before_to
      THEN d.purchased ELSE 0 END), 2) AS before_purchase_amount,
    ROUND(SUM(CASE WHEN d.date BETWEEN a.before_from AND a.before_to
      THEN d.purchase_count ELSE 0 END), 2) AS before_purchase_count,
    SUM(CASE WHEN d.date BETWEEN a.before_from AND a.before_to
      THEN d.active_day ELSE 0 END) AS before_active_days,
    ROUND(SUM(CASE WHEN d.date BETWEEN a.before_from AND a.before_to
      THEN d.sc_bets ELSE 0 END), 2) AS before_sc_bets,
    ROUND(SUM(CASE WHEN d.date BETWEEN a.after_from AND a.after_to
      THEN d.purchased ELSE 0 END), 2) AS after_purchase_amount,
    ROUND(SUM(CASE WHEN d.date BETWEEN a.after_from AND a.after_to
      THEN d.purchase_count ELSE 0 END), 2) AS after_purchase_count,
    SUM(CASE WHEN d.date BETWEEN a.after_from AND a.after_to
      THEN d.active_day ELSE 0 END) AS after_active_days,
    ROUND(SUM(CASE WHEN d.date BETWEEN a.after_from AND a.after_to
      THEN d.sc_bets ELSE 0 END), 2) AS after_sc_bets,
    GREATEST(
      0,
      DATE_DIFF(
        LEAST(a.after_to, CURRENT_DATE() - 1),
        a.after_from,
        DAY
      ) + 1
    ) AS after_days_available,
    DATE_DIFF(a.after_to, a.after_from, DAY) + 1 AS after_window_days
  FROM agents a
  LEFT JOIN lifetime lt ON lt.AID = a.AID
  LEFT JOIN daily d ON d.AID = a.AID
  GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11
)
SELECT *
FROM periods
ORDER BY AID
"""


def build_sql(start: date, end: date) -> str:
    """Legacy warehouse discovery (month-15 windows). Prefer AID + explicit dates."""
    return f"""
WITH gifts AS (
  SELECT
    br.account_id AS AID,
    DATE(br.accepted_at) AS gift_date,
    FORMAT_DATE('%Y-%m', DATE(br.accepted_at)) AS gift_month,
    DATE(
      EXTRACT(YEAR FROM DATE(br.accepted_at)),
      EXTRACT(MONTH FROM DATE(br.accepted_at)),
      {ANCHOR_DAY}
    ) AS anchor_date,
    CAST(br.sweepstake_amount AS FLOAT64) AS gift_sc
  FROM `{PROJECT_ID}.transactional_data.uam_bonus_rewards` br
  WHERE br.campaign_id = {BIRTHDAY_CAMPAIGN_ID}
    AND br.accepted = TRUE
    AND DATE(br.accepted_at) BETWEEN DATE '{start.isoformat()}' AND DATE '{end.isoformat()}'
),
elite_gifts AS (
  SELECT g.*
  FROM gifts g
  INNER JOIN `{PROJECT_ID}.dbt_aninditac.elite` e ON e.account_id = g.AID
),
latest AS (
  SELECT MAX(snapshot_date) AS snap
  FROM `{PROJECT_ID}.dbt_utils.elite_account_tags`
),
agents AS (
  SELECT
    eg.AID,
    eg.gift_date,
    eg.gift_month,
    DATE_SUB(eg.anchor_date, INTERVAL {WINDOW_DAYS} DAY) AS before_from,
    DATE_SUB(eg.anchor_date, INTERVAL 1 DAY) AS before_to,
    DATE_ADD(eg.anchor_date, INTERVAL 1 DAY) AS after_from,
    DATE_ADD(eg.anchor_date, INTERVAL {WINDOW_DAYS} DAY) AS after_to,
    eg.gift_sc,
    COALESCE(t.tag_agent_1, e.agent_name) AS agent
  FROM elite_gifts eg
  LEFT JOIN `{PROJECT_ID}.dbt_aninditac.elite` e ON e.account_id = eg.AID
  CROSS JOIN latest l
  LEFT JOIN `{PROJECT_ID}.dbt_utils.elite_account_tags` t
    ON eg.AID = t.account_id
    AND t.snapshot_date = l.snap
    AND t.category = 'Elite'
),
lifetime AS (
  SELECT
    k.account_id AS AID,
    ROUND(SUM(CAST(k.purchased AS FLOAT64)), 2) AS lifetime_purchased,
    ROUND(SUM(
      CAST(k.purchased AS FLOAT64)
      - CAST(COALESCE(k.redeemed, 0) AS FLOAT64)
      - CAST(COALESCE(k.chargeback, 0) AS FLOAT64)
      - CAST(COALESCE(k.refunds, 0) AS FLOAT64)
    ), 2) AS lifetime_net_purchase
  FROM `{PROJECT_ID}.jackpota_agg.daily_player_revenue_kpis` k
  INNER JOIN elite_gifts g ON g.AID = k.account_id
  GROUP BY 1
),
daily AS (
  SELECT
    k.account_id AS AID,
    a.before_from,
    a.after_to,
    k.date,
    SUM(CAST(k.purchased AS FLOAT64)) AS purchased,
    SUM(CAST(COALESCE(k.purchased_num, 0) AS FLOAT64)) AS purchase_count,
    SUM(CAST(COALESCE(k.profit, 0) AS FLOAT64)) AS sc_bets,
    MAX(CASE WHEN COALESCE(k.spins, 0) > 0 THEN 1 ELSE 0 END) AS active_day
  FROM `{PROJECT_ID}.jackpota_agg.daily_player_revenue_kpis` k
  INNER JOIN agents a ON a.AID = k.account_id
  WHERE k.date BETWEEN a.before_from AND a.after_to
  GROUP BY 1, 2, 3, 4
),
periods AS (
  SELECT
    a.AID,
    a.agent,
    a.gift_date,
    a.gift_month,
    a.before_from,
    a.before_to,
    a.after_from,
    a.after_to,
    a.gift_sc,
    ROUND(COALESCE(lt.lifetime_purchased, 0), 2) AS lifetime_purchased,
    ROUND(COALESCE(lt.lifetime_net_purchase, 0), 2) AS lifetime_net_purchase,
    ROUND(SUM(CASE WHEN d.date BETWEEN a.before_from AND a.before_to
      THEN d.purchased ELSE 0 END), 2) AS before_purchase_amount,
    ROUND(SUM(CASE WHEN d.date BETWEEN a.before_from AND a.before_to
      THEN d.purchase_count ELSE 0 END), 2) AS before_purchase_count,
    SUM(CASE WHEN d.date BETWEEN a.before_from AND a.before_to
      THEN d.active_day ELSE 0 END) AS before_active_days,
    ROUND(SUM(CASE WHEN d.date BETWEEN a.before_from AND a.before_to
      THEN d.sc_bets ELSE 0 END), 2) AS before_sc_bets,
    ROUND(SUM(CASE WHEN d.date BETWEEN a.after_from AND a.after_to
      THEN d.purchased ELSE 0 END), 2) AS after_purchase_amount,
    ROUND(SUM(CASE WHEN d.date BETWEEN a.after_from AND a.after_to
      THEN d.purchase_count ELSE 0 END), 2) AS after_purchase_count,
    SUM(CASE WHEN d.date BETWEEN a.after_from AND a.after_to
      THEN d.active_day ELSE 0 END) AS after_active_days,
    ROUND(SUM(CASE WHEN d.date BETWEEN a.after_from AND a.after_to
      THEN d.sc_bets ELSE 0 END), 2) AS after_sc_bets,
    GREATEST(
      0,
      DATE_DIFF(
        LEAST(a.after_to, CURRENT_DATE() - 1),
        a.after_from,
        DAY
      ) + 1
    ) AS after_days_available,
    DATE_DIFF(a.after_to, a.after_from, DAY) + 1 AS after_window_days
  FROM agents a
  LEFT JOIN lifetime lt ON lt.AID = a.AID
  LEFT JOIN daily d ON d.AID = a.AID
  GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11
)
SELECT *
FROM periods
ORDER BY gift_month, gift_date, AID
"""


def format_hold(lifetime_purchased: float, lifetime_net: float) -> str:
    if lifetime_purchased <= 0:
        return "n/a"
    return f"{100 * lifetime_net / lifetime_purchased:.1f}%"


def row_to_export(r: dict) -> dict:
    gift_date = r.get("gift_date")
    lt_purchase = float(r.get("lifetime_purchased") or 0)
    lt_net = float(r.get("lifetime_net_purchase") or 0)
    out = {
        "AID": r["AID"],
        "Agent": r.get("agent") or "",
        "LT Purchase": round(lt_purchase, 2),
        "Hold": format_hold(lt_purchase, lt_net),
        "Gift month": r.get("gift_month") or "",
        "Gift date": "" if gift_date is None else gift_date,
        "Before from": r["before_from"],
        "Before to": r["before_to"],
        "After from": r["after_from"],
        "After to": r["after_to"],
        "Gift SC": r.get("gift_sc"),
        "After days available": r.get("after_days_available"),
        "After window days": r.get("after_window_days"),
    }
    mapping = [
        ("purchase_amount", "before_purchase_amount", "after_purchase_amount"),
        ("purchase_count", "before_purchase_count", "after_purchase_count"),
        ("active_days", "before_active_days", "after_active_days"),
        ("sc_bets", "before_sc_bets", "after_sc_bets"),
    ]
    for key, bcol, acol in mapping:
        before = float(r.get(bcol) or 0)
        after = float(r.get(acol) or 0)
        diff = round(after - before, 2)
        pct = pct_change(before, after)
        label = dict(METRICS)[key]
        out[f"Before — {label}"] = before
        out[f"After — {label}"] = after
        out[f"Diff — {label}"] = diff
        out[f"% change — {label}"] = "" if pct is None else pct
    return out


def build_summary(rows: list[dict], label: str = "") -> list[dict]:
    if not rows:
        return []
    summary_rows = []
    for key, metric_label in METRICS:
        before_vals = [float(r[f"Before — {metric_label}"]) for r in rows]
        after_vals = [float(r[f"After — {metric_label}"]) for r in rows]
        avg_before = round(sum(before_vals) / len(before_vals), 2)
        avg_after = round(sum(after_vals) / len(after_vals), 2)
        avg_diff = round(avg_after - avg_before, 2)
        avg_pct = (
            round((avg_after - avg_before) / avg_before * 100, 2) if avg_before else ""
        )
        summary_rows.append(
            {
                "Cohort": label,
                "Metric": metric_label,
                "Avg before": avg_before,
                "Avg after": avg_after,
                "Avg diff": avg_diff,
                "Avg % change": avg_pct,
                "Players": len(rows),
            }
        )
    return summary_rows


def build_month_summaries(rows: list[dict]) -> list[dict]:
    months = sorted({r["Gift month"] for r in rows if r.get("Gift month")})
    out: list[dict] = []
    for month in months:
        month_rows = [r for r in rows if r["Gift month"] == month]
        out.extend(build_summary(month_rows, label=month))
    return out


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def print_counts(export_rows: list[dict], as_of: date) -> None:
    if not export_rows:
        print("Elite birthday gift players: 0")
        return
    bf = export_rows[0].get("Before from", "")
    bt = export_rows[0].get("Before to", "")
    af = export_rows[0].get("After from", "")
    at = export_rows[0].get("After to", "")
    window_days = int(export_rows[0].get("After window days") or 0)
    full_after = sum(
        1
        for r in export_rows
        if int(r.get("After days available") or 0) >= window_days
    )
    print(f"Elite birthday gift players: {len(export_rows)}")
    print(f"  Before: {bf} to {bt}")
    print(f"  After:  {af} to {at}")
    print(f"Full after window complete (as of {as_of}): {full_after} players")


def resolve_windows(args: argparse.Namespace) -> tuple[date, date, date, date]:
    missing = [
        name
        for name in ("before_from", "before_to", "after_from", "after_to")
        if getattr(args, name) is None
    ]
    if missing:
        raise SystemExit(
            "AID mode requires checking periods: "
            "--before-from --before-to --after-from --after-to "
            f"(missing: {', '.join('--' + m.replace('_', '-') for m in missing)})"
        )
    before_from = parse_date(args.before_from)
    before_to = parse_date(args.before_to)
    after_from = parse_date(args.after_from)
    after_to = parse_date(args.after_to)
    if before_from > before_to:
        raise SystemExit("before-from must be on or before before-to")
    if after_from > after_to:
        raise SystemExit("after-from must be on or before after-to")
    return before_from, before_to, after_from, after_to


def run_aid_mode(
    client,
    aids: list[int],
    before_from: date,
    before_to: date,
    after_from: date,
    after_to: date,
    stem: str,
    gift_month: str | None,
) -> tuple[list[dict], str]:
    print(
        f"AID cohort: {len(aids)} AIDs · "
        f"before {before_from} to {before_to} · after {after_from} to {after_to}"
    )
    raw = run_query(
        client,
        build_cohort_sql(
            aids, before_from, before_to, after_from, after_to, gift_month
        ),
    )
    return raw, stem


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Elite birthday gift before/after activity (explicit checking periods)"
    )
    parser.add_argument("--start", default=None, help="Legacy warehouse gift start")
    parser.add_argument("--end", default=None, help="Legacy warehouse gift end")
    parser.add_argument(
        "--cohort",
        choices=sorted(COHORT_CONFIG),
        help="Named cohort shortcut (uses saved AIDs + default periods unless overridden)",
    )
    parser.add_argument("--aids-file", help="Path to AID list (one per line)")
    parser.add_argument("--before-from", help="Checking period before start (YYYY-MM-DD)")
    parser.add_argument("--before-to", help="Checking period before end (YYYY-MM-DD)")
    parser.add_argument("--after-from", help="Checking period after start (YYYY-MM-DD)")
    parser.add_argument("--after-to", help="Checking period after end (YYYY-MM-DD)")
    parser.add_argument(
        "--gift-month",
        help="Optional YYYY-MM for birthday gift enrichment only (does not set windows)",
    )
    parser.add_argument("--stem", help="Export filename stem")
    args = parser.parse_args()

    client = get_client()
    aids: list[int] | None = None
    gift_month: str | None = args.gift_month
    aid_mode = False

    if args.cohort:
        cfg = COHORT_CONFIG[args.cohort]
        aids = load_aids(cfg["aids_file"])
        before_from = parse_date(args.before_from or cfg["before_from"])
        before_to = parse_date(args.before_to or cfg["before_to"])
        after_from = parse_date(args.after_from or cfg["after_from"])
        after_to = parse_date(args.after_to or cfg["after_to"])
        gift_month = gift_month or cfg.get("gift_month")
        stem = args.stem or cfg["stem"]
        raw, stem = run_aid_mode(
            client, aids, before_from, before_to, after_from, after_to, stem, gift_month
        )
        aid_mode = True
    elif args.aids_file:
        aids_path = Path(args.aids_file)
        if not aids_path.is_absolute():
            aids_path = PROJECT_ROOT / aids_path
        aids = load_aids(aids_path)
        before_from, before_to, after_from, after_to = resolve_windows(args)
        stem = args.stem or (
            f"birthday_gift_activity_{before_from.isoformat()}_to_{after_to.isoformat()}_cohort"
        )
        raw, stem = run_aid_mode(
            client, aids, before_from, before_to, after_from, after_to, stem, gift_month
        )
        aid_mode = True
    else:
        start = parse_date(args.start or "2026-06-01")
        end = parse_date(args.end or "2026-07-31")
        raw = run_query(client, build_sql(start, end))
        stem = args.stem or (
            f"birthday_gift_activity_{start.isoformat()}_to_{end.isoformat()}"
        )

    export_rows = [row_to_export(r) for r in raw]

    if aid_mode and aids is not None:
        returned_aids = {int(r["AID"]) for r in export_rows}
        missing = [a for a in aids if a not in returned_aids]
        if missing:
            print(f"WARNING: missing from query result: {missing}")
        zero_kpi = [
            int(r["AID"])
            for r in export_rows
            if float(r.get("Before — Purchase amount ($)") or 0) == 0
            and float(r.get("After — Purchase amount ($)") or 0) == 0
            and float(r.get("Before — Active days") or 0) == 0
            and float(r.get("After — Active days") or 0) == 0
        ]
        if zero_kpi:
            print(f"WARNING: no activity in before/after windows: {zero_kpi}")

    summary_rows = build_summary(export_rows, label="all")
    month_summary_rows = build_month_summaries(export_rows)
    window_days = (
        int(export_rows[0].get("After window days") or WINDOW_DAYS) if export_rows else WINDOW_DAYS
    )
    full_after_rows = [
        r
        for r in export_rows
        if int(r.get("After days available") or 0) >= window_days
    ]
    full_after_summary_rows = build_summary(full_after_rows, label="full_after_window")

    detail_path = OUTPUT_DIR / f"{stem}.csv"
    summary_path = OUTPUT_DIR / f"{stem}_summary.csv"
    month_summary_path = OUTPUT_DIR / f"{stem}_summary_by_month.csv"
    full_summary_path = OUTPUT_DIR / f"{stem}_summary_full_after.csv"
    write_csv(detail_path, export_rows)
    write_csv(summary_path, summary_rows)
    if month_summary_rows:
        write_csv(month_summary_path, month_summary_rows)
    if full_after_summary_rows:
        write_csv(full_summary_path, full_after_summary_rows)

    as_of = date.today() - timedelta(days=1)
    print_counts(export_rows, as_of)
    print(f"Detail: {detail_path}")
    print(f"Summary: {summary_path}")
    for s in summary_rows:
        print(
            f"  {s['Metric']}: avg before {s['Avg before']}, "
            f"avg after {s['Avg after']}, avg % change {s['Avg % change']}"
        )

    if aid_mode:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from generate_birthday_gift_html import build_html, load_players, load_summary

        html_path = OUTPUT_DIR / f"{stem}.html"
        periods = None
        if export_rows:
            periods = {
                "beforeFrom": str(export_rows[0]["Before from"]),
                "beforeTo": str(export_rows[0]["Before to"]),
                "afterFrom": str(export_rows[0]["After from"]),
                "afterTo": str(export_rows[0]["After to"]),
                "title": (
                    "Jackpota Anniversary Gift Performance"
                    if "anniversary" in stem
                    else stem.replace("birthday_gift_activity_", "").replace("_", " ")
                ),
            }
        html_path.write_text(
            build_html(
                load_players(detail_path),
                load_summary(summary_path),
                periods=periods,
            ),
            encoding="utf-8",
        )
        print(f"HTML: {html_path}")


if __name__ == "__main__":
    main()
