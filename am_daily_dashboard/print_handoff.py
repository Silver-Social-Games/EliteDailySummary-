"""Print a new-chat handoff block for @elite-am-brief continuity."""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
EXPORTS = PACKAGE_DIR / "exports"
VERIFIED = EXPORTS / "verified"
EXPANSION_PLAN = PACKAGE_DIR / "AM_BRIEF_EXPANSION_PLAN.md"


def _newest_manager_json() -> Path | None:
    import re

    pat = re.compile(r"^(\d{4}-\d{2}-\d{2})_elite_am_brief\.json$")
    files = [p for p in EXPORTS.glob("*_elite_am_brief.json") if pat.match(p.name)]
    return sorted(files)[-1] if files else None


def _verified_dates() -> list[str]:
    if not VERIFIED.exists():
        return []
    return sorted(p.name.split("_")[0] for p in VERIFIED.glob("*_elite_am_brief.json"))


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    newest = _newest_manager_json()
    last_good = newest.name.split("_")[0] if newest else "none"
    verified = _verified_dates()
    last_verified = verified[-1] if verified else last_good
    _ = (date.today() - timedelta(days=1)).isoformat()

    verify_hint = ""
    if last_verified != "none":
        verify_hint = (
            f"\nRestore if needed:\n"
            f"  python am_daily_dashboard/verify_brief.py --date {last_verified} --restore-verified\n"
            f"  python am_daily_dashboard/generate_am_daily_dashboard.py --date {last_verified} "
            f"--html-only --cursor-audience manager"
        )

    block = f"""@elite-am-brief — continue on branch am-brief-expansion.

Last verify PASS: {last_verified} (newest export: {last_good}). Do not read exports/ JSON.
Test baseline: python -m unittest discover -s am_daily_dashboard (291 tests; any failure is new).

Open manager: VIP\\Elite_Cursor\\AM Brief\\elite_am_brief.html

Locked this round (see @elite-am-brief SKILL.md):
- Purchase Trends: purchase_trend_sql (60d), trends.ts + trend.ts; hero 3rd panel = Last 30 Days;
  State chart removed — do not re-add. Same Weekday = last 8 weekdays.
- Snapshot bands 3x3; 9th tile This Month Hold % = MTD Net / MTD Purchase.
- Lock & TAB: two tables, 8 columns; self-exclusion 7-day rule (LOCKS_SELF_EXCLUSION_LEAD_DAYS).
- After web/src edit: npx tsc --noEmit -> build.mjs -> --html-only -> verify_brief.py

Plan + rollback: am_daily_dashboard/AM_BRIEF_EXPANSION_PLAN.md
Daily catch-up: python am_daily_dashboard/generate_am_brief_range.py --catch-up --verify

Git: am-brief-expansion — eae2fe0 (expansion), cc9a99b (Big Winners dedupe + Looker 30d wiring).
Looker 5207: Purchase+filter+date=30+day (calibrated 2026-09-27) — capture_looker_portal_url.py <AID>.{verify_hint}
"""
    print(block)
    if EXPANSION_PLAN.exists():
        print(f"\n(Expansion plan: {EXPANSION_PLAN.name})")


if __name__ == "__main__":
    main()
