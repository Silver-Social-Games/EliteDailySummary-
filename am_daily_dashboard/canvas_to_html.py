"""Export Elite AM Brief payload to standalone HTML matching canvas design."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from elite_lib import write_html_shell  # noqa: E402

SHELL = PACKAGE_DIR / "handoffs" / "elite_am_brief_web.html"
OUT_DIR = PACKAGE_DIR / "exports"


def write_am_brief_html(payload: dict, out_path: Path) -> Path:
    """Inject payload into the interactive web shell and write HTML."""
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
    out = out_path or OUT_DIR / f"{date_key}_elite_am_brief.html"
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
    if args.publish:
        publish_am_brief(out)


if __name__ == "__main__":
    main()
