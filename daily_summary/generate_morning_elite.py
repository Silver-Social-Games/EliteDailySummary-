"""
Elite morning reports — weekday router (Sun–Thu at 10:00 Israel).

Run from repo root:
  python daily_summary/generate_morning_elite.py
  python daily_summary/generate_morning_elite.py --force daily --date 2026-07-07
  python daily_summary/generate_morning_elite.py --force weekend

Schedule: daily_summary/register_daily_summary_task.ps1 (10:00 Israel time).
Sun=weekend (prior Thu–Sat), Mon–Thu=daily (yesterday), Fri/Sat=skip.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CANVAS_DIR = Path.home() / ".cursor" / "projects" / "c-Users-Owner-Downloads-Elite" / "canvases"


def _run_daily(report_date: str | None) -> None:
    sys.path.insert(0, str(PROJECT_ROOT))
    import daily_summary.generate_daily_summary as daily_mod  # noqa: E402

    argv = [sys.argv[0]]
    if report_date:
        argv.extend(["--date", report_date])
    sys.argv = argv
    daily_mod.main()


def _run_weekend(dates: str | None) -> None:
    sys.path.insert(0, str(PROJECT_ROOT))
    import daily_summary.generate_weekend_summary as weekend_mod  # noqa: E402

    argv = [sys.argv[0]]
    if dates:
        argv.extend(["--dates", dates])
    sys.argv = argv
    weekend_mod.main()


def _resolve_mode(today: date, force: str | None) -> str | None:
    if force == "daily":
        return "daily"
    if force == "weekend":
        return "weekend"
    wd = today.weekday()  # Mon=0 … Sun=6
    if wd == 6:
        return "weekend"
    if wd in (0, 1, 2, 3):
        return "daily"
    return None


def _check_daily_format(canvas_path: Path) -> list[str]:
    errors: list[str] = []
    if not canvas_path.exists():
        return [f"Canvas not found: {canvas_path}"]
    text = canvas_path.read_text(encoding="utf-8")
    if "TicketDraftModal" not in text:
        errors.append("Missing TicketDraftModal")
    if "Weekend · WoW" in text:
        errors.append("Unexpected 'Weekend · WoW' in daily canvas")
    m = re.search(r'headers=\[([^\]]+)\]', text)
    if m:
        cols = [c.strip() for c in m.group(1).split(",")]
        if len(cols) != 14:
            errors.append(f"Expected 14 player columns, found {len(cols)}")
    return errors


def _check_weekend_format(canvas_path: Path) -> list[str]:
    errors: list[str] = []
    if not canvas_path.exists():
        return [f"Canvas not found: {canvas_path}"]
    text = canvas_path.read_text(encoding="utf-8")
    if "TicketDraftModal" not in text:
        errors.append("Missing TicketDraftModal")
    if "Weekend · WoW" in text:
        errors.append("Found removed 'Weekend · WoW' heading")
    if "dayFilter" not in text:
        errors.append("Missing dayFilter pills")
    if "AGENT_OPTIONS" not in text:
        errors.append("Missing AGENT_OPTIONS filter bar")
    return errors


def _validate_output(mode: str, report_date: date | None, weekend_dates: list[date] | None) -> None:
    if mode == "daily" and report_date:
        canvas = CANVAS_DIR / f"elite-daily-summary-{report_date.isoformat()}.canvas.tsx"
        errors = _check_daily_format(canvas)
    elif mode == "weekend" and weekend_dates:
        slug = f"{weekend_dates[0].isoformat()}_to_{weekend_dates[-1].isoformat()}"
        canvas = CANVAS_DIR / f"elite-weekend-summary-{slug}.canvas.tsx"
        errors = _check_weekend_format(canvas)
    else:
        return
    if errors:
        print("FORMAT CHECK FAILED:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)
    print(f"Format check passed: {canvas.name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Elite Sun–Thu morning report router")
    parser.add_argument(
        "--force",
        choices=["daily", "weekend"],
        help="Override weekday routing (daily or weekend)",
    )
    parser.add_argument(
        "--date",
        help="Report date for daily (YYYY-MM-DD); default yesterday",
    )
    parser.add_argument(
        "--dates",
        help="Comma-separated dates for weekend override (YYYY-MM-DD,...)",
    )
    parser.add_argument(
        "--skip-format-check",
        action="store_true",
        help="Skip post-run format validation",
    )
    args = parser.parse_args()

    today = date.today()
    mode = _resolve_mode(today, args.force)

    if mode is None:
        print(f"Skipped — no Elite morning report on {today.strftime('%A')} (Fri/Sat).")
        return

    if mode == "daily":
        report_date = args.date or (today - timedelta(days=1)).isoformat()
        print(f"Morning Elite: daily for {report_date}")
        _run_daily(report_date)
        if not args.skip_format_check:
            _validate_output("daily", date.fromisoformat(report_date), None)
    else:
        print("Morning Elite: weekend (prior Thu–Sat)")
        _run_weekend(args.dates)
        if not args.skip_format_check:
            from daily_summary.generate_weekend_summary import parse_dates  # noqa: E402

            weekend_dates = parse_dates(args.dates)
            _validate_output("weekend", None, weekend_dates)


if __name__ == "__main__":
    main()
