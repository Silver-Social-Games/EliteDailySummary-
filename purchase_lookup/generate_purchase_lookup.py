"""
Elite purchase lookup — order-level history with offer codes, GC/SC, free spins.

Usage:
  python purchase_lookup/generate_purchase_lookup.py --aid 458523630
  python purchase_lookup/generate_purchase_lookup.py --elite --from 2026-06-26 --to 2026-07-02
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from elite_lib import (  # noqa: E402
    PROJECT_ID,
    get_client,
    latest_elite_tags_cte,
    run_query,
)

MODULE_DIR = Path(__file__).resolve().parent
EXPORT_DIR = MODULE_DIR / "exports"
HANDOFFS_DIR = MODULE_DIR / "handoffs"
DEFAULT_CANVAS_DIR = Path(
    r"C:\Users\Owner\.cursor\projects\c-Users-Owner-Downloads-Elite\canvases"
)

DEFAULT_WINDOW_DAYS = 30
ELITE_MAX_DAYS = 7

TABLE_COLUMNS = [
    "aid",
    "fullName",
    "agent",
    "offerCode",
    "offerTitle",
    "purchaseDate",
    "purchaseTs",
    "amountUsd",
    "scAmount",
    "scBonus",
    "gcAmount",
    "freeSpins",
    "fsLinked",
]


def _iso(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _num(value: object, decimals: int = 2) -> float:
    if value is None:
        return 0.0
    return round(float(value), decimals)


def _fmt_usd(value: float) -> str:
    return f"${value:,.2f}"


def _slug(meta: dict) -> str:
    if meta.get("aid"):
        return str(meta["aid"])
    if meta.get("agent"):
        return f"elite-{meta['agent']}"
    return "elite-book"


def build_orders_sql(
    date_from: date,
    date_to: date,
    aid: int | None = None,
    elite_only: bool = False,
    agent: str | None = None,
) -> str:
    aid_filter = f"AND p.account_id = {aid}" if aid else ""
    agent_filter = f"AND t.tag_agent_1 = '{agent}'" if agent else ""
    tags_cte = latest_elite_tags_cte(cte_name="latest_tags")
    elite_join = ""
    elite_where = ""
    if elite_only:
        elite_join = f"""
    INNER JOIN `{PROJECT_ID}.dbt_aninditac.elite` e ON e.account_id = p.account_id
    INNER JOIN latest_tags el ON el.account_id = p.account_id
        """
        elite_where = "AND el.tag_agent_1 IS NOT NULL"

    return f"""
    WITH {tags_cte}
    SELECT
      p.account_id AS aid,
      COALESCE(CONCAT(per.first_name, ' ', per.last_name), ua.name) AS full_name,
      t.tag_agent_1 AS agent,
      COALESCE(h.code, CAST(p.offer_id AS STRING)) AS offer_code,
      h.title AS offer_title,
      DATE(p.created_at) AS purchase_date,
      DATETIME(p.created_at) AS purchase_ts,
      ROUND(p.amount, 2) AS amount_usd,
      ROUND(p.sc_amount, 2) AS sc_amount,
      ROUND(GREATEST(p.sc_amount - p.amount, 0), 2) AS sc_bonus,
      ROUND(p.gc_amount, 2) AS gc_amount,
      p.id AS order_id
    FROM `{PROJECT_ID}.transactional_data.payment_payment_orders` p
    LEFT JOIN `{PROJECT_ID}.transactional_data.payment_offer_templates` h
      ON h.id = p.offer_id
    LEFT JOIN `{PROJECT_ID}.transactional_data.uam_accounts` ua
      ON ua.id = p.account_id
    LEFT JOIN `{PROJECT_ID}.transactional_data.uam_persons` per
      ON ua.person_id = per.id
    LEFT JOIN latest_tags t ON t.account_id = p.account_id
    {elite_join}
    WHERE p.status = 'succeeded'
      AND COALESCE(p.refunded, FALSE) = FALSE
      AND DATE(p.created_at) BETWEEN DATE '{date_from.isoformat()}' AND DATE '{date_to.isoformat()}'
      {aid_filter}
      {agent_filter}
      {elite_where}
    ORDER BY purchase_ts DESC
    """


def build_freespin_sql(
    date_from: date,
    date_to: date,
    aids: list[int] | None = None,
) -> str:
    aid_filter = ""
    if aids:
        aid_list = ", ".join(str(a) for a in aids)
        aid_filter = f"AND r.account_id IN ({aid_list})"

  # Widen reward_date window — FS from a purchase can post up to a few days later.
    reward_from = (date_from - timedelta(days=1)).isoformat()
    reward_to = (date_to + timedelta(days=5)).isoformat()

    return f"""
    SELECT
      r.account_id AS aid,
      r.reward_date,
      r.campaign_code,
      r.campaign_title,
      SUM(COALESCE(r.reward_count, 1)) AS reward_count,
      SUM(COALESCE(r.total_spins, 0)) AS total_spins
    FROM `{PROJECT_ID}.jackpota_agg.fact_rewards` r
    WHERE r.reward_date BETWEEN DATE '{reward_from}' AND DATE '{reward_to}'
      AND (
        LOWER(COALESCE(r.product_title, '')) = 'freespin'
        OR LOWER(COALESCE(r.product_type, '')) = 'freespin'
      )
      {aid_filter}
    GROUP BY r.account_id, r.reward_date, r.campaign_code, r.campaign_title
    """


def campaign_matches_offer(campaign_code: str, offer_code: str) -> bool:
    if not campaign_code or not offer_code:
        return False
    cc = campaign_code.lower()
    oc = offer_code.lower()
    if oc in cc:
        return True
    # Strip trailing _NN suffix used on daily-deal FS campaigns.
    base = re.sub(r"_\d+$", "", oc)
    return base in cc


def date_matches_purchase(
    purchase_date: str,
    reward_date: str,
    campaign_code: str,
) -> bool:
    if purchase_date == reward_date:
        return True
    # Campaigns like 20260626_dd_fr_... embed the purchase calendar day.
    compact = purchase_date.replace("-", "")
    if campaign_code.startswith(compact):
        return True
    try:
        p_dt = date.fromisoformat(purchase_date)
        r_dt = date.fromisoformat(reward_date)
    except ValueError:
        return False
    delta = (r_dt - p_dt).days
    return 0 <= delta <= 5


def normalize_order(row: dict) -> dict:
    return {
        "aid": str(row["aid"]),
        "fullName": row.get("full_name") or "",
        "agent": row.get("agent") or "",
        "offerCode": row.get("offer_code") or "",
        "offerTitle": row.get("offer_title") or "",
        "purchaseDate": _iso(row.get("purchase_date")),
        "purchaseTs": _iso(row.get("purchase_ts")),
        "amountUsd": _num(row.get("amount_usd")),
        "scAmount": _num(row.get("sc_amount")),
        "scBonus": _num(row.get("sc_bonus")),
        "gcAmount": _num(row.get("gc_amount")),
        "freeSpins": 0,
        "fsLinked": "no",
        "orderId": str(row.get("order_id") or ""),
    }


def merge_freespins(orders: list[dict], freespin_rows: list[dict]) -> list[dict]:
    if not freespin_rows:
        return orders

    fs_rows: list[dict] = []
    for fs in freespin_rows:
        spin_count = int(fs.get("total_spins") or 0) or int(fs.get("reward_count") or 1)
        fs_rows.append(
            {
                "aid": str(fs["aid"]),
                "reward_date": _iso(fs.get("reward_date")),
                "campaign_code": str(fs.get("campaign_code") or ""),
                "campaign_title": str(fs.get("campaign_title") or ""),
                "spin_count": spin_count,
            }
        )

    used_fs: set[tuple[str, str]] = set()

    for order in orders:
        matched = [
            fs
            for fs in fs_rows
            if fs["aid"] == order["aid"]
            and campaign_matches_offer(fs["campaign_code"], order["offerCode"])
            and date_matches_purchase(
                order["purchaseDate"], fs["reward_date"], fs["campaign_code"]
            )
        ]
        if matched:
            order["freeSpins"] = sum(fs["spin_count"] for fs in matched)
            order["fsLinked"] = "yes"
            for fs in matched:
                used_fs.add((fs["aid"], fs["campaign_code"]))

    # Aggregate unlinked FS by campaign (not per raw reward row).
    unlinked_totals: dict[tuple[str, str, str], dict] = {}
    sample_by_aid = {o["aid"]: o for o in orders}
    for fs in fs_rows:
        key = (fs["aid"], fs["campaign_code"])
        if key in used_fs:
            continue
        bucket = (fs["aid"], fs["reward_date"], fs["campaign_code"])
        if bucket not in unlinked_totals:
            unlinked_totals[bucket] = {
                "aid": fs["aid"],
                "reward_date": fs["reward_date"],
                "campaign_code": fs["campaign_code"],
                "campaign_title": fs["campaign_title"],
                "spin_count": 0,
            }
        unlinked_totals[bucket]["spin_count"] += fs["spin_count"]

    extra: list[dict] = []
    for row in unlinked_totals.values():
        sample_order = sample_by_aid.get(row["aid"])
        extra.append(
            {
                "aid": row["aid"],
                "fullName": sample_order["fullName"] if sample_order else "",
                "agent": sample_order["agent"] if sample_order else "",
                "offerCode": row["campaign_code"] or "unlinked_fs",
                "offerTitle": f"Unlinked FS — {row['campaign_title'] or 'freespin'}",
                "purchaseDate": row["reward_date"],
                "purchaseTs": f"{row['reward_date']} (FS reward)",
                "amountUsd": 0.0,
                "scAmount": 0.0,
                "scBonus": 0.0,
                "gcAmount": 0.0,
                "freeSpins": row["spin_count"],
                "fsLinked": "unlinked",
                "orderId": "",
            }
        )

    return orders + extra


def summarize_by_offer(orders: list[dict]) -> list[dict]:
    purchase_orders = [o for o in orders if o.get("fsLinked") != "unlinked"]
    totals: dict[str, dict] = {}
    for o in purchase_orders:
        code = o["offerCode"] or "(unknown)"
        if code not in totals:
            totals[code] = {
                "offerCode": code,
                "offerTitle": o.get("offerTitle") or "",
                "orders": 0,
                "totalPurchased": 0.0,
                "totalSc": 0.0,
                "totalGc": 0.0,
                "totalFs": 0,
            }
        totals[code]["orders"] += 1
        totals[code]["totalPurchased"] += o["amountUsd"]
        totals[code]["totalSc"] += o["scAmount"]
        totals[code]["totalGc"] += o["gcAmount"]
        totals[code]["totalFs"] += o.get("freeSpins") or 0

    ranked = sorted(totals.values(), key=lambda x: x["totalPurchased"], reverse=True)
    total_spend = sum(r["totalPurchased"] for r in ranked) or 1.0
    for r in ranked:
        r["pctOfSpend"] = round(100 * r["totalPurchased"] / total_spend, 1)
        r["totalPurchasedFmt"] = _fmt_usd(r["totalPurchased"])
    return ranked


def sample_orders() -> list[dict]:
    return [
        {
            "aid": "458523630",
            "fullName": "John O'Grady",
            "agent": "rachel_a",
            "offerCode": "1mgc_512sc_499_99",
            "offerTitle": "1M GC and 512 SC Offer",
            "purchaseDate": "2026-06-26",
            "purchaseTs": "2026-06-26 16:20:41",
            "amountUsd": 499.99,
            "scAmount": 512.0,
            "scBonus": 12.01,
            "gcAmount": 1000000.0,
            "freeSpins": 0,
            "fsLinked": "no",
            "orderId": "sample-1",
        },
        {
            "aid": "458523630",
            "fullName": "John O'Grady",
            "agent": "rachel_a",
            "offerCode": "dd_fr_480kg_240s_199_99_56",
            "offerTitle": "Daily Deal",
            "purchaseDate": "2026-06-26",
            "purchaseTs": "2026-06-26 16:20:23",
            "amountUsd": 199.99,
            "scAmount": 240.0,
            "scBonus": 40.01,
            "gcAmount": 480000.0,
            "freeSpins": 25,
            "fsLinked": "yes",
            "orderId": "sample-2",
        },
    ]


def fetch_data(
    date_from: date,
    date_to: date,
    aid: int | None,
    elite_only: bool,
    agent: str | None,
    no_query: bool,
) -> tuple[list[dict], list[dict]]:
    if no_query:
        orders = sample_orders()
        return orders, summarize_by_offer(orders)

    client = get_client()
    raw_orders = run_query(
        client,
        build_orders_sql(date_from, date_to, aid=aid, elite_only=elite_only, agent=agent),
    )
    orders = [normalize_order(r) for r in raw_orders]

    aids = list({int(o["aid"]) for o in orders})
    if aid is not None:
        aid_int = int(aid)
        if aid_int not in aids:
            aids.append(aid_int)
    freespin_rows: list[dict] = []
    if aids:
        freespin_rows = run_query(
            client,
            build_freespin_sql(date_from, date_to, aids=aids),
        )

    orders = merge_freespins(orders, freespin_rows)
    return orders, summarize_by_offer(orders)


def build_meta(
    date_from: date,
    date_to: date,
    aid: int | None,
    elite_only: bool,
    agent: str | None,
    orders: list[dict],
    offer_summary: list[dict],
) -> dict:
    purchase_orders = [o for o in orders if o.get("fsLinked") != "unlinked"]
    total = sum(o["amountUsd"] for o in purchase_orders)
    leading = offer_summary[0] if offer_summary else None
    sample = purchase_orders[0] if purchase_orders else {}
    return {
        "generatedAt": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "dateFrom": date_from.isoformat(),
        "dateTo": date_to.isoformat(),
        "aid": str(aid) if aid else "",
        "eliteOnly": elite_only,
        "agent": agent or "",
        "mode": "single" if aid else "elite_book",
        "playerName": sample.get("fullName", ""),
        "playerAgent": sample.get("agent", ""),
        "orderCount": len(purchase_orders),
        "totalPurchased": _fmt_usd(total),
        "totalPurchasedNum": total,
        "leadingOfferCode": leading["offerCode"] if leading else "",
        "leadingOfferSpend": leading["totalPurchasedFmt"] if leading else "",
        "htmlExport": "",
        "csvExport": "",
    }


def render_canvas_tsx(meta: dict, orders: list[dict], offer_summary: list[dict]) -> str:
    meta_json = json.dumps(meta, indent=2)
    orders_json = json.dumps(orders, indent=2)

    return f"""import {{
  Card,
  CardBody,
  H1,
  H2,
  Pill,
  Row,
  Spacer,
  Stack,
  Stat,
  Table,
  Text,
  TextInput,
  useCanvasState,
  useHostTheme,
}} from "cursor/canvas";

