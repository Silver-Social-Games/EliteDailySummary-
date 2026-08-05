"""Generate birthday gift canvas from export CSV."""
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXPORT_DIR = ROOT / "birthday_gift" / "exports"
PAYLOAD_PATH = EXPORT_DIR / "canvas_payload.json"
CANVAS_DIR = Path(
    r"C:\Users\Owner\.cursor\projects\c-Users-Owner-Downloads-Elite\canvases"
)

DEFAULT_LOOKER_ACCOUNT_PORTAL_URL = (
    "https://lookerpatrianna.cloud.looker.com/dashboards/5207?Account+ID+={aid}"
)

METRIC_KEYS = {
    "Purchase amount ($)": "purchase_amount",
    "Number of purchases": "number_of_purchases",
    "Active days": "active_days",
    "Total SC bets": "total_sc_bets",
}


def looker_account_portal_url(aid: object) -> str:
    """Looker Jackpota Account Portal for an AID. Template uses {aid} or {account_id}."""
    aid_s = str(aid or "").strip()
    if not aid_s:
        return ""
    template = os.environ.get("LOOKER_ACCOUNT_PORTAL_URL", DEFAULT_LOOKER_ACCOUNT_PORTAL_URL)
    return template.format(aid=aid_s, account_id=aid_s)


