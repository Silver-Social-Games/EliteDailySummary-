"""
VIP Event (Vegas) — Top 30 Elite brief from Players Table export + BigQuery enrich.

Usage:
  python vip_event/generate_vegas_top30_elite_brief.py
  python vip_event/generate_vegas_top30_elite_brief.py --copy-desktop
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from elite_lib import PROJECT_ID, get_client, run_query

MODULE_DIR = Path(__file__).resolve().parent
DATA_DIR = MODULE_DIR / "data"
DEFAULT_PLAYERS_CSV = Path(r"c:\Users\Owner\Downloads\Players Table (45).csv")
DEFAULT_CANVAS_DIR = Path(
    r"C:\Users\Owner\.cursor\projects\c-Users-Owner-Downloads-Elite\canvases"
)
DESKTOP_EXPORT_DIR = Path(
    r"c:\Users\Owner\OneDrive - Silver Social Games\Desktop\VIP\Cursor"
)
EXPORT_DIR = MODULE_DIR / "exports"
HANDOFFS_DIR = MODULE_DIR / "handoffs"
EXPORT_BASENAME = "vegas-vip-event-elite-top30"

TOP_N = 30
WAITLIST_N = 10


def parse_money(raw: str | None) -> float:
    if raw is None:
        return 0.0
    s = str(raw).strip().replace("$", "").replace(",", "").replace('"', "")
    if not s or s in ("—", "-", "UD", "OK"):
        return 0.0
    neg = s.startswith("(") and s.endswith(")")
    if neg:
        s = s[1:-1]
    try:
        v = float(s)
    except ValueError:
        return 0.0
    return -v if neg else v


def fmt_money(v: float | None) -> str:
    if v is None:
        return "$0"
    av = abs(float(v))
    if av >= 100:
        return f"${float(v):,.0f}"
    return f"${float(v):,.2f}"


def fmt_pct(num: float, den: float) -> str:
    if not den:
        return "—"
    return f"{100 * num / den:.1f}%"


def normalize_state(st: str) -> str:
    s = (st or "unknown").strip().lower()
    names = {
        "arizona": "az",
        "california": "ca",
        "nevada": "nv",
        "texas": "tx",
        "florida": "fl",
        "new york": "ny",
        "new hampshire": "nh",
        "north carolina": "nc",
        "massachusetts": "ma",
        "ohio": "oh",
        "illinois": "il",
        "colorado": "co",
        "hawaii": "hi",
        "louisiana": "la",
        "mississippi": "ms",
        "missouri": "mo",
        "nebraska": "ne",
        "pennsylvania": "pa",
        "minnesota": "mn",
        "south carolina": "sc",
    }
    return names.get(s, s[:2] if len(s) == 2 else s)


def read_players_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-16", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def build_enrich_sql(aids: list[str], report_date: date) -> str:
    if not aids:
        return "SELECT 1 LIMIT 0"
    rd = report_date.isoformat()
    d30 = (report_date - timedelta(days=29)).isoformat()
    in_list = ", ".join(aids)
    return f"""
WITH aids AS (
  SELECT aid FROM UNNEST([{in_list}]) AS aid
),
auth AS (
  SELECT id AS aid, ANY_VALUE(last_sign_in_state) AS last_sign_in_state
  FROM `{PROJECT_ID}.transactional_data.uam_account_auth_info`
  WHERE id IN ({in_list})
  GROUP BY id
),
daily AS (
  SELECT
    k.account_id AS aid,
    SUM(CAST(k.purchased AS FLOAT64)) AS purchased_30d,
    SUM(
      CAST(k.profit AS FLOAT64) - CAST(k.loss AS FLOAT64)
      - COALESCE(k.sc_reward_amount, 0)
    ) AS ngr_30d,
    MAX(IF(CAST(k.purchased AS FLOAT64) > 0, k.date, NULL)) AS last_purchase_date
  FROM `{PROJECT_ID}.jackpota_agg.daily_player_revenue_kpis` k
  WHERE k.account_id IN ({in_list})
    AND k.date BETWEEN DATE '{d30}' AND DATE '{rd}'
  GROUP BY k.account_id
)
SELECT
  a.aid,
  auth.last_sign_in_state,
  COALESCE(d.purchased_30d, 0) AS purchased_30d_bq,
  COALESCE(d.ngr_30d, 0) AS ngr_30d,
  d.last_purchase_date,
  ua.locked,
  ua.lock_reason,
  ua.status AS redeem_workflow_status,
  eu.redeem_status,
  COALESCE(eu.red_flag, 0) AS red_flag
