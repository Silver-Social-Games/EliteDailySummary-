"""
Q2 2026 Elite Goals Evaluation — reproducible calculator.

Reads Goals w Agent V2.csv, applies locked scoring rules, writes:
  - exports/q2_2026_scoreboard.csv
  - exports/q2_2026_kpi_audit.csv
  - exports/q2_2026_monthly_detail.csv
  - exports/q2_2026_elite_goals_evaluation.html
"""

from __future__ import annotations

import csv
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

# ---------------------------------------------------------------------------
# Locked rules
# ---------------------------------------------------------------------------

KPI_WEIGHTS = {
    "daily_purchase": 20.0,
    "daily_net_purchase": 25.0,
    "monthly_purchasers": 15.0,
    "reactivations": 8.0,
    "upgrades": 5.0,
    "pct_active": 7.0,
}

KPI_LABELS = {
    "daily_purchase": "Daily Avg Purchase",
    "daily_net_purchase": "Daily Avg Net Purchase",
    "monthly_purchasers": "Monthly Purchasers",
    "reactivations": "# Reactivation",
    "upgrades": "Upgrade to Elite",
    "pct_active": "% Active from portfolio",
}

# Agent key -> eligible months (1-12)
ELIGIBILITY = {
    "coral_s": {4, 5, 6},
    "lee_t": {5, 6},
    "rachel_a": {6},
}

MANAGER_SCORE = {
    "coral_s": 15.0,
    "lee_t": 12.0,
    "rachel_a": 10.0,
}

MANAGER_NOTES = {
    "coral_s": (
        "Improve time management; dive deeper when she doesn't understand."
    ),
    "lee_t": (
        "Sometimes gives up early, doesn't go deep (VIP Event); "
        "needs to improve depth/follow-through."
    ),
    "rachel_a": (
        "Improve time management; messy. Must learn to be organized; "
        "learn to receive feedback."
    ),
}

DISPLAY_NAME = {
    "coral_s": "Coral",
    "lee_t": "Lee",
    "rachel_a": "Rachel",
}

ELIGIBLE_LABEL = {
    "coral_s": "Apr + May + Jun",
    "lee_t": "May + Jun only",
    "rachel_a": "June only",
}

MONTH_NAME = {4: "April", 5: "May", 6: "June"}

AGENT_ORDER = ["coral_s", "lee_t", "rachel_a"]

UPGRADES_FORCED_ACHIEVEMENT = 1.0  # 100% for all agents


def parse_number(raw: str) -> float:
    if raw is None:
        return 0.0
    s = str(raw).strip().replace(",", "").replace('"', "").replace("%", "")
    if not s:
        return 0.0
    return float(s)


def ceil_pct(value: float) -> int:
    """Ceiling to whole percentage (submission rounding)."""
    return int(math.ceil(value - 1e-12))


@dataclass
class MonthRow:
    agent: str
    year: int
    month: int
    days: int
    daily_purchase_goal: float
    daily_purchase_actual: float
    daily_net_goal: float
    daily_net_actual: float
    purchasers_goal: float
    purchasers_actual: float
    pct_active_goal: float
    pct_active_actual: float
    upgrades_goal: float
    upgrades_actual: float
    reactivations_goal: float
    reactivations_actual: float
    eligible: bool = False


@dataclass
class KpiResult:
    key: str
    label: str
    weight: float
    sum_goal: float
    sum_actual: float
    achievement: float  # 0..1
    points: float
    forced: bool = False
    note: str = ""


@dataclass
class AgentResult:
    agent: str
    display: str
    eligible_label: str
    months: List[MonthRow]
    kpis: List[KpiResult]
    goals_exact: float
    goals_ceil: int
    manager: float
    final_exact: float
    final_ceil: int
    note: str


def default_csv_path() -> Path:
    return Path(r"c:\Users\Owner\Downloads\Goals w Agent V2.csv")


def open_csv(csv_path: Path):
    """Open Goals CSV — Excel often saves as UTF-16 LE with tabs."""
    raw = csv_path.read_bytes()
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return csv_path.open(newline="", encoding="utf-16")
    return csv_path.open(newline="", encoding="utf-8-sig")