const META = {meta_json};

type OrderRow = {{
  aid: string;
  fullName: string;
  agent: string;
  offerCode: string;
  offerTitle: string;
  purchaseDate: string;
  purchaseTs: string;
  amountUsd: number;
  scAmount: number;
  scBonus: number;
  gcAmount: number;
  freeSpins: number;
  fsLinked: string;
}};

type OfferSummary = {{
  offerCode: string;
  offerTitle: string;
  orders: number;
  totalPurchased: number;
  totalPurchasedFmt: string;
  totalSc: number;
  totalGc: number;
  totalFs: number;
  pctOfSpend: number;
}};

const ORDERS: OrderRow[] = {orders_json};

function fmtUsd(n: number): string {{
  return `$${{n.toLocaleString(undefined, {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }})}}`;
}}

function fmtNum(n: number): string {{
  return n.toLocaleString(undefined, {{ maximumFractionDigits: 2 }});
}}

function matchesAid(row: OrderRow, query: string): boolean {{
  if (!query.trim()) return true;
  const q = query.trim();
  return row.aid.includes(q);
}}

function matchesSearch(row: OrderRow, query: string): boolean {{
  if (!query.trim()) return true;
  const q = query.trim().toLowerCase();
  return (
    row.fullName.toLowerCase().includes(q) ||
    row.agent.toLowerCase().includes(q) ||
    row.offerCode.toLowerCase().includes(q) ||
    row.offerTitle.toLowerCase().includes(q) ||
    row.purchaseTs.toLowerCase().includes(q)
  );
}}