FROM aids a
LEFT JOIN auth ON a.aid = auth.aid
LEFT JOIN daily d ON a.aid = d.aid
LEFT JOIN `{PROJECT_ID}.transactional_data.uam_accounts` ua ON a.aid = ua.id
LEFT JOIN `{PROJECT_ID}.dbt_dashboards_mart.elite_users` eu
  ON a.aid = eu.account_id AND eu.report_date = DATE '{rd}'
"""


def invite_status(csv_row: dict, enrich: dict) -> str:
    locked_csv = (csv_row.get("Is Locked") or "").strip().lower() == "locked"
    if locked_csv or enrich.get("locked"):
        return "do_not_invite"
    redeem = (
        enrich.get("redeem_workflow_status")
        or enrich.get("redeem_status")
        or "default"
    )
    if str(redeem).lower() not in ("default", "closed", ""):
        return "review_required"
    if int(enrich.get("red_flag") or 0) == 1:
        return "review_required"
    if (csv_row.get("Is High Risk Player") or "").strip().upper() == "HIGH RISK":
        return "review_required"
    if parse_money(csv_row.get("Previous 30d Purchased *")) <= 0:
        return "review_required"
    return "invite_ok"


def status_label(code: str) -> str:
    return {"invite_ok": "OK", "review_required": "Review", "do_not_invite": "Blocked"}.get(
        code, code
    )


def status_tone(code: str) -> str:
    return {
        "invite_ok": "success",
        "review_required": "warning",
        "do_not_invite": "danger",
    }.get(code, "neutral")


def load_and_rank(csv_path: Path, report_date: date, no_query: bool) -> tuple[list[dict], list[dict]]:
    raw_rows = read_players_csv(csv_path)
    raw_rows.sort(
        key=lambda r: (
            parse_money(r.get("Avg. LT_net_purchases")),
            parse_money(r.get("Previous 30d Purchased *")),
        ),
        reverse=True,
    )
    shortlisted = raw_rows[: TOP_N + WAITLIST_N]

    aids = [str(r["account_id"]).strip() for r in shortlisted]
    enrich_map: dict[str, dict] = {}
    if not no_query:
        rows = run_query(get_client(), build_enrich_sql(aids, report_date))
        enrich_map = {str(r["aid"]): r for r in rows}

    players: list[dict] = []
    for i, row in enumerate(shortlisted, start=1):
        aid = str(row["account_id"]).strip()
        enrich = enrich_map.get(aid, {})
        first = (row.get("first_name") or "").strip()
        last = (row.get("last_name") or "").strip()
        name = f"{first} {last}".strip() or "—"
        lifetime_np = parse_money(row.get("Avg. LT_net_purchases"))
        purchased_30d = parse_money(row.get("Previous 30d Purchased *"))
        if enrich.get("purchased_30d_bq") is not None and purchased_30d == 0:
            purchased_30d = float(enrich.get("purchased_30d_bq") or 0)
        ngr_30d = float(enrich.get("ngr_30d") or 0)
        hold_raw = (row.get("Hold %") or "").strip().replace("%", "")
        hold_pct = f"{hold_raw}%" if hold_raw and hold_raw != "—" else "—"
        if hold_pct == "—" and parse_money(row.get("Avg. LT_purchased")) > 0:
            hold_pct = f"{100 * lifetime_np / parse_money(row.get('Avg. LT_purchased')):.1f}%"

        last_purchase = enrich.get("last_purchase_date")
        if last_purchase is not None and not isinstance(last_purchase, str):
            last_purchase = str(last_purchase)[:10]

        code = invite_status(row, enrich)
        reg = (row.get("Reg. State") or "—").strip()
        sign_in = enrich.get("last_sign_in_state") or "—"

        players.append(
            {
                "rank": i,
                "agent": (row.get("agent_name (group)") or "—").strip(),
                "aid": aid,
                "name": name,
                "email": (row.get("email") or "—").strip(),
                "age": (row.get("Age") or "—").strip(),
                "channel": (row.get("Channel Type") or "—").strip(),
                "lifetimeNp": fmt_money(lifetime_np),
                "lifetimePurchased": fmt_money(parse_money(row.get("Avg. LT_purchased"))),
                "purchased30d": fmt_money(purchased_30d),
                "purchased7d": fmt_money(parse_money(row.get("Previous 7d Purchased*"))),
                "maxValueNp": fmt_money(parse_money(row.get("Max Value Net Purchase"))),
                "ngr30d": fmt_money(ngr_30d),
                "holdPct": hold_pct,
                "regState": reg.upper() if reg != "—" else "—",
                "lastSignInState": str(sign_in).upper() if sign_in != "—" else "—",
                "ftpDate": (row.get("FTP Date") or "—").strip(),
                "lockReason": (row.get("Lock Reason") or "—").strip(),
                "lastPurchaseDate": last_purchase or "—",
                "statusCode": code,
                "status": status_label(code),
                "statusTone": status_tone(code),
                "responsiveness": "",
                "_lifetime_np": lifetime_np,
                "_purchased_30d": purchased_30d,
                "_ngr_30d": ngr_30d,
                "_reg_state": normalize_state(reg),
            }
        )

    return players[:TOP_N], players[TOP_N : TOP_N + WAITLIST_N]


def build_meta(
    players: list[dict],
    waitlist: list[dict],
    report_date: date,
    source_name: str,
    book_size: int,
) -> dict:
    top = players
    all_invite = top + waitlist
    sum_lt_np = sum(p["_lifetime_np"] for p in top)
    sum_p30 = sum(p["_purchased_30d"] for p in top)
    sum_ngr30 = sum(p["_ngr_30d"] for p in top)

    state_counts = Counter(p["_reg_state"] for p in top)
    top_states = state_counts.most_common(8)
    geo_lines = [f"{st.upper()}: {cnt} ({fmt_pct(cnt, len(top))})" for st, cnt in top_states[:5]]

    agent_agg: dict[str, dict] = defaultdict(
        lambda: {"players": 0, "lt_np": 0.0, "p30": 0.0}
    )
    for p in top:
        a = p["agent"]
        agent_agg[a]["players"] += 1
        agent_agg[a]["lt_np"] += p["_lifetime_np"]
        agent_agg[a]["p30"] += p["_purchased_30d"]

    agent_rows = sorted(
        [
            {
                "agent": agent,
                "players": v["players"],
                "lifetimeNp": fmt_money(v["lt_np"]),
                "purchased30d": fmt_money(v["p30"]),
            }
            for agent, v in agent_agg.items()
        ],
        key=lambda x: x["players"],
        reverse=True,
    )

    blocked = sum(1 for p in all_invite if p["statusCode"] == "do_not_invite")
    review = sum(1 for p in all_invite if p["statusCode"] == "review_required")
    inactive = sum(1 for p in top if p["_purchased_30d"] <= 0)
    ok = sum(1 for p in top if p["statusCode"] == "invite_ok")

    western = {"nv", "ca", "az", "ut", "co", "wa", "or", "id", "nm"}
    western_cnt = sum(1 for p in top if p["_reg_state"] in western)

    geo_chart = {
        "categories": [s[0].upper() for s in top_states],
        "values": [s[1] for s in top_states],
    }
    agent_lt = []
    agent_p30 = []
    for row in agent_rows:
        agent = row["agent"]
        agent_lt.append(round(agent_agg[agent]["lt_np"] / 1000))
        agent_p30.append(round(agent_agg[agent]["p30"] / 1000))
    agent_chart = {
        "categories": [r["agent"] for r in agent_rows],
        "lifetimeNpK": agent_lt,
        "purchased30dK": agent_p30,
    }

    status_breakdown = [
        {"label": "OK", "count": ok, "tone": "success"},
        {"label": "Review", "count": review, "tone": "warning"},
        {"label": "Blocked", "count": blocked, "tone": "danger"},
    ]

    geo_note = (
        f"{western_cnt} of {len(top)} Top 30 are western US by reg state — reasonable for Vegas."
        if western_cnt >= len(top) * 0.4
        else f"Only {western_cnt} of {len(top)} Top 30 are western US — check Vegas travel logistics."
    )

    takeaway = (
        f"Top {len(top)} Elite from {book_size:,} managed book · {fmt_money(sum_lt_np)} lifetime NP · "
        f"{fmt_money(sum_p30)} purchased 30d. Leading state: {geo_lines[0] if geo_lines else 'n/a'}. "
        f"{ok} invite-ready · {review} review · {blocked} blocked."
    )

    return {
        "title": "VIP Event (Vegas) — Top 30 Elite Brief",
        "dateLine": (
            f"Source: {source_name} · enriched {report_date.strftime('%d %b %Y')} · "
            "rank: lifetime NP → purchased 30d"
        ),
        "takeaway": takeaway,
        "geoNote": geo_note,
        "sumLifetimeNp": fmt_money(sum_lt_np),
        "sumPurchased30d": fmt_money(sum_p30),
        "sumNgr30d": fmt_money(sum_ngr30),
        "blockedCount": blocked,
        "reviewCount": review,
        "okCount": ok,
        "inactive30dCount": inactive,
        "westernCount": western_cnt,
        "bookSize": book_size,
        "geoTop5": geo_lines,
        "agentRows": agent_rows,
        "geoChart": geo_chart,
        "agentChart": agent_chart,
        "statusBreakdown": status_breakdown,
        "responsivenessNote": "Responsiveness is blank — fill from Zendesk / agent notes.",
    }


def strip_private(rows: list[dict]) -> list[dict]:
    return [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]


def render_canvas_tsx(meta: dict, players: list[dict], waitlist: list[dict]) -> str:
    meta_json = json.dumps(meta, indent=2)
    players_json = json.dumps(strip_private(players), indent=2)
    waitlist_json = json.dumps(strip_private(waitlist), indent=2)
    all_json = json.dumps(strip_private(players + waitlist), indent=2)

    return f"""import {{
  BarChart,
  Callout,
  Card,
  CardBody,
  CardHeader,
  CollapsibleSection,
  Divider,
  Grid,
  H1,
  H2,
  Pill,
  Row,
  Select,
  Spacer,
  Stack,
  Stat,
  Swatch,
  Table,
  Text,
  TextInput,
  useCanvasState,
  useHostTheme,
}} from "cursor/canvas";

