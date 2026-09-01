"""Monthly Elite AM Brief trigger rollup from archived manager JSON exports."""
from __future__ import annotations

import argparse
import calendar
import csv
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent
EXPORTS = PACKAGE_DIR / "exports"
MONTHLY_DIR = PROJECT_ROOT / "monthly_summaries"

AM_ORDER = ["Coral", "Gabriel", "Lee", "Rachel", "Alon"]
CATEGORIES: list[tuple[str, str]] = [
    ("Open Tickets (daily sum)", "openZd"),
    ("Pending RD ≥$5k", "rdOver5k"),
    ("First-time locked RD", "rdFirstTime"),
    ("Big Winners", "bigWinners"),
    ("Big Losers", "bigLosers"),
    ("Take a Break", "takeABreak"),
    ("Birthdays", "birthdays"),
    ("Top 20 WoW gaps", "declineCount"),
]


def month_bounds(month: str) -> tuple[date, date]:
    year, mon = map(int, month.split("-"))
    last = calendar.monthrange(year, mon)[1]
    return date(year, mon, 1), date(year, mon, last)


def manager_jsons_for_month(month: str) -> list[Path]:
    start, end = month_bounds(month)
    out: list[Path] = []
    for path in sorted(EXPORTS.glob("*_elite_am_brief.json")):
        if not path.name.endswith("_elite_am_brief.json"):
            continue
        if path.name.count("_") != 2:
            continue
        d = date.fromisoformat(path.name.split("_")[0])
        if start <= d <= end:
            out.append(path)
    return out


def day_counts(payload: dict) -> dict[str, dict[str, int]]:
    """Per-AM focus counters for one report day."""
    by_am: dict[str, dict[str, int]] = {name: defaultdict(int) for name in AM_ORDER}
    for agent in payload.get("agents") or []:
        name = agent.get("agentName")
        if name not in by_am:
            continue
        focus = agent.get("focus") or {}
        by_am[name]["openZd"] += int(focus.get("openZd") or 0)
        by_am[name]["rdOver5k"] += int(focus.get("rdOver5k") or 0)
        by_am[name]["rdFirstTime"] += len(agent.get("rdFirstTime") or [])
        by_am[name]["bigWinners"] += int(focus.get("bigWinners") or 0)
        by_am[name]["bigLosers"] += int(focus.get("bigLosers") or 0)
        by_am[name]["takeABreak"] += int(focus.get("takeABreak") or 0)
        by_am[name]["birthdays"] += int(focus.get("birthdays") or 0)
        by_am[name]["declineCount"] += int(focus.get("declineCount") or 0)
    return by_am


def aggregate_month(month: str) -> tuple[dict[str, dict[str, int]], int]:
    totals: dict[str, dict[str, int]] = {
        name: defaultdict(int) for name in AM_ORDER
    }
    days = 0
    for path in manager_jsons_for_month(month):
        payload = json.loads(path.read_text(encoding="utf-8"))
        day = day_counts(payload)
        for name in AM_ORDER:
            for key, value in day[name].items():
                totals[name][key] += value
        days += 1
    return totals, days


def build_rows(totals: dict[str, dict[str, int]]) -> list[list[str | int]]:
    rows: list[list[str | int]] = []
    for label, key in CATEGORIES:
        row: list[str | int] = [label]
        team = 0
        for name in AM_ORDER:
            val = int(totals[name].get(key, 0))
            row.append(val)
            team += val
        row.append(team)
        rows.append(row)
    return rows


def write_csv(path: Path, rows: list[list[str | int]], month: str, days: int) -> None:
    headers = ["Category", *AM_ORDER, "Team"]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(headers)
        writer.writerows(rows)
        writer.writerow([])
        writer.writerow(["Notes"])
        writer.writerow([
            f"Month {month}: {days} archived manager day(s). "
            "Counts sum daily snapshot focus badges (alert-days), not unique players."
        ])


def write_xlsx(path: Path, rows: list[list[str | int]], month: str, days: int) -> bool:
    try:
        from openpyxl import Workbook
    except ImportError:
        return False
    wb = Workbook()
    ws = wb.active
    ws.title = "Trigger totals"
    headers = ["Category", *AM_ORDER, "Team"]
    ws.append(headers)
    for row in rows:
        ws.append(row)
    notes = wb.create_sheet("Notes")
    notes.append(["Footnote"])
    notes.append([
        f"Month {month}: {days} archived manager day(s). "
        "Open Tickets and Locks sum daily snapshot counts, not unique players."
    ])
    wb.save(path)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Monthly AM Brief trigger summary")
    parser.add_argument("--month", required=True, help="YYYY-MM")
    parser.add_argument("--dry-run", action="store_true", help="Print totals only")
    args = parser.parse_args()

    paths = manager_jsons_for_month(args.month)
    if not paths:
        raise SystemExit(
            f"No manager JSON in {EXPORTS} for {args.month}. "
            "Run generate_am_brief_range.py backfill first."
        )
    totals, days = aggregate_month(args.month)
    rows = build_rows(totals)

    if args.dry_run:
        print(f"Month {args.month}: {days} day(s), {len(paths)} file(s)")
        for row in rows:
            print("  ", row)
        return

    MONTHLY_DIR.mkdir(parents=True, exist_ok=True)
    stem = f"{args.month}_elite_trigger_summary"
    csv_path = MONTHLY_DIR / f"{stem}.csv"
    xlsx_path = MONTHLY_DIR / f"{stem}.xlsx"
    write_csv(csv_path, rows, args.month, days)
    print(f"Wrote {csv_path}")
    if write_xlsx(xlsx_path, rows, args.month, days):
        print(f"Wrote {xlsx_path}")
    else:
        print("openpyxl not installed; CSV only (pip install openpyxl for Excel).")


if __name__ == "__main__":
    main()
