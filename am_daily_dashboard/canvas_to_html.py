"""Export Elite AM Brief payload to standalone HTML matching canvas design."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from elite_lib import render_html_shell  # noqa: E402
from elite_lib.export_paths import mirror_to_cursor  # noqa: E402
from mirror_am_brief import mirror_am_brief_to_cursor  # noqa: E402
from payload_builders import strip_bonus_lookup_for_payload  # noqa: E402

SHELL = PACKAGE_DIR / "handoffs" / "elite_am_brief_web.html"
OUT_DIR = PACKAGE_DIR / "exports"
VERIFIED_DIR = OUT_DIR / "verified"

DATED_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})_elite_am_brief(?:_([a-z]+))?\.html$")
JSON_DATED_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})_elite_am_brief(?:_([a-z]+))?\.json$")
SLUG_RE = re.compile(r"^(?:\d{4}-\d{2}-\d{2}_)?elite_am_brief(?:_([a-z]+))?\.html$")


def audience_slug(out_path: Path, payload: dict | None = None) -> str:
    """Which audience a brief is for: "" is the manager, else that AM's slug.

    The payload decides, not the filename: `strip_payload_for_am` marks a
    single-AM file, and an `--out` name chosen by the caller carries no
    audience. Getting this wrong hands an AM the manager's archive, and those
    dated manager files contain every AM's data.
    """
    if payload is not None:
        explicit = str(payload.get("audienceSlug") or "").strip().lower()
        if explicit:
            return explicit
        if payload.get("singleAm"):
            name = payload.get("singleAmName") or ""
            if not name:
                agents = payload.get("agents") or []
                name = (agents[0] or {}).get("agentName", "") if agents else ""
            if name:
                return str(name).strip().lower()
        if not payload.get("peerMode"):
            return ""
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


def all_brief_export_html() -> list[Path]:
    """Every dated and dateless brief HTML under exports/."""
    if not OUT_DIR.exists():
        return []
    return sorted(OUT_DIR.glob("*elite_am_brief*.html"))


def mirror_brief_exports_to_cursor() -> list[Path]:
    """Copy the full brief export set to Elite_Cursor AM Brief.

    html-only and archive refresh rewrite files in exports/ but previously
    only mirrored the current run's paths, leaving older dated copies in
    Elite_Cursor with stale archive calendars.
    """
    paths = all_brief_export_html()
    if paths:
        mirror_am_brief_to_cursor(*paths)
    return paths


def _load_bonus_lookup_for_date(report_date: str) -> dict | None:
    path = OUT_DIR / f"{report_date}_elite_bonus_lookup.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def refresh_all_brief_archives(*, mirror: bool = False) -> list[Path]:
    """Re-embed archive lists in saved briefs whose calendar is stale.

    Each dated HTML is written with whatever exports existed at generate time.
    After a new day is added, older files still point at a stale archive unless
    we rewrite them from their saved JSON. Skips files whose archive list is
    already current so a new run does not rewrite every historical export.

    Returns every HTML path rewritten so callers can mirror them to Elite_Cursor.
    """
    if not OUT_DIR.exists():
        return []
    refreshed: list[Path] = []
    mirror_paths: list[Path] = []
    for json_path in sorted(OUT_DIR.glob("*_elite_am_brief*.json")):
        m = JSON_DATED_RE.match(json_path.name)
        if not m:
            continue
        slug = m.group(2) or ""
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        report_date = str((payload.get("report") or {}).get("date") or m.group(1))
        report = dict(payload.get("report") or {})
        new_archive = archive_entries(slug, report_date)
        json_changed = (report.get("archive") or []) != new_archive
        if json_changed:
            report["archive"] = new_archive
            payload = {**payload, "report": report}
            json_path.write_text(
                json.dumps(payload, indent=2, default=str),
                encoding="utf-8",
            )
        html_path = json_path.with_suffix(".html")
        # Sidecar is always YYYY-MM-DD_elite_bonus_lookup.json — never slugged.
        full_lookup = _load_bonus_lookup_for_date(report_date)
        scoped = (
            strip_bonus_lookup_for_payload(payload, full_lookup)
            if full_lookup
            else None
        )
        write_am_brief_html(payload, html_path, bonus_lookup=scoped)
        refreshed.append(html_path)
        mirror_paths.extend([html_path, json_path])
    if mirror and mirror_paths:
        mirror_am_brief_to_cursor(*mirror_paths)
    # Dateless bookmarks: rebuild from the newest dated JSON per audience.
    latest_by_slug: dict[str, dict] = {}
    for json_path in sorted(OUT_DIR.glob("*_elite_am_brief*.json")):
        m = JSON_DATED_RE.match(json_path.name)
        if not m:
            continue
        slug = m.group(2) or ""
        report_date = m.group(1)
        prev = latest_by_slug.get(slug)
        if prev and prev["_date"] >= report_date:
            continue
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        latest_by_slug[slug] = {"_date": report_date, "payload": payload}
    for slug, item in latest_by_slug.items():
        name = f"elite_am_brief{f'_{slug}' if slug else ''}.html"
        html_path = OUT_DIR / name
        scoped = None
        full_lookup = _load_bonus_lookup_for_date(item["_date"])
        if full_lookup:
            scoped = strip_bonus_lookup_for_payload(item["payload"], full_lookup)
        write_am_brief_html(item["payload"], html_path, bonus_lookup=scoped)
        refreshed.append(html_path)
    if refreshed:
        print(f"  Refreshed archive calendar on {len(refreshed)} saved brief(s)")
    return refreshed


def snapshot_verified_exports(report_date: str) -> list[Path]:
    """Copy dated JSON payloads to exports/verified/ after verify PASS.

    JSON is the source of truth for a report day. HTML is rebuilt from it.
    These copies are the recovery point when a later chat run overwrites the
    working export — git does not track exports/.
    """
    VERIFIED_DIR.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    for json_path in sorted(OUT_DIR.glob(f"{report_date}_elite_am_brief*.json")):
        dst = VERIFIED_DIR / json_path.name
        shutil.copy2(json_path, dst)
        copied.append(dst)
    if copied:
        stamp = VERIFIED_DIR / f"{report_date}_verified.txt"
        stamp.write_text(
            f"verified_at={datetime.now(timezone.utc).isoformat()}\n"
            f"files={len(copied)}\n",
            encoding="utf-8",
        )
        print(f"  Verified snapshot: {len(copied)} JSON file(s) in {VERIFIED_DIR.name}/")
    return copied


def restore_verified_exports(report_date: str) -> list[Path]:
    """Restore working exports/ JSON from exports/verified/ for one report date."""
    restored: list[Path] = []
    for src in sorted(VERIFIED_DIR.glob(f"{report_date}_elite_am_brief*.json")):
        dst = OUT_DIR / src.name
        shutil.copy2(src, dst)
        restored.append(dst)
    if not restored:
        raise SystemExit(
            f"No verified snapshot for {report_date} in {VERIFIED_DIR}.\n"
            "Run verify_brief after a good generate to create one."
        )
    print(f"Restored {len(restored)} JSON file(s) from verified/")
    return restored


def with_archive(payload: dict, slug: str = "") -> dict:
    """Copy of the payload whose report carries the archive list for `slug`."""
    report = dict(payload.get("report") or {})
    report["archive"] = archive_entries(slug, str(report.get("date") or ""))
    return {**payload, "report": report}


BONUS_LOOKUP_PLACEHOLDER = "__BONUS_LOOKUP_JSON__"


def write_am_brief_html(
    payload: dict,
    out_path: Path,
    bonus_lookup: dict | None = None,
) -> Path:
    """Inject payload into the interactive web shell and write HTML.

    The archive calendar is always rebuilt for this file's audience so a stale
    manager list can never survive into a per-AM export. When ``bonus_lookup``
    is provided, the second ``#am-brief-lookup`` script block is filled too.
    """
    payload = with_archive(payload, audience_slug(out_path, payload))
    html = render_html_shell(SHELL, payload, json_default=str)
    lookup_json = json.dumps(
        bonus_lookup if bonus_lookup is not None else {"rows": []},
        ensure_ascii=False,
        default=str,
    ).replace("</", "<\\/")
    if BONUS_LOOKUP_PLACEHOLDER not in html:
        raise RuntimeError(
            f"Web shell missing {BONUS_LOOKUP_PLACEHOLDER} — rebuild web/ first."
        )
    html = html.replace(BONUS_LOOKUP_PLACEHOLDER, lookup_json)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return out


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
    report_date = str((payload.get("report") or {}).get("date") or date_key)
    full_lookup = _load_bonus_lookup_for_date(report_date)
    scoped = (
        strip_bonus_lookup_for_payload(payload, full_lookup)
        if full_lookup
        else None
    )
    return write_am_brief_html(payload, out, bonus_lookup=scoped)


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
    mirror_am_brief_to_cursor(out, payload_path)
    if args.publish:
        publish_am_brief(out)


if __name__ == "__main__":
    main()
