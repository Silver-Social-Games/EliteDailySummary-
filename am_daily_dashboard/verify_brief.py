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
sys.path.insert(0, str(PACKAGE_DIR))

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
    args = ap.parse_args()

    date_str = args.date or newest_date()
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
    verify_isolation(date_str, report)
    if args.render_check:
        render_check(date_str, report)

    verdict = (
        "OK - all checks passed"
        if not report.failures
        else f"{report.failures} FAILURE(S)"
    )
    print(f"\n{verdict}")
    sys.exit(1 if report.failures else 0)


if __name__ == "__main__":
    main()
