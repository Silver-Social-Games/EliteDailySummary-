"""
Elite weekend summary — combined Thu/Fri/Sat canvas (20 players per day).

Run from repo root:
  python daily_summary/generate_weekend_summary.py
  python daily_summary/generate_weekend_summary.py --dates 2026-07-09,2026-07-10,2026-07-11
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = Path(__file__).resolve().parent / "daily_summaries"

sys.path.insert(0, str(PROJECT_ROOT / "decline_check"))

import generate_daily_elite_summary as gen  # noqa: E402
from generate_daily_elite_summary import (  # noqa: E402
    build_sql,
    get_client,
    run_query,
    weekday_label,
    _day_row,
)
from generate_weekend_elite_canvas import write_weekend_canvas  # noqa: E402
from wow_drop_reason import fetch_top10_by_delta  # noqa: E402


def parse_dates(raw: str | None) -> list[date]:
    if raw:
        return [date.fromisoformat(d.strip()) for d in raw.split(",") if d.strip()]
    # Default: Thu–Sat ending yesterday (Sun run → Sat is yesterday)
    end = date.today() - timedelta(days=1)
    while end.weekday() != 5:  # Saturday
        end -= timedelta(days=1)
    return [end - timedelta(days=2), end - timedelta(days=1), end]


def fetch_day_bundle(client, report_date: date) -> tuple[list[dict], list[dict], list[dict]]:
    sql = build_sql(report_date)
    day_rows = run_query(client, sql["weekday_compare"])
    overall_rows = run_query(client, sql["overall_weekday_compare"])
    prior_day = report_date - timedelta(days=7)
    elite_this = _day_row(day_rows, report_date)
    elite_prior = _day_row(day_rows, prior_day)
    elite_wow_drop = max(
        0.0,
        float(elite_prior.get("revenue") or 0) - float(elite_this.get("revenue") or 0),
    )
    top20 = fetch_top10_by_delta(client, report_date, elite_wow_drop=elite_wow_drop)
    return day_rows, overall_rows, top20


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Elite weekend summary (combined canvas)")
    parser.add_argument(
        "--dates",
        help="Comma-separated report dates YYYY-MM-DD (default: last Thu,Fri,Sat)",
    )
    args = parser.parse_args()
    dates = parse_dates(args.dates)

    client = get_client()
    bundles: list[tuple[date, list[dict], list[dict], list[dict]]] = []
    for report_date in dates:
        print(f"Fetching {report_date} ({weekday_label(report_date)})...")
        day_rows, overall_rows, top20 = fetch_day_bundle(client, report_date)
        print(f"  Top 20: {len(top20)} players")
        bundles.append((report_date, day_rows, overall_rows, top20))

    canvas_path = write_weekend_canvas(dates, bundles)
    print(f"Wrote {canvas_path}")

    try:
        ds = PROJECT_ROOT / "daily_summary"
        if str(ds) not in sys.path:
            sys.path.insert(0, str(ds))
        from canvas_to_html import export_for_canvas

        slug = f"{dates[0].isoformat()}_to_{dates[-1].isoformat()}"
        html_out = OUTPUT_DIR / f"{slug}_elite_weekend_summary_canvas.html"
        export_for_canvas(canvas_path, out_path=html_out)
    except Exception as exc:
        print(f"HTML canvas export skipped: {exc}")


if __name__ == "__main__":
    main()