function downloadCsv(rows: OrderRow[]) {{
  const headers = [
    "AID", "Full Name", "Agent", "Offer Code", "Offer Title",
    "Purchase Date", "Purchase Timestamp", "Amount USD", "SC", "SC Bonus", "GC", "Free Spins", "FS Linked",
  ];
  const lines = [headers.join(",")];
  for (const r of rows) {{
    const cells = [
      r.aid, r.fullName, r.agent, r.offerCode, r.offerTitle,
      r.purchaseDate, r.purchaseTs,
      r.amountUsd, r.scAmount, r.scBonus, r.gcAmount, r.freeSpins, r.fsLinked,
    ].map((c) => `"${{String(c).replace(/"/g, '""')}}"`);
    lines.push(cells.join(","));
  }}
  const blob = new Blob([lines.join("\\n")], {{ type: "text/csv" }});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `purchase-lookup-${{META.aid || "elite"}}-${{META.dateFrom}}_${{META.dateTo}}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}}

export default function PurchaseLookup() {{
  const theme = useHostTheme();
  const [aidSearch, setAidSearch] = useCanvasState("aidSearch", META.aid || "");
  const [search, setSearch] = useCanvasState("search", "");
  const [minAmount, setMinAmount] = useCanvasState("minAmount", "");

  const minAmt = parseFloat(minAmount) || 0;
  const purchaseRows = ORDERS.filter((r) => r.fsLinked !== "unlinked");
  const aidRows = purchaseRows.filter((row) => matchesAid(row, aidSearch));
  const filtered = aidRows.filter((row) => {{
    if (row.amountUsd < minAmt) return false;
    return matchesSearch(row, search);
  }});

  const selectedTotal = filtered.reduce((sum, row) => sum + row.amountUsd, 0);
  const selectedOfferMap = new Map<string, OfferSummary>();
  for (const row of filtered) {{
    const key = row.offerCode || "(unknown)";
    const current = selectedOfferMap.get(key) || {{
      offerCode: key,
      offerTitle: row.offerTitle,
      orders: 0,
      totalPurchased: 0,
      totalPurchasedFmt: "$0.00",
      totalSc: 0,
      totalGc: 0,
      totalFs: 0,
      pctOfSpend: 0,
    }};
    current.orders += 1;
    current.totalPurchased += row.amountUsd;
    current.totalSc += row.scAmount;
    current.totalGc += row.gcAmount;
    current.totalFs += row.freeSpins;
    selectedOfferMap.set(key, current);
  }}
  const selectedOfferSummary = Array.from(selectedOfferMap.values())
    .sort((a, b) => b.totalPurchased - a.totalPurchased)
    .map((row) => ({{
      ...row,
      totalPurchasedFmt: fmtUsd(row.totalPurchased),
      pctOfSpend: selectedTotal ? Math.round((1000 * row.totalPurchased) / selectedTotal) / 10 : 0,
    }}));
  const leadingOffer = selectedOfferSummary[0];
  const unlinkedRows = ORDERS.filter((r) => r.fsLinked === "unlinked" && matchesAid(r, aidSearch));
  const selectedAids = Array.from(new Set(filtered.map((row) => row.aid)));
  const selectedPlayers = Array.from(new Set(filtered.map((row) => `${{row.fullName}} (${{row.aid}})`)));
  const filterActive = aidSearch.trim() !== "" || search.trim() !== "" || minAmount.trim() !== "";

  const title = META.aid
    ? `AID ${{META.aid}}${{META.playerName ? ` — ${{META.playerName}}` : ""}}`
    : META.agent
      ? `Elite book — Agent ${{META.agent}}`
      : "Elite Purchase Lookup";

  return (
    <Stack gap={{16}} style={{{{ padding: 20, maxWidth: 1280, background: theme.bg.editor }}}}>
      <Stack gap={{4}}>
        <H1>{{title}}</H1>
        <Text tone="tertiary" size="small">
          {{META.dateFrom}} → {{META.dateTo}} · Generated {{META.generatedAt}}
          {{META.playerAgent ? ` · Agent ${{META.playerAgent}}` : ""}}
        </Text>
      </Stack>

      <Row gap={{12}} wrap>
        <Stat label="Selected purchased" value={{fmtUsd(selectedTotal)}} />
        <Stat label="Selected orders" value={{String(filtered.length)}} />
        <Stat label="Selected AIDs" value={{String(selectedAids.length)}} />
        <Stat
          label="Leading offer"
          value={{leadingOffer?.offerCode || "—"}}
          detail={{leadingOffer ? leadingOffer.totalPurchasedFmt : undefined}}
        />
      </Row>

      <Card>
        <CardBody>
          <Stack gap={{8}}>
            <Text weight="medium">Find purchases by AID</Text>
            <Row gap={{8}} align="center" wrap>
              <TextInput
                value={{aidSearch}}
                onChange={{setAidSearch}}
                placeholder="Type AID, e.g. 458523630"
                type="search"
                style={{{{ flex: "1 1 260px", minWidth: 220 }}}}
              />
              {{aidSearch ? (
                <Pill onClick={{() => setAidSearch("")}} size="sm">
                  Clear AID
                </Pill>
              ) : null}}
            </Row>
            <Text tone="tertiary" size="small">
              {{selectedPlayers.length
                ? `Showing ${{selectedPlayers.slice(0, 3).join(" · ")}}${{selectedPlayers.length > 3 ? ` +${{selectedPlayers.length - 3}} more` : ""}}`
                : "No AID matches the current dataset. Run a wider Elite range or a single-AID lookup if needed."}}
            </Text>
          </Stack>
        </CardBody>
      </Card>

      <Stack gap={{8}}>
        <H2>Spend by offer code for selected AID</H2>
        <Table
          headers={{["Offer code", "Title", "Orders", "Purchased", "% spend", "SC", "GC", "FS"]}}
          rows={{selectedOfferSummary.map((o) => [
            o.offerCode,
            o.offerTitle,
            String(o.orders),
            o.totalPurchasedFmt,
            `${{o.pctOfSpend}}%`,
            fmtNum(o.totalSc),
            fmtNum(o.totalGc),
            String(o.totalFs),
          ])}}
          columnAlign={{["left", "left", "right", "right", "right", "right", "right", "right"]}}
          striped
          emptyMessage="No purchases match the selected AID."
        />
      </Stack>

      <Stack gap={{8}}>
        <Row gap={{8}} align="center" wrap>
          <H2>Orders</H2>
          <Spacer />
          <Text tone="tertiary" size="small">
            {{filterActive ? `Showing ${{filtered.length}} of ${{purchaseRows.length}}` : `${{purchaseRows.length}} orders`}}
          </Text>
        </Row>

        <Row gap={{8}} align="center" wrap>
          <TextInput
            value={{search}}
            onChange={{setSearch}}
            placeholder="Search name, agent, offer code, timestamp…"
            type="search"
            style={{{{ flex: "1 1 240px", minWidth: 200 }}}}
          />
          <TextInput
            value={{minAmount}}
            onChange={{setMinAmount}}
            placeholder="Min amount USD"
            type="number"
            style={{{{ flex: "0 0 140px" }}}}
          />
          <Pill onClick={{() => downloadCsv(filtered)}} size="sm">
            Download CSV
          </Pill>
        </Row>

        <Table
          headers={{[
            "AID", "Full name", "Agent", "Offer code", "Offer title",
            "Date", "Timestamp", "USD", "SC", "SC bonus", "GC", "Free spins", "FS linked",
          ]}}
          rows={{filtered.map((r) => [
            r.aid,
            r.fullName,
            r.agent,
            r.offerCode,
            r.offerTitle,
            r.purchaseDate,
            r.purchaseTs,
            fmtUsd(r.amountUsd),
            fmtNum(r.scAmount),
            fmtNum(r.scBonus),
            fmtNum(r.gcAmount),
            String(r.freeSpins),
            r.fsLinked,
          ])}}
          columnAlign={{[
            "left", "left", "left", "left", "left", "left", "left",
            "right", "right", "right", "right", "right", "left",
          ]}}
          striped
          stickyHeader
          emptyMessage="No orders match the current filters."
        />
      </Stack>

      {{unlinkedRows.length ? (
        <Stack gap={{8}}>
          <H2>Unlinked free spins for selected AID</H2>
          <Text tone="tertiary" size="small">
            Freespin rewards in the lookup window that did not match an order offer code.
          </Text>
          <Table
            headers={{["AID", "Date", "Campaign", "Title", "Free spins"]}}
            rows={{unlinkedRows.map((r) => [
              r.aid, r.purchaseDate, r.offerCode, r.offerTitle, String(r.freeSpins),
            ])}}
            columnAlign={{["left", "left", "left", "left", "right"]}}
            striped
          />
        </Stack>
      ) : null}}
    </Stack>
  );
}}
"""


def build_csv(orders: list[dict]) -> str:
    import io

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "AID",
            "Full Name",
            "Agent",
            "Offer Code",
            "Offer Title",
            "Purchase Date",
            "Purchase Timestamp",
            "Amount USD",
            "SC",
            "SC Bonus",
            "GC",
            "Free Spins",
            "FS Linked",
        ]
    )
    for r in orders:
        writer.writerow(
            [
                r["aid"],
                r["fullName"],
                r["agent"],
                r["offerCode"],
                r["offerTitle"],
                r["purchaseDate"],
                r["purchaseTs"],
                r["amountUsd"],
                r["scAmount"],
                r["scBonus"],
                r["gcAmount"],
                r.get("freeSpins", 0),
                r.get("fsLinked", ""),
            ]
        )
    return buf.getvalue()


def build_html(meta: dict, orders: list[dict], offer_summary: list[dict]) -> str:
    purchase_orders = [o for o in orders if o.get("fsLinked") != "unlinked"]
    unlinked = [o for o in orders if o.get("fsLinked") == "unlinked"]

    def esc(s: object) -> str:
        return (
            str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    offer_rows = "".join(
        f"<tr><td>{esc(o['offerCode'])}</td><td>{esc(o.get('offerTitle',''))}</td>"
        f"<td class='num'>{o['orders']}</td><td class='num'>{esc(o['totalPurchasedFmt'])}</td>"
        f"<td class='num'>{o['pctOfSpend']}%</td><td class='num'>{o['totalSc']}</td>"
        f"<td class='num'>{o['totalGc']}</td><td class='num'>{o['totalFs']}</td></tr>"
        for o in offer_summary
    )

    order_rows = "".join(
        f"<tr><td>{esc(r['aid'])}</td><td>{esc(r['fullName'])}</td><td>{esc(r['agent'])}</td>"
        f"<td>{esc(r['offerCode'])}</td><td>{esc(r['offerTitle'])}</td>"
        f"<td>{esc(r['purchaseDate'])}</td><td>{esc(r['purchaseTs'])}</td>"
        f"<td class='num'>{_fmt_usd(r['amountUsd'])}</td><td class='num'>{r['scAmount']}</td>"
        f"<td class='num'>{r['scBonus']}</td><td class='num'>{r['gcAmount']}</td>"
        f"<td class='num'>{r.get('freeSpins',0)}</td><td>{esc(r.get('fsLinked',''))}</td></tr>"
        for r in purchase_orders
    )

    unlinked_section = ""
    if unlinked:
        unlinked_rows = "".join(
            f"<tr><td>{esc(r['aid'])}</td><td>{esc(r['purchaseDate'])}</td>"
            f"<td>{esc(r['offerCode'])}</td><td>{esc(r['offerTitle'])}</td>"
            f"<td class='num'>{r.get('freeSpins',0)}</td></tr>"
            for r in unlinked
        )
        unlinked_section = f"""
        <h2>Same-day unlinked free spins</h2>
        <table><thead><tr><th>AID</th><th>Date</th><th>Campaign</th><th>Title</th><th>FS</th></tr></thead>
        <tbody>{unlinked_rows}</tbody></table>"""

    title = f"AID {meta['aid']}" if meta.get("aid") else "Elite Purchase Lookup"
    if meta.get("playerName"):
        title += f" — {meta['playerName']}"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>{esc(title)}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; background: #0f1117; color: #e6e8ef; padding: 24px; }}
    h1 {{ font-size: 1.4rem; margin-bottom: 4px; }}
    h2 {{ font-size: 1.1rem; margin-top: 28px; }}
    .meta {{ color: #9aa3b5; font-size: 0.9rem; margin-bottom: 20px; }}
    .stats {{ display: flex; gap: 24px; flex-wrap: wrap; margin-bottom: 20px; }}
    .stat {{ background: #1a1d27; border-radius: 8px; padding: 12px 16px; min-width: 140px; }}
    .stat label {{ display: block; color: #9aa3b5; font-size: 0.75rem; text-transform: uppercase; }}
    .stat value {{ font-size: 1.2rem; font-weight: 600; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; margin-top: 8px; }}
    th, td {{ border-bottom: 1px solid #2a2f3d; padding: 8px 10px; text-align: left; }}
    th {{ color: #9aa3b5; font-weight: 500; position: sticky; top: 0; background: #0f1117; }}
    .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  </style>
</head>
<body>
  <h1>{esc(title)}</h1>
  <div class="meta">{esc(meta['dateFrom'])} → {esc(meta['dateTo'])} · Generated {esc(meta['generatedAt'])}</div>
  <div class="stats">
    <div class="stat"><label>Total purchased</label><div class="value">{esc(meta['totalPurchased'])}</div></div>
    <div class="stat"><label>Orders</label><div class="value">{meta['orderCount']}</div></div>
    <div class="stat"><label>Leading offer</label><div class="value">{esc(meta.get('leadingOfferCode') or '—')}</div></div>
  </div>
  <h2>Spend by offer code</h2>
  <table>
    <thead><tr><th>Offer code</th><th>Title</th><th>Orders</th><th>Purchased</th><th>%</th><th>SC</th><th>GC</th><th>FS</th></tr></thead>
    <tbody>{offer_rows}</tbody>
  </table>
  <h2>Orders</h2>
  <table>
    <thead><tr>
      <th>AID</th><th>Name</th><th>Agent</th><th>Offer code</th><th>Title</th>
      <th>Date</th><th>Timestamp</th><th>USD</th><th>SC</th><th>SC bonus</th><th>GC</th><th>FS</th><th>Linked</th>
    </tr></thead>
    <tbody>{order_rows}</tbody>
  </table>
  {unlinked_section}
</body>
</html>"""


def write_outputs(
    meta: dict,
    orders: list[dict],
    offer_summary: list[dict],
    canvas_dir: Path,
) -> dict[str, Path]:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    HANDOFFS_DIR.mkdir(parents=True, exist_ok=True)
    canvas_dir.mkdir(parents=True, exist_ok=True)

    slug = _slug(meta)
    run_date = date.today().isoformat()
    canvas_name = f"purchase-lookup-{slug}.canvas.tsx" if meta.get("aid") else "purchase-lookup.canvas.tsx"
    canvas_path = canvas_dir / canvas_name
    handoff_canvas = HANDOFFS_DIR / canvas_name

    html_path = EXPORT_DIR / f"purchase-lookup-{slug}-{run_date}.html"
    csv_path = EXPORT_DIR / f"purchase-lookup-{slug}-{run_date}.csv"
    json_path = HANDOFFS_DIR / f"{run_date}_{slug}_purchase_lookup.json"

    tsx = render_canvas_tsx(meta, orders, offer_summary)
    canvas_path.write_text(tsx, encoding="utf-8")
    shutil.copy2(canvas_path, handoff_canvas)

    html_path.write_text(build_html(meta, orders, offer_summary), encoding="utf-8")
    csv_path.write_text(build_csv(orders), encoding="utf-8")

    meta["htmlExport"] = str(html_path)
    meta["csvExport"] = str(csv_path)
    json_path.write_text(
        json.dumps({"meta": meta, "orders": orders, "offerSummary": offer_summary}, indent=2),
        encoding="utf-8",
    )

    return {
        "canvas": canvas_path,
        "canvas_backup": handoff_canvas,
        "html": html_path,
        "csv": csv_path,
        "json": json_path,
    }


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def main() -> None:
    parser = argparse.ArgumentParser(description="Elite purchase lookup canvas")
    parser.add_argument("--aid", type=int, help="Single player AID")
    parser.add_argument("--elite", action="store_true", help="Elite managed book mode")
    parser.add_argument("--agent", type=str, help="Filter Elite book by tag_agent_1")
    parser.add_argument("--from", dest="date_from", type=str, help="Start date YYYY-MM-DD")
    parser.add_argument("--to", dest="date_to", type=str, help="End date YYYY-MM-DD")
    parser.add_argument("--canvas-dir", type=Path, default=DEFAULT_CANVAS_DIR)
    parser.add_argument("--no-query", action="store_true", help="Dry run with sample data")
    args = parser.parse_args()

    today = date.today()
    date_to = parse_date(args.date_to) or today
    date_from = parse_date(args.date_from)

    if date_from is None:
        window = DEFAULT_WINDOW_DAYS if args.aid or not args.elite else ELITE_MAX_DAYS
        date_from = date_to - timedelta(days=window - 1)

    if args.elite and not args.date_from:
        max_start = date_to - timedelta(days=ELITE_MAX_DAYS - 1)
        if date_from < max_start:
            date_from = max_start
            print(f"Elite book mode: capped window to {ELITE_MAX_DAYS} days ({date_from} → {date_to})")

    if args.elite and not args.aid and not args.date_from:
        print("Elite book mode requires --from (or uses last 7 days by default).")

    if not args.aid and not args.elite and not args.no_query:
        parser.error("Provide --aid for single player or --elite for managed book mode.")

    orders, offer_summary = fetch_data(
        date_from=date_from,
        date_to=date_to,
        aid=args.aid,
        elite_only=args.elite and not args.aid,
        agent=args.agent,
        no_query=args.no_query,
    )

    meta = build_meta(
        date_from=date_from,
        date_to=date_to,
        aid=args.aid,
        elite_only=args.elite,
        agent=args.agent,
        orders=orders,
        offer_summary=offer_summary,
    )

    paths = write_outputs(meta, orders, offer_summary, args.canvas_dir)

    print(f"Orders: {meta['orderCount']} · Total: {meta['totalPurchased']}")
    if meta.get("leadingOfferCode"):
        print(f"Leading offer: {meta['leadingOfferCode']} ({meta.get('leadingOfferSpend', '')})")
    print(f"Canvas: {paths['canvas']}")
    print(f"HTML:   {paths['html']}")
    print(f"CSV:    {paths['csv']}")
    print(f"JSON:   {paths['json']}")


if __name__ == "__main__":
    main()
