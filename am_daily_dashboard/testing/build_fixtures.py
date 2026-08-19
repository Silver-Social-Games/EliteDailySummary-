"""Materialize AM Brief payload fixtures into real HTML + small assertion JSON.

Run before the jsdom suite (the Node harness does this itself via
tests_js/render.test.mjs, so this rarely needs to run by hand):

  python am_daily_dashboard/testing/build_fixtures.py

Writes into am_daily_dashboard/tests_js/fixtures/ (gitignored — nothing here
is ever committed). Each fixture gets:
  - <name>.html  — the exact production shell (write_am_brief_html), so the
    JS suite exercises the real renderer, not a hand-copied stand-in.
  - <name>.meta.json — a handful of small values the test needs to assert
    against (manager gate token, archive dates, agent names). Deliberately
    NOT the full payload — the point of a fixture is that it's tiny.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = PACKAGE_DIR.parent
for _p in (PROJECT_ROOT, PACKAGE_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from canvas_to_html import write_am_brief_html  # noqa: E402

from testing.payload_fixtures import (  # noqa: E402
    build_empty_sections_payload,
    build_large_tickets_payload,
    build_manager_payload,
    build_single_am_payload,
)

OUT_DIR = PACKAGE_DIR / "tests_js" / "fixtures"


def _meta(payload: dict) -> dict:
    report = payload.get("report") or {}
    return {
        "managerGate": payload.get("managerGate"),
        "singleAm": bool(payload.get("singleAm")),
        "singleAmName": payload.get("singleAmName"),
        "amOrder": payload.get("amOrder") or [],
        "archiveDates": [a["d"] for a in report.get("archive") or []],
        "reportDate": report.get("date"),
        "hasTeamGoals": bool(payload.get("teamGoals")),
    }


def _write(name: str, payload: dict) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    html_path = OUT_DIR / f"{name}.html"
    write_am_brief_html(payload, html_path)
    (OUT_DIR / f"{name}.meta.json").write_text(
        json.dumps(_meta(payload), indent=2), encoding="utf-8"
    )
    print(f"  wrote {html_path.name} + meta")


def main() -> None:
    print(f"Building AM Brief render-test fixtures into {OUT_DIR} ...")
    _write("manager", build_manager_payload())
    _write("single_am_coral", build_single_am_payload("Coral"))
    _write("empty_sections_alon", build_empty_sections_payload("Alon"))
    _write("large_tickets", build_large_tickets_payload())
    print("Done.")


if __name__ == "__main__":
    main()
