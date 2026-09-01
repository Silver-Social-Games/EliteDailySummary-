"""Print a new-chat handoff block for @elite-am-brief continuity."""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
EXPORTS = PACKAGE_DIR / "exports"
VERIFIED = EXPORTS / "verified"
HANDOFF_MD = PACKAGE_DIR / "HANDOFF_2026-08-25.md"


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
    newest = _newest_manager_json()
    last_good = newest.name.split("_")[0] if newest else "none"
    verified = _verified_dates()
    last_verified = verified[-1] if verified else last_good
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    verify_hint = ""
    if last_verified != "none":
        verify_hint = (
            f"\nRestore if needed:\n"
            f"  python am_daily_dashboard/verify_brief.py --date {last_verified} --restore-verified\n"
            f"  python am_daily_dashboard/generate_am_daily_dashboard.py --date {last_verified} --html-only"
        )

    block = f"""@elite-am-brief — continue from HANDOFF_2026-08-25.md

Last verify PASS: {last_verified} (newest export: {last_good}).
Open manager: VIP\\Elite_Cursor\\AM Brief\\elite_am_brief.html
Per-AM Coral: VIP\\Elite_Cursor\\AM Brief\\elite_am_brief_coral.html

Locked:
- % Active = MTD purchasers / portfolio (Goals + snapshots; Team Aug 24 = 79.7%)
- Snapshot: neutral ink; Active % of Portfolio = percent only; no footnotes
- After web/src edit: npx tsc --noEmit → build.mjs → --html-only
- Do not read exports/ JSON in agent tools

Pending:
- Coral reference row cleanup (elite_goals_reference.tsv) + --goals-only
- Slack go-live Thu 2026-08-28 setup; Sun 2026-08-31 first send
- Backfill older dates with new % Active? (see HANDOFF md)

Sun-Thu: python am_daily_dashboard/generate_am_brief_range.py --catch-up --verify
Full handoff: am_daily_dashboard/HANDOFF_2026-08-25.md{verify_hint}
"""
    print(block)
    if HANDOFF_MD.exists():
        print(f"\n(Full detail: {HANDOFF_MD})")


if __name__ == "__main__":
    main()
