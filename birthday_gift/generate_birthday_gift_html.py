"""Export birthday gift AID cohort to standalone HTML (canvas-parity layout)."""
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXPORT_DIR = Path(__file__).resolve().parent / "exports"

DEFAULT_LOOKER_ACCOUNT_PORTAL_URL = (
    "https://lookerpatrianna.cloud.looker.com/dashboards/5207?Account+ID+={aid}"
)


def looker_account_portal_url(aid: object) -> str:
    aid_s = str(aid or "").strip()
    if not aid_s:
        return ""
    template = os.environ.get(
        "LOOKER_ACCOUNT_PORTAL_URL", DEFAULT_LOOKER_ACCOUNT_PORTAL_URL
    )
    return template.format(aid=aid_s, account_id=aid_s)


def load_players(csv_path: Path) -> list[dict]:
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))

    def pct(val: str) -> float | None:
        return float(val) if val else None

    players = []
    for r in rows:
        aid = r["AID"]
        players.append(
            {
                "aid": aid,
                "aidUrl": looker_account_portal_url(aid),
                "agent": r["Agent"] or "—",
                "ltPurchase": float(r.get("LT Purchase") or 0),
                "hold": r.get("Hold") or "n/a",
                "giftDate": r.get("Gift date") or "—",
                "beforeFrom": r.get("Before from") or "",
                "beforeTo": r.get("Before to") or "",
                "afterFrom": r.get("After from") or "",
                "afterTo": r.get("After to") or "",
                "purchaseBefore": float(r["Before — Purchase amount ($)"]),
                "purchaseAfter": float(r["After — Purchase amount ($)"]),
                "purchaseDiff": float(r["Diff — Purchase amount ($)"]),
                "purchasePct": pct(r["% change — Purchase amount ($)"]),
                "purchasesBefore": float(r["Before — Number of purchases"]),
                "purchasesAfter": float(r["After — Number of purchases"]),
                "purchasesDiff": float(r["Diff — Number of purchases"]),
                "purchasesPct": pct(r["% change — Number of purchases"]),
                "activeBefore": float(r["Before — Active days"]),
                "activeAfter": float(r["After — Active days"]),
                "activeDiff": float(r["Diff — Active days"]),
                "activePct": pct(r["% change — Active days"]),
                "betsBefore": float(r["Before — Total SC bets"]),
                "betsAfter": float(r["After — Total SC bets"]),
                "betsDiff": float(r["Diff — Total SC bets"]),
                "betsPct": pct(r["% change — Total SC bets"]),
            }
        )
    players.sort(
        key=lambda p: (
            -(p["purchasePct"] if p["purchasePct"] is not None else float("-inf")),
            -p["purchaseAfter"],
            p["aid"],
        )
    )
    return players


def load_summary(path: Path) -> dict[str, dict]:
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    key_map = {
        "Purchase amount ($)": "purchase",
        "Number of purchases": "purchases",
        "Active days": "active",
        "Total SC bets": "bets",
    }
    out: dict[str, dict] = {}
    for r in rows:
        out[key_map[r["Metric"]]] = {
            "label": r["Metric"],
            "avgBefore": float(r["Avg before"]),
            "avgAfter": float(r["Avg after"]),
            "avgDiff": float(r["Avg diff"]),
            "avgPct": float(r["Avg % change"]) if r.get("Avg % change") else None,
            "players": int(r["Players"]),
        }
    return out


def periods_from_players(players: list[dict]) -> dict[str, str]:
    if not players:
        return {
            "beforeFrom": "",
            "beforeTo": "",
            "afterFrom": "",
            "afterTo": "",
        }
    p0 = players[0]
    return {
        "beforeFrom": str(p0.get("beforeFrom") or ""),
        "beforeTo": str(p0.get("beforeTo") or ""),
        "afterFrom": str(p0.get("afterFrom") or ""),
        "afterTo": str(p0.get("afterTo") or ""),
    }


