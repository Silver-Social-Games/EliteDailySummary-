"""Export Elite AM Brief payload to standalone HTML matching canvas design."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
SHELL = PACKAGE_DIR / "handoffs" / "elite_am_brief_web.html"
OUT_DIR = PACKAGE_DIR / "exports"


def write_am_brief_html(payload: dict, out_path: Path) -> Path:
    """Inject payload into the interactive web shell and write HTML."""
    if not SHELL.exists():
        raise FileNotFoundError(f"Web shell missing: {SHELL}")
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    html = SHELL.read_text(encoding="utf-8").replace(
        "__PAYLOAD_JSON__",
        json.dumps(payload, ensure_ascii=False, default=str),
    )
    if "__PAYLOAD_JSON__" in html:
        raise RuntimeError("Payload placeholder still present after replace")
    out.write_text(html, encoding="utf-8")
    return out


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


if __name__ == "__main__":
    main()