def load_rows(csv_path: Path) -> List[MonthRow]:
    rows: List[MonthRow] = []
    with open_csv(csv_path) as f:
        sample = f.read(4096)
        f.seek(0)
        dialect_delim = "\t" if "\t" in sample.splitlines()[0] else ","
        reader = csv.DictReader(f, delimiter=dialect_delim)
        for rec in reader:
            agent = (rec.get("Agent Name") or "").strip()
            if not agent or agent.lower() in {"total", ""}:
                continue
            try:
                month = int(parse_number(rec.get("Month*") or "0"))
                year = int(parse_number(rec.get("Year*") or "0"))
            except ValueError:
                continue
            if year != 2026 or month not in (4, 5, 6):
                continue
            if agent not in ELIGIBILITY:
                continue

            row = MonthRow(
                agent=agent,
                year=year,
                month=month,
                days=int(parse_number(rec.get("# Days Actual") or "0")),
                daily_purchase_goal=parse_number(rec.get("Daily Avg Purchase Goal")),
                daily_purchase_actual=parse_number(rec.get("Daily Avg Purchase Actual")),
                daily_net_goal=parse_number(rec.get("Daily Avg Net Purchase Goal")),
                daily_net_actual=parse_number(rec.get("Daily Avg Net Purchase Actual")),
                purchasers_goal=parse_number(rec.get("Monthly Players w purchase Goal")),
                purchasers_actual=parse_number(rec.get("#Players w Purchase")),
                pct_active_goal=parse_number(rec.get("% Active From Portfolio Goal")),
                pct_active_actual=parse_number(
                    rec.get("% Active From Portfolio Actual (agent Ver)")
                ),
                upgrades_goal=parse_number(rec.get("#Players Upgraded to Elite")),
                upgrades_actual=parse_number(rec.get("#Players Upgraded Actual")),
                reactivations_goal=parse_number(rec.get("#Reactivations")),
                reactivations_actual=parse_number(rec.get("#Reactivations Actual")),
                eligible=month in ELIGIBILITY[agent],
            )
            rows.append(row)
    return rows


def achievement_ratio(sum_actual: float, sum_goal: float) -> float:
    if sum_goal <= 0:
        return 1.0 if sum_actual >= 0 else 0.0
    return min(1.0, sum_actual / sum_goal)


def score_agent(agent: str, all_rows: List[MonthRow]) -> AgentResult:
    months = sorted(
        [r for r in all_rows if r.agent == agent],
        key=lambda r: r.month,
    )
    eligible = [r for r in months if r.eligible]

    def sum_pair(goal_attr: str, actual_attr: str) -> Tuple[float, float]:
        g = sum(getattr(r, goal_attr) for r in eligible)
        a = sum(getattr(r, actual_attr) for r in eligible)
        return g, a

    kpis: List[KpiResult] = []

    specs = [
        ("daily_purchase", "daily_purchase_goal", "daily_purchase_actual", False),
        ("daily_net_purchase", "daily_net_goal", "daily_net_actual", False),
        ("monthly_purchasers", "purchasers_goal", "purchasers_actual", False),
        ("reactivations", "reactivations_goal", "reactivations_actual", False),
        ("upgrades", "upgrades_goal", "upgrades_actual", True),
        ("pct_active", "pct_active_goal", "pct_active_actual", False),
    ]

    for key, g_attr, a_attr, forced in specs:
        weight = KPI_WEIGHTS[key]
        sum_g, sum_a = sum_pair(g_attr, a_attr)
        if forced:
            ach = UPGRADES_FORCED_ACHIEVEMENT
            note = "Forced 100% — Upgrade to Elite full score for all agents"
        else:
            ach = achievement_ratio(sum_a, sum_g)
            note = ""
        points = ach * weight
        kpis.append(
            KpiResult(
                key=key,
                label=KPI_LABELS[key],
                weight=weight,
                sum_goal=sum_g,
                sum_actual=sum_a,
                achievement=ach,
                points=points,
                forced=forced,
                note=note,
            )
        )

    goals_exact = sum(k.points for k in kpis)
    manager = MANAGER_SCORE[agent]
    final_exact = goals_exact + manager

    return AgentResult(
        agent=agent,
        display=DISPLAY_NAME[agent],
        eligible_label=ELIGIBLE_LABEL[agent],
        months=months,
        kpis=kpis,
        goals_exact=goals_exact,
        goals_ceil=ceil_pct(goals_exact),
        manager=manager,
        final_exact=final_exact,
        final_ceil=ceil_pct(final_exact),
        note=MANAGER_NOTES[agent],
    )


