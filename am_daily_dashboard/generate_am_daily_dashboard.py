"""
Elite AM Brief — morning board per AM (Coral, Gabriel, Lee, Rachel, Alon).

Run from repo root:
  python am_daily_dashboard/generate_am_daily_dashboard.py
  python am_daily_dashboard/generate_am_daily_dashboard.py --date 2026-07-27

Orchestration only: BigQuery calls → payload_builders → output writers.
Pure section builders live in payload_builders.py (testable without BQ).
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PACKAGE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PACKAGE_DIR))

from elite_lib.bigquery import HEAVY_QUERY_SCAN_CAP_BYTES, get_client, run_query  # noqa: E402
from elite_lib.export_paths import cursor_export_dir, mirror_to_cursor  # noqa: E402
from elite_lib.console import use_utf8_stdout  # noqa: E402

from config import (  # noqa: E402
    PENDING_RD_LOOKBACK_DAYS,
    PRODUCT_TITLE,
    manager_gate_token,
)
import queries as am_queries  # noqa: E402
from goals import (  # noqa: E402
    GOALS_AGENT_DISPLAY,
    GOALS_AGENT_TAGS,
    INCLUDED_WEIGHT_TOTAL,
    MANAGER_APPRECIATION_MAX,
    TEAM_AGENT_TAG,
    TEAM_DISPLAY_NAME,
    actuals_by_agent,
    appreciation_for_month,
    build_agent_goals_block,
    build_team_goals_block,
    strip_payload_for_am,
    targets_for_month,
    team_actuals,
)
from goals_reference import (  # noqa: E402
    gap_text,
    load_reference_tsv,
    reference_for,
)
from goals_history import (  # noqa: E402
    attach_history_to_payload,
    close_month_from_payload,
)
from am_brief_canvas import render_am_brief_canvas  # noqa: E402
from canvas_to_html import (  # noqa: E402
    publish_am_brief,
    refresh_all_brief_archives,
    mirror_brief_exports_to_cursor,
    write_am_brief_html,
)
from daily_summary.generate_daily_elite_canvas import build_report, build_top10_rows  # noqa: E402
from daily_summary.generate_daily_elite_summary import (  # noqa: E402
    build_sql,
    day_row,
    weekday_label,
)
from wow_drop_analysis.wow_drop_reason import (  # noqa: E402
    enrich_aids_sql,
    fetch_top_same_day_by_agent,
)
from payload_builders import (  # noqa: E402
    agent_display,
    build_am_shares_and_overview,
    build_anniversary_section,
    build_big_winners_section,
    build_big_losers_section,
    build_birthday_section,
    build_lock_section,
    build_rd_section,
    build_top10_section,
    build_zd_section,
    focus_for_agent,
    greeting_lines,
    soften_decline_rows,
)

OUTPUT_DIR = Path(__file__).resolve().parent / "exports"
DEFAULT_CANVAS_DIR = Path(
    r"C:\Users\Owner\.cursor\projects\c-Users-Owner-Downloads-Elite\canvases"
)

AM_ORDER = ["Coral", "Gabriel", "Lee", "Rachel", "Alon"]
# Goals exports (file-level isolation) — Alon omitted.
GOALS_AM_ORDER = ["Coral", "Gabriel", "Lee", "Rachel"]
CURSOR_AUDIENCE_CHOICES = ("manager", "coral", "gabriel", "lee", "rachel")
CURSOR_AUDIENCE_NAMES = {
    "coral": "Coral",
    "gabriel": "Gabriel",
    "lee": "Lee",
    "rachel": "Rachel",
}


def normalize_cursor_audience(raw: str | None) -> str | None:
    if not raw:
        return None
    key = raw.strip().lower()
    if key not in CURSOR_AUDIENCE_CHOICES:
        known = ", ".join(CURSOR_AUDIENCE_CHOICES)
        raise SystemExit(f"Unknown --cursor-audience {raw!r}. Choose: {known}")
    return key


def mirror_cursor_audience(
    audience: str,
    *,
    payload: dict,
    manager_html: Path,
) -> Path | None:
    """Write one self-contained brief to Elite_Cursor as elite_am_brief.html."""
    dest_dir = cursor_export_dir("am_brief")
    if dest_dir is None:
        return None
    dest = dest_dir / "elite_am_brief.html"
    if audience == "manager":
        if manager_html.resolve() != dest.resolve():
            shutil.copy2(manager_html, dest)
    else:
        am_payload = strip_payload_for_am(payload, CURSOR_AUDIENCE_NAMES[audience])
        write_am_brief_html(am_payload, dest)
    print(f"  Elite_Cursor audience ({audience}): {dest}")
    return dest

UPGRADES_NOTE = (
    "Upgrade to Elite = first Elite `dbt_utils.elite_account_tags` snapshot "
    "in the month through as-of, for accounts that were not Elite on the last "
    "snapshot before month start. Tag history starts 2026-04-08; attributed to "
    "tag_agent_1 on that first in-window snapshot (not current roster only)."
)


def resolve_report_date(arg: str | None) -> date:
    if arg:
        return date.fromisoformat(arg)
    return date.today() - timedelta(days=1)


def build_goals_blocks(
    report_date: date, client
) -> tuple[dict[str, dict | None], dict | None]:
    """Goals blocks per AM display name, plus the manager's team block.

    One query, so `--goals-only` can verify the numbers without paying for the
    whole board. The team row comes out of the same query's ROLLUP, so the
    manager view costs nothing extra to compute.
    """
    print("  Fetching Elite Goals MTD actuals...")
    goals_raw = run_query(
        client,
        am_queries.goals_mtd_actuals_sql(report_date),
        maximum_bytes_billed=HEAVY_QUERY_SCAN_CAP_BYTES,
    )
    goals_actuals = actuals_by_agent(goals_raw)
    goals_targets = targets_for_month(report_date)
    appreciation = appreciation_for_month(report_date)
    if appreciation:
        print(
            "  Manager appreciation set for: "
            + ", ".join(
                f"{GOALS_AGENT_DISPLAY[t]} {v['points']:g}/20"
                for t, v in sorted(appreciation.items())
            )
        )
    else:
        print("  Manager appreciation: none set for this month (score reads KPI only)")
    goals_by_display: dict[str, dict | None] = {}
    for tag in GOALS_AGENT_TAGS:
        block = build_agent_goals_block(
            tag,
            goals_targets.get(tag),
            goals_actuals.get(tag) or {},
            report_date,
            upgrades_available=True,
            upgrades_note=UPGRADES_NOTE,
            appreciation=appreciation.get(tag),
        )
        goals_by_display[GOALS_AGENT_DISPLAY[tag]] = block
        if block and block.get("available"):
            purchasers = next(
                (
                    k["actual"]
                    for k in block["kpis"]
                    if k["key"] == "monthly_purchasers"
                ),
                None,
            )
            score = block.get("score") or {}
            print(
                f"    {GOALS_AGENT_DISPLAY[tag]}: purchasers={purchasers} "
                f"score={score.get('totalDisplay')} ({score.get('scoreSubline')})"
            )
    for name in AM_ORDER:
        if name not in goals_by_display:
            goals_by_display[name] = None  # Alon
    team_block = build_team_goals_block(
        goals_targets.get(TEAM_AGENT_TAG),
        team_actuals(goals_raw),
        report_date,
        upgrades_available=True,
        upgrades_note=UPGRADES_NOTE,
    )
    if team_block and team_block.get("available"):
        print(
            f"    {TEAM_DISPLAY_NAME}: book={team_block.get('portfolioSize')} "
            f"tracked={team_block.get('weightedTrackedDisplay')}"
        )
    elif not goals_targets.get(TEAM_AGENT_TAG):
        print(
            f"  No '{TEAM_AGENT_TAG}' target row in elite_goals.tsv for "
            f"{report_date:%b %Y} — team view will report unavailable"
        )
    return goals_by_display, team_block


GEO_STATE_PATH = PACKAGE_DIR / "data" / "elite_players_by_state.json"


def load_geo_chart() -> dict | None:
    """Book-wide Elite player state mix — bundled JSON, refreshed from export."""
    if not GEO_STATE_PATH.is_file():
        return None
    try:
        return json.loads(GEO_STATE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def build_payload(report_date: date, client) -> dict:
    print(f"Fetching AM Brief data for {report_date}...")
    top10_raw = run_query(client, am_queries.top10_purchasers_sql(report_date))
    print(f"  Top 10 rows: {len(top10_raw)}")
    rd5k_raw = run_query(client, am_queries.locked_rd_over_5k_sql(report_date))
    print(f"  Pending Redemptions (>=$5k, 3d): {len(rd5k_raw)}")
    rd_first_raw = run_query(client, am_queries.first_time_locked_rd_sql(report_date))
    print(f"  First-time locked RD (3d): {len(rd_first_raw)}")
    bday_raw = run_query(client, am_queries.birthdays_last_3d_sql(report_date))
    print(f"  Birthdays (3d): {len(bday_raw)}")
    anniv_raw = run_query(client, am_queries.anniversary_sql(report_date))
    print(f"  One-month anniversaries (3d): {len(anniv_raw)}")
    zd_raw = run_query(client, am_queries.open_zendesk_sql())
    print(f"  Open ZD players: {len(zd_raw)}")
    bw_raw = run_query(client, am_queries.big_winners_sql(report_date))
    print(f"  Big Winners (≥$20K GGR win): {len(bw_raw)}")
    bl_raw = run_query(client, am_queries.big_losers_sql(report_date))
    print(f"  Big Losers (≥$5K GGR loss): {len(bl_raw)}")
    # One shared enrich fetch (lifetime purchase/hold for Open Tickets, plus
    # zendesk_user_id so First-Time Locked RD / Birthdays tickets can
    # pre-select the requester) covering every AID that needs it.
    # Big Winner AIDs are included here at no extra query cost.
    ticket_aids: set[int] = set()
    for r in zd_raw:
        try:
            ticket_aids.add(int(r["AID"]))
        except (TypeError, ValueError, KeyError):
            continue
    # rd5k_raw is in here for its missing-document status and account context,
    # not for a ticket draft — Pending RD stays view-only.
    for r in (*top10_raw, *rd5k_raw, *rd_first_raw, *bday_raw, *anniv_raw, *bw_raw, *bl_raw):
        try:
            ticket_aids.add(int(r["AID"]))
        except (TypeError, ValueError, KeyError):
            continue
    shared_enrich: dict[int, dict] = {}
    if ticket_aids:
        print(
            f"  Enriching metrics for {len(ticket_aids)} AIDs "
            f"(Top 10, Open Tickets, RD, Birthdays, Big Winners)..."
        )
        shared_enrich = {
            int(e["AID"]): e
            for e in run_query(client, enrich_aids_sql(sorted(ticket_aids), report_date))
        }
    zd = build_zd_section(zd_raw, shared_enrich, report_date=report_date)
    big_winners = build_big_winners_section(bw_raw, shared_enrich)
    big_losers = build_big_losers_section(bl_raw, shared_enrich)
    locks_raw = run_query(client, am_queries.locked_players_sql())
    print(f"  Locked players (raw): {len(locks_raw)}")
    purchase_raw = run_query(client, am_queries.agent_day_purchase_sql(report_date))
    purchase_by_tag = {r["agent"]: r for r in purchase_raw}
    book_raw = run_query(client, am_queries.agent_book_size_sql())
    book_by_tag = {r["agent"]: int(r.get("total_players") or 0) for r in book_raw}
    print(f"  AM book sizes: {len(book_by_tag)} agents")

    goals_by_display, team_goals = build_goals_blocks(report_date, client)

    print("  Fetching Elite / Jackpota weekday summary...")
    sql = build_sql(report_date)
    day_rows = run_query(client, sql["weekday_compare"])
    overall_rows = run_query(client, sql["overall_weekday_compare"])
    decline_report = build_report(report_date, day_rows, overall_rows)
    prior_day = report_date - timedelta(days=7)
    elite_this = day_row(day_rows, report_date)
    elite_prior = day_row(day_rows, prior_day)
    elite_wow_drop = max(
        0.0,
        float(elite_prior.get("revenue") or 0) - float(elite_this.get("revenue") or 0),
    )
    elite_rev = float(elite_this.get("revenue") or 0)
    elite_ply = int(elite_this.get("players") or 0)

    print("  Fetching Top 20 same-day decline per AM (Daily Elite logic)...")
    decline_by_am_raw = fetch_top_same_day_by_agent(
        client,
        report_date,
        AM_ORDER,
        elite_wow_drop=elite_wow_drop,
    )
    decline_by_am = {
        name: soften_decline_rows(build_top10_rows(raw), raw)
        for name, raw in decline_by_am_raw.items()
    }
    for name, rows in decline_by_am.items():
        print(f"    {name}: {len(rows)} Top 20 rows")

    top10 = build_top10_section(top10_raw, metrics_enrich=shared_enrich)
    rd5k = build_rd_section(
        rd5k_raw,
        report_date,
        aging_threshold_days=PENDING_RD_LOOKBACK_DAYS - 1,
        metrics_enrich=shared_enrich,
    )
    rd_first = build_rd_section(rd_first_raw, ticket_enrich=shared_enrich)
    birthdays = build_birthday_section(bday_raw, ticket_enrich=shared_enrich)
    anniversary = build_anniversary_section(anniv_raw, enrich_map=shared_enrich)
    locks = build_lock_section(locks_raw, report_date)
    print(f"  Locked after past-day window filter: {len(locks)}")

    weekday = weekday_label(report_date)
    subtitle = f"{weekday} {report_date.strftime('%d %b %Y')}"
    day_short = weekday[:3]

    agents = []
    for name in AM_ORDER:
        purchase = None
        total_players = 0
        for tag, row in purchase_by_tag.items():
            if agent_display(tag) == name:
                purchase = row
                break
        for tag, n in book_by_tag.items():
            if agent_display(tag) == name:
                total_players = n
                break
        agents.append(
            focus_for_agent(
                name,
                weekday,
                top10=top10,
                decline=decline_by_am.get(name, []),
                rd5k=rd5k,
                rd_first=rd_first,
                birthdays=birthdays,
                anniversary=anniversary,
                zd=zd,
                locks=locks,
                big_winners=big_winners,
                big_losers=big_losers,
                purchase=purchase,
                total_players=total_players,
                elite_rev=elite_rev,
                elite_ply=elite_ply,
                goals=goals_by_display.get(name),
            )
        )

    am_shares, overview = build_am_shares_and_overview(agents)

    payload = {
        "report": {
            "date": report_date.isoformat(),
            "weekday": weekday,
            "dayShort": day_short,
            "subtitle": subtitle,
            "title": PRODUCT_TITLE,
            "headline": decline_report.get("headline") or "",
            "segmentTitle": "WoW Purchase",
            "geoChart": load_geo_chart(),
            "overviewGreetingLines": [
                "Good morning.",
                f"Here is your {weekday} summary.",
                "Good luck 🚀",
            ],
            "segments": decline_report.get("segments") or [],
        },
        "amShares": am_shares,
        "overview": overview,
        "agents": agents,
        "amOrder": AM_ORDER,
        "goalsMeta": {
            "includedWeightTotal": INCLUDED_WEIGHT_TOTAL,
            "managerAppreciationMax": MANAGER_APPRECIATION_MAX,
            "upgradesNote": UPGRADES_NOTE,
            "asOf": report_date.isoformat(),
            "goalsAmOrder": GOALS_AM_ORDER,
        },
        # Manager-only, both of them. strip_payload_for_am rebuilds the payload
        # from a fixed key list, so neither reaches a per-AM file.
        "teamGoals": team_goals,
        "managerGate": manager_gate_token(),
    }
    # Prior completed months' final Goals, per AM (inside each goals block) and
    # for the team (inside manager-only teamGoals). Isolation is automatic.
    attach_history_to_payload(payload)
    return payload


def write_outputs(
    payload: dict,
    canvas_dir: Path,
    *,
    publish: bool = False,
    cursor_audience: str | None = None,
) -> tuple[Path, Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    canvas_dir.mkdir(parents=True, exist_ok=True)
    d = payload["report"]["date"]
    canvas_path = canvas_dir / f"elite-am-brief-{d}.canvas.tsx"
    canvas_path.write_text(render_am_brief_canvas(payload), encoding="utf-8")
    html_path = OUTPUT_DIR / f"{d}_elite_am_brief.html"
    write_am_brief_html(payload, html_path)
    json_path = OUTPUT_DIR / f"{d}_elite_am_brief.json"
    json_path.write_text(
        json.dumps(payload, indent=2, default=str),
        encoding="utf-8",
    )
    # Clean prior Focus slug artifacts for same date if present
    old_canvas = canvas_dir / f"elite-am-focus-{d}.canvas.tsx"
    if old_canvas.exists():
        old_canvas.unlink()

    per_am_paths: list[Path] = []
    # Dateless copies so a bookmark survives to tomorrow. The dated file stays
    # the archive; these are overwritten every run and are what people open.
    latest_paths: list[Path] = [OUTPUT_DIR / "elite_am_brief.html"]
    write_am_brief_html(payload, latest_paths[0])
    for name in GOALS_AM_ORDER:
        slug = name.lower()
        am_payload = strip_payload_for_am(payload, name)
        am_html = OUTPUT_DIR / f"{d}_elite_am_brief_{slug}.html"
        am_json = OUTPUT_DIR / f"{d}_elite_am_brief_{slug}.json"
        write_am_brief_html(am_payload, am_html)
        am_json.write_text(
            json.dumps(am_payload, indent=2, default=str),
            encoding="utf-8",
        )
        am_latest = OUTPUT_DIR / f"elite_am_brief_{slug}.html"
        write_am_brief_html(am_payload, am_latest)
        latest_paths.append(am_latest)
        am_canvas = canvas_dir / f"elite-am-brief-{d}-{slug}.canvas.tsx"
        am_canvas.write_text(render_am_brief_canvas(am_payload), encoding="utf-8")
        per_am_paths.extend([am_html, am_json])
        print(f"  Per-AM: {am_html.name}  (+ {am_latest.name})")

    # Month-end: freeze this month's final Goals into the history file so next
    # month's board can show it. No-op on any other day; idempotent on re-run.
    closed = close_month_from_payload(payload)
    if closed:
        print(f"  Month-end: closed Goals history for {closed}")

    if publish:
        publish_am_brief(html_path)
    refresh_all_brief_archives(mirror=False)
    mirror_brief_exports_to_cursor()
    if cursor_audience:
        mirror_cursor_audience(cursor_audience, payload=payload, manager_html=html_path)
    return canvas_path, html_path


def rebuild_html_from_json(
    report_date: date,
    *,
    publish: bool = False,
    cursor_audience: str | None = None,
) -> Path:
    """Rewrite every HTML file for a date from the saved payload, no query.

    Editing the web shell used to mean a full ~90s run against BigQuery just to
    see the change, and the saved JSON already holds everything the HTML needs.
    Per-AM files are re-derived with strip_payload_for_am rather than read from
    their own JSONs, so this cannot drift from what a real run produces.
    """
    d = report_date.isoformat()
    json_path = OUTPUT_DIR / f"{d}_elite_am_brief.json"
    if not json_path.exists():
        raise SystemExit(
            f"No saved payload for {d}: {json_path}\n"
            "Run without --html-only once to fetch the data."
        )
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    report = payload.setdefault("report", {})
    report["title"] = PRODUCT_TITLE
    report["segmentTitle"] = "WoW Purchase"
    geo = load_geo_chart()
    if geo:
        report["geoChart"] = geo
    # Refresh prior-month Goals history from the current history file so an
    # html-only rebuild picks up any month closed since this JSON was written.
    attach_history_to_payload(payload)
    written: list[Path] = []
    manager_dated = OUTPUT_DIR / f"{d}_elite_am_brief.html"
    for path in (manager_dated, OUTPUT_DIR / "elite_am_brief.html"):
        write_am_brief_html(payload, path)
        written.append(path)
    for name in GOALS_AM_ORDER:
        slug = name.lower()
        am_payload = strip_payload_for_am(payload, name)
        for path in (
            OUTPUT_DIR / f"{d}_elite_am_brief_{slug}.html",
            OUTPUT_DIR / f"elite_am_brief_{slug}.html",
        ):
            write_am_brief_html(am_payload, path)
            written.append(path)
    print(f"Rebuilt {len(written)} HTML files from {json_path.name} (no query)")
    refresh_all_brief_archives(mirror=False)
    mirror_brief_exports_to_cursor()
    if cursor_audience:
        mirror_cursor_audience(
            cursor_audience,
            payload=payload,
            manager_html=manager_dated,
        )
    if publish:
        publish_am_brief(manager_dated)
    return manager_dated


def print_goals_audit(payload: dict) -> None:
    """Compact audit table for verification against external Goals sheet.

    Adds Yours / Gap columns for any AM and as-of date present in
    data/elite_goals_reference.tsv, so a drift against the AM's own table shows up
    in the audit itself rather than in a manual read-out. See goals_reference.py.
    """
    reference = load_reference_tsv()
    # The team block lives outside `agents` (it is manager-only), so append it
    # here rather than at each call site — otherwise a full run audits four AMs
    # while --goals-only audits five.
    rows = list(payload.get("agents") or [])
    team = payload.get("teamGoals")
    if team and not any(a.get("agentName") == TEAM_DISPLAY_NAME for a in rows):
        rows.append({"agentName": TEAM_DISPLAY_NAME, "goals": team})
    print("\n=== Goals audit (as of report date) ===")
    has_ref = bool(reference)
    header = (
        f"{'AM':<10} {'KPI':<28} {'Goal':>12} {'Actual':>12} {'Pace':>12} "
        f"{'Status':<10}"
    )
    if has_ref:
        header += f" {'Yours':>12} {'Gap':>16}"
    print(header)
    print("-" * len(header))
    for a in rows:
        goals = a.get("goals")
        if not goals or not goals.get("available"):
            continue
        theirs = (
            reference_for(reference, goals.get("agent") or "", goals.get("asOf") or "")
            if has_ref
            else {}
        )
        for k in goals.get("kpis") or []:
            line = (
                f"{a['agentName']:<10} {k['label']:<28} "
                f"{k.get('goalDisplay') or '—':>12} "
                f"{k.get('actualDisplay') or '—':>12} "
                f"{k.get('paceDisplay') or '—':>12} "
                f"{k.get('status') or '—':<10}"
            )
            if has_ref:
                mine, gap = gap_text(
                    k["label"], k.get("actual"), theirs.get(k["label"])
                )
                line += f" {mine:>12} {gap:>16}"
            print(line)
        tracked = goals.get("weightedTrackedDisplay") or "—"
        print(f"{a['agentName']:<10} {'(weighted tracked)':<28} {'':>12} {'':>12} {tracked:>12}")
        shapes = (
            f"purchasers {goals.get('purchasersShape') or 0:.3f} / "
            f"upgrades {goals.get('upgradesShape') or 0:.3f}"
        )
        print(f"{a['agentName']:<10} {'(month-shape divisors)':<28} {shapes}")
        print(
            f"{a['agentName']:<10} {'(net if paid-redeem instead)':<28} "
            f"{'':>12} ${goals.get('dailyNetPaidRedeem') or 0:>11,.0f}"
        )
        print(
            f"{a['agentName']:<10} {'(portfolio: tagged book)':<28} "
            f"{goals.get('portfolioSize') or 0:>12,} "
            f"{'':>11}"
            f"   ({goals.get('portfolioLocked') or 0} locked, still counted)"
        )
        snap = goals.get("bookSnapshotDate") or ""
        as_of = goals.get("asOf") or ""
        drift = "" if snap == as_of else "  <-- DRIFTED, book is not the report date"
        print(
            f"{a['agentName']:<10} {'(book tag snapshot)':<28} "
            f"{snap or '—':>12}{drift}"
        )
        print("-" * len(header))



def main() -> None:
    use_utf8_stdout()
    parser = argparse.ArgumentParser(description="Elite AM Brief morning board")
    parser.add_argument("--date", help="Report date YYYY-MM-DD (default: yesterday)")
    parser.add_argument(
        "--canvas-dir",
        type=Path,
        default=DEFAULT_CANVAS_DIR,
        help="Canvas output directory",
    )
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Copy HTML into docs/ for GitHub Pages (off by default; local review only)",
    )
    parser.add_argument(
        "--goals-only",
        action="store_true",
        help="Print the Goals audit from one query and exit; writes no files. "
        "Use to check Goal/MTD/Pace against an external sheet.",
    )
    parser.add_argument(
        "--html-only",
        action="store_true",
        help="Rebuild every HTML file for the date from the saved JSON, with no "
        "BigQuery query (~3s vs ~90s). Use after editing the web shell.",
    )
    parser.add_argument(
        "--cursor-audience",
        choices=CURSOR_AUDIENCE_CHOICES,
        help="Also mirror one elite_am_brief.html to Elite_Cursor for this audience "
        "(manager = full book; coral/gabriel/lee/rachel = stripped payload)",
    )
    args = parser.parse_args()
    report_date = resolve_report_date(args.date)
    cursor_audience = normalize_cursor_audience(args.cursor_audience)
    if args.html_only:
        rebuild_html_from_json(
            report_date,
            publish=args.publish,
            cursor_audience=cursor_audience,
        )
        return
    client = get_client()
    if args.goals_only:
        goals, team_goals = build_goals_blocks(report_date, client)
        print_goals_audit(
            {
                "agents": [
                    {"agentName": name, "goals": block}
                    for name, block in goals.items()
                    if block
                ],
                "teamGoals": team_goals,
            }
        )
        return
    payload = build_payload(report_date, client)
    canvas_path, html_path = write_outputs(
        payload,
        args.canvas_dir,
        publish=args.publish,
        cursor_audience=cursor_audience,
    )
    print_goals_audit(payload)
    print(f"Wrote {canvas_path}")
    print(f"Wrote {html_path}")


if __name__ == "__main__":
    main()