def load_players(csv_path: Path) -> list[dict]:
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    players = []

    def pct(val: str) -> float | None:
        return float(val) if val else None

    for r in rows:
        aid = r["AID"]
        players.append(
            {
                "aid": aid,
                "aidUrl": looker_account_portal_url(aid),
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
  Link,
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
  aidUrl: string;
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

const fmtMoney = (n: number) => `$${Math.round(n).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
const fmtInt = (n: number) => Math.round(n).toLocaleString(undefined, { maximumFractionDigits: 0 });
const fmtNum = (n: number) => n.toLocaleString(undefined, { maximumFractionDigits: 1 });
const fmtPct = (n: number | null) => (n == null ? "—" : `${n > 0 ? "+" : ""}${n.toFixed(1)}%`);
const chgColor = (n: number | null) => (n == null || n === 0 ? T.text.secondary : n > 0 ? POS : NEG);
const fmtDiffMoney = (n: number) => `${n > 0 ? "+" : ""}${fmtMoney(n)}`;
const fmtDiffInt = (n: number) => `${n > 0 ? "+" : ""}${fmtInt(n)}`;
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
const sortByPurchasePct = (a: PlayerRow, b: PlayerRow, asc: boolean) => {
  const ap = a.purchasePct ?? (asc ? Number.POSITIVE_INFINITY : Number.NEGATIVE_INFINITY);
  const bp = b.purchasePct ?? (asc ? Number.POSITIVE_INFINITY : Number.NEGATIVE_INFINITY);
  if (ap !== bp) return asc ? ap - bp : bp - ap;
  if (a.purchaseAfter !== b.purchaseAfter) {
    return asc ? a.purchaseAfter - b.purchaseAfter : b.purchaseAfter - a.purchaseAfter;
  }
  return a.aid.localeCompare(b.aid);
};
const aidLink = (p: PlayerRow) =>
  p.aidUrl ? <Link href={p.aidUrl}>{p.aid}</Link> : p.aid;

function playerMetricRows(p: PlayerRow) {
  return [
    { metric: "Purchase amount ($)", before: fmtMoney(p.purchaseBefore), after: fmtMoney(p.purchaseAfter), diff: fmtDiffMoney(p.purchaseDiff), pct: fmtPct(p.purchasePct), pctNum: p.purchasePct },
    { metric: "Number of purchases", before: fmtInt(p.purchasesBefore), after: fmtInt(p.purchasesAfter), diff: fmtDiffInt(p.purchasesDiff), pct: fmtPct(p.purchasesPct), pctNum: p.purchasesPct },
    { metric: "Active days", before: fmtInt(p.activeBefore), after: fmtInt(p.activeAfter), diff: fmtDiffInt(p.activeDiff), pct: fmtPct(p.activePct), pctNum: p.activePct },
    { metric: "Total SC bets", before: fmtMoney(p.betsBefore), after: fmtMoney(p.betsAfter), diff: fmtDiffMoney(p.betsDiff), pct: fmtPct(p.betsPct), pctNum: p.betsPct },
  ];
}

export default function EliteBirthdayGiftActivity() {
  const summary = DATA.summaryAll;
  const reportTitle = DATA.title || "Elite Gift Players vs Rest of Elite";
  const compare = DATA.compare;
  const [showPlayerList, setShowPlayerList] = useCanvasState<boolean>("showPlayerList", true);

  const byKey = Object.fromEntries((compare?.metrics ?? []).map((m) => [m.key, m]));
  const purchaseCmp = byKey.purchase;
  const purchasesCmp = byKey.purchases;
  const activeCmp = byKey.active;
  const betsCmp = byKey.sc_bets;

  const players = DATA.players
    .slice()
    .sort((a, b) => sortByPurchasePct(a, b, false));

  const upliftCount = players.filter((p) => purchaseDirection(p) === "up").length;
  const downCount = players.filter((p) => purchaseDirection(p) === "down").length;
  const flatCount = players.filter((p) => purchaseDirection(p) === "flat").length;

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

          <H2>Elite Gift vs Rest (Avg Per Player)</H2>
          <Grid columns={2} gap={16}>
            <Card style={surfaceStyle}>
              <CardHeader>Elite Gift</CardHeader>
              <CardBody>
                <BarChart
                  categories={["Purchase ($)", "Purchases", "Active Rate", "SC Bets"]}
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
                  categories={["Purchase ($)", "Purchases", "Active Rate", "SC Bets"]}
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
        <Text tone="secondary">
          {players.length} player{players.length === 1 ? "" : "s"}
          {" · "}sorted by purchase % (high → low)
        </Text>

        {showPlayerList
          ? players.map((p) => {
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
        <H2>All Players ({players.length})</H2>
        <Table
          headers={["AID", "AM", "Direction", "LT Purchase", "Hold", "Purchase", "Purchases", "Active Days", "SC Bets"]}
          columnAlign={["left", "left", "left", "right", "right", "right", "right", "right", "right"]}
          striped
          stickyHeader
          rowTone={players.map((p) => {
            const dir = purchaseDirection(p);
            return dir === "up" ? "success" : dir === "down" ? "danger" : "neutral";
          })}
          rows={players.map((p) => {
            const dir = purchaseDirection(p);
            return [
              aidLink(p),
              amName(p.agent),
              <span style={{ color: dir === "up" ? POS : dir === "down" ? NEG : T.text.secondary, fontWeight: 700 }}>
                {dir === "up" ? "UPLIFT" : dir === "down" ? "DECREASE" : "FLAT"}
              </span>,
              fmtMoney(p.ltPurchase),
              p.hold,
              `${fmtMoney(p.purchaseBefore)} - ${fmtMoney(p.purchaseAfter)} (${fmtPct(p.purchasePct)})`,
              `${fmtInt(p.purchasesBefore)} - ${fmtInt(p.purchasesAfter)}`,
              `${fmtInt(p.activeBefore)} - ${fmtInt(p.activeAfter)}`,
              `${fmtMoney(p.betsBefore)} - ${fmtMoney(p.betsAfter)}`,
            ];
          })}
        />

        <H2>Summary</H2>
        <Text tone="secondary">
          n={players.length}
          {" · "}
          <span style={{ color: POS, fontWeight: 700 }}>Uplift {upliftCount}</span>
          {" · "}
          <span style={{ color: NEG, fontWeight: 700 }}>Decrease {downCount}</span>
          {" · "}Flat {flatCount}
        </Text>
        <Grid columns={4} gap={12}>
          <div style={statStyle}>
            <Stat
              label="Avg Purchase"
              value={`${fmtMoney(summary.purchase_amount.avgBefore)} - ${fmtMoney(summary.purchase_amount.avgAfter)}`}
              detail={fmtPct(summary.purchase_amount.avgPct)}
            />
          </div>
          <div style={statStyle}>
            <Stat
              label="Avg Purchases"
              value={`${fmtInt(summary.number_of_purchases.avgBefore)} - ${fmtInt(summary.number_of_purchases.avgAfter)}`}
              detail={fmtPct(summary.number_of_purchases.avgPct)}
            />
          </div>
          <div style={statStyle}>
            <Stat
              label="Avg Active Days"
              value={`${fmtInt(summary.active_days.avgBefore)} - ${fmtInt(summary.active_days.avgAfter)}`}
              detail={fmtPct(summary.active_days.avgPct)}
            />
          </div>
          <div style={statStyle}>
            <Stat
              label="Avg SC Bets"
              value={`${fmtMoney(summary.total_sc_bets.avgBefore)} - ${fmtMoney(summary.total_sc_bets.avgAfter)}`}
              detail={fmtPct(summary.total_sc_bets.avgPct)}
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
  H2,
  Link,
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
  aidUrl: string;
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

const fmtMoney = (n: number) => `$${Math.round(n).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
const fmtInt = (n: number) => Math.round(n).toLocaleString(undefined, { maximumFractionDigits: 0 });
const fmtPct = (n: number | null) => (n == null ? "-" : `${n > 0 ? "+" : ""}${n.toFixed(1)}%`);
const sortByPurchasePct = (a: PlayerRow, b: PlayerRow, asc: boolean) => {
  const ap = a.purchasePct ?? (asc ? Number.POSITIVE_INFINITY : Number.NEGATIVE_INFINITY);
  const bp = b.purchasePct ?? (asc ? Number.POSITIVE_INFINITY : Number.NEGATIVE_INFINITY);
  if (ap !== bp) return asc ? ap - bp : bp - ap;
  if (a.purchaseAfter !== b.purchaseAfter) {
    return asc ? a.purchaseAfter - b.purchaseAfter : b.purchaseAfter - a.purchaseAfter;
  }
  return a.aid.localeCompare(b.aid);
};
const aidLink = (p: PlayerRow) =>
  p.aidUrl ? <Link href={p.aidUrl}>{p.aid}</Link> : p.aid;

export default function EliteBirthdayGiftActivity() {
  const [month, setMonth] = useCanvasState<string>("month", "all");
  const summary = month === "all" ? DATA.summaryAll : (DATA.summaryByMonth[month] ?? DATA.summaryAll);
  const monthPlayers = month === "all" ? DATA.players : DATA.players.filter((p) => p.giftMonth === month);
  const players = monthPlayers
    .slice()
    .sort((a, b) => sortByPurchasePct(a, b, false));
  const periods = DATA.periods;
  const reportTitle = DATA.title || "Elite Birthday Gift Activity";

  return (
    <Stack gap={20}>
      <Stack gap={6}>
        <H1>{reportTitle}</H1>
        <Text tone="secondary">
          Before {periods.beforeFrom} to {periods.beforeTo} · After {periods.afterFrom} to {periods.afterTo}
          {" · "}n={monthPlayers.length}
        </Text>
      </Stack>

      {Object.keys(DATA.monthCounts).length > 1 ? (
        <Row gap={8}>
          <Pill active={month === "all"} onClick={() => setMonth("all")}>All ({DATA.playerCount})</Pill>
          {Object.entries(DATA.monthCounts).map(([m, n]) => (
            <Pill key={m} active={month === m} onClick={() => setMonth(m)}>{m} ({n})</Pill>
          ))}
        </Row>
      ) : null}

      <Grid columns={4} gap={12}>
        <Stat
          label="Avg Purchase"
          value={`${fmtMoney(summary.purchase_amount.avgBefore)} - ${fmtMoney(summary.purchase_amount.avgAfter)}`}
          detail={fmtPct(summary.purchase_amount.avgPct)}
        />
        <Stat
          label="Avg Purchases"
          value={`${fmtInt(summary.number_of_purchases.avgBefore)} - ${fmtInt(summary.number_of_purchases.avgAfter)}`}
          detail={fmtPct(summary.number_of_purchases.avgPct)}
        />
        <Stat
          label="Avg Active Days"
          value={`${fmtInt(summary.active_days.avgBefore)} - ${fmtInt(summary.active_days.avgAfter)}`}
          detail={fmtPct(summary.active_days.avgPct)}
        />
        <Stat
          label="Avg SC Bets"
          value={`${fmtMoney(summary.total_sc_bets.avgBefore)} - ${fmtMoney(summary.total_sc_bets.avgAfter)}`}
          detail={fmtPct(summary.total_sc_bets.avgPct)}
        />
      </Grid>

      <Card>
        <CardHeader trailing={<Text tone="secondary">n={summary.purchase_amount.players}</Text>}>
          Average Before vs After
        </CardHeader>
        <CardBody>
          <BarChart
            categories={["Purchase ($)", "Purchases", "Active Days", "SC Bets"]}
            series={[
              {
                name: "Before",
                data: [
                  summary.purchase_amount.avgBefore,
                  summary.number_of_purchases.avgBefore,
                  summary.active_days.avgBefore,
                  summary.total_sc_bets.avgBefore,
                ],
                tone: "neutral",
              },
              {
                name: "After",
                data: [
                  summary.purchase_amount.avgAfter,
                  summary.number_of_purchases.avgAfter,
                  summary.active_days.avgAfter,
                  summary.total_sc_bets.avgAfter,
                ],
                tone: "info",
              },
            ]}
            height={280}
            showValues
          />
        </CardBody>
      </Card>

      <Stack gap={10}>
        <H2>Player Data</H2>
        <Text tone="secondary">
          {players.length} player{players.length === 1 ? "" : "s"}
          {" · "}values shown as before - after · sorted by purchase % (high → low)
        </Text>
        <Table
          headers={["AID", "AM", "LT Purchase", "Hold", "Purchase", "Purchases", "Active Days", "SC Bets", "% Purchase"]}
          columnAlign={["left", "left", "right", "right", "right", "right", "right", "right", "right"]}
          striped
          stickyHeader
          rows={players.map((p) => [
            aidLink(p),
            p.agent,
            fmtMoney(p.ltPurchase),
            p.hold,
            `${fmtMoney(p.purchaseBefore)} - ${fmtMoney(p.purchaseAfter)}`,
            `${fmtInt(p.purchasesBefore)} - ${fmtInt(p.purchasesAfter)}`,
            `${fmtInt(p.activeBefore)} - ${fmtInt(p.activeAfter)}`,
            `${fmtMoney(p.betsBefore)} - ${fmtMoney(p.betsAfter)}`,
            fmtPct(p.purchasePct),
          ])}
        />
      </Stack>
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