def fmt_num(n: float, decimals: int = 0) -> str:
    if decimals == 0:
        return f"{n:,.0f}"
    return f"{n:,.{decimals}f}"


def fmt_pct(n: float, decimals: int = 2) -> str:
    return f"{n:.{decimals}f}%"


def write_csvs(outdir: Path, results: List[AgentResult]) -> None:
    outdir.mkdir(parents=True, exist_ok=True)

    # Scoreboard
    sb_path = outdir / "q2_2026_scoreboard.csv"
    with sb_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "Agent",
                "Eligible Months",
                "Goals Exact %",
                "Goals Ceil %",
                "Manager %",
                "Final Exact %",
                "Final Ceil % (Submission)",
                "Manager Note",
            ]
        )
        for r in results:
            w.writerow(
                [
                    r.display,
                    r.eligible_label,
                    f"{r.goals_exact:.4f}",
                    r.goals_ceil,
                    f"{r.manager:.0f}",
                    f"{r.final_exact:.4f}",
                    r.final_ceil,
                    r.note,
                ]
            )

    # KPI audit
    kpi_path = outdir / "q2_2026_kpi_audit.csv"
    with kpi_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "Agent",
                "KPI",
                "Weight %",
                "Sum Goal (eligible)",
                "Sum Actual (eligible)",
                "Achievement %",
                "Points %",
                "Forced Override",
                "Note",
            ]
        )
        for r in results:
            for k in r.kpis:
                w.writerow(
                    [
                        r.display,
                        k.label,
                        f"{k.weight:.0f}",
                        f"{k.sum_goal:.6f}",
                        f"{k.sum_actual:.6f}",
                        f"{k.achievement * 100:.6f}",
                        f"{k.points:.6f}",
                        "Yes" if k.forced else "No",
                        k.note,
                    ]
                )

    # Monthly detail
    mon_path = outdir / "q2_2026_monthly_detail.csv"
    with mon_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "Agent",
                "Month",
                "Eligible",
                "Daily Purchase Goal",
                "Daily Purchase Actual",
                "Daily Net Goal",
                "Daily Net Actual",
                "Purchasers Goal",
                "Purchasers Actual",
                "% Active Goal",
                "% Active Actual",
                "Upgrades Goal",
                "Upgrades Actual",
                "Reactivations Goal",
                "Reactivations Actual",
            ]
        )
        for r in results:
            for m in r.months:
                w.writerow(
                    [
                        r.display,
                        MONTH_NAME[m.month],
                        "Yes" if m.eligible else "No (excluded)",
                        m.daily_purchase_goal,
                        m.daily_purchase_actual,
                        m.daily_net_goal,
                        m.daily_net_actual,
                        m.purchasers_goal,
                        m.purchasers_actual,
                        m.pct_active_goal,
                        m.pct_active_actual,
                        m.upgrades_goal,
                        m.upgrades_actual,
                        m.reactivations_goal,
                        m.reactivations_actual,
                    ]
                )