def build_html(
    players: list[dict],
    summary: dict[str, dict],
    periods: dict[str, str],
    title: str,
) -> str:
    subtitle = (
        f"Before {periods.get('beforeFrom', '')} to {periods.get('beforeTo', '')} · "
        f"After {periods.get('afterFrom', '')} to {periods.get('afterTo', '')}"
        f" · n={len(players)}"
    )
    payload = json.dumps(
        {"players": players, "summary": summary, "periods": periods, "title": title},
        ensure_ascii=False,
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title}</title>
  <style>
    :root {{
      --bg: #f5f7fa;
      --surface: #fff;
      --text: #1a1d21;
      --muted: #6b7280;
      --stroke: #e2e8f0;
      --pos: #15803d;
      --neg: #b91c1c;
      --accent: #2563eb;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
      font-size: 14px;
      line-height: 1.45;
    }}
    .wrap {{ max-width: 1280px; margin: 0 auto; padding: 24px; }}
    h1 {{ margin: 0 0 8px; font-size: 24px; font-weight: 600; }}
    .sub {{ color: var(--muted); margin: 0 0 20px; font-size: 13px; }}
    h2 {{ margin: 0 0 8px; font-size: 16px; font-weight: 600; }}
    .section-note {{ color: var(--muted); margin: 0 0 12px; font-size: 13px; }}
    .stats4 {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 20px;
    }}
    @media (max-width: 900px) {{ .stats4 {{ grid-template-columns: repeat(2, 1fr); }} }}
    .stat {{
      background: var(--surface);
      border: 1px solid var(--stroke);
      border-radius: 10px;
      padding: 14px;
    }}
    .stat label {{ display: block; color: var(--muted); font-size: 12px; margin-bottom: 6px; }}
    .stat .val {{ font-size: 18px; font-weight: 600; }}
    .stat .detail {{ font-size: 12px; margin-top: 6px; font-weight: 600; }}
    .card {{
      background: var(--surface);
      border: 1px solid var(--stroke);
      border-radius: 10px;
      padding: 16px;
      margin-bottom: 20px;
    }}
    .card-head {{
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      gap: 12px;
      margin-bottom: 12px;
    }}
    .card-head h2 {{ margin: 0; }}
    .card-head .n {{ color: var(--muted); font-size: 13px; }}
    .bars {{
      display: flex; gap: 28px; align-items: flex-end; height: 200px;
      padding-top: 8px; justify-content: center; flex-wrap: wrap;
    }}
    .bar-group {{ display: flex; flex-direction: column; align-items: center; gap: 8px; min-width: 88px; }}
    .bar-pair {{ display: flex; gap: 10px; align-items: flex-end; height: 160px; }}
    .bar {{ width: 34px; border-radius: 6px 6px 0 0; min-height: 4px; }}
    .bar.before {{ background: #94a3b8; }}
    .bar.after {{ background: var(--accent); }}
    .bar-label {{ color: var(--muted); font-size: 12px; text-align: center; }}
    .bar-legend {{ display: flex; gap: 20px; margin-top: 12px; font-size: 12px; color: var(--muted); justify-content: center; }}
    .dot {{ display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 6px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th, td {{ padding: 10px 12px; border-bottom: 1px solid var(--stroke); text-align: left; vertical-align: middle; }}
    th {{ color: var(--muted); font-weight: 600; font-size: 11px; text-transform: uppercase; letter-spacing: 0.03em; background: #f8fafc; position: sticky; top: 0; }}
    td.num, th.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    tbody tr:nth-child(even) td {{ background: #fafbfc; }}
    tr:hover td {{ background: #f1f5f9; }}
    .pos {{ color: var(--pos); font-weight: 700; }}
    .neg {{ color: var(--neg); font-weight: 700; }}
    a.aid {{ color: var(--accent); text-decoration: none; font-weight: 600; }}
    a.aid:hover {{ text-decoration: underline; }}
    .table-card {{ padding: 0; overflow-x: auto; }}
  </style>
</head>
<body>
  <div class="wrap">
    <h1 id="title"></h1>
    <p class="sub" id="subtitle"></p>
    <div class="stats4" id="stats"></div>
    <div class="card">
      <div class="card-head">
        <h2>Average Before vs After</h2>
        <span class="n" id="chart-n"></span>
      </div>
      <div class="bars" id="bars"></div>
      <div class="bar-legend">
        <span><span class="dot" style="background:#94a3b8"></span>Before</span>
        <span><span class="dot" style="background:var(--accent)"></span>After</span>
      </div>
    </div>
    <h2>Player Data</h2>
    <p class="section-note" id="player-note"></p>
    <div class="card table-card">
      <table id="players">
        <thead>
          <tr>
            <th>AID</th>
            <th>AM</th>
            <th class="num">LT Purchase</th>
            <th class="num">Hold</th>
            <th class="num">Purchase</th>
            <th class="num">Purchases</th>
            <th class="num">Active Days</th>
            <th class="num">SC Bets</th>
            <th class="num">% Purchase</th>
          </tr>
        </thead>
        <tbody></tbody>
      </table>
    </div>
  </div>
  <script>
    const DATA = {payload};

    const fmtMoney = (n) => `$${{Math.round(n).toLocaleString()}}`;
    const fmtInt = (n) => Math.round(n).toLocaleString();
    const fmtPct = (n) => n == null ? "-" : `${{n > 0 ? "+" : ""}}${{n.toFixed(1)}}%`;
    const chgClass = (n) => n == null || n === 0 ? "" : n > 0 ? "pos" : "neg";
    const pairMoney = (a, b) => `${{fmtMoney(a)}} - ${{fmtMoney(b)}}`;
    const pairInt = (a, b) => `${{fmtInt(a)}} - ${{fmtInt(b)}}`;
    const aidCell = (p) => p.aidUrl
      ? `<a class="aid" href="${{p.aidUrl}}" target="_blank" rel="noopener noreferrer">${{p.aid}}</a>`
      : p.aid;

    document.getElementById("title").textContent = DATA.title;
    document.getElementById("subtitle").textContent =
      `Before ${{DATA.periods.beforeFrom}} to ${{DATA.periods.beforeTo}} · After ${{DATA.periods.afterFrom}} to ${{DATA.periods.afterTo}} · n=${{DATA.players.length}}`;
    document.getElementById("chart-n").textContent = `n=${{DATA.summary.purchase.players}}`;
    document.getElementById("player-note").textContent =
      `${{DATA.players.length}} player${{DATA.players.length === 1 ? "" : "s"}} · values shown as before - after · sorted by purchase % (high → low)`;

    const statDefs = [
      ["purchase", "Avg Purchase", fmtMoney],
      ["purchases", "Avg Purchases", fmtInt],
      ["active", "Avg Active Days", fmtInt],
      ["bets", "Avg SC Bets", fmtMoney],
    ];
    document.getElementById("stats").innerHTML = statDefs.map(([key, label, fmt]) => {{
      const s = DATA.summary[key];
      return `<div class="stat"><label>${{label}}</label><div class="val">${{fmt(s.avgBefore)}} - ${{fmt(s.avgAfter)}}</div><div class="detail ${{chgClass(s.avgPct)}}">${{fmtPct(s.avgPct)}}</div></div>`;
    }}).join("");

    const chartKeys = [
      ["purchase", "Purchase ($)", true],
      ["purchases", "Purchases", false],
      ["active", "Active Days", false],
      ["bets", "SC Bets", true],
    ];
    const maxVal = Math.max(...chartKeys.flatMap(([k]) => [DATA.summary[k].avgBefore, DATA.summary[k].avgAfter]), 1);
    document.getElementById("bars").innerHTML = chartKeys.map(([k, label, money]) => {{
      const s = DATA.summary[k];
      const bH = Math.max(4, (s.avgBefore / maxVal) * 140);
      const aH = Math.max(4, (s.avgAfter / maxVal) * 140);
      const fmt = money ? fmtMoney : fmtInt;
      return `<div class="bar-group"><div class="bar-pair"><div class="bar before" style="height:${{bH}}px" title="Before: ${{fmt(s.avgBefore)}}"></div><div class="bar after" style="height:${{aH}}px" title="After: ${{fmt(s.avgAfter)}}"></div></div><div class="bar-label">${{label}}</div></div>`;
    }}).join("");

    document.querySelector("#players tbody").innerHTML = DATA.players.map((p) => `
      <tr>
        <td>${{aidCell(p)}}</td>
        <td>${{p.agent}}</td>
        <td class="num">${{fmtMoney(p.ltPurchase)}}</td>
        <td class="num">${{p.hold}}</td>
        <td class="num">${{pairMoney(p.purchaseBefore, p.purchaseAfter)}}</td>
        <td class="num">${{pairInt(p.purchasesBefore, p.purchasesAfter)}}</td>
        <td class="num">${{pairInt(p.activeBefore, p.activeAfter)}}</td>
        <td class="num">${{pairMoney(p.betsBefore, p.betsAfter)}}</td>
        <td class="num ${{chgClass(p.purchasePct)}}">${{fmtPct(p.purchasePct)}}</td>
      </tr>
    `).join("");
  </script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Export birthday gift cohort to HTML")
    parser.add_argument(
        "--input",
        default="birthday_gift/exports/birthday_gift_activity_june_2026_cohort.csv",
    )
    parser.add_argument("--output", default=None)
    parser.add_argument(
        "--title",
        default=None,
        help="Report title (defaults from input stem)",
    )
    args = parser.parse_args()

    csv_path = Path(args.input)
    if not csv_path.is_absolute():
        csv_path = ROOT / csv_path
    summary_path = csv_path.with_name(csv_path.stem + "_summary.csv")
    out_path = Path(args.output) if args.output else csv_path.with_suffix(".html")
    if not out_path.is_absolute():
        out_path = ROOT / out_path

    players = load_players(csv_path)
    summary = load_summary(summary_path)
    periods = periods_from_players(players)
    title = args.title or (
        "Birthday Gift Activity - "
        + csv_path.stem.replace("birthday_gift_activity_", "").replace("_", " ")
    )
    out_path.write_text(
        build_html(players, summary, periods=periods, title=title),
        encoding="utf-8",
    )
    print(out_path)


if __name__ == "__main__":
    main()
