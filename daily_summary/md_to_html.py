"""Convert daily summary markdown to a standalone HTML file."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import markdown
except ImportError:
    print("Install: pip install markdown", file=sys.stderr)
    raise SystemExit(1)

SUMMARY_DIR = Path(__file__).resolve().parent / "daily_summaries"

HTML_SHELL = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    body {{ font-family: system-ui, -apple-system, sans-serif; max-width: 1280px; margin: 2rem auto; padding: 0 1rem; line-height: 1.5; color: #111; }}
    table {{ border-collapse: collapse; width: 100%; font-size: 0.82rem; margin: 1rem 0; }}
    th, td {{ border: 1px solid #ccc; padding: 6px 8px; text-align: left; vertical-align: top; }}
    th {{ background: #f0f0f0; position: sticky; top: 0; }}
    tr:nth-child(even) {{ background: #fafafa; }}
    h1 {{ font-size: 1.45rem; margin-bottom: 0.25rem; }}
    h2 {{ margin-top: 2rem; font-size: 1.15rem; border-bottom: 1px solid #ddd; padding-bottom: 0.25rem; }}
    p em, li em {{ color: #444; font-size: 0.9rem; }}
    code {{ background: #f4f4f4; padding: 0.1rem 0.35rem; border-radius: 3px; }}
  </style>
</head>
<body>
{body}
</body>
</html>
"""


def latest_summary() -> Path:
    files = sorted(SUMMARY_DIR.glob("*_elite_daily_summary.md"), reverse=True)
    if not files:
        raise FileNotFoundError(f"No summaries in {SUMMARY_DIR}")
    return files[0]


def convert(md_path: Path, out_path: Path | None = None) -> Path:
    out = out_path or md_path.with_suffix(".html")
    text = md_path.read_text(encoding="utf-8")
    body = markdown.markdown(text, extensions=["tables", "fenced_code"])
    title = md_path.stem.replace("_", " ")
    out.write_text(HTML_SHELL.format(title=title, body=body), encoding="utf-8")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert Elite daily summary .md to .html")
    parser.add_argument("--date", help="Report date YYYY-MM-DD (default: latest file)")
    parser.add_argument("--input", type=Path, help="Explicit .md path")
    args = parser.parse_args()

    if args.input:
        md_path = args.input
    elif args.date:
        md_path = SUMMARY_DIR / f"{args.date}_elite_daily_summary.md"
    else:
        md_path = latest_summary()

    if not md_path.exists():
        raise SystemExit(f"Not found: {md_path}")

    out = convert(md_path)
    print(out)


if __name__ == "__main__":
    main()