def html_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def build_html(results: List[AgentResult]) -> str:
    scoreboard_rows = ""
    for r in results:
        scoreboard_rows += f"""
        <tr>
          <td><strong>{html_escape(r.display)}</strong></td>
          <td>{html_escape(r.eligible_label)}</td>
          <td>{r.goals_exact:.2f}%</td>
          <td class="ceil">{r.goals_ceil}%</td>
          <td>+{r.manager:.0f}%</td>
          <td>{r.final_exact:.2f}%</td>
          <td class="ceil final">{r.final_ceil}%</td>
        </tr>"""

    notes_block = ""
    for r in results:
        notes_block += f"""
        <div class="note-card">
          <h3>{html_escape(r.display)} — {r.final_ceil}%</h3>
          <p class="meta">Eligible: {html_escape(r.eligible_label)} · Goals {r.goals_ceil}% + Manager {r.manager:.0f}%</p>
          <p class="note"><strong>Manager note:</strong> {html_escape(r.note)}</p>
        </div>"""

    agent_sections = ""
    for r in results:
        month_rows = ""
        for m in r.months:
            elig_class = "eligible" if m.eligible else "excluded"
            elig_txt = "Yes" if m.eligible else "No"
            month_rows += f"""
            <tr class="{elig_class}">
              <td>{MONTH_NAME[m.month]}</td>
              <td>{elig_txt}</td>
              <td>{fmt_num(m.daily_purchase_goal)}</td>
              <td>{fmt_num(m.daily_purchase_actual)}</td>
              <td>{fmt_num(m.daily_net_goal)}</td>
              <td>{fmt_num(m.daily_net_actual)}</td>
              <td>{fmt_num(m.purchasers_goal)}</td>
              <td>{fmt_num(m.purchasers_actual)}</td>
              <td>{m.pct_active_goal:.0f}%</td>
              <td>{m.pct_active_actual:.0f}%</td>
              <td>{fmt_num(m.upgrades_goal)}</td>
              <td>{fmt_num(m.upgrades_actual)}</td>
              <td>{fmt_num(m.reactivations_goal)}</td>
              <td>{fmt_num(m.reactivations_actual)}</td>
            </tr>"""

        kpi_rows = ""
        for k in r.kpis:
            forced_txt = "Yes — full score" if k.forced else "—"
            kpi_rows += f"""
            <tr>
              <td>{html_escape(k.label)}</td>
              <td>{k.weight:.0f}%</td>
              <td>{fmt_num(k.sum_goal, 2) if k.key.startswith('daily') or k.key == 'pct_active' else fmt_num(k.sum_goal)}</td>
              <td>{fmt_num(k.sum_actual, 2) if k.key.startswith('daily') or k.key == 'pct_active' else fmt_num(k.sum_actual)}</td>
              <td>{k.achievement * 100:.2f}%</td>
              <td><strong>{k.points:.2f}%</strong></td>
              <td>{forced_txt}</td>
            </tr>"""

        agent_sections += f"""
        <section class="agent">
          <h2>{html_escape(r.display)} — Final {r.final_ceil}%</h2>
          <p class="meta">Eligible months: <strong>{html_escape(r.eligible_label)}</strong>
            · Goals exact {r.goals_exact:.2f}% → ceil <strong>{r.goals_ceil}%</strong>
            · Manager <strong>+{r.manager:.0f}%</strong>
            · Final exact {r.final_exact:.2f}% → ceil <strong>{r.final_ceil}%</strong></p>
          <p class="note"><strong>Manager note:</strong> {html_escape(r.note)}</p>

          <h3>Monthly Actual vs Goal</h3>
          <p class="hint">Grey rows are outside eligibility and are excluded from scoring (not treated as fails).</p>
          <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Month</th><th>Eligible</th>
                <th>Purch Goal</th><th>Purch Act</th>
                <th>Net Goal</th><th>Net Act</th>
                <th>Buyers Goal</th><th>Buyers Act</th>
                <th>%Act Goal</th><th>%Act Act</th>
                <th>Upg Goal</th><th>Upg Act</th>
                <th>React Goal</th><th>React Act</th>
              </tr>
            </thead>
            <tbody>{month_rows}</tbody>
          </table>
          </div>

          <h3>KPI score (eligible window)</h3>
          <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>KPI</th><th>Weight</th>
                <th>Sum Goal</th><th>Sum Actual</th>
                <th>Achievement</th><th>Points</th><th>Override</th>
              </tr>
            </thead>
            <tbody>{kpi_rows}</tbody>
            <tfoot>
              <tr>
                <td colspan="5"><strong>Goals block</strong></td>
                <td><strong>{r.goals_exact:.2f}% → {r.goals_ceil}%</strong></td>
                <td></td>
              </tr>
              <tr>
                <td colspan="5">Manager evaluation</td>
                <td>+{r.manager:.0f}%</td>
                <td></td>
              </tr>
              <tr class="final-row">
                <td colspan="5"><strong>Final (submission)</strong></td>
                <td><strong>{r.final_ceil}%</strong></td>
                <td>exact {r.final_exact:.2f}%</td>
              </tr>
            </tfoot>
          </table>
          </div>
        </section>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Q2 2026 Elite Goals Evaluation</title>
  <style>
    :root {{
      --ink: #1a1a1a;
      --muted: #5a5a5a;
      --line: #d8d8d8;
      --bg: #f7f6f3;
      --card: #ffffff;
      --accent: #0b3d2e;
      --ceil: #0b3d2e;
      --excluded: #f0f0f0;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
      color: var(--ink);
      background: var(--bg);
      line-height: 1.45;
    }}
    header {{
      background: var(--accent);
      color: #fff;
      padding: 28px 32px;
    }}
    header h1 {{ margin: 0 0 6px; font-size: 1.55rem; font-weight: 650; }}
    header p {{ margin: 0; opacity: 0.9; font-size: 0.95rem; }}
    main {{ max-width: 1100px; margin: 0 auto; padding: 24px 20px 48px; }}
    section {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 20px 22px;
      margin-bottom: 20px;
    }}
    h2 {{ margin: 0 0 10px; font-size: 1.25rem; color: var(--accent); }}
    h3 {{ margin: 18px 0 8px; font-size: 1.02rem; }}
    .meta {{ color: var(--muted); margin: 0 0 10px; font-size: 0.92rem; }}
    .hint {{ color: var(--muted); font-size: 0.85rem; margin: 0 0 8px; }}
    .note {{ margin: 8px 0 14px; padding: 10px 12px; background: #f3f7f5; border-left: 3px solid var(--accent); }}
    .table-wrap {{ overflow-x: auto; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.84rem;
    }}
    th, td {{
      border-bottom: 1px solid var(--line);
      padding: 7px 8px;
      text-align: left;
      white-space: nowrap;
    }}
    th {{ background: #eef3f0; font-weight: 600; }}
    tr.excluded td {{ background: var(--excluded); color: #777; }}
    td.ceil, .ceil {{ color: var(--ceil); font-weight: 700; }}
    td.final {{ font-size: 1.05rem; }}
    tfoot tr.final-row td {{ background: #eef3f0; }}
    .note-card {{
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 12px 14px;
      margin-bottom: 10px;
      background: #fff;
    }}
    .note-card h3 {{ margin: 0 0 4px; }}
    .rules li {{ margin-bottom: 4px; }}
    footer {{
      text-align: center;
      color: var(--muted);
      font-size: 0.8rem;
      padding: 8px;
    }}
  </style>
</head>
<body>
  <header>
    <h1>Q2 2026 Elite Goals Evaluation</h1>
    <p>CEO submission pack · KPI goals (max 80%) + Manager evaluation · Submission % rounded up</p>
  </header>
  <main>

    <section>
      <h2>Summary scoreboard</h2>
      <p class="hint">Submission columns use ceiling to whole percentages. Exact decimals retained for audit.</p>
      <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Agent</th>
            <th>Eligible</th>
            <th>Goals (exact)</th>
            <th>Goals (ceil)</th>
            <th>Manager</th>
            <th>Final (exact)</th>
            <th>Final (submission)</th>
          </tr>
        </thead>
        <tbody>
          {scoreboard_rows}
        </tbody>
      </table>
      </div>
      {notes_block}
    </section>

    <section class="rules">
      <h2>Methodology</h2>
      <ul>
        <li><strong>KPI weights (80%):</strong> Daily Avg Purchase 20%, Daily Avg Net Purchase 25%, Monthly Purchasers 15%, # Reactivation 8%, Upgrade to Elite 5%, % Active from portfolio 7%.</li>
        <li><strong>Eligibility:</strong> Coral = Apr–Jun; Lee = May–Jun only; Rachel = June only. Ineligible months are excluded (not fails).</li>
        <li><strong>Achievement:</strong> min(100%, sum(Actual) / sum(Goal)) over eligible months × KPI weight. Partial credit when short.</li>
        <li><strong>Upgrades:</strong> forced to 100% achievement (full 5%) for every agent.</li>
        <li><strong>Manager:</strong> Coral +15%, Lee +12%, Rachel +10%.</li>
        <li><strong>Final:</strong> Goals block + Manager. Submitted Goals % and Final % are rounded <em>up</em> (ceiling) to whole percentages.</li>
        <li><strong>Source:</strong> Goals w Agent V2.csv — Yes/No flags ignored; Actual vs Goal only.</li>
      </ul>
    </section>

    {agent_sections}

  </main>
  <footer>Generated by goals_q2_2026/calculate_q2_goals.py · Elite Analytics</footer>
</body>
</html>"""


