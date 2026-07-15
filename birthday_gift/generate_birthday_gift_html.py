"""Export June birthday gift cohort to standalone HTML."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXPORT_DIR = Path(__file__).resolve().parent / "exports"


def load_players(csv_path: Path) -> list[dict]:
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))

    def pct(val: str) -> float | None:
        return float(val) if val else None

    players = []
    for r in rows:
        players.append(
            {
                "aid": r["AID"],
                "agent": r["Agent"] or "—",
                "ltPurchase": float(r.get("LT Purchase") or 0),
                "hold": r.get("Hold") or "n/a",
                "giftDate": r["Gift date"] or "—",
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


def build_html(players: list[dict], summary: dict[str, dict]) -> str:
    payload = json.dumps({"players": players, "summary": summary}, ensure_ascii=False)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Elite Birthday Gift — June 2026</title>
  <style>
    :root {{
      --bg: #f5f7fa;
      --surface: #fff;
      --text: #1a1d21;
      --muted: #6b7280;
      --stroke: #e2e8f0;
      --before-bg: #eef1f5;
      --before-text: #475569;
      --after-bg: #e8f2fb;
      --after-text: #1d4f7c;
      --pos: #15803d;
      --pos-bg: #dcfce7;
      --neg: #b91c1c;
      --neg-bg: #fee2e2;
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
    h1 {{ margin: 0 0 20px; font-size: 24px; font-weight: 600; }}
    h2 {{ margin: 0 0 12px; font-size: 16px; font-weight: 600; }}
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
    .stat .val {{ font-size: 20px; font-weight: 600; }}
    .stat .detail {{ font-size: 12px; margin-top: 6px; font-weight: 600; }}
    .card {{
      background: var(--surface);
      border: 1px solid var(--stroke);
      border-radius: 10px;
      padding: 16px;
      margin-bottom: 20px;
    }}
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
    th {{ color: var(--muted); font-weight: 600; font-size: 11px; text-transform: uppercase; letter-spacing: 0.03em; background: #f8fafc; }}
    td.num, th.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    tr:hover td {{ background: #f8fafc; }}
    .pos {{ color: var(--pos); }}
    .neg {{ color: var(--neg); }}
    .badge {{
      display: inline-block;
      padding: 4px 10px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 600;
      font-variant-numeric: tabular-nums;
    }}
    .badge-before {{ background: var(--before-bg); color: var(--before-text); }}
    .badge-after {{ background: var(--after-bg); color: var(--after-text); }}
    .badge-pos {{ background: var(--pos-bg); color: var(--pos); }}
    .badge-neg {{ background: var(--neg-bg); color: var(--neg); }}
    .badge-flat {{ background: #f1f5f9; color: var(--muted); }}
    .compare {{
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: 8px;
      flex-wrap: wrap;
    }}
    .arrow {{ color: var(--muted); font-size: 12px; }}
    details {{
      border: 1px solid var(--stroke);
      border-radius: 10px;
      margin-bottom: 10px;
      background: var(--surface);
      overflow: hidden;
    }}
    summary {{
      cursor: pointer;
      padding: 14px 16px;
      font-weight: 600;
      list-style: none;
      display: flex;
      justify-content: space-between;
      gap: 12px;
      flex-wrap: wrap;
      background: #fafbfc;
    }}
    summary::-webkit-details-marker {{ display: none; }}
    summary .meta {{ color: var(--muted); font-weight: 500; font-size: 13px; }}
    details .inner {{ padding: 0 16px 16px; overflow-x: auto; }}
    .th-before {{ background: var(--before-bg) !important; color: var(--before-text) !important; }}
    .th-after {{ background: var(--after-bg) !important; color: var(--after-text) !important; }}
    .td-before {{ background: #f8fafc; }}
    .td-after {{ background: #f0f7ff; }}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>Elite Birthday Gift — June 2026</h1>
    <div class="stats4" id="stats"></div>
    <div class="card">
      <h2>Average before vs after</h2>
      <div class="bars" id="bars"></div>
      <div class="bar-legend">
        <span><span class="dot" style="background:#94a3b8"></span>Before</span>
        <span><span class="dot" style="background:var(--accent)"></span>After</span>
      </div>
    </div>
    <h2>Per-player split</h2>
    <div id="players"></div>
    <h2 style="margin-top:24px">All players</h2>
    <div class="card" style="padding:0; overflow-x:auto">
      <table id="snapshot">
        <thead>
          <tr>
            <th>AID</th><th>Agent</th><th class="num">LT Purchase</th><th class="num">Hold</th>
            <th class="num th-before">Purchase before</th><th class="num th-after">Purchase after</th><th class="num">Change</th>
            <th class="num th-before">Purchases before</th><th class="num th-after">Purchases after</th>
            <th class="num th-before">Active before</th><th class="num th-after">Active after</th>
            <th class="num th-before">SC bets before</th><th class="num th-after">SC bets after</th>
          </tr>
        </thead>
        <tbody></tbody>
      </table>
    </div>
  </div>
  <script>
    const DATA = {payload};

    const fmtMoney = (n) => `$${{Math.round(n).toLocaleString()}}`;
    const fmtNum = (n) => Math.round(n).toLocaleString();
    const fmtPct = (n) => n == null ? "—" : `${{n > 0 ? "+" : ""}}${{n.toFixed(1)}}%`;
    const chgClass = (n) => n == null || n === 0 ? "badge-flat" : n > 0 ? "badge-pos" : "badge-neg";
    const chgTextClass = (n) => n == null || n === 0 ? "" : n > 0 ? "pos" : "neg";

    function compareCell(beforeFmt, afterFmt, pct) {{
      const badge = pct == null ? "badge-flat" : pct > 0 ? "badge-pos" : pct < 0 ? "badge-neg" : "badge-flat";
      return `<div class="compare"><span class="badge badge-before">${{beforeFmt}}</span><span class="arrow">→</span><span class="badge badge-after">${{afterFmt}}</span><span class="badge ${{badge}}">${{fmtPct(pct)}}</span></div>`;
    }}

    const statDefs = [
      ["purchase", "Avg purchase", fmtMoney],
      ["purchases", "Avg purchases", fmtNum],
      ["active", "Avg active days", fmtNum],
      ["bets", "Avg SC bets", fmtMoney],
    ];
    document.getElementById("stats").innerHTML = statDefs.map(([key, label, fmt]) => {{
      const s = DATA.summary[key];
      const cls = chgTextClass(s.avgPct);
      return `<div class="stat"><label>${{label}}</label><div class="val">${{fmt(s.avgBefore)}} <span style="color:var(--muted);font-weight:400">→</span> ${{fmt(s.avgAfter)}}</div><div class="detail ${{cls}}">${{fmtPct(s.avgPct)}}</div></div>`;
    }}).join("");

    const chartKeys = [
      ["purchase", "Purchase", true],
      ["purchases", "Purchases", false],
      ["active", "Active days", false],
      ["bets", "SC bets", true],
    ];
    const maxVal = Math.max(...chartKeys.flatMap(([k]) => [DATA.summary[k].avgBefore, DATA.summary[k].avgAfter]), 1);
    document.getElementById("bars").innerHTML = chartKeys.map(([k, label, money]) => {{
      const s = DATA.summary[k];
      const bH = Math.max(4, (s.avgBefore / maxVal) * 140);
      const aH = Math.max(4, (s.avgAfter / maxVal) * 140);
      const fmt = money ? fmtMoney : fmtNum;
      return `<div class="bar-group"><div class="bar-pair"><div class="bar before" style="height:${{bH}}px" title="Before: ${{fmt(s.avgBefore)}}"></div><div class="bar after" style="height:${{aH}}px" title="After: ${{fmt(s.avgAfter)}}"></div></div><div class="bar-label">${{label}}</div></div>`;
    }}).join("");

    function metricRows(p, money, before, after, diff, pct) {{
      const fmtB = money ? fmtMoney(before) : fmtNum(before);
      const fmtA = money ? fmtMoney(after) : fmtNum(after);
      const fmtD = money ? `${{diff > 0 ? "+" : ""}}${{fmtMoney(diff)}}` : `${{diff > 0 ? "+" : ""}}${{fmtNum(diff)}}`;
      return {{ before: fmtB, after: fmtA, diff: fmtD, pct }};
    }}

    document.getElementById("players").innerHTML = DATA.players.map((p) => {{
      const metrics = [
        ["Purchase amount", metricRows(p, true, p.purchaseBefore, p.purchaseAfter, p.purchaseDiff, p.purchasePct)],
        ["Purchases", metricRows(p, false, p.purchasesBefore, p.purchasesAfter, p.purchasesDiff, p.purchasesPct)],
        ["Active days", metricRows(p, false, p.activeBefore, p.activeAfter, p.activeDiff, p.activePct)],
        ["SC bets", metricRows(p, true, p.betsBefore, p.betsAfter, p.betsDiff, p.betsPct)],
      ];
      return `<details>
        <summary>
          <span>AID ${{p.aid}}</span>
          <span class="meta">${{p.agent}} · LT ${{fmtMoney(p.ltPurchase)}} · Hold ${{p.hold}} · <span class="${{chgTextClass(p.purchasePct)}}">${{fmtPct(p.purchasePct)}} purchase</span></span>
        </summary>
        <div class="inner">
          <table>
            <thead><tr><th>Metric</th><th class="num th-before">Before</th><th class="num th-after">After</th><th class="num">Diff</th><th class="num">Change</th></tr></thead>
            <tbody>
              ${{metrics.map(([name, m]) => `<tr>
                <td>${{name}}</td>
                <td class="num td-before"><span class="badge badge-before">${{m.before}}</span></td>
                <td class="num td-after"><span class="badge badge-after">${{m.after}}</span></td>
                <td class="num ${{chgTextClass(m.pct)}}">${{m.diff}}</td>
                <td class="num"><span class="badge ${{chgClass(m.pct)}}">${{fmtPct(m.pct)}}</span></td>
              </tr>`).join("")}}
            </tbody>
          </table>
        </div>
      </details>`;
    }}).join("");

    document.querySelector("#snapshot tbody").innerHTML = DATA.players.map((p) => `
      <tr>
        <td>${{p.aid}}</td>
        <td>${{p.agent}}</td>
        <td class="num">${{fmtMoney(p.ltPurchase)}}</td>
        <td class="num">${{p.hold}}</td>
        <td class="num td-before"><span class="badge badge-before">${{fmtMoney(p.purchaseBefore)}}</span></td>
        <td class="num td-after"><span class="badge badge-after">${{fmtMoney(p.purchaseAfter)}}</span></td>
        <td class="num"><span class="badge ${{chgClass(p.purchasePct)}}">${{fmtPct(p.purchasePct)}}</span></td>
        <td class="num td-before">${{fmtNum(p.purchasesBefore)}}</td>
        <td class="num td-after">${{fmtNum(p.purchasesAfter)}}</td>
        <td class="num td-before">${{fmtNum(p.activeBefore)}}</td>
        <td class="num td-after">${{fmtNum(p.activeAfter)}}</td>
        <td class="num td-before">${{fmtMoney(p.betsBefore)}}</td>
        <td class="num td-after">${{fmtMoney(p.betsAfter)}}</td>
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
    out_path.write_text(build_html(players, summary), encoding="utf-8")
    print(out_path)


if __name__ == "__main__":
    main()
