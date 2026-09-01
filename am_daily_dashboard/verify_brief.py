"""Compact post-generate check for the Elite AM Brief.

Reads the newest (or --date) export and prints ~25 lines of PASS/FAIL instead of
requiring anyone to open a 0.3-1.1 MB HTML/JSON. Exit code 1 on any FAIL.

Run from repo root:
  python am_daily_dashboard/verify_brief.py
  python am_daily_dashboard/verify_brief.py --date 2026-08-17
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PACKAGE_DIR))

from canvas_to_html import restore_verified_exports, snapshot_verified_exports  # noqa: E402

EXPORTS = PACKAGE_DIR / "exports"
TESTS_JS_DIR = PACKAGE_DIR / "tests_js"

AM_ORDER = ["Coral", "Gabriel", "Lee", "Rachel", "Alon"]
GOALS_AM_ORDER = ["Coral", "Gabriel", "Lee", "Rachel"]

# focus counter -> the list it should agree with
FOCUS_VS_LIST = {
    "locked": "locks",
    "rdOver5k": "rdOver5k",
    "birthdays": "birthdays",
    "declineCount": "decline",
}

# Manager-only keys that must never appear in a per-AM export.
MANAGER_ONLY = ["teamGoals", "managerGate"]


class Report:
    def __init__(self) -> None:
        self.failures = 0

    def check(self, ok: bool, label: str, detail: str = "") -> bool:
        tag = "PASS" if ok else "FAIL"
        if not ok:
            self.failures += 1
        suffix = f"  {detail}" if detail else ""
        print(f"  [{tag}] {label}{suffix}")
        return ok


def newest_date() -> str:
    files = sorted(EXPORTS.glob("*_elite_am_brief.json"))
    if not files:
        raise SystemExit(
            f"No AM Brief JSON in {EXPORTS}. Run "
            "generate_am_daily_dashboard.py first."
        )
    return files[-1].name.split("_")[0]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_structure(payload: dict, report: Report) -> None:
    print("Payload structure")
    for key in ("report", "agents", "amShares", "overview", "amOrder", "goalsMeta"):
        report.check(key in payload, f"top-level key {key!r}")
    agents = payload.get("agents") or []
    names = [a.get("agentName") for a in agents]
    report.check(names == AM_ORDER, "agents match AM_ORDER", f"got {names}")
    report.check(
        len(payload.get("overview") or []) == len(AM_ORDER), "overview row per AM"
    )
    segments = (payload.get("report") or {}).get("segments") or []
    report.check(bool(segments), "weekday segments present", f"{len(segments)} rows")


def verify_agents(payload: dict, report: Report) -> None:
    print("\nPer-AM section counts (focus badge vs actual rows)")
    header = f"  {'AM':<9}{'Top10':>6}{'WoW':>5}{'RD5k':>6}{'RDnew':>6}"
    print(header + f"{'Bday':>6}{'ZD':>4}{'Lock':>6}{'Goals':>7}")
    for agent in payload.get("agents") or []:
        name = agent.get("agentName", "?")
        focus = agent.get("focus") or {}
        counts = (
            f"  {name:<9}"
            f"{len(agent.get('top10') or []):>6}"
            f"{len(agent.get('decline') or []):>5}"
            f"{len(agent.get('rdOver5k') or []):>6}"
            f"{len(agent.get('rdFirstTime') or []):>6}"
            f"{len(agent.get('birthdays') or []):>6}"
            f"{len(agent.get('zendesk') or []):>4}"
            f"{len(agent.get('locks') or []):>6}"
            f"{('yes' if agent.get('goals') else 'no'):>7}"
        )
        print(counts)
        for badge, list_key in FOCUS_VS_LIST.items():
            expected = len(agent.get(list_key) or [])
            got = focus.get(badge)
            if got != expected:
                report.check(
                    False,
                    f"{name} focus.{badge} disagrees with {list_key}",
                    f"badge={got} rows={expected}",
                )
        if not agent.get("greetingLines"):
            report.check(False, f"{name} greetingLines empty")

    print("\nGoals coverage")
    by_name = {a.get("agentName"): a for a in payload.get("agents") or []}
    for name in GOALS_AM_ORDER:
        block = (by_name.get(name) or {}).get("goals")
        report.check(bool(block), f"{name} has a goals block")
        kpis = (block or {}).get("kpis") or []
        if block:
            missing = [k.get("key") for k in kpis if k.get("actual") is None]
            report.check(not missing, f"{name} KPIs all have actuals", str(missing))
    report.check(
        not (by_name.get("Alon") or {}).get("goals"),
        "Alon carries no goals block (by design)",
    )
    report.check(bool(payload.get("teamGoals")), "manager teamGoals present in full export")


def verify_goals_math(payload: dict, report: Report) -> None:
    """MTD / elapsed must equal Goals daily avgs; net must sit below purchase."""
    print("\nGoals math (MTD / elapsed = daily avg)")
    by_name = {a.get("agentName"): a for a in payload.get("agents") or []}
    for name in GOALS_AM_ORDER:
        block = (by_name.get(name) or {}).get("goals") or {}
        if not block.get("available"):
            continue
        elapsed = int(block.get("elapsedDays") or 0)
        if elapsed <= 0:
            report.check(False, f"{name} goals elapsedDays", "missing or zero")
            continue
        mtd_p = float(block.get("mtdPurchase") or 0)
        mtd_n = float(block.get("mtdNetPurchase") or 0)
        kpis = {k.get("key"): k for k in block.get("kpis") or []}
        dap = kpis.get("daily_avg_purchase") or {}
        dan = kpis.get("daily_avg_net_purchase") or {}
        dap_v = dap.get("actual")
        dan_v = dan.get("actual")
        if dap_v is None or dan_v is None:
            report.check(False, f"{name} daily avg KPIs present")
            continue
        dap_f = float(dap_v)
        dan_f = float(dan_v)
        report.check(
            abs(mtd_p / elapsed - dap_f) < 0.02,
            f"{name} MTD purchase / {elapsed} = Daily Avg Purchase",
            f"mtd={mtd_p:,.0f} daily={dap_f:,.2f}",
        )
        report.check(
            abs(mtd_n / elapsed - dan_f) < 0.02,
            f"{name} MTD net / {elapsed} = Daily Avg Net",
            f"mtd={mtd_n:,.0f} daily={dan_f:,.2f}",
        )
        report.check(
            mtd_n <= mtd_p + 0.01,
            f"{name} net purchase <= gross purchase",
            f"net={mtd_n:,.0f} purchase={mtd_p:,.0f}",
        )
        _verify_pct_active(block, name, report)

    team = payload.get("teamGoals") or {}
    if team.get("available"):
        _verify_pct_active(team, "Team", report)


def _verify_pct_active(block: dict, label: str, report: Report) -> None:
    """% Active = MTD purchasers / portfolio everywhere."""
    portfolio = int(block.get("portfolioSize") or 0)
    kpis = {k.get("key"): k for k in block.get("kpis") or []}
    pct_kpi = kpis.get("pct_active") or {}
    pct = pct_kpi.get("actual")
    purchasers = (kpis.get("monthly_purchasers") or {}).get("actual")
    if portfolio <= 0 or pct is None or purchasers is None:
        return
    expected = min(100.0, float(purchasers) / portfolio * 100.0)
    report.check(
        abs(float(pct) - expected) < 0.06,
        f"{label} % Active = MTD purchasers / portfolio",
        f"purchasers={float(purchasers):,.0f} book={portfolio:,} pct={float(pct):.1f}%",
    )


def verify_responsiveness(payload: dict, report: Report) -> None:
    """Phase E: responsiveness section — skip gracefully when not yet built."""
    agents = payload.get("agents") or []
    has_any = any(a.get("responsiveness") is not None for a in agents)
    if not has_any:
        return
    print("\nResponsiveness (90-day no-ticket)")
    for agent in agents:
        name = agent.get("agentName", "?")
        rows = agent.get("responsiveness")
        if rows is None:
            continue
        report.check(isinstance(rows, list), f"{name} responsiveness is a list")
        for row in rows:
            report.check("aid" in row, f"{name} responsiveness row has 'aid'")
            report.check("daysSinceTicket" in row, f"{name} responsiveness row has 'daysSinceTicket'")


def verify_birthday_gift(payload: dict, report: Report) -> None:
    """Phase D: birthday gift eligible section — skip gracefully when not yet built."""
    agents = payload.get("agents") or []
    has_any = any(a.get("birthdayGift") is not None for a in agents)
    if not has_any:
        return
    print("\nBirthday Gift eligibility")
    for agent in agents:
        name = agent.get("agentName", "?")
        rows = agent.get("birthdayGift")
        if rows is None:
            continue
        report.check(isinstance(rows, list), f"{name} birthdayGift is a list")
        for row in rows:
            report.check("aid" in row, f"{name} birthdayGift row has 'aid'")
            report.check("holdPct" in row, f"{name} birthdayGift row has 'holdPct'")
            report.check("purchase30d" in row, f"{name} birthdayGift row has 'purchase30d'")


def verify_anniversary(payload: dict, report: Report) -> None:
    """Phase C: one-month anniversary section — skip gracefully when not yet built."""
    agents = payload.get("agents") or []
    has_any = any(a.get("anniversary") is not None for a in agents)
    if not has_any:
        return
    print("\nOne-month anniversary")
    for agent in agents:
        name = agent.get("agentName", "?")
        rows = agent.get("anniversary")
        if rows is None:
            continue
        report.check(isinstance(rows, list), f"{name} anniversary is a list")
        for row in rows:
            report.check("aid" in row, f"{name} anniversary row has 'aid'")
            report.check("managedDate" in row, f"{name} anniversary row has 'managedDate'")
            report.check("anniversaryDate" in row, f"{name} anniversary row has 'anniversaryDate'")


def verify_isolation(date_str: str, report: Report) -> None:
    print("\nPer-AM file isolation")
    for name in GOALS_AM_ORDER:
        slug = name.lower()
        path = EXPORTS / f"{date_str}_elite_am_brief_{slug}.json"
        if not report.check(path.exists(), f"{slug} export exists"):
            continue
        data = load(path)
        others = [
            a.get("agentName")
            for a in data.get("agents") or []
            if a.get("agentName") != name
        ]
        report.check(not others, f"{slug} file holds only {name}", str(others))
        leaked = [k for k in MANAGER_ONLY if data.get(k)]
        report.check(not leaked, f"{slug} file has no manager-only keys", str(leaked))
        html = EXPORTS / f"{date_str}_elite_am_brief_{slug}.html"
        report.check(
            html.exists() and html.stat().st_size > 50_000,
            f"{slug} HTML written",
            f"{html.stat().st_size // 1024} KB" if html.exists() else "missing",
        )


def render_check(date_str: str, report: Report) -> None:
    """Actually render today's real manager HTML in a DOM (jsdom via Node) and
    confirm every nav item shows content with no uncaught JS error.

    This is the one check here that a payload-only read cannot do: the board
    can be JSON-correct and still render blank (the sessionStorage bug this
    board actually shipped). Requires Node — skips with a clear message
    rather than failing the whole verify run if it is not on PATH."""
    print("\nRender check (real export, not a fixture)")
    node = shutil.which("node")
    if not node:
        print("  [SKIP] node not found on PATH - install Node to run --render-check")
        return
    html_path = EXPORTS / f"{date_str}_elite_am_brief.html"
    if not html_path.exists():
        report.check(False, "manager HTML exists for render check", str(html_path))
        return
    script = TESTS_JS_DIR / "real_export_check.mjs"
    node_modules = TESTS_JS_DIR / "node_modules"
    if not node_modules.exists():
        print("  [SKIP] tests_js/node_modules missing - run `npm install` in am_daily_dashboard/tests_js")
        return
    result = subprocess.run(
        [node, str(script), str(html_path)],
        cwd=TESTS_JS_DIR, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    print(result.stdout.rstrip())
    if result.returncode != 0:
        report.check(False, "render check passed", f"exit {result.returncode}")
    else:
        report.check(True, "render check passed")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date", help="YYYY-MM-DD; defaults to newest export")
    ap.add_argument(
        "--render-check", action="store_true",
        help="Also render today's real HTML in a DOM (jsdom via Node) and "
             "confirm every view shows content with no JS error",
    )
    ap.add_argument(
        "--no-snapshot",
        action="store_true",
        help="Skip verified snapshot even when checks pass",
    )
    ap.add_argument(
        "--restore-verified",
        action="store_true",
        help="Restore exports/ JSON from exports/verified/ for --date, then exit",
    )
    args = ap.parse_args()

    date_str = args.date or newest_date()
    if args.restore_verified:
        restore_verified_exports(date_str)
        print(f"Restored verified JSON for {date_str}. Rebuild HTML with:\n"
              f"  python am_daily_dashboard/generate_am_daily_dashboard.py "
              f"--date {date_str} --html-only")
        return

    full = EXPORTS / f"{date_str}_elite_am_brief.json"
    if not full.exists():
        raise SystemExit(f"Missing {full}")

    payload = load(full)
    print(f"AM Brief verify - {date_str} ({full.stat().st_size // 1024} KB)")
    report = Report()
    report.check(
        (payload.get("report") or {}).get("date") == date_str,
        "payload date matches filename",
    )
    verify_structure(payload, report)
    verify_agents(payload, report)
    verify_goals_math(payload, report)
    verify_responsiveness(payload, report)
    verify_birthday_gift(payload, report)
    verify_anniversary(payload, report)
    verify_isolation(date_str, report)
    if args.render_check:
        render_check(date_str, report)

    verdict = (
        "OK - all checks passed"
        if not report.failures
        else f"{report.failures} FAILURE(S)"
    )
    print(f"\n{verdict}")
    if not report.failures and not args.no_snapshot:
        snapshot_verified_exports(date_str)
    sys.exit(1 if report.failures else 0)


if __name__ == "__main__":
    main()
