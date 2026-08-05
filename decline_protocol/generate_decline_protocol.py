"""
Elite decline protocol — rolling 7d WoW spend-down cohort analysis.
Run from project root:
  python decline_protocol/generate_decline_protocol.py
  python decline_protocol/generate_decline_protocol.py --date 2026-06-09

Output: decline_protocol/decline_protocols/YYYY-MM-DD_decline_protocol.md
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from daily_summary.generate_daily_elite_summary import (  # noqa: E402
    build_sql,
    fmt_money,
    fmt_reason,
    get_client,
    resolve_report_date,
    run_query,
    weekday_label,
)

PROTOCOL_DIR = Path(__file__).resolve().parent / "decline_protocols"


def render_protocol(report_date: date, reasons: list[dict], agents: list[dict], top: list[dict]) -> str:
    day_name = weekday_label(report_date)
    lines = [
        f"# Elite Decline Protocol — {report_date.isoformat()}",
        "",
        f"**Report date:** {report_date.isoformat()} ({day_name})  ",
        "_Rolling 7d cohort: bought in both windows but less this week than prior week._",
        "",
        "---",
        "",
        "## Primary decline reasons",
        "",
        "| Reason | Players | $ drop | Avg NGR 7d | Avg bonus 7d |",
        "|--------|--------:|-------:|-----------:|-------------:|",
    ]
    for r in reasons:
        lines.append(
            f"| {fmt_reason(r.get('primary_reason', ''))} | {int(r.get('players') or 0)} | "
            f"{fmt_money(r.get('revenue_drop'))} | {fmt_money(r.get('avg_ngr_7d'))} | "
            f"{fmt_money(r.get('avg_bonus_7d'))} |"
        )
    lines.extend([
        "",
        "## WoW purchase decline by agent",
        "",
        "| Agent | Players | WoW $ drop |",
        "|-------|--------:|-----------:|",
    ])
    for a in agents:
        lines.append(
            f"| {a.get('agent', '')} | {int(a.get('active_decliners') or 0)} | "
            f"{fmt_money(a.get('revenue_drop'))} |"
        )
    lines.extend([
        "",
        "## Top WoW purchase decline (by AID)",
        "",
        "| AID | Agent | Name | This wk | Prior wk | Drop | NGR 7d | Bonus 7d | Game (30d) | Redeem status |",
        "|-----|-------|------|--------:|--------:|-----:|-------:|---------:|------------|---------------|",
    ])
    for row in top:
        lines.append(
            f"| {row.get('AID', '')} | {row.get('agent', '')} | {row.get('name', '')} | "
            f"{fmt_money(row.get('this_week_bought'))} | {fmt_money(row.get('prior_week_bought'))} | "
            f"{fmt_money(row.get('wow_drop'))} | {fmt_money(row.get('ngr_7d'))} | "
            f"{fmt_money(row.get('bonus_7d'))} | {row.get('favourite_game_30d') or '—'} | "
            f"{row.get('redemption_workflow_status') or '—'} |"
        )
    lines.extend([
        "",
        "---",
        "",
        "*See `Elite.MD` · Run on demand when investigating spend-down cohorts.*",
        "",
    ])
    return "\n".join(lines) + "\n"


def main() -> None:
    import argparse
    from datetime import datetime

    parser = argparse.ArgumentParser(description="Elite decline protocol")
    parser.add_argument("--date", dest="report_date", help="Report date YYYY-MM-DD")
    args = parser.parse_args()
    report_date = resolve_report_date(args.report_date)
    client = get_client()
    sql = build_sql(report_date)

    print(f"Running decline protocol for {report_date} ({weekday_label(report_date)})...")
    reasons = run_query(client, sql["reasons"])
    top = run_query(client, sql["top_decliners"])
    agents = run_query(client, sql["agents"])

    PROTOCOL_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PROTOCOL_DIR / f"{report_date.isoformat()}_decline_protocol.md"
    out_path.write_text(render_protocol(report_date, reasons, agents, top), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