const META = {meta_json};
const TOP_PLAYERS = {players_json};
const WAITLIST = {waitlist_json};
const ALL_PLAYERS = {all_json};

const HEADERS = [
  "#", "Agent", "AID", "Name", "Lifetime NP", "Max value NP",
  "Purch 30d", "Purch 7d", "NGR 30d", "Hold", "Reg state", "Sign-in",
  "Channel", "Status", "Responsiveness",
];

const COL_ALIGN = [
  "right", "left", "left", "left", "right", "right", "right", "right",
  "right", "right", "left", "left", "left", "left", "left",
] as const;

function playerCells(p: (typeof TOP_PLAYERS)[number]) {{
  return [
    String(p.rank),
    p.agent,
    p.aid,
    p.name,
    p.lifetimeNp,
    p.maxValueNp,
    p.purchased30d,
    p.purchased7d,
    p.ngr30d,
    p.holdPct,
    p.regState,
    p.lastSignInState,
    p.channel,
    p.status,
    p.responsiveness || "—",
  ];
}}

function rowTone(status: string) {{
  if (status === "OK") return "success" as const;
  if (status === "Review") return "warning" as const;
  if (status === "Blocked") return "danger" as const;
  return undefined;
}}

export default function VegasVipEventTop30EliteBrief() {{
  const theme = useHostTheme();
  const [search, setSearch] = useCanvasState("search", "");
  const [statusFilter, setStatusFilter] = useCanvasState("status", "all");
  const [listFilter, setListFilter] = useCanvasState("list", "top30");

  const q = search.trim().toLowerCase();
  const pool = listFilter === "waitlist" ? WAITLIST : listFilter === "all" ? ALL_PLAYERS : TOP_PLAYERS;
  const filtered = pool.filter((p) => {{
    if (statusFilter !== "all" && p.status !== statusFilter) return false;
    if (!q) return true;
    return (
      p.name.toLowerCase().includes(q) ||
      p.aid.includes(q) ||
      p.agent.toLowerCase().includes(q) ||
      p.regState.toLowerCase().includes(q)
    );
  }});

  const calloutTone =
    META.reviewCount > 8 ? "warning" : META.blockedCount > 0 ? "danger" : "success";

  return (
    <Stack gap={{24}} style={{{{ padding: 28, maxWidth: 1320, background: theme.bg.editor }}}}>
      <Stack gap={{6}}>
        <Row gap={{12}} align="center">
          <H1 style={{{{ margin: 0 }}}}>{{META.title}}</H1>
          <Pill tone="info">VIP Event</Pill>
        </Row>
        <Text tone="tertiary" size="small">{{META.dateLine}}</Text>
        <Text tone="secondary" size="small">
          {{META.bookSize.toLocaleString()}} players in source export · Top 30 + waitlist 31–40
        </Text>
      </Stack>

      <Callout tone={{calloutTone}} title="Elite stakeholder takeaway">
        {{META.takeaway}}
      </Callout>

      <Grid columns={{3}} gap={{12}}>
        <Stat label="Top 30 lifetime NP" value={{META.sumLifetimeNp}} tone="info" />
        <Stat label="Purchased 30d" value={{META.sumPurchased30d}} />
        <Stat label="NGR 30d (BQ)" value={{META.sumNgr30d}} />
        <Stat label="Invite-ready" value={{String(META.okCount)}} tone="success" />
        <Stat label="Need review" value={{String(META.reviewCount)}} tone="warning" />
        <Stat label="Blocked" value={{String(META.blockedCount)}} tone="danger" />
      </Grid>

      <Grid columns={{2}} gap={{16}}>
        <Card>
          <CardHeader trailing={{<Text size="small" tone="tertiary">Vegas logistics</Text>}}>
            Reg state — Top 30 count
          </CardHeader>
          <CardBody>
            <BarChart
              horizontal
              categories={{META.geoChart.categories}}
              series={{[{{ name: "Players", data: META.geoChart.values, tone: "info" }}]}}
              height={{220}}
              showValues
            />
            <Spacer />
            <Text tone="tertiary" size="small">{{META.geoNote}}</Text>
          </CardBody>
        </Card>

        <Card>
          <CardHeader trailing={{<Text size="small" tone="tertiary">$000s</Text>}}>
            Lifetime NP vs purchased 30d by agent
          </CardHeader>
          <CardBody>
            <BarChart
              categories={{META.agentChart.categories}}
              series={{[
                {{ name: "Lifetime NP", data: META.agentChart.lifetimeNpK, tone: "info" }},
                {{ name: "Purch 30d", data: META.agentChart.purchased30dK, tone: "success" }},
              ]}}
              height={{220}}
              valuePrefix="$"
              valueSuffix="k"
              showValues
            />
          </CardBody>
        </Card>
      </Grid>

      <Card>
        <CardHeader>Invite status mix — Top 30 + waitlist</CardHeader>
        <CardBody>
          <Row gap={{16}} wrap>
            {{META.statusBreakdown.map((s) => (
              <Row key={{s.label}} gap={{8}} align="center">
                <Swatch color={{s.tone === "success" ? "green" : s.tone === "warning" ? "yellow" : "pink"}} />
                <Text weight="medium">{{s.label}}</Text>
                <Pill tone={{s.tone as "success" | "warning" | "danger"}}>{{String(s.count)}}</Pill>
              </Row>
            ))}}
          </Row>
        </CardBody>
      </Card>

      <Divider />

      <H2>Player roster</H2>
      <Row gap={{12}} wrap align="center">
        <TextInput
          placeholder="Search name, AID, agent, state…"
          value={{search}}
          onChange={{setSearch}}
          style={{{{ minWidth: 260 }}}}
        />
        <Select
          value={{statusFilter}}
          onChange={{setStatusFilter}}
          options={{[
            {{ value: "all", label: "All statuses" }},
            {{ value: "OK", label: "OK" }},
            {{ value: "Review", label: "Review" }},
            {{ value: "Blocked", label: "Blocked" }},
          ]}}
        />
        <Select
          value={{listFilter}}
          onChange={{setListFilter}}
          options={{[
            {{ value: "top30", label: "Top 30" }},
            {{ value: "waitlist", label: "Waitlist 31–40" }},
            {{ value: "all", label: "All 40" }},
          ]}}
        />
        <Text tone="tertiary" size="small">{{filtered.length}} shown</Text>
      </Row>

      <Callout tone="info" title="Responsiveness — manual fill">
        {{META.responsivenessNote}}
      </Callout>

      <Table
        headers={{HEADERS}}
        rows={{filtered.map((p) => playerCells(p))}}
        columnAlign={{[...COL_ALIGN]}}
        rowTone={{filtered.map((p) => rowTone(p.status))}}
        striped
        stickyHeader
      />

      <CollapsibleSection title="Agent ownership detail" defaultOpen={{false}} count={{META.agentRows.length}}>
        <Table
          headers={{["Agent", "Players", "Lifetime NP", "Purchased 30d"]}}
          rows={{META.agentRows.map((a) => [a.agent, String(a.players), a.lifetimeNp, a.purchased30d])}}
          columnAlign={{["left", "right", "right", "right"]}}
        />
      </CollapsibleSection>
    </Stack>
  );
}}
"""


def build_markdown(meta: dict, players: list[dict], waitlist: list[dict]) -> str:
    lines = [
        f"# {meta['title']}",
        "",
        meta["dateLine"],
        "",
        f"**Takeaway:** {meta['takeaway']}",
        "",
        "## Elite stakeholder snapshot",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Book size (source) | {meta['bookSize']:,} |",
        f"| Top 30 lifetime NP | {meta['sumLifetimeNp']} |",
        f"| Purchased 30d | {meta['sumPurchased30d']} |",
        f"| NGR 30d (BQ) | {meta['sumNgr30d']} |",
        f"| Invite-ready | {meta['okCount']} |",
        f"| Review | {meta['reviewCount']} |",
        f"| Blocked | {meta['blockedCount']} |",
        "",
    ]
    for g in meta["geoTop5"]:
        lines.append(f"- {g}")
    lines.extend(["", meta["geoNote"], "", "## Top 30", ""])
    lines.append(
        "| # | Agent | AID | Name | Lifetime NP | Purch 30d | NGR 30d | Reg state | Status | Responsiveness |"
    )
    lines.append("|---|-------|-----|------|-------------|-----------|---------|-----------|--------|----------------|")
    for p in strip_private(players):
        lines.append(
            f"| {p['rank']} | {p['agent']} | {p['aid']} | {p['name']} | {p['lifetimeNp']} | "
            f"{p['purchased30d']} | {p['ngr30d']} | {p['regState']} | {p['status']} | |"
        )
    return "\n".join(lines) + "\n"


def write_csv(path: Path, players: list[dict], waitlist: list[dict]) -> None:
    fieldnames = [
        "rank", "agent", "aid", "name", "email", "age", "channel",
        "lifetime_np", "max_value_np", "purchased_30d", "purchased_7d", "ngr_30d",
        "hold_pct", "reg_state", "last_sign_in_state", "ftp_date", "status",
        "responsiveness", "list",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for p, lst in [(players, "top30"), (waitlist, "waitlist")]:
            for row in strip_private(p):
                w.writerow({
                    "rank": row["rank"],
                    "agent": row["agent"],
                    "aid": row["aid"],
                    "name": row["name"],
                    "email": row.get("email", ""),
                    "age": row.get("age", ""),
                    "channel": row.get("channel", ""),
                    "lifetime_np": row["lifetimeNp"],
                    "max_value_np": row["maxValueNp"],
                    "purchased_30d": row["purchased30d"],
                    "purchased_7d": row.get("purchased7d", ""),
                    "ngr_30d": row["ngr30d"],
                    "hold_pct": row["holdPct"],
                    "reg_state": row["regState"],
                    "last_sign_in_state": row["lastSignInState"],
                    "ftp_date": row.get("ftpDate", ""),
                    "status": row["status"],
                    "responsiveness": "",
                    "list": lst,
                })


def write_exports(
    meta: dict,
    players: list[dict],
    waitlist: list[dict],
    canvas_path: Path,
    copy_desktop: bool = False,
) -> dict[str, Path]:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    HANDOFFS_DIR.mkdir(parents=True, exist_ok=True)
    md_path = EXPORT_DIR / f"{EXPORT_BASENAME}.md"
    html_path = EXPORT_DIR / f"{EXPORT_BASENAME}.html"
    csv_path = EXPORT_DIR / f"{EXPORT_BASENAME}.csv"
    handoff = HANDOFFS_DIR / f"{EXPORT_BASENAME}.canvas.tsx"
    md_path.write_text(build_markdown(meta, players, waitlist), encoding="utf-8")
    write_csv(csv_path, players, waitlist)
    shutil.copy2(canvas_path, handoff)
    paths: dict[str, Path] = {"markdown": md_path, "csv": csv_path, "canvas_backup": handoff}
    if copy_desktop:
        DESKTOP_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        for name, src in [
            ("Vegas-VIP-Event-Elite-Top30.csv", csv_path),
            ("Vegas-VIP-Event-Elite-Top30.md", md_path),
        ]:
            shutil.copy2(src, DESKTOP_EXPORT_DIR / name)
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="VIP Event (Vegas) - Top 30 Elite brief")
    parser.add_argument("--csv", type=Path, default=DEFAULT_PLAYERS_CSV)
    parser.add_argument(
        "--date",
        type=lambda s: date.fromisoformat(s),
        default=date.today() - timedelta(days=1),
    )
    parser.add_argument("--canvas-dir", type=Path, default=DEFAULT_CANVAS_DIR)
    parser.add_argument("--copy-desktop", action="store_true")
    parser.add_argument("--no-query", action="store_true")
    args = parser.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    workspace_csv = DATA_DIR / "players-table-latest.csv"
    shutil.copy2(args.csv, workspace_csv)

    book_size = len(read_players_csv(args.csv))
    players, waitlist = load_and_rank(args.csv, args.date, args.no_query)
    meta = build_meta(players, waitlist, args.date, args.csv.name, book_size)

    args.canvas_dir.mkdir(parents=True, exist_ok=True)
    canvas_path = args.canvas_dir / f"{EXPORT_BASENAME}.canvas.tsx"
    canvas_path.write_text(render_canvas_tsx(meta, players, waitlist), encoding="utf-8")
    paths = write_exports(meta, players, waitlist, canvas_path, copy_desktop=args.copy_desktop)

    print(f"Source: {args.csv} ({book_size:,} players)")
    print(f"Top 30 lifetime NP: {meta['sumLifetimeNp']}")
    print(f"OK: {meta['okCount']} · Review: {meta['reviewCount']} · Blocked: {meta['blockedCount']}")
    print(f"Canvas: {canvas_path}")
    print(f"CSV: {paths['csv']}")


if __name__ == "__main__":
    main()
