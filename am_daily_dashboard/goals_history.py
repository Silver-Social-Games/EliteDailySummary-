"""Elite AM Brief — final month Goals history.

A month's Goals numbers are live and moving until the calendar month ends. On
the last day of a month the figures are final, so we **close** them: a compact
snapshot per AM (and the manager's team block) is written to
``data/elite_goals_history.json`` keyed by ``YYYY-MM``. Later months then show a
"Goals History" card listing prior months' final results.

Two entry points:

* ``attach_history_to_payload(payload)`` — called during every generate /
  html-only rebuild. Loads the history file and hangs each AM's prior months on
  ``agents[].goals["history"]`` and the team's on ``teamGoals["history"]``.
  Isolation is automatic: per-AM history travels inside that AM's own goals
  block (kept by ``strip_payload_for_am``); team history stays inside the
  manager-only ``teamGoals`` key, which no per-AM file carries.

* ``close_month_from_payload(payload)`` — called on a full generate; a no-op
  unless the report date is the last day of its month. Idempotent: re-running a
  month-end run rewrites the same entry.

Only completed months **before** the report month are shown, so the current
in-progress month is never duplicated between the live Goals view and history.

CLI (backfill / manual close, reads the saved export as a script — never an
agent file tool):

    python am_daily_dashboard/goals_history.py --close 2026-08-31
"""

from __future__ import annotations

import argparse
import calendar
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

PACKAGE_DIR = Path(__file__).resolve().parent
DATA_DIR = PACKAGE_DIR / "data"
HISTORY_PATH = DATA_DIR / "elite_goals_history.json"
EXPORTS_DIR = PACKAGE_DIR / "exports"

# KPI actuals surfaced in the compact history card (a month-over-month trend).
# The full KPI list is still stored, so the card can grow without a reclose.
HISTORY_CARD_KPIS = ("daily_avg_purchase", "monthly_purchasers", "pct_active")


def month_key(d: date) -> str:
    return d.strftime("%Y-%m")


def is_month_end(d: date) -> bool:
    return d.day == calendar.monthrange(d.year, d.month)[1]


def load_history(path: Path | None = None) -> dict[str, Any]:
    """Return the history file as a dict; empty scaffold when missing/blank.

    Deliberately tolerant of a missing or unparseable file — history is an
    additive convenience, never a hard dependency, so the board must render
    before any month has closed.
    """
    path = path or HISTORY_PATH
    if not path.exists():
        return {"months": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"months": {}}
    if not isinstance(data, dict):
        return {"months": {}}
    data.setdefault("months", {})
    return data


def save_history(data: dict[str, Any], path: Path | None = None) -> None:
    path = path or HISTORY_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _snapshot_goals_block(block: dict[str, Any]) -> dict[str, Any]:
    """Compact, display-ready snapshot of one goals block for the history file.

    Copies only presentation fields (never the nested ``history`` list or the
    manager's appreciation points), so a stored month is small and cannot leak
    a running total back into itself on re-close.
    """
    kpis: list[dict[str, Any]] = []
    for k in block.get("kpis") or []:
        kpis.append(
            {
                "key": k.get("key"),
                "label": k.get("label"),
                "weightLabel": k.get("weightLabel"),
                "goalDisplay": k.get("goalDisplay"),
                "actualDisplay": k.get("actualDisplay"),
                "paceDisplay": k.get("paceDisplay"),
                "gapDisplay": k.get("gapDisplay"),
                "status": k.get("status"),
                "statusTone": k.get("statusTone"),
            }
        )
    kpi_points = block.get("kpiPoints")
    kpi_max = block.get("kpiPointsMax") or 80.0
    kpi_pct = (
        round(float(kpi_points) / float(kpi_max) * 100.0, 1)
        if kpi_points is not None and kpi_max
        else None
    )
    return {
        "agent": block.get("agent"),
        "agentName": block.get("agentName"),
        "monthLabel": block.get("monthLabel"),
        "kpiPoints": kpi_points,
        "kpiPointsMax": kpi_max,
        "kpiPct": kpi_pct,
        "weightedTrackedPct": block.get("weightedTrackedPct"),
        "portfolioSize": block.get("portfolioSize"),
        "activePlayers": block.get("activePlayers"),
        "mtdPurchase": block.get("mtdPurchase"),
        "mtdNetPurchase": block.get("mtdNetPurchase"),
        "kpis": kpis,
    }


