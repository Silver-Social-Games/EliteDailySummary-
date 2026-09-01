"""Generate Elite AM Brief exports for a date range (backfill or daily catch-up).

Daily use (after the first run exists):
  python am_daily_dashboard/generate_am_brief_range.py --catch-up

Backfill a month:
  python am_daily_dashboard/generate_am_brief_range.py --from 2026-08-01 --to 2026-08-31

Rebuild HTML only when JSON already exists:
  python am_daily_dashboard/generate_am_brief_range.py --from 2026-08-01 --to 2026-08-31 --html-only
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from datetime import date, timedelta
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PACKAGE_DIR))

from generate_am_daily_dashboard import (  # noqa: E402
    DEFAULT_CANVAS_DIR,
    OUTPUT_DIR,
    build_payload,
    print_goals_audit,
    rebuild_html_from_json,
    resolve_report_date,
    write_outputs,
)
from elite_lib.bigquery import get_client  # noqa: E402
from elite_lib.console import use_utf8_stdout  # noqa: E402

MANAGER_JSON_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})_elite_am_brief\.json$")


def archived_dates(export_dir: Path = OUTPUT_DIR) -> list[date]:
    """Report dates that already have a manager JSON on disk."""
    seen: set[date] = set()
    if export_dir.exists():
        for path in export_dir.glob("*_elite_am_brief.json"):
            m = MANAGER_JSON_RE.match(path.name)
            if m:
                seen.add(date.fromisoformat(m.group(1)))
    return sorted(seen)


def catch_up_bounds(
    *,
    export_dir: Path = OUTPUT_DIR,
    through: date | None = None,
) -> tuple[date, date] | None:
    """Day after newest archive through `through` (default: yesterday)."""
    end = through or (date.today() - timedelta(days=1))
    archived = archived_dates(export_dir)
    if not archived:
        return None
    start = max(archived) + timedelta(days=1)
    if start > end:
        return None
    return start, end


def iter_report_dates(
    start: date,
    end: date,
    *,
    export_dir: Path = OUTPUT_DIR,
    skip_existing: bool = False,
    html_only: bool = False,
) -> list[date]:
    """Inclusive date list, optionally skipping days that already have manager JSON."""
    if start > end:
        return []
    out: list[date] = []
    d = start
    while d <= end:
        json_path = export_dir / f"{d.isoformat()}_elite_am_brief.json"
        if skip_existing and json_path.exists() and not html_only:
            d += timedelta(days=1)
            continue
        out.append(d)
        d += timedelta(days=1)
    return out


def run_one_day(
    report_date: date,
    *,
    canvas_dir: Path,
    publish: bool,
    html_only: bool,
    client,
) -> None:
    if html_only:
        rebuild_html_from_json(report_date, publish=publish)
        return
    payload = build_payload(report_date, client)
    canvas_path, html_path = write_outputs(payload, canvas_dir, publish=publish)
    print_goals_audit(payload)
    print(f"Wrote {canvas_path}")
    print(f"Wrote {html_path}")


def run_verify(report_date: date, *, render_check: bool) -> int:
    cmd = [
        sys.executable,
        str(PACKAGE_DIR / "verify_brief.py"),
        "--date",
        report_date.isoformat(),
    ]
    if render_check:
        cmd.append("--render-check")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    return result.returncode


def main() -> None:
    use_utf8_stdout()
    parser = argparse.ArgumentParser(
        description="Generate Elite AM Brief for a date range (catch-up or backfill)"
    )
    parser.add_argument("--from", dest="from_date", help="Start date YYYY-MM-DD")
    parser.add_argument("--to", dest="to_date", help="End date YYYY-MM-DD (default: yesterday)")
    parser.add_argument(
        "--catch-up",
        action="store_true",
        help="Generate from the day after the newest saved JSON through --to or yesterday",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip dates that already have manager JSON (default with --catch-up)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate even when manager JSON already exists",
    )
    parser.add_argument(
        "--html-only",
        action="store_true",
        help="Rebuild HTML from saved JSON only (~3s/day, no BigQuery)",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Run verify_brief.py after each day (snapshots JSON on PASS)",
    )
    parser.add_argument(
        "--render-check",
        action="store_true",
        help="Pass --render-check to verify_brief (implies --verify)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print dates that would run and exit",
    )
    parser.add_argument("--publish", action="store_true", help="Copy HTML into docs/")
    parser.add_argument(
        "--canvas-dir",
        type=Path,
        default=DEFAULT_CANVAS_DIR,
        help="Canvas output directory",
    )
    args = parser.parse_args()

    if args.render_check:
        args.verify = True

    end = resolve_report_date(args.to_date) if args.to_date else date.today() - timedelta(days=1)

    if args.catch_up:
        bounds = catch_up_bounds(through=end)
        if bounds is None:
            archived = archived_dates()
            if not archived:
                raise SystemExit(
                    "No saved AM Brief JSON in exports/. Run a single day first:\n"
                    "  python am_daily_dashboard/generate_am_daily_dashboard.py --date YYYY-MM-DD"
                )
            print(f"Already caught up through {end.isoformat()} (newest archive: {max(archived)}).")
            return
        start, end = bounds
        skip_existing = not args.force
    elif args.from_date:
        start = date.fromisoformat(args.from_date)
        skip_existing = args.skip_existing and not args.force
    else:
        raise SystemExit("Provide --catch-up or --from YYYY-MM-DD (with optional --to).")

    dates = iter_report_dates(
        start,
        end,
        skip_existing=skip_existing,
        html_only=args.html_only,
    )
    if not dates:
        print(f"No dates to run between {start.isoformat()} and {end.isoformat()}.")
        return

    mode = "html-only" if args.html_only else "full"
    print(
        f"AM Brief range: {len(dates)} day(s), {mode}, "
        f"{dates[0].isoformat()} .. {dates[-1].isoformat()}"
    )
    if args.dry_run:
        for d in dates:
            print(f"  would run: {d.isoformat()}")
        return

    client = None if args.html_only else get_client()
    failures: list[str] = []
    t0 = time.perf_counter()
    for i, d in enumerate(dates, 1):
        print(f"\n=== [{i}/{len(dates)}] {d.isoformat()} ===")
        try:
            run_one_day(
                d,
                canvas_dir=args.canvas_dir,
                publish=args.publish,
                html_only=args.html_only,
                client=client,
            )
        except Exception as exc:
            failures.append(f"{d.isoformat()}: {exc}")
            print(f"FAILED {d.isoformat()}: {exc}", file=sys.stderr)
            continue
        if args.verify:
            code = run_verify(d, render_check=args.render_check)
            if code != 0:
                failures.append(f"{d.isoformat()}: verify exit {code}")

    elapsed = time.perf_counter() - t0
    print(
        f"\nDone: {len(dates) - len(failures)}/{len(dates)} succeeded in {elapsed:.0f}s."
    )
    if failures:
        print("Failures:")
        for line in failures:
            print(f"  - {line}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
