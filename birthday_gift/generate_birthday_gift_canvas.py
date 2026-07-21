"""Generate birthday gift canvas from export CSV."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXPORT_DIR = ROOT / "birthday_gift" / "exports"
PAYLOAD_PATH = EXPORT_DIR / "canvas_payload.json"
CANVAS_DIR = Path(
    r"C:\Users\Owner\.cursor\projects\c-Users-Owner-Downloads-Elite\canvases"
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
                "giftMonth": r.get("Gift month") or "",
                "giftDate": r.get("Gift date") or "",
                "beforeFrom": str(r.get("Before from") or r.get("Anchor date") or ""),
                "beforeTo": str(r.get("Before to") or ""),
                "afterFrom": str(r.get("After from") or ""),
                "afterTo": str(r.get("After to") or ""),
                "giftSc": float(r["Gift SC"] or 0) if r.get("Gift SC") else 0,
                "afterDays": int(r.get("After days available") or 0),
                "afterWindowDays": int(r.get("After window days") or 0),
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


def build_payload(
    csv_path: Path,
    summary_path: Path,
    cohort_mode: bool,
    title: str | None = None,
    compare: dict | None = None,
) -> dict:
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
    periods = {
        "beforeFrom": players[0]["beforeFrom"] if players else "",
        "beforeTo": players[0]["beforeTo"] if players else "",
        "afterFrom": players[0]["afterFrom"] if players else "",
        "afterTo": players[0]["afterTo"] if players else "",
    }
    window_days = players[0]["afterWindowDays"] if players else 0
    default_title = (
        csv_path.stem.replace("birthday_gift_activity_", "")
        .replace("jackpota_", "Jackpota ")
        .replace("_", " ")
        .title()
    )
    return {
        "cohortMode": cohort_mode,
        "title": title or default_title,
        "periods": periods,
        "players": players,
        "summaryAll": summary_all,
        "summaryByMonth": summary_by_month,
        "playerCount": len(players),
        "monthCounts": month_counts,
        "fullAfterCount": sum(
            1 for p in players if window_days and p["afterDays"] >= window_days
        ),
        "compare": compare,
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
  Pill,
  Row,
  Stack,
  Stat,
  Table,
  Text,
  canvasTokensLight,
  useCanvasState,
} from "cursor/canvas";

const T = canvasTokensLight;
const POS = "#15803d";
const NEG = "#b91c1c";
const BEFORE_BG = "#eef1f5";
const BEFORE_FG = "#475569";
const AFTER_BG = "#e8f2fb";
const AFTER_FG = "#1d4f7c";
const POS_BG = "#dcfce7";
const NEG_BG = "#fee2e2";
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

const AM_NAMES: Record<string, string> = {
  coral_s: "Coral",
  rachel_a: "Rachel",
  lee_t: "Lee",
  gabriel_e: "Gabriel",
};

type PlayerRow = {
  aid: string;
  agent: string;
  ltPurchase: number;
  hold: string;
  giftMonth: string;
  giftDate: string;
  beforeFrom: string;
  beforeTo: string;
  afterFrom: string;
  afterTo: string;
  giftSc: number;
  afterDays: number;
  afterWindowDays: number;
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
  title: string;
  periods: { beforeFrom: string; beforeTo: string; afterFrom: string; afterTo: string };
  players: PlayerRow[];
  summaryAll: Record<string, SummaryMetric>;
  summaryByMonth: Record<string, Record<string, SummaryMetric>>;
  playerCount: number;
  monthCounts: Record<string, number>;
  fullAfterCount: number;
  compare: null | {
    cohortSize: number;
    restSize: number;
    beforeFrom: string;
    beforeTo: string;
    afterFrom: string;
    afterTo: string;
    metrics: Array<{
      key: string;
      label: string;
      cohort: {
        beforeMean: number;
        afterMean: number;
        deltaMean: number;
        beforeMedian: number;
        afterMedian: number;
        deltaMedian: number;
      };
      rest: {
        beforeMean: number;
        afterMean: number;
        deltaMean: number;
        beforeMedian: number;
        afterMedian: number;
        deltaMedian: number;
      };
      didMean: number;
      didMedian: number;
    }>;
  };
};

const fmtMoney = (n: number) => `$${n.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
const fmtNum = (n: number) => n.toLocaleString(undefined, { maximumFractionDigits: 1 });
const fmtPct = (n: number | null) => (n == null ? "—" : `${n > 0 ? "+" : ""}${n.toFixed(1)}%`);
const chgColor = (n: number | null) => (n == null || n === 0 ? T.text.secondary : n > 0 ? POS : NEG);
const fmtDiffMoney = (n: number) => `${n > 0 ? "+" : ""}${fmtMoney(n)}`;
const fmtDiffNum = (n: number) => `${n > 0 ? "+" : ""}${fmtNum(n)}`;
const badge = (text: string, bg: string, color: string) => (
  <span style={{ display: "inline-block", padding: "4px 10px", borderRadius: 999, fontSize: 12, fontWeight: 600, background: bg, color }}>{text}</span>
);
const fmtSigned = (n: number, money = false) => {
  const body = money ? fmtMoney(Math.abs(n)).replace("$", "") : fmtNum(Math.abs(n));
  const sign = n > 0 ? "+" : n < 0 ? "−" : "";
  return money ? `${sign}$${body}` : `${sign}${body}`;
};
const amName = (agent: string) => {
  const key = (agent || "").trim();
  if (!key) return "Unassigned";
  return AM_NAMES[key] || key;
};
const toneSpan = (text: string, n: number) => (
  <span style={{ color: chgColor(n), fontWeight: 700 }}>{text}</span>
);
const purchaseDirection = (p: PlayerRow): "up" | "down" | "flat" => {
  if (p.purchaseAfter > p.purchaseBefore) return "up";
  if (p.purchaseAfter < p.purchaseBefore) return "down";
  return "flat";
};

function playerMetricRows(p: PlayerRow) {
  return [
    { metric: "Purchase amount ($)", before: fmtMoney(p.purchaseBefore), after: fmtMoney(p.purchaseAfter), diff: fmtDiffMoney(p.purchaseDiff), pct: fmtPct(p.purchasePct), pctNum: p.purchasePct },
    { metric: "Number of purchases", before: fmtNum(p.purchasesBefore), after: fmtNum(p.purchasesAfter), diff: fmtDiffNum(p.purchasesDiff), pct: fmtPct(p.purchasesPct), pctNum: p.purchasesPct },
    { metric: "Active days", before: fmtNum(p.activeBefore), after: fmtNum(p.activeAfter), diff: fmtDiffNum(p.activeDiff), pct: fmtPct(p.activePct), pctNum: p.activePct },
    { metric: "Total SC bets", before: fmtMoney(p.betsBefore), after: fmtMoney(p.betsAfter), diff: fmtDiffMoney(p.betsDiff), pct: fmtPct(p.betsPct), pctNum: p.betsPct },
  ];
}

export default function EliteBirthdayGiftActivity() {
  const summary = DATA.summaryAll;
  const reportTitle = DATA.title || "Elite Gift Players vs Rest of Elite";
  const compare = DATA.compare;
  const [direction, setDirection] = useCanvasState<"all" | "up" | "down">("direction", "all");
  const [amFilter, setAmFilter] = useCanvasState<string>("am", "all");
  const [showPlayerList, setShowPlayerList] = useCanvasState<boolean>("showPlayerList", true);

  const byKey = Object.fromEntries((compare?.metrics ?? []).map((m) => [m.key, m]));
  const purchaseCmp = byKey.purchase;
  const purchasesCmp = byKey.purchases;
  const activeCmp = byKey.active;
  const betsCmp = byKey.sc_bets;

  const amOptions = Array.from(
    new Set(DATA.players.map((p) => amName(p.agent)))
  )
    .filter((name) => name !== "Unassigned")
    .sort((a, b) => a.localeCompare(b));

  const filteredPlayers = DATA.players
    .filter((p) => {
      const dir = purchaseDirection(p);
      if (direction === "up" && dir !== "up") return false;
      if (direction === "down" && dir !== "down") return false;
      if (amFilter !== "all" && amName(p.agent) !== amFilter) return false;
      return true;
    })
    .slice()
    .sort((a, b) => {
      if (direction === "up") return b.purchasePct - a.purchasePct;
      if (direction === "down") return a.purchasePct - b.purchasePct;
      const rank = (p: PlayerRow) => {
        const d = purchaseDirection(p);
        if (d === "up") return 0;
        if (d === "flat") return 1;
        return 2;
      };
      const ra = rank(a);
      const rb = rank(b);
      if (ra !== rb) return ra - rb;
      if (ra === 0) return b.purchasePct - a.purchasePct;
      if (ra === 2) return a.purchasePct - b.purchasePct;
      return a.aid.localeCompare(b.aid);
    });

  const upliftCount = DATA.players.filter((p) => {
    if (amFilter !== "all" && amName(p.agent) !== amFilter) return false;
    return purchaseDirection(p) === "up";
  }).length;
  const downCount = DATA.players.filter((p) => {
    if (amFilter !== "all" && amName(p.agent) !== amFilter) return false;
    return purchaseDirection(p) === "down";
  }).length;
  const allCount = DATA.players.filter((p) => {
    if (amFilter !== "all" && amName(p.agent) !== amFilter) return false;
    return true;
  }).length;

  const filteredUplift = filteredPlayers.filter((p) => purchaseDirection(p) === "up").length;
  const filteredDown = filteredPlayers.filter((p) => purchaseDirection(p) === "down").length;
  const filteredFlat = filteredPlayers.filter((p) => purchaseDirection(p) === "flat").length;

  const avg = (vals: number[]) => (vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : 0);
  const pctChange = (before: number, after: number) => (before === 0 ? (after === 0 ? 0 : 100) : ((after - before) / before) * 100);
  const useFullSummary = direction === "all" && amFilter === "all";
  const filterSummary = {
    purchaseBefore: useFullSummary ? summary.purchase_amount.avgBefore : avg(filteredPlayers.map((p) => p.purchaseBefore)),
    purchaseAfter: useFullSummary ? summary.purchase_amount.avgAfter : avg(filteredPlayers.map((p) => p.purchaseAfter)),
    purchasesBefore: useFullSummary ? summary.number_of_purchases.avgBefore : avg(filteredPlayers.map((p) => p.purchasesBefore)),
    purchasesAfter: useFullSummary ? summary.number_of_purchases.avgAfter : avg(filteredPlayers.map((p) => p.purchasesAfter)),
    activeBefore: useFullSummary ? summary.active_days.avgBefore : avg(filteredPlayers.map((p) => p.activeBefore)),
    activeAfter: useFullSummary ? summary.active_days.avgAfter : avg(filteredPlayers.map((p) => p.activeAfter)),
    betsBefore: useFullSummary ? summary.total_sc_bets.avgBefore : avg(filteredPlayers.map((p) => p.betsBefore)),
    betsAfter: useFullSummary ? summary.total_sc_bets.avgAfter : avg(filteredPlayers.map((p) => p.betsAfter)),
  };
  const filterPct = {
    purchase: useFullSummary ? summary.purchase_amount.avgPct : pctChange(filterSummary.purchaseBefore, filterSummary.purchaseAfter),
    purchases: useFullSummary ? summary.number_of_purchases.avgPct : pctChange(filterSummary.purchasesBefore, filterSummary.purchasesAfter),
    active: useFullSummary ? summary.active_days.avgPct : pctChange(filterSummary.activeBefore, filterSummary.activeAfter),
    bets: useFullSummary ? summary.total_sc_bets.avgPct : pctChange(filterSummary.betsBefore, filterSummary.betsAfter),
  };

  return (
    <Stack gap={20} style={shellStyle}>
      <H1>{reportTitle}</H1>

      {compare && purchaseCmp && purchasesCmp && activeCmp && betsCmp ? (
        <Stack gap={12}>
          <Card style={surfaceStyle}>
            <CardHeader>Summary</CardHeader>
            <CardBody>
              <Stack gap={10}>
                <Text>
                  Both groups spent less after 7 Jul.{" "}
                  {toneSpan(
                    `Purchase $/day Gift vs Rest (median) ${fmtSigned(purchaseCmp.didMedian, true)}`,
                    purchaseCmp.didMedian
                  )}
                  {" - "}Gift held up better than Rest on the typical player.
                </Text>
                <Text>
                  {toneSpan(
                    `SC bets/day Gift vs Rest (median) ${fmtSigned(betsCmp.didMedian, true)}`,
                    betsCmp.didMedian
                  )}
                  {" - "}stronger relative hold. Purchases/day and active rate
                  {" "}({toneSpan(fmtSigned(purchasesCmp.didMedian), purchasesCmp.didMedian)} purchases, {toneSpan(fmtSigned(activeCmp.didMedian), activeCmp.didMedian)} active)
                  {" - "}check against Rest carefully; not a broad absolute uplift.
                </Text>
              </Stack>
            </CardBody>
          </Card>

          <Text tone="secondary">Main table: median daily rate per player</Text>
          <Table
            headers={[
              "Metric",
              "Gift before - after",
              "Gift change",
              "Rest before - after",
              "Rest change",
              "Gift vs Rest",
            ]}
            columnAlign={["left", "right", "right", "right", "right", "right"]}
            striped
            rows={[
              [
                "Purchase ($)/day",
                `${fmtMoney(purchaseCmp.cohort.beforeMedian)} - ${fmtMoney(purchaseCmp.cohort.afterMedian)}`,
                <span style={{ color: chgColor(purchaseCmp.cohort.deltaMedian), fontWeight: 600 }}>{fmtSigned(purchaseCmp.cohort.deltaMedian, true)}</span>,
                `${fmtMoney(purchaseCmp.rest.beforeMedian)} - ${fmtMoney(purchaseCmp.rest.afterMedian)}`,
                <span style={{ color: chgColor(purchaseCmp.rest.deltaMedian), fontWeight: 600 }}>{fmtSigned(purchaseCmp.rest.deltaMedian, true)}</span>,
                <span style={{ color: chgColor(purchaseCmp.didMedian), fontWeight: 700, background: purchaseCmp.didMedian >= 0 ? POS_BG : NEG_BG, padding: "2px 8px", borderRadius: 999 }}>{fmtSigned(purchaseCmp.didMedian, true)}</span>,
              ],
              [
                "Purchases/day",
                `${fmtNum(purchasesCmp.cohort.beforeMedian)} - ${fmtNum(purchasesCmp.cohort.afterMedian)}`,
                <span style={{ color: chgColor(purchasesCmp.cohort.deltaMedian), fontWeight: 600 }}>{fmtSigned(purchasesCmp.cohort.deltaMedian)}</span>,
                `${fmtNum(purchasesCmp.rest.beforeMedian)} - ${fmtNum(purchasesCmp.rest.afterMedian)}`,
                <span style={{ color: chgColor(purchasesCmp.rest.deltaMedian), fontWeight: 600 }}>{fmtSigned(purchasesCmp.rest.deltaMedian)}</span>,
                <span style={{ color: chgColor(purchasesCmp.didMedian), fontWeight: 700, background: purchasesCmp.didMedian >= 0 ? POS_BG : NEG_BG, padding: "2px 8px", borderRadius: 999 }}>{fmtSigned(purchasesCmp.didMedian)}</span>,
              ],
              [
                "Active rate/day",
                `${fmtNum(activeCmp.cohort.beforeMedian)} - ${fmtNum(activeCmp.cohort.afterMedian)}`,
                <span style={{ color: chgColor(activeCmp.cohort.deltaMedian), fontWeight: 600 }}>{fmtSigned(activeCmp.cohort.deltaMedian)}</span>,
                `${fmtNum(activeCmp.rest.beforeMedian)} - ${fmtNum(activeCmp.rest.afterMedian)}`,
                <span style={{ color: chgColor(activeCmp.rest.deltaMedian), fontWeight: 600 }}>{fmtSigned(activeCmp.rest.deltaMedian)}</span>,
                <span style={{ color: chgColor(activeCmp.didMedian), fontWeight: 700, background: activeCmp.didMedian >= 0 ? POS_BG : NEG_BG, padding: "2px 8px", borderRadius: 999 }}>{fmtSigned(activeCmp.didMedian)}</span>,
              ],
              [
                "SC bets/day",
                `${fmtMoney(betsCmp.cohort.beforeMedian)} - ${fmtMoney(betsCmp.cohort.afterMedian)}`,
                <span style={{ color: chgColor(betsCmp.cohort.deltaMedian), fontWeight: 600 }}>{fmtSigned(betsCmp.cohort.deltaMedian, true)}</span>,
                `${fmtMoney(betsCmp.rest.beforeMedian)} - ${fmtMoney(betsCmp.rest.afterMedian)}`,
                <span style={{ color: chgColor(betsCmp.rest.deltaMedian), fontWeight: 600 }}>{fmtSigned(betsCmp.rest.deltaMedian, true)}</span>,
                <span style={{ color: chgColor(betsCmp.didMedian), fontWeight: 700, background: betsCmp.didMedian >= 0 ? POS_BG : NEG_BG, padding: "2px 8px", borderRadius: 999 }}>{fmtSigned(betsCmp.didMedian, true)}</span>,
              ],
            ]}
          />

          <H2>Elite Gift vs Rest (Avg per player)</H2>
          <Grid columns={2} gap={16}>
            <Card style={surfaceStyle}>
              <CardHeader>Elite Gift</CardHeader>
              <CardBody>
                <BarChart
                  categories={["Purchase ($)", "Purchases", "Active rate", "SC bets"]}
                  series={[
                    {
                      name: "Before",
                      data: [
                        purchaseCmp.cohort.beforeMean,
                        purchasesCmp.cohort.beforeMean,
                        activeCmp.cohort.beforeMean,
                        betsCmp.cohort.beforeMean,
                      ],
                      tone: "neutral",
                    },
                    {
                      name: "After",
                      data: [
                        purchaseCmp.cohort.afterMean,
                        purchasesCmp.cohort.afterMean,
                        activeCmp.cohort.afterMean,
                        betsCmp.cohort.afterMean,
                      ],
                      tone: "info",
                    },
                  ]}
                  height={280}
                  showValues
                />
              </CardBody>
            </Card>
            <Card style={surfaceStyle}>
              <CardHeader>Rest</CardHeader>
              <CardBody>
                <BarChart
                  categories={["Purchase ($)", "Purchases", "Active rate", "SC bets"]}
                  series={[
                    {
                      name: "Before",
                      data: [
                        purchaseCmp.rest.beforeMean,
                        purchasesCmp.rest.beforeMean,
                        activeCmp.rest.beforeMean,
                        betsCmp.rest.beforeMean,
                      ],
                      tone: "neutral",
                    },
                    {
                      name: "After",
                      data: [
                        purchaseCmp.rest.afterMean,
                        purchasesCmp.rest.afterMean,
                        activeCmp.rest.afterMean,
                        betsCmp.rest.afterMean,
                      ],
                      tone: "danger",
                    },
                  ]}
                  height={280}
                  showValues
                />
              </CardBody>
            </Card>
          </Grid>
        </Stack>
      ) : null}

      <Stack gap={10}>
        <Row gap={12} style={{ alignItems: "center", justifyContent: "space-between", flexWrap: "wrap" }}>
          <H2>Per-Player Split</H2>
          <Pill active={showPlayerList} onClick={() => setShowPlayerList(!showPlayerList)}>
            {showPlayerList ? "Hide list" : "Show list"}
          </Pill>
        </Row>
        <Row gap={8} style={{ flexWrap: "wrap" }}>
          <Pill active={direction === "all"} onClick={() => setDirection("all")}>All ({allCount})</Pill>
          <Pill active={direction === "up"} onClick={() => setDirection("up")}>
            <span style={{ color: POS, fontWeight: 700 }}>Uplift ({upliftCount})</span>
          </Pill>
          <Pill active={direction === "down"} onClick={() => setDirection("down")}>
            <span style={{ color: NEG, fontWeight: 700 }}>Decrease ({downCount})</span>
          </Pill>
        </Row>
        <Row gap={8} style={{ flexWrap: "wrap" }}>
          <Pill active={amFilter === "all"} onClick={() => setAmFilter("all")}>All AMs</Pill>
          {amOptions.map((name) => (
            <Pill key={name} active={amFilter === name} onClick={() => setAmFilter(name)}>
              {name} ({DATA.players.filter((p) => amName(p.agent) === name).length})
            </Pill>
          ))}
        </Row>
        <Text tone="secondary">
          {filteredPlayers.length} players
          {direction === "up" ? " · sorted best uplift first" : ""}
          {direction === "down" ? " · sorted biggest decrease first" : ""}
        </Text>

        {showPlayerList
          ? filteredPlayers.map((p) => {
              const dir = purchaseDirection(p);
              const am = amName(p.agent);
              const dirLabel = dir === "up" ? "UPLIFT" : dir === "down" ? "DECREASE" : "FLAT";
              const dirColor = dir === "up" ? POS : dir === "down" ? NEG : T.text.secondary;
              return (
                <CollapsibleSection
                  key={p.aid}
                  title={`AID ${p.aid}`}
                  trailing={
                    <Row gap={12} style={{ alignItems: "center", flexWrap: "wrap" }}>
                      <span style={{ color: T.text.secondary, fontSize: 13 }}>AM {am}</span>
                      <span
                        style={{
                          color: dirColor,
                          fontWeight: 700,
                          fontSize: 12,
                          padding: "2px 8px",
                          borderRadius: 999,
                          background: dir === "up" ? POS_BG : dir === "down" ? NEG_BG : T.fill.tertiary,
                        }}
                      >
                        {dirLabel}
                      </span>
                      <span style={{ color: T.text.secondary, fontSize: 13 }}>LT {fmtMoney(p.ltPurchase)}</span>
                      <span style={{ color: T.text.secondary, fontSize: 13 }}>Hold {p.hold}</span>
                      <span style={{ color: chgColor(p.purchasePct), fontWeight: 700, fontSize: 13 }}>
                        {fmtPct(p.purchasePct)}
                      </span>
                    </Row>
                  }
                  defaultOpen={false}
                  style={{
                    ...surfaceStyle,
                    padding: "6px 10px",
                    borderLeft: `4px solid ${dir === "up" ? POS : dir === "down" ? NEG : T.stroke.secondary}`,
                  }}
                >
                  <Table
                    headers={["Metric", "Before", "After", "Diff", "Change"]}
                    columnAlign={["left", "right", "right", "right", "right"]}
                    rows={playerMetricRows(p).map((row) => [
                      row.metric,
                      badge(row.before, BEFORE_BG, BEFORE_FG),
                      badge(row.after, AFTER_BG, AFTER_FG),
                      <span style={{ color: chgColor(row.pctNum), fontWeight: 600 }}>{row.diff}</span>,
                      <span style={{ color: chgColor(row.pctNum), fontWeight: 600 }}>{row.pct}</span>,
                    ])}
                  />
                </CollapsibleSection>
              );
            })
          : null}
      </Stack>

      <Stack gap={12}>
        <H2>All Players ({filteredPlayers.length})</H2>
        <Table
          headers={["AID", "AM", "Direction", "LT Purchase", "Hold", "Purchase", "Purchases", "Active days", "SC bets"]}
          columnAlign={["left", "left", "left", "right", "right", "right", "right", "right", "right"]}
          striped
          stickyHeader
          rowTone={filteredPlayers.map((p) => {
            const dir = purchaseDirection(p);
            return dir === "up" ? "success" : dir === "down" ? "danger" : "neutral";
          })}
          rows={filteredPlayers.map((p) => {
            const dir = purchaseDirection(p);
            return [
              p.aid,
              amName(p.agent),
              <span style={{ color: dir === "up" ? POS : dir === "down" ? NEG : T.text.secondary, fontWeight: 700 }}>
                {dir === "up" ? "UPLIFT" : dir === "down" ? "DECREASE" : "FLAT"}
              </span>,
              fmtMoney(p.ltPurchase),
              p.hold,
              `${fmtMoney(p.purchaseBefore)} - ${fmtMoney(p.purchaseAfter)} (${fmtPct(p.purchasePct)})`,
              `${fmtNum(p.purchasesBefore)} - ${fmtNum(p.purchasesAfter)}`,
              `${fmtNum(p.activeBefore)} - ${fmtNum(p.activeAfter)}`,
              `${fmtMoney(p.betsBefore)} - ${fmtMoney(p.betsAfter)}`,
            ];
          })}
        />

        <H2>Summary</H2>
        <Text tone="secondary">
          n={filteredPlayers.length}
          {" · "}
          <span style={{ color: POS, fontWeight: 700 }}>Uplift {filteredUplift}</span>
          {" · "}
          <span style={{ color: NEG, fontWeight: 700 }}>Decrease {filteredDown}</span>
          {" · "}Flat {filteredFlat}
          {!useFullSummary ? " · filtered view" : ""}
        </Text>
        <Grid columns={4} gap={12}>
          <div style={statStyle}>
            <Stat
              label="Avg purchase"
              value={`${fmtMoney(filterSummary.purchaseBefore)} - ${fmtMoney(filterSummary.purchaseAfter)}`}
              detail={fmtPct(filterPct.purchase)}
            />
          </div>
          <div style={statStyle}>
            <Stat
              label="Avg purchases"
              value={`${fmtNum(filterSummary.purchasesBefore)} - ${fmtNum(filterSummary.purchasesAfter)}`}
              detail={fmtPct(filterPct.purchases)}
            />
          </div>
          <div style={statStyle}>
            <Stat
              label="Avg active days"
              value={`${fmtNum(filterSummary.activeBefore)} - ${fmtNum(filterSummary.activeAfter)}`}
              detail={fmtPct(filterPct.active)}
            />
          </div>
          <div style={statStyle}>
            <Stat
              label="Avg SC bets"
              value={`${fmtMoney(filterSummary.betsBefore)} - ${fmtMoney(filterSummary.betsAfter)}`}
              detail={fmtPct(filterPct.bets)}
            />
          </div>
        </Grid>
      </Stack>
    </Stack>
  );
}
'''

FULL_HEADER = '''import {
  BarChart,
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
  beforeFrom: string;
  beforeTo: string;
  afterFrom: string;
  afterTo: string;
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
  title: string;
  periods: { beforeFrom: string; beforeTo: string; afterFrom: string; afterTo: string };
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
  const periods = DATA.periods;
  const reportTitle = DATA.title || "Elite Birthday Gift Activity";

  const chartData = [
    { label: "Purchase ($)", before: summary.purchase_amount.avgBefore, after: summary.purchase_amount.avgAfter },
    { label: "Purchases", before: summary.number_of_purchases.avgBefore, after: summary.number_of_purchases.avgAfter },
    { label: "Active days", before: summary.active_days.avgBefore, after: summary.active_days.avgAfter },
    { label: "SC bets", before: summary.total_sc_bets.avgBefore, after: summary.total_sc_bets.avgAfter },
  ];

  return (
    <Stack gap={20}>
      <Stack gap={6}>
        <H1>{reportTitle}</H1>
        <Text tone="secondary">
          Before {periods.beforeFrom} to {periods.beforeTo} · After {periods.afterFrom} to {periods.afterTo}
        </Text>
      </Stack>

      <Row gap={8}>
        <Pill active={month === "all"} onClick={() => setMonth("all")}>All ({DATA.playerCount})</Pill>
        {Object.entries(DATA.monthCounts).map(([m, n]) => (
          <Pill key={m} active={month === m} onClick={() => setMonth(m)}>{m} ({n})</Pill>
        ))}
      </Row>

      <Grid columns={4} gap={12}>
        <Stat label="Avg purchase before" value={fmtMoney(summary.purchase_amount.avgBefore)} detail={`${fmtPct(summary.purchase_amount.avgPct)} after`} />
        <Stat label="Avg purchases before" value={fmtNum(summary.number_of_purchases.avgBefore)} detail={`${fmtPct(summary.number_of_purchases.avgPct)} after`} />
        <Stat label="Avg active days before" value={fmtNum(summary.active_days.avgBefore)} detail={`${fmtPct(summary.active_days.avgPct)} after`} />
        <Stat label="Avg SC bets before" value={fmtMoney(summary.total_sc_bets.avgBefore)} detail={`${fmtPct(summary.total_sc_bets.avgPct)} after`} />
      </Grid>

      <Card>
        <CardHeader trailing={<Text tone="secondary">n={summary.purchase_amount.players}</Text>}>
          Average before vs after
        </CardHeader>
        <CardBody>
          <BarChart
            title="Average metric levels (before vs after)"
            data={chartData}
            xKey="label"
            series={[
              { key: "before", label: "Before", tone: "neutral" },
              { key: "after", label: "After", tone: "accent" },
            ]}
            yLabel="Average value"
          />
        </CardBody>
      </Card>

      <H2>Player detail</H2>
      <Table
        headers={["AID", "Agent", "Gift month", "Gift date", "After days", "Purchase before", "Purchase after", "% chg"]}
        columnAlign={["left", "left", "left", "left", "right", "right", "right", "right"]}
        striped
        stickyHeader
        rows={players.map((p) => [
          p.aid,
          p.agent,
          p.giftMonth,
          p.giftDate || "—",
          String(p.afterDays),
          fmtMoney(p.purchaseBefore),
          fmtMoney(p.purchaseAfter),
          fmtPct(p.purchasePct),
        ])}
      />
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
    parser.add_argument(
        "--canvas-name",
        default=None,
        help="Canvas filename stem (default derived from input)",
    )
    parser.add_argument(
        "--title",
        default=None,
        help="Report title shown in the canvas header",
    )
    parser.add_argument(
        "--compare-json",
        default=None,
        help="Optional vs-rest-Elite comparison JSON from compare_anniversary_vs_rest_elite.py",
    )
    args = parser.parse_args()

    csv_path = Path(args.input)
    if not csv_path.is_absolute():
        csv_path = ROOT / csv_path
    summary_path = csv_path.with_name(csv_path.stem + "_summary.csv")
    cohort_mode = "cohort" in csv_path.stem or "anniversary" in csv_path.stem

    compare = None
    if args.compare_json:
        cmp_path = Path(args.compare_json)
        if not cmp_path.is_absolute():
            cmp_path = ROOT / cmp_path
        compare = json.loads(cmp_path.read_text(encoding="utf-8"))

    payload = build_payload(
        csv_path, summary_path, cohort_mode, title=args.title, compare=compare
    )
    PAYLOAD_PATH.write_text(json.dumps(payload), encoding="utf-8")

    canvas_stem = args.canvas_name or csv_path.stem.replace(
        "birthday_gift_activity_", "elite-birthday-gift-"
    ).replace("_", "-")
    canvas_path = CANVAS_DIR / f"{canvas_stem}.canvas.tsx"

    if cohort_mode:
        canvas = COHORT_HEADER + json.dumps(payload) + COHORT_FOOTER
    else:
        canvas = FULL_HEADER + json.dumps(payload) + FULL_FOOTER
    canvas_path.write_text(canvas, encoding="utf-8")
    print(canvas_path)


if __name__ == "__main__":
    main()
