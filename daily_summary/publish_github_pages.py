"""Publish daily/weekend HTML reports to docs/ for GitHub Pages."""
from __future__ import annotations

import json
import re
import shutil
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = PROJECT_ROOT / "docs"
REPORTS_DIR = DOCS_DIR / "reports"
MANIFEST_PATH = DOCS_DIR / "reports.json"


def _report_meta(filename: str) -> dict:
    weekend = re.match(
        r"^(?P<start>\d{4}-\d{2}-\d{2})_to_(?P<end>\d{4}-\d{2}-\d{2})_elite_weekend_summary_canvas\.html$",
        filename,
    )
    if weekend:
        return {
            "filename": filename,
            "kind": "weekend",
            "title": f"Weekend {weekend.group('start')} to {weekend.group('end')}",
            "date": weekend.group("end"),
            "sort_key": weekend.group("end"),
        }
    daily = re.match(r"^(?P<date>\d{4}-\d{2}-\d{2})_elite_daily_summary_canvas\.html$", filename)
    if daily:
        return {
            "filename": filename,
            "kind": "daily",
            "title": f"Daily {daily.group('date')}",
            "date": daily.group("date"),
            "sort_key": daily.group("date"),
        }
    return {
        "filename": filename,
        "kind": "other",
        "title": filename,
        "date": "",
        "sort_key": "",
    }


def _build_manifest() -> list[dict]:
    if not REPORTS_DIR.exists():
        return []
    entries = [_report_meta(p.name) for p in REPORTS_DIR.glob("*.html")]
    entries.sort(key=lambda e: e["sort_key"], reverse=True)
    return entries


def _write_manifest(entries: list[dict]) -> None:
    MANIFEST_PATH.write_text(json.dumps(entries, indent=2), encoding="utf-8")


def _write_index(entries: list[dict]) -> None:
    latest = entries[0] if entries else None
    latest_href = f"reports/{latest['filename']}" if latest else None
    rows = "\n".join(
        f"""        <tr>
          <td>{e['title']}</td>
          <td><span class="pill {e['kind']}">{e['kind']}</span></td>
          <td><a href="reports/{e['filename']}">Open report</a></td>
        </tr>"""
        for e in entries
    )
    updated = datetime.now().strftime("%Y-%m-%d %H:%M")
    latest_block = (
        f'<p class="lead"><a class="button" href="{latest_href}">Open latest report</a></p>'
        if latest_href
        else '<p class="lead">No reports published yet. Run the morning elite script locally.</p>'
    )
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Elite Daily Summary</title>
  <style>
    :root {{
      --fg: #141414;
      --muted: #5c5c5c;
      --bg: #f7f7f8;
      --card: #ffffff;
      --line: #e6e6e8;
      --accent: #1f8a65;
      --weekend: #3685bf;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
      color: var(--fg);
      background: var(--bg);
      line-height: 1.5;
    }}
    .wrap {{ max-width: 920px; margin: 0 auto; padding: 32px 20px 48px; }}
    h1 {{ margin: 0 0 8px; font-size: 2rem; }}
    .sub {{ color: var(--muted); margin-bottom: 24px; }}
    .card {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 20px 22px;
      margin-bottom: 20px;
    }}
    .lead {{ margin: 0 0 8px; }}
    .button {{
      display: inline-block;
      background: var(--accent);
      color: #fff;
      text-decoration: none;
      padding: 10px 16px;
      border-radius: 8px;
      font-weight: 600;
    }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ text-align: left; padding: 10px 8px; border-bottom: 1px solid var(--line); }}
    th {{ color: var(--muted); font-size: 0.9rem; }}
    a {{ color: #0b57d0; }}
    .pill {{
      display: inline-block;
      font-size: 0.75rem;
      padding: 2px 8px;
      border-radius: 999px;
      background: #e8f5ef;
      color: var(--accent);
      text-transform: capitalize;
    }}
    .pill.weekend {{ background: #e7f1fa; color: var(--weekend); }}
    .foot {{ color: var(--muted); font-size: 0.85rem; margin-top: 16px; }}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>Elite Daily Summary</h1>
    <p class="sub">Published morning reports for the Elite managed book.</p>
    <div class="card">
      {latest_block}
      <p class="foot">Updated {updated}. Sun–Thu reports publish after each local run.</p>
    </div>
    <div class="card">
      <h2 style="margin-top:0">Archive</h2>
      <table>
        <thead>
          <tr><th>Report</th><th>Type</th><th>Link</th></tr>
        </thead>
        <tbody>
{rows if rows else '          <tr><td colspan="3">No reports yet.</td></tr>'}
        </tbody>
      </table>
    </div>
  </div>
</body>
</html>
"""
    (DOCS_DIR / "index.html").write_text(html, encoding="utf-8")


def publish_html(html_path: Path) -> Path | None:
    """Copy report HTML into docs/ and refresh GitHub Pages index."""
    html_path = Path(html_path)
    if not html_path.exists():
        return None

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / ".nojekyll").touch()

    dest = REPORTS_DIR / html_path.name
    shutil.copy2(html_path, dest)
    shutil.copy2(html_path, DOCS_DIR / "latest.html")

    entries = _build_manifest()
    _write_manifest(entries)
    _write_index(entries)
    print(f"Published GitHub Pages: {dest.relative_to(PROJECT_ROOT)}")
    return dest


def seed_baselines() -> None:
    """Copy committed format baselines into docs/ if present."""
    baseline_dir = PROJECT_ROOT / "daily_summary" / "daily_summaries"
    for name in (
        "2026-07-07_elite_daily_summary_canvas.html",
        "2026-07-09_to_2026-07-11_elite_weekend_summary_canvas.html",
    ):
        src = baseline_dir / name
        if src.exists():
            publish_html(src)


if __name__ == "__main__":
    seed_baselines()