def verify(results: List[AgentResult]) -> None:
    expected = {
        "coral_s": (95, 5.0),
        "lee_t": (84, 5.0),
        "rachel_a": (87, 5.0),
    }
    errors = []
    for r in results:
        exp_final, exp_upgrade = expected[r.agent]
        upgrade_pts = next(k.points for k in r.kpis if k.key == "upgrades")
        if r.final_ceil != exp_final:
            errors.append(
                f"{r.display}: final_ceil={r.final_ceil} expected {exp_final} "
                f"(exact={r.final_exact:.4f})"
            )
        if abs(upgrade_pts - exp_upgrade) > 1e-9:
            errors.append(f"{r.display}: upgrades points={upgrade_pts} expected {exp_upgrade}")
        # Eligibility sanity
        elig_months = {m.month for m in r.months if m.eligible}
        if elig_months != ELIGIBILITY[r.agent]:
            errors.append(f"{r.display}: eligibility mismatch {elig_months}")
    if errors:
        raise SystemExit("VERIFICATION FAILED:\n  " + "\n  ".join(errors))
    print("Verification OK:")
    for r in results:
        print(
            f"  {r.display}: goals {r.goals_exact:.4f}% -> {r.goals_ceil}% | "
            f"final {r.final_exact:.4f}% -> {r.final_ceil}% | upgrades=5.00%"
        )


