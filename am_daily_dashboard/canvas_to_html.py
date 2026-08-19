"""Export Elite AM Brief payload to standalone HTML matching canvas design."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from elite_lib import write_html_shell  # noqa: E402
from elite_lib.export_paths import mirror_to_cursor  # noqa: E402

SHELL = PACKAGE_DIR / "handoffs" / "elite_am_brief_web.html"
OUT_DIR = PACKAGE_DIR / "exports"

DATED_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})_elite_am_brief(?:_([a-z]+))?\.html$")
SLUG_RE = re.compile(r"^(?:\d{4}-\d{2}-\d{2}_)?elite_am_brief(?:_([a-z]+))?\.html$")


def audience_slug(out_path: Path, payload: dict | None = None) -> str:
    """Which audience a brief is for: "" is the manager, else that AM's slug.

    The payload decides, not the filename: `strip_payload_for_am` marks a
    single-AM file, and an `--out` name chosen by the caller carries no
    audience. Getting this wrong hands an AM the manager's archive, and those
    dated manager files contain every AM's data.
    """
    if payload is not None:
        if not payload.get("singleAm"):
            return ""
        name = payload.get("singleAmName") or ""
        if not name:
            agents = payload.get("agents") or []
            name = (agents[0] or {}).get("agentName", "") if agents else ""
        if name:
            return str(name).strip().lower()
    m = SLUG_RE.match(Path(out_path).name)
    return (m.group(1) or "") if m else ""


def archive_entries(slug: str = "", report_date: str = "") -> list[dict[str, str]]:
    """Dates that already have a brief HTML on disk, for the calendar control.

    Built by listing the export folder rather than by walking back N days: the
    board is not generated every day (Fri/Sat are skipped, and runs get missed),
    so any date we compute rather than observe risks a dead link. `slug` selects
    the audience — an AM must never be offered a day their own file does not
    exist for.
    """
    seen: dict[str, str] = {}
    if OUT_DIR.exists():
        for path in OUT_DIR.glob("*_elite_am_brief*.html"):
            m = DATED_RE.match(path.name)
            if m and (m.group(2) or "") == slug:
                seen[m.group(1)] = path.name
    if report_date:
        seen[report_date] = (
            f"{report_date}_elite_am_brief{f'_{slug}' if slug else ''}.html"
        )
    return [{"d": d, "f": seen[d]} for d in sorted(seen)]


def with_archive(payload: dict, slug: str = "") -> dict:
    """Copy of the payload whose report carries the archive list for `slug`."""
    report = dict(payload.get("report") or {})
    report["archive"] = archive_entries(slug, str(report.get("date") or ""))
    return {**payload, "report": report}


def write_am_brief_html(payload: dict, out_path: Path) -> Path:
    """Inject payload into the interactive web shell and write HTML.

    The archive calendar is attached here rather than by each caller, so a
    standalone refresh from JSON produces the same navigable file as a full
    generator run. An archive already on the payload is left alone.
    """
    if not (payload.get("report") or {}).get("archive"):
        payload = with_archive(payload, audience_slug(out_path, payload))
    return write_html_shell(SHELL, payload, out_path, json_default=str)


def publish_am_brief(html_path: Path) -> Path | None:
    """Opt-in: copy AM Brief HTML into docs/ (local review is the default)."""
    sys.path.insert(0, str(PROJECT_ROOT / "daily_summary"))
    try:
        from publish_github_pages import publish_html

        return publish_html(html_path)
    except Exception as exc:
        print(f"GitHub Pages publish skipped: {exc}")
        return None


def convert(payload_path: Path, out_path: Path | None = None) -> Path:
    payload = json.loads(Path(payload_path).read_text(encoding="utf-8"))
    report = payload.get("report") or {}
    date_key = report.get("date", "unknown")
    # Keep a per-AM payload on its own filename. Defaulting every refresh to the
    # manager name would overwrite the manager brief with one AM's data.
    stem = Path(payload_path).stem
    default_name = (
        f"{stem}.html"
        if SLUG_RE.match(f"{stem}.html")
        else f"{date_key}_elite_am_brief.html"
    )
    out = out_path or OUT_DIR / default_name
    return write_am_brief_html(payload, out)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Elite AM Brief HTML from payload JSON (canvas-matched shell)"
    )
    parser.add_argument(
        "payload",
        type=Path,
        nargs="?",
        help="Payload JSON path (e.g. exports/YYYY-MM-DD_elite_am_brief.json)",
    )
    parser.add_argument(
        "--payload",
        dest="payload_opt",
        type=Path,
        help="Payload JSON path",
    )
    parser.add_argument("--out", type=Path, help="Output HTML path")
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Copy HTML into docs/ for GitHub Pages (off by default; local review only)",
    )
    args = parser.parse_args()
    payload_path = args.payload_opt or args.payload
    if not payload_path:
        raise SystemExit("Provide payload JSON path")
    if not payload_path.exists():
        raise SystemExit(f"Payload not found: {payload_path}")
    try:
        out = convert(payload_path, out_path=args.out)
    except Exception as exc:
        print(f"HTML canvas export failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    print(out)
    mirror_to_cursor("am_brief", out, payload_path)
    if args.publish:
        publish_am_brief(out)


if __name__ == "__main__":
    main()
