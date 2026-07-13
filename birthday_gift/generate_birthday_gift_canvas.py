"""Generate birthday gift canvas from export CSV."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXPORT_DIR = ROOT / "birthday_gift" / "exports"
PAYLOAD_PATH = EXPORT_DIR / "canvas_payload.json"
CANVAS_PATH = Path(
    r"C:\Users\Owner\.cursor\projects\c-Users-Owner-Downloads-Elite\canvases"
    r"\elite-birthday-gift-activity-2026-06-to-2026-07.canvas.tsx"
)

METRIC_KEYS = {
    "Purchase amount ($)": "purchase_amount",
    "Number of purchases": "number_of_purchases",
    "Active days": "active_days",
    "Total SC bets": "total_sc_bets",
}


def load_players(csv_path: Path) -> list[dict]:
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    players = []

    def pct(val: str) -> float | None:
        return float(val) if val else None

    for r in rows:
        players.append(
            {
                "aid": r["AID"],
                "agent": r["Agent"],
                "ltPurchase": float(r.get("LT Purchase") or 0),
                "hold": r.get("Hold") or "n/a",
                "giftMonth": r["Gift month"],
                "giftDate": r["Gift date"],
                "anchorDate": r["Anchor date"],
                "giftSc": float(r["Gift SC"] or 0) if r.get("Gift SC") else 0,
                "afterDays": int(r["After days available"]),
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


def summary_from_csv(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    out: dict[str, dict] = {}
    for r in rows:
        key = METRIC_KEYS.get(r["Metric"], r["Metric"])
        out[key] = {
            "cohort": r.get("Cohort", "all"),
            "metric": r["Metric"],
            "avgBefore": float(r["Avg before"]),
            "avgAfter": float(r["Avg after"]),
            "avgDiff": float(r["Avg diff"]),
            "avgPct": float(r["Avg % change"]) if r.get("Avg % change") else None,
            "players": int(r["Players"]),
        }
    return out


def build_payload(csv_path: Path, summary_path: Path, cohort_mode: bool) -> dict:
    players = load_players(csv_path)
    summary_all = summary_from_csv(summary_path)
    month_summary_path = summary_path.with_name(
        summary_path.stem.replace("_summary", "_summary_by_month") + ".csv"
    )
    summary_by_month: dict[str, dict[str, dict]] = {}
    if month_summary_path.exists():
        for r in csv.DictReader(month_summary_path.open(encoding="utf-8")):
            month = r["Cohort"]
            key = METRIC_KEYS.get(r["Metric"], r["Metric"])
            summary_by_month.setdefault(month, {})[key] = {
                "metric": r["Metric"],
                "avgBefore": float(r["Avg before"]),
                "avgAfter": float(r["Avg after"]),
                "avgDiff": float(r["Avg diff"]),
                "avgPct": float(r["Avg % change"]) if r.get("Avg % change") else None,
                "players": int(r["Players"]),
            }
    month_counts: dict[str, int] = {}
    for p in players:
        month_counts[p["giftMonth"]] = month_counts.get(p["giftMonth"], 0) + 1
    return {
        "cohortMode": cohort_mode,
        "players": players,
        "summaryAll": summary_all,
        "summaryByMonth": summary_by_month,
        "playerCount": len(players),
        "monthCounts": month_counts,
        "fullAfterCount": sum(1 for p in players if p["afterDays"] >= 30),
    }


COHORT_HEADER = '''import {
  BarChart,
  Card,
  CardBody,
  CardHeader,
  CollapsibleSection,
  Grid,
  H1,
  H2,
  Stack,
  Stat,
  Table,
  Text,
  canvasTokensLight,
} from "cursor/canvas";

const T = canvasTokensLight;
const POS = "#15803d";
const NEG = "#b91c1c";
const shellStyle = {
  padding: 24,
  maxWidth: 1200,
  background: T.bg.editor,
  color: T.text.primary,
  minHeight: "100%",
};
const surfaceStyle = {
  background: T.bg.chrome,
  border: `1px solid ${T.stroke.secondary}`,
  borderRadius: 8,
};
const statStyle = {
  background: T.fill.tertiary,
  border: `1px solid ${T.stroke.tertiary}`,
  borderRadius: 8,
  padding: 12,
};

type PlayerRow = {
  aid: string;
  agent: string;
  ltPurchase: number;
  hold: string;
  giftMonth: string;
  giftDate: string;
  anchorDate: string;
  giftSc: number;
  afterDays: number;
  purchaseBefore: number;
  purchaseAfter: number;
  purchaseDiff: number;
  purchasePct: number | null;
  purchasesBefore: number;
  purchasesAfter: number;
  purchasesDiff: number;
  purchasesPct: number | null;
  activeBefore: number;
  activeAfter: number;
  activeDiff: number;
  activePct: number | null;
  betsBefore: number;
  betsAfter: number;
  betsDiff: number;
  betsPct: number | null;
};

type SummaryMetric = {
  metric: string;
  avgBefore: number;
  avgAfter: number;
  avgDiff: number;
  avgPct: number | null;
  players: number;
};

const DATA = '''

COHORT_FOOTER = ''' as {
  cohortMode: boolean;
  players: PlayerRow[];
  summaryAll: Record<string, SummaryMetric>;
  summaryByMonth: Record<string, Record<string, SummaryMetric>>;
  playerCount: number;
  monthCounts: Record<string, number>;
  fullAfterCount: number;
};

const fmtMoney = (n: number) => `$${n.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
const fmtNum = (n: number) => n.toLocaleString(undefined, { maximumFractionDigits: 0 });
const fmtPct = (n: number | null) => (n == null ? "—" : `${n > 0 ? "+" : ""}${n.toFixed(1)}%`);
const chgColor = (n: number | null) => (n == null || n === 0 ? T.text.secondary : n > 0 ? POS : NEG);
const fmtDiffMoney = (n: number) => `${n > 0 ? "+" : ""}${fmtMoney(n)}`;
const fmtDiffNum = (n: number) => `${n > 0 ? "+" : ""}${fmtNum(n)}`;
const badge = (text: string, bg: string, color: string) => (
  <span style={{ display: "inline-block", padding: "4px 10px", borderRadius: 999, fontSize: 12, fontWeight: 600, background: bg, color }}>{text}</span>
);

function playerMetricRows(p: PlayerRow) {
  const rows = [
    { metric: "Purchase amount ($)", before: fmtMoney(p.purchaseBefore), after: fmtMoney(p.purchaseAfter), diff: fmtDiffMoney(p.purchaseDiff), pct: fmtPct(p.purchasePct), pctNum: p.purchasePct },
    { metric: "Number of purchases", before: fmtNum(p.purchasesBefore), after: fmtNum(p.purchasesAfter), diff: fmtDiffNum(p.purchasesDiff), pct: fmtPct(p.purchasesPct), pctNum: p.purchasesPct },
    { metric: "Active days", before: fmtNum(p.activeBefore), after: fmtNum(p.activeAfter), diff: fmtDiffNum(p.activeDiff), pct: fmtPct(p.activePct), pctNum: p.activePct },
    { metric: "Total SC bets", before: fmtMoney(p.betsBefore), after: fmtMoney(p.betsAfter), diff: fmtDiffMoney(p.betsDiff), pct: fmtPct(p.betsPct), pctNum: p.betsPct },
  ];
  return rows;
}

export default function EliteBirthdayGiftActivity() {
  const summary = DATA.summaryAll;
  const chartData = [
    { label: "Purchase ($)", before: summary.purchase_amount.avgBefore, after: summary.purchase_amount.avgAfter },
    { label: "Purchases", before: summary.number_of_purchases.avgBefore, after: summary.number_of_purchases.avgAfter },
    { label: "Active days", before: summary.active_days.avgBefore, after: summary.active_days.avgAfter },
    { label: "SC bets", before: summary.total_sc_bets.avgBefore, after: summary.total_sc_bets.avgAfter },
  ];

  return (
    <Stack gap={20} style={shellStyle}>
      <H1>Elite Birthday Gift — June 2026</H1>

      <Grid columns={4} gap={12}>
        <div style={statStyle}><Stat label="Avg purchase" value={`${fmtMoney(summary.purchase_amount.avgBefore)} → ${fmtMoney(summary.purchase_amount.avgAfter)}`} detail={fmtPct(summary.purchase_amount.avgPct)} /></div>
        <div style={statStyle}><Stat label="Avg purchases" value={`${fmtNum(summary.number_of_purchases.avgBefore)} → ${fmtNum(summary.number_of_purchases.avgAfter)}`} detail={fmtPct(summary.number_of_purchases.avgPct)} /></div>
        <div style={statStyle}><Stat label="Avg active days" value={`${fmtNum(summary.active_days.avgBefore)} → ${fmtNum(summary.active_days.avgAfter)}`} detail={fmtPct(summary.active_days.avgPct)} /></div>
        <div style={statStyle}><Stat label="Avg SC bets" value={`${fmtMoney(summary.total_sc_bets.avgBefore)} → ${fmtMoney(summary.total_sc_bets.avgAfter)}`} detail={fmtPct(summary.total_sc_bets.avgPct)} /></div>
      </Grid>

      <Card style={surfaceStyle}>
        <CardHeader title="Average before vs after" trailing={<Text tone="secondary" style={{ color: T.text.tertiary }}>n={summary.purchase_amount.players}</Text>} />
        <CardBody>
          <BarChart
            title="Average metric levels (before vs after)"
            data={chartData}
            xKey="label"
            series={[
              { key: "before", label: "Before (30d)", tone: "neutral" },
              { key: "after", label: "After (30d)", tone: "accent" },
            ]}
            yLabel="Average value"
          />
        </CardBody>
      </Card>

      <Stack gap={8}>
        <H2>Per-player split</H2>
        {DATA.players.map((p) => (
          <CollapsibleSection
            key={p.aid}
            title={`AID ${p.aid}`}
            trailing={
              <Text tone="secondary" style={{ color: T.text.tertiary }}>
                {p.agent || "—"} · LT {fmtMoney(p.ltPurchase)} · Hold {p.hold} ·{" "}
                <span style={{ color: chgColor(p.purchasePct) }}>{fmtPct(p.purchasePct)} purchase</span>
              </Text>
            }
            defaultOpen={false}
            style={{ ...surfaceStyle, padding: "4px 8px" }}
          >
            <Table
              columns={[
                { key: "metric", label: "Metric" },
                { key: "before", label: "Before", align: "right" },
                { key: "after", label: "After", align: "right" },
                { key: "diff", label: "Diff", align: "right" },
                { key: "pct", label: "Change", align: "right" },
              ]}
              rows={playerMetricRows(p).map((row) => ({
                metric: row.metric,
                before: badge(row.before, "#eef1f5", "#475569"),
                after: badge(row.after, "#e8f2fb", "#1d4f7c"),
                diff: <span style={{ color: chgColor(row.pctNum), fontWeight: 600 }}>{row.diff}</span>,
                pct: <span style={{ color: chgColor(row.pctNum), fontWeight: 600 }}>{row.pct}</span>,
              }))}
            />
          </CollapsibleSection>
        ))}
      </Stack>

      <Card style={surfaceStyle}>
        <CardHeader title="All players" trailing={<Text tone="secondary" style={{ color: T.text.tertiary }}>{DATA.playerCount} rows</Text>} />
        <CardBody padding={0}>
          <Table
            columns={[
              { key: "aid", label: "AID" },
              { key: "agent", label: "Agent" },
              { key: "ltPurchase", label: "LT Purchase", align: "right" },
              { key: "hold", label: "Hold", align: "right" },
              { key: "purchase", label: "Purchase", align: "right" },
              { key: "purchases", label: "Purchases", align: "right" },
              { key: "active", label: "Active days", align: "right" },
              { key: "bets", label: "SC bets", align: "right" },
            ]}
            rows={DATA.players.map((p) => ({
              aid: p.aid,
              agent: p.agent || "—",
              ltPurchase: fmtMoney(p.ltPurchase),
              hold: p.hold,
              purchase: `${fmtMoney(p.purchaseBefore)} → ${fmtMoney(p.purchaseAfter)} (${fmtPct(p.purchasePct)})`,
              purchases: `${fmtNum(p.purchasesBefore)} → ${fmtNum(p.purchasesAfter)}`,
              active: `${fmtNum(p.activeBefore)} → ${fmtNum(p.activeAfter)}`,
              bets: `${fmtMoney(p.betsBefore)} → ${fmtMoney(p.betsAfter)}`,
            }))}
          />
        </CardBody>
      </Card>
    </Stack>
  );
}
'''

FULL_HEADER = '''import {
  BarChart,
  Callout,
  Card,
  CardBody,
  CardHeader,
  Grid,
  H1,
  Pill,
  Row,
  Stack,
  Stat,
  Table,
  Text,
  useCanvasState,
} from "cursor/canvas";

type PlayerRow = {
  aid: string;
  agent: string;
  giftMonth: string;
  giftDate: string;
  anchorDate: string;
  giftSc: number;
  afterDays: number;
  purchaseBefore: number;
  purchaseAfter: number;
  purchaseDiff: number;
  purchasePct: number | null;
  purchasesBefore: number;
  purchasesAfter: number;
  activeBefore: number;
  activeAfter: number;
  betsBefore: number;
  betsAfter: number;
};

type SummaryMetric = {
  metric: string;
  avgBefore: number;
  avgAfter: number;
  avgDiff: number;
  avgPct: number | null;
  players: number;
};

const DATA = '''

FULL_FOOTER = ''' as {
  cohortMode: boolean;
  players: PlayerRow[];
  summaryAll: Record<string, SummaryMetric>;
  summaryByMonth: Record<string, Record<string, SummaryMetric>>;
  playerCount: number;
  monthCounts: Record<string, number>;
  fullAfterCount: number;
};

const fmtMoney = (n: number) => `$${n.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
const fmtNum = (n: number) => n.toLocaleString(undefined, { maximumFractionDigits: 0 });
const fmtPct = (n: number | null) => (n == null ? "—" : `${n > 0 ? "+" : ""}${n.toFixed(1)}%`);

export default function EliteBirthdayGiftActivity() {
  const [month, setMonth] = useCanvasState<string>("month", "all");
  const summary = month === "all" ? DATA.summaryAll : (DATA.summaryByMonth[month] ?? DATA.summaryAll);
  const players = month === "all" ? DATA.players : DATA.players.filter((p) => p.giftMonth === month);

  const chartData = [
    { label: "Purchase ($)", before: summary.purchase_amount.avgBefore, after: summary.purchase_amount.avgAfter },
    { label: "Purchases", before: summary.number_of_purchases.avgBefore, after: summary.number_of_purchases.avgAfter },
    { label: "Active days", before: summary.active_days.avgBefore, after: summary.active_days.avgAfter },
    { label: "SC bets", before: summary.total_sc_bets.avgBefore, after: summary.total_sc_bets.avgAfter },
  ];

  return (
    <Stack gap={20}>
      <Stack gap={6}>
        <H1>Elite Birthday Gift — Month-15th Anchor</H1>
        <Text tone="secondary">
          Source: BigQuery · Birthday_Bonus (id 1816) · windows anchored to 15th of gift month
        </Text>
      </Stack>

      <Callout tone="info">
        Before = 30 days ending day before month-15th anchor. After = 30 days starting day after anchor.
      </Callout>

      <Row gap={8}>
        <Pill tone={month === "all" ? "accent" : "neutral"} onClick={() => setMonth("all")}>All ({DATA.playerCount})</Pill>
        {Object.entries(DATA.monthCounts).map(([m, n]) => (
          <Pill key={m} tone={month === m ? "accent" : "neutral"} onClick={() => setMonth(m)}>{m} ({n})</Pill>
        ))}
      </Row>

      <Grid columns={4} gap={12}>
        <Stat label="Avg purchase before" value={fmtMoney(summary.purchase_amount.avgBefore)} detail={`${fmtPct(summary.purchase_amount.avgPct)} after`} />
        <Stat label="Avg purchases before" value={fmtNum(summary.number_of_purchases.avgBefore)} detail={`${fmtPct(summary.number_of_purchases.avgPct)} after`} />
        <Stat label="Avg active days before" value={fmtNum(summary.active_days.avgBefore)} detail={`${fmtPct(summary.active_days.avgPct)} after`} />
        <Stat label="Avg SC bets before" value={fmtMoney(summary.total_sc_bets.avgBefore)} detail={`${fmtPct(summary.total_sc_bets.avgPct)} after`} />
      </Grid>

      <Card>
        <CardHeader title="Average before vs after" trailing={<Text tone="secondary">n={summary.purchase_amount.players}</Text>} />
        <CardBody>
          <BarChart
            title="Average metric levels (before vs after)"
            data={chartData}
            xKey="label"
            series={[
              { key: "before", label: "Before (30d)", tone: "neutral" },
              { key: "after", label: "After (30d)", tone: "accent" },
            ]}
            yLabel="Average value"
          />
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Player detail" trailing={<Text tone="secondary">{players.length} rows</Text>} />
        <CardBody padding={0}>
          <Table
            columns={[
              { key: "aid", label: "AID" },
              { key: "agent", label: "Agent" },
              { key: "giftMonth", label: "Gift month" },
              { key: "giftDate", label: "Gift date" },
              { key: "anchorDate", label: "Anchor" },
              { key: "afterDays", label: "After days", align: "right" },
              { key: "purchaseBefore", label: "Purchase before", align: "right" },
              { key: "purchaseAfter", label: "Purchase after", align: "right" },
              { key: "purchasePct", label: "% chg", align: "right" },
            ]}
            rows={players.map((p) => ({
              aid: p.aid,
              agent: p.agent,
              giftMonth: p.giftMonth,
              giftDate: p.giftDate || "—",
              anchorDate: p.anchorDate,
              afterDays: String(p.afterDays),
              purchaseBefore: fmtMoney(p.purchaseBefore),
              purchaseAfter: fmtMoney(p.purchaseAfter),
              purchasePct: fmtPct(p.purchasePct),
            }))}
          />
        </CardBody>
      </Card>
    </Stack>
  );
}
'''


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate birthday gift canvas")
    parser.add_argument(
        "--input",
        default="birthday_gift/exports/birthday_gift_activity_june_2026_cohort.csv",
        help="Path to detail CSV (relative to project root or absolute)",
    )
    args = parser.parse_args()

    csv_path = Path(args.input)
    if not csv_path.is_absolute():
        csv_path = ROOT / csv_path
    summary_path = csv_path.with_name(csv_path.stem + "_summary.csv")
    cohort_mode = "june_2026_cohort" in csv_path.stem

    payload = build_payload(csv_path, summary_path, cohort_mode)
    PAYLOAD_PATH.write_text(json.dumps(payload), encoding="utf-8")

    if cohort_mode:
        canvas = COHORT_HEADER + json.dumps(payload) + COHORT_FOOTER
    else:
        canvas = FULL_HEADER + json.dumps(payload) + FULL_FOOTER
    CANVAS_PATH.write_text(canvas, encoding="utf-8")
    print(CANVAS_PATH)


if __name__ == "__main__":
    main()