def main() -> None:
    root = Path(__file__).resolve().parent
    csv_path = Path(os.environ.get("GOALS_CSV", str(default_csv_path())))
    if not csv_path.exists():
        raise SystemExit(f"CSV not found: {csv_path}")

    rows = load_rows(csv_path)
    if not rows:
        raise SystemExit("No agent rows loaded from CSV")

    results = [score_agent(a, rows) for a in AGENT_ORDER]
    verify(results)

    exports = root / "exports"
    write_csvs(exports, results)
    html = build_html(results)
    html_path = exports / "q2_2026_elite_goals_evaluation.html"
    html_path.write_text(html, encoding="utf-8")

    # Methodology markdown (one-pager for attach)
    method_path = root / "METHODOLOGY.md"
    method_path.write_text(
        """# Q2 2026 Elite Goals Evaluation — Methodology

## Scoring model

| Block | Max |
|-------|-----|
| KPI goals | 80% |
| Manager evaluation | 20% (assigned per agent) |
| **Total** | **100%** |

### KPI weights (80%)

| KPI | Weight |
|-----|--------|
| Daily Avg Purchase | 20% |
| Daily Avg Net Purchase | 25% |
| Monthly Purchasers | 15% |
| # Reactivation | 8% |
| Upgrade to Elite | 5% |
| % Active from portfolio | 7% |

### Eligibility

| Agent | Counted months |
|-------|----------------|
| Coral | April + May + June |
| Lee | May + June only |
| Rachel | June only |

Ineligible months are **excluded** from scoring (not treated as misses).

### Achievement formula

For each KPI (except Upgrades):

```
Achievement% = min(100%, sum(Actual over eligible months) / sum(Goal over eligible months))
KPI points   = Achievement% × KPI weight
```

Shortfalls receive **partial credit**. Overperformance is capped at 100% of the KPI weight.
Multi-month catch-up is automatic via the eligible-window sum ratio.

**Upgrade to Elite:** forced to **100%** (full 5%) for every agent.

### Manager scores & notes

| Agent | Manager % | Note |
|-------|-----------|------|
| Coral | +15% | Improve time management; dive deeper when she doesn't understand. |
| Lee | +12% | Sometimes gives up early, doesn't go deep (VIP Event); needs to improve depth/follow-through. |
| Rachel | +10% | Improve time management; messy. Must learn to be organized; learn to receive feedback. |

### Presentation rounding

Submitted **Goals %** and **Final %** are rounded **up** (ceiling) to whole percentages.
Exact decimals are retained in audit CSVs.

### Source

`Goals w Agent V2.csv` — Actual vs Goal columns only; sheet Yes/No flags ignored.

### Outputs

- `exports/q2_2026_elite_goals_evaluation.html` — CEO HTML pack
- `exports/q2_2026_scoreboard.csv`
- `exports/q2_2026_kpi_audit.csv`
- `exports/q2_2026_monthly_detail.csv`
""",
        encoding="utf-8",
    )

    print(f"Wrote {html_path}")
    print(f"Wrote CSVs in {exports}")
    print(f"Wrote {method_path}")


if __name__ == "__main__":
    main()