def close_month_from_payload(
    payload: dict[str, Any], path: Path | None = None
) -> str | None:
    """If the payload's report date is a month-end, write that month's finals.

    Returns the month key it closed, or ``None`` when the date is not a
    month-end (the common case) or no goals were available.
    """
    report = payload.get("report") or {}
    date_str = report.get("date")
    if not date_str:
        return None
    try:
        d = date.fromisoformat(str(date_str))
    except ValueError:
        return None
    if not is_month_end(d):
        return None

    agents_snap: dict[str, Any] = {}
    month_label = ""
    for a in payload.get("agents") or []:
        block = a.get("goals")
        if block and block.get("available"):
            snap = _snapshot_goals_block(block)
            agents_snap[a.get("agentName")] = snap
            month_label = month_label or (snap.get("monthLabel") or "")
    team_block = payload.get("teamGoals")
    team_snap = (
        _snapshot_goals_block(team_block)
        if team_block and team_block.get("available")
        else None
    )
    if team_snap and not month_label:
        month_label = team_snap.get("monthLabel") or ""

    if not agents_snap and not team_snap:
        return None

    key = month_key(d)
    history = load_history(path)
    history["months"][key] = {
        "monthKey": key,
        "monthLabel": month_label or d.strftime("%b %Y"),
        "closedAsOf": d.isoformat(),
        "agents": agents_snap,
        "team": team_snap,
    }
    save_history(history, path)
    return key


def _prior_months(history: dict[str, Any], report_date: date) -> list[str]:
    """Closed month keys strictly before the report month, newest first."""
    current = month_key(report_date)
    keys = [k for k in (history.get("months") or {}) if k < current]
    return sorted(keys, reverse=True)


def agent_history(
    history: dict[str, Any], agent_name: str, report_date: date
) -> list[dict[str, Any]]:
    """Prior-month final snapshots for one AM, newest first."""
    out: list[dict[str, Any]] = []
    months = history.get("months") or {}
    for key in _prior_months(history, report_date):
        entry = months.get(key) or {}
        snap = (entry.get("agents") or {}).get(agent_name)
        if snap:
            # Stamp the month key/label from the entry so each history row is
            # self-describing (older closes stored these only on the entry).
            out.append({
                **snap,
                "monthKey": key,
                "monthLabel": snap.get("monthLabel") or entry.get("monthLabel"),
            })
    return out


def team_history(
    history: dict[str, Any], report_date: date
) -> list[dict[str, Any]]:
    """Prior-month final team snapshots, newest first."""
    out: list[dict[str, Any]] = []
    months = history.get("months") or {}
    for key in _prior_months(history, report_date):
        entry = months.get(key) or {}
        snap = entry.get("team")
        if snap:
            out.append({
                **snap,
                "monthKey": key,
                "monthLabel": snap.get("monthLabel") or entry.get("monthLabel"),
            })
    return out


def attach_history_to_payload(
    payload: dict[str, Any], path: Path | None = None
) -> None:
    """Hang prior-month history on each available goals block, in place.

    Safe to call on any payload: no-op when the report date is missing or no
    months have closed. Per-AM blocks get their own history only; the team
    block gets team history, and it lives inside the manager-only ``teamGoals``
    key so ``strip_payload_for_am`` never carries it into an AM file.
    """
    report = payload.get("report") or {}
    date_str = report.get("date")
    if not date_str:
        return
    try:
        report_date = date.fromisoformat(str(date_str))
    except ValueError:
        return
    history = load_history(path)
    if not history.get("months"):
        return
    for a in payload.get("agents") or []:
        block = a.get("goals")
        if block and block.get("available"):
            block["history"] = agent_history(
                history, a.get("agentName"), report_date
            )
    team_block = payload.get("teamGoals")
    if team_block and team_block.get("available"):
        team_block["history"] = team_history(history, report_date)


def _close_from_export(date_str: str) -> int:
    """CLI backfill: read the saved manager export for a date and close it.

    Reads the export as a plain script (allowed) — this is never an agent file
    tool, which the cost-discipline rule forbids for exports.
    """
    d = date.fromisoformat(date_str)
    export = EXPORTS_DIR / f"{date_str}_elite_am_brief.json"
    if not export.exists():
        print(f"No export to close: {export}", file=sys.stderr)
        return 1
    payload = json.loads(export.read_text(encoding="utf-8"))
    if not is_month_end(d):
        print(
            f"{date_str} is not the last day of its month — nothing to close."
        )
        return 1
    key = close_month_from_payload(payload)
    if key:
        entry = load_history()["months"][key]
        ams = ", ".join(sorted(entry.get("agents") or {}))
        print(
            f"Closed Goals history for {key} ({entry.get('monthLabel')}): "
            f"{ams}{' + Team' if entry.get('team') else ''}"
        )
        print(f"  {HISTORY_PATH}")
        return 0
    print(f"Nothing closed for {date_str} (no available goals in export).")
    return 1


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--close",
        metavar="YYYY-MM-DD",
        help="Close the month for this date from its saved manager export "
        "(must be the last day of the month).",
    )
    args = ap.parse_args()
    if args.close:
        raise SystemExit(_close_from_export(args.close))
    ap.print_help()


if __name__ == "__main__":
    main()
