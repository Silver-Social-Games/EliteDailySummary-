"""Export elite-daily-summary canvas to standalone HTML (Chrome) matching Cursor canvas design."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

CANVAS_DIR = Path(
    r"C:\Users\Owner\.cursor\projects\c-Users-Owner-Downloads-Elite\canvases"
)
OUT_DIR = Path(__file__).resolve().parent / "daily_summaries"
SHELL = Path(__file__).resolve().parent / "handoffs" / "elite_daily_summary_web.html"


def extract_const_json(text: str, marker: str) -> object:
    start = text.index(marker) + len(marker)
    while start < len(text) and text[start] in " \n":
        start += 1
    if text[start] not in "{[":
        raise ValueError(f"Expected JSON after {marker}")
    opener = text[start]
    closer = "}" if opener == "{" else "]"
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
            continue
        if ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0:
                return json.loads(text[start : i + 1])
    raise ValueError(f"Unclosed JSON for {marker}")


def extract_titles(text: str) -> dict:
    m = re.search(r"const TITLES = (\{.*?\});", text, re.DOTALL)
    return json.loads(m.group(1)) if m else {}


def latest_canvas() -> Path:
    files = sorted(CANVAS_DIR.glob("elite-daily-summary-*.canvas.tsx"), reverse=True)
    if not files:
        raise FileNotFoundError(f"No canvas in {CANVAS_DIR}")
    return files[0]


def build_payload(canvas_path: Path) -> dict:
    text = canvas_path.read_text(encoding="utf-8")
    report = extract_const_json(text, "const REPORT = ")
    if report.get("mode") == "weekend":
        day_blocks = extract_const_json(text, "const DAY_BLOCKS = ")
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "decline_check"))
        from wow_drop_reason import format_agent_name, format_urgency_legend_one_line

        try:
            agent_options = extract_const_json(
                text, "const AGENT_OPTIONS: { value: string; label: string }[] = "
            )
        except ValueError:
            tags = sorted(
                {p["agent"] for block in day_blocks for p in block["players"] if p.get("agent")}
            )
            agent_options = [
                {"value": tag, "label": format_agent_name({"agent": tag})} for tag in tags
            ]

        return {
            "report": report,
            "dayBlocks": day_blocks,
            "agentOptions": agent_options,
            "urgencyLegend": format_urgency_legend_one_line(),
        }

    segments = extract_const_json(text, "const SEGMENTS: SegmentRow[] = ")
    players = extract_const_json(text, "const TOP10: PlayerRow[] = ")
    titles = extract_titles(text)
    try:
        agents = extract_const_json(text, "const AGENTS: string[] = ")
    except ValueError:
        agents = sorted({p["agent"] for p in players})
    weekday = report.get("weekday", "")
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "decline_check"))
    from wow_drop_reason import format_urgency_legend_one_line

    return {
        "report": report,
        "segments": segments,
        "players": players,
        "titles": titles,
        "agents": agents,
        "dayShort": weekday[:3] if weekday else "",
        "urgencyLegend": format_urgency_legend_one_line(),
    }


def convert(canvas_path: Path, out_path: Path | None = None) -> Path:
    if not SHELL.exists():
        raise FileNotFoundError(f"Web shell missing: {SHELL}")
    payload = build_payload(canvas_path)
    report = payload["report"]
    if report.get("mode") == "weekend":
        slug = f"{report['dateStart']}_to_{report['dateEnd']}"
        out = out_path or OUT_DIR / f"{slug}_elite_weekend_summary_canvas.html"
    else:
        date_key = report.get("date", "unknown")
        out = out_path or OUT_DIR / f"{date_key}_elite_daily_summary_canvas.html"
    html = SHELL.read_text(encoding="utf-8").replace(
        "__PAYLOAD_JSON__",
        json.dumps(payload, ensure_ascii=False),
    )
    out.write_text(html, encoding="utf-8")
    return out


def export_for_canvas(canvas_path: Path, out_path: Path | None = None) -> Path | None:
    try:
        out = convert(canvas_path, out_path=out_path)
        print(f"Wrote {out}")
        return out
    except Exception as exc:
        print(f"HTML canvas export skipped: {exc}", file=sys.stderr)
        return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="YYYY-MM-DD")
    parser.add_argument("--canvas", type=Path)
    args = parser.parse_args()

    if args.canvas:
        canvas = args.canvas
    elif args.date:
        canvas = CANVAS_DIR / f"elite-daily-summary-{args.date}.canvas.tsx"
    else:
        canvas = latest_canvas()

    if not canvas.exists():
        raise SystemExit(f"Canvas not found: {canvas}")

    print(convert(canvas))


if __name__ == "__main__":
    main()
