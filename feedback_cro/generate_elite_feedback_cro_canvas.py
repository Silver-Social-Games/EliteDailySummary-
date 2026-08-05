"""
Elite negative feedback — CRO canvas generator.
Usage:
  python feedback_cro/generate_elite_feedback_cro_canvas.py
  python feedback_cro/generate_elite_feedback_cro_canvas.py --xlsx "path/to/Elite Feedback.xlsx"
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from elite_lib import PROJECT_ID, get_client, run_query  # noqa: E402

DEFAULT_XLSX = Path(
    r"c:\Users\Owner\OneDrive - Silver Social Games\Desktop\VIP\Cursor\Elite Feedback.xlsx"
)
DEFAULT_CANVAS_DIR = Path(
    r"C:\Users\Owner\.cursor\projects\c-Users-Owner-Downloads-Elite\canvases"
)
DESKTOP_EXPORT_DIR = Path(
    r"c:\Users\Owner\OneDrive - Silver Social Games\Desktop\VIP\Cursor"
)
EXPORT_DIR = Path(__file__).resolve().parent / "exports"
HANDOFFS_DIR = Path(__file__).resolve().parent / "handoffs"
DEFAULT_BEFORE_START = date(2026, 4, 22)
DEFAULT_BEFORE_END = date(2026, 5, 18)
DEFAULT_AFTER_START = date(2026, 5, 19)

TAG_LABELS: dict[str, str] = {
    "no_wins": "No Wins / Dry Play",
    "rewards": "Rewards & Bonuses",
    "competitors": "Playing Elsewhere",
    "support": "Support / Live Agent",
    "redemption": "Redemption / Payout",
    "product_ux": "Product / UX",
    "churn": "Churn / Break",
}

TAG_TONES: dict[str, str] = {
    "no_wins": "danger",
    "rewards": "warning",
    "competitors": "info",
    "support": "neutral",
    "redemption": "warning",
    "product_ux": "info",
    "churn": "danger",
}

TAG_COLORS: dict[str, str] = {
    "no_wins": "orange",
    "rewards": "yellow",
    "competitors": "blue",
    "support": "gray",
    "redemption": "purple",
    "product_ux": "green",
    "churn": "pink",
}

TAG_SHORT: dict[str, str] = {
    "no_wins": "No Wins",
    "rewards": "Rewards",
    "competitors": "Competitors",
    "support": "Support",
    "redemption": "Redemption",
    "product_ux": "Product UX",
    "churn": "Churn",
}

TAG_DESCRIPTIONS: dict[str, str] = {
    "no_wins": "Dry sessions, losing streaks, or difficulty hitting features.",
    "rewards": "Coinback, free SC, daily bonuses, or overall appreciation too low.",
    "competitors": "Better deals or wins on Chumba, playfame, pulsz, or other platforms.",
    "support": "Live agent access, unhelpful support, or validation/KYC friction.",
    "redemption": "Slow payouts, funds returned to play balance, or instant-pay elsewhere.",
    "product_ux": "App vs browser limits, purchase chains, or verification blocking play.",
    "churn": "Taking a break, account closed, or explicit disinterest in continuing.",
}

TAG_RULES: list[tuple[str, re.Pattern[str]]] = [
    (
        "no_wins",
        re.compile(
            r"no wins|haven.?t been winning|not winning|hard to win|lost it all|"
            r"takes a lot more|dry|rough|slowed down|nothing was hitting|lost a bit|"
            r"loose more|lose more|lost to much|wants more wins",
            re.I,
        ),
    ),
    (
        "rewards",
        re.compile(
            r"coin\s?back|coinback|free sc|free play|bonuses|appreciation|"
            r"player awards|gc promotion|reward offer|holiday sc|daily bonus|"
            r"wheel|spin wheel|megabonanza.*wheel|percentage back|200 sc|"
            r"bigger percentage|more sc gift",
            re.I,
        ),
    ),
    (
        "competitors",
        re.compile(
            r"chumba|megabonanza|playfame|pulsz|hello millions|spinblitz|mcluck|"
            r"legendz|shuffle\.us|luckyland|other platform|another platform|"
            r"searching for a casino|better deals|better as far as rewards",
            re.I,
        ),
    ),
    (
        "support",
        re.compile(
            r"live agent|contact support|support.*no help|chat and get|"
            r"validation request|bank statement.*denied|denied|"
            r"verification code|24-48 hours they never",
            re.I,
        ),
    ),
    (
        "redemption",
        re.compile(
            r"redemption|redeem|payout|deposited into my account|"
            r"placed back into my play|24 hours redeems|instant payout|"
            r"pay out slightly slower|pay you out",
            re.I,
        ),
    ),
    (
        "product_ux",
        re.compile(
            r"app don.?t work|browser|not available in my area|"
            r"claim rewards.*app|customer service via the app|"
            r"debit card.*transactions|buy them all at once|chain|"
            r"cannot play from california",
            re.I,
        ),
    ),
    (
        "churn",
        re.compile(
            r"taking a break|account closed|not interested|dont pay|don't pay|"
            r"you guys dont|break from jackpota|haven.?t been on jackpota|"
            r"not a fan of our slots",
            re.I,
        ),
    ),
]

POSITIVE_ONLY = re.compile(
    r"^(thank you again i love jackpota|super happy with the platform|"
    r"love jackpota!!|happy with the games, missing hacksaw|"
    r"blitz games are the favourite\.?)$",
    re.I,
)

NEGATIVE_SIGNAL = re.compile(
    r"rough|no wins|dry|terrible|no help|not winning|hard to win|lost it all|"
    r"better deals|other platform|taking a break|dont pay|don't pay|not interested|"
    r"account closed|lost to much|loose more|lose more|not happy|not a fan|"
    r"concerned|validation|denied|coin back|coinback|appreciation|"
    r"searching for a casino|slowed down|requires heavy spend|chumba|megabonanza|"
    r"playfame|pulsz|hello millions|spinblitz|support|redemption|hell to chat|"
    r"break from|haven.?t been on jackpota|wants more wins|not that happy",
    re.I,
)


def fmt_money(v: float | None) -> str:
    if v is None or v == 0:
        return "$0"
    av = abs(float(v))
    if av >= 100:
        return f"${float(v):,.0f}"
    return f"${float(v):,.2f}"


def fmt_pct(num: float, den: float) -> str:
    if not den:
        return "—"
    return f"{100 * num / den:.1f}%"


def fmt_delta(v: float, pct: float | None = None) -> str:
    sign = "+" if v >= 0 else ""
    base = f"{sign}{fmt_money(v)}"
    if pct is not None and pct != 0:
        return f"{base} ({pct:+.1f}%)"
    return base


def _col_index(ref: str) -> int:
    col = "".join(ch for ch in ref if ch.isalpha())
    idx = 0
    for ch in col:
        idx = idx * 26 + (ord(ch.upper()) - ord("A") + 1)
    return idx - 1


def _parse_xlsx_zip(path: Path) -> list[list[str]]:
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(path) as z:
        ss: list[str] = []
        if "xl/sharedStrings.xml" in z.namelist():
            root = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in root.findall("m:si", ns):
                ss.append("".join((t.text or "") for t in si.findall(".//m:t", ns)))

        root = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
        rows: list[list[str]] = []
        for row in root.findall(".//m:sheetData/m:row", ns):
            vals: list[str] = []
            for c in row.findall("m:c", ns):
                ref = c.get("r", "")
                idx = _col_index(ref)
                while len(vals) <= idx:
                    vals.append("")
                t = c.get("t")
                v = c.find("m:v", ns)
                if v is None:
                    val = ""
                elif t == "s":
                    val = ss[int(v.text)]
                else:
                    val = v.text or ""
                vals[idx] = val
            rows.append(vals)
    return rows


def _parse_xlsx_openpyxl(path: Path) -> list[list[str]]:
    import openpyxl

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    return [[str(c) if c is not None else "" for c in row] for row in ws.iter_rows(values_only=True)]


def read_xlsx(path: Path) -> list[list[str]]:
    try:
        return _parse_xlsx_openpyxl(path)
    except ImportError:
        return _parse_xlsx_zip(path)


def copy_xlsx_if_needed(src: Path) -> Path:
    tmp = Path(__file__).resolve().parent / "_tmp_elite_feedback.xlsx"
    try:
        shutil.copy2(src, tmp)
        return tmp
    except OSError:
        return src


def parse_feedback_rows(rows: list[list[str]]) -> list[dict]:
    records: list[dict] = []
    cur: dict | None = None
    for r in rows[1:]:
        cells = (r + [""] * 7)[:7]
        am, aid, fn, ln, email, ticket, fb = cells
        aid = str(aid).strip().replace(".0", "") if aid else ""
        fb = str(fb).strip() if fb else ""
        if aid:
            if cur:
                records.append(cur)
            cur = {
                "agent": str(am).strip(),
                "aid": aid,
                "name": f"{fn} {ln}".strip(),
                "email": str(email).strip(),
                "ticket": str(ticket).strip(),
                "feedback_parts": [fb] if fb else [],
            }
        elif cur and fb:
            cur["feedback_parts"].append(fb)
    if cur:
        records.append(cur)
    return records


def entry_feedback(record: dict) -> str:
    parts = record.get("feedback_parts")
    if parts is not None:
        return " · ".join(p.strip() for p in parts if p and str(p).strip())
    return str(record.get("feedback") or "").strip()


def summarize_entries(records: list[dict]) -> dict[str, int]:
    with_text = [r for r in records if entry_feedback(r)]
    negative_entries = [r for r in with_text if is_negative(entry_feedback(r))]
    return {
        "totalEntries": len(with_text),
        "negativeEntries": len(negative_entries),
        "positiveEntries": len(with_text) - len(negative_entries),
    }


def dedupe_by_aid(records: list[dict]) -> list[dict]:
    by_aid: dict[str, dict] = {}
    for r in records:
        aid = r["aid"]
        if aid not in by_aid:
            by_aid[aid] = {
                "agent": r["agent"],
                "aid": aid,
                "name": r["name"],
                "email": r["email"],
                "tickets": [r["ticket"]] if r["ticket"] else [],
                "feedback_parts": list(r["feedback_parts"]),
            }
        else:
            existing = by_aid[aid]
            if r["agent"] and not existing["agent"]:
                existing["agent"] = r["agent"]
            if r["ticket"] and r["ticket"] not in existing["tickets"]:
                existing["tickets"].append(r["ticket"])
            existing["feedback_parts"].extend(r["feedback_parts"])
    out = []
    for v in by_aid.values():
        parts = [p.strip() for p in v["feedback_parts"] if p.strip()]
        v["feedback"] = " · ".join(parts)
        v["ticket"] = ", ".join(v["tickets"]) if v["tickets"] else ""
        del v["feedback_parts"]
        del v["tickets"]
        out.append(v)
    return out


def assign_tags(text: str) -> list[str]:
    tags = [tag for tag, pat in TAG_RULES if pat.search(text)]
    return tags or ["no_wins"]


def is_negative(text: str) -> bool:
    if not text.strip():
        return False
    if POSITIVE_ONLY.match(text.strip()):
        return False
    if NEGATIVE_SIGNAL.search(text):
        return True
    for _, pat in TAG_RULES:
        if pat.search(text):
            return True
    negative_phrases = ("terrible", "concerned", "hell", "break", "dry", "rough")
    lower = text.lower()
    return any(p in lower for p in negative_phrases)


def build_metrics_sql(
    aids: list[str],
    before_start: date,
    before_end: date,
    after_start: date,
    after_end: date,
) -> str:
    aid_list = ", ".join(aids)
    bs, be = before_start.isoformat(), before_end.isoformat()
    ast, ae = after_start.isoformat(), after_end.isoformat()
    return f"""
WITH kpi AS (
  SELECT account_id, date,
    SUM(CAST(purchased AS FLOAT64)) AS purchased,
    SUM(CAST(profit AS FLOAT64) - CAST(loss AS FLOAT64)
      - COALESCE(sc_reward_amount, 0)) AS ngr
  FROM `{PROJECT_ID}.jackpota_agg.daily_player_revenue_kpis`
  WHERE account_id IN ({aid_list})
  GROUP BY 1, 2
)
SELECT
  account_id AS aid,
  SUM(purchased) AS lifetime_purchased,
  SUM(IF(date BETWEEN DATE '{bs}' AND DATE '{be}', purchased, 0)) AS purchased_before,
  SUM(IF(date BETWEEN DATE '{ast}' AND DATE '{ae}', purchased, 0)) AS purchased_after,
  SUM(IF(date BETWEEN DATE '{bs}' AND DATE '{be}', ngr, 0)) AS ngr_before,
  SUM(IF(date BETWEEN DATE '{ast}' AND DATE '{ae}', ngr, 0)) AS ngr_after
FROM kpi
GROUP BY 1
"""


def fetch_metrics(
    aids: list[str],
    before_start: date,
    before_end: date,
    after_start: date,
    after_end: date,
) -> dict[str, dict]:
    if not aids:
        return {}
    client = get_client()
    rows = run_query(
        client,
        build_metrics_sql(aids, before_start, before_end, after_start, after_end),
    )
    return {str(r["aid"]): r for r in rows}


def build_player_rows(players: list[dict], metrics: dict[str, dict]) -> list[dict]:
    rows = []
    for p in players:
        m = metrics.get(p["aid"], {})
        pb = float(m.get("purchased_before") or 0)
        pa = float(m.get("purchased_after") or 0)
        nb = float(m.get("ngr_before") or 0)
        na = float(m.get("ngr_after") or 0)
        lt = float(m.get("lifetime_purchased") or 0)
        delta = pa - pb
        delta_pct = (delta / pb * 100) if pb else None
        rows.append(
            {
                "aid": p["aid"],
                "name": p["name"] or "—",
                "agent": p["agent"] or "—",
                "ticket": p["ticket"],
                "tags": p["tags"],
                "feedback": p["feedback"],
                "lifetimePurchased": fmt_money(lt),
                "purchasedBefore": fmt_money(pb),
                "purchasedAfter": fmt_money(pa),
                "ngrBefore": fmt_money(nb),
                "ngrAfter": fmt_money(na),
                "purchaseDelta": fmt_delta(delta, delta_pct),
                "ngrDelta": fmt_delta(na - nb),
                "ngrBeforeAfter": f"{fmt_money(nb)} → {fmt_money(na)}",
                "_lt": lt,
                "_pb": pb,
                "_pa": pa,
                "_nb": nb,
                "_na": na,
            }
        )
    rows.sort(key=lambda r: r["_pa"] - r["_pb"])
    for r in rows:
        for k in list(r):
            if k.startswith("_"):
                del r[k]
    return rows


def tag_counts(players: list[dict]) -> dict[str, int]:
    counts = {t: 0 for t in TAG_LABELS}
    for p in players:
        for t in p["tags"]:
            counts[t] = counts.get(t, 0) + 1
    return counts


def build_tag_segments(counts: dict[str, int]) -> list[dict]:
    total_tags = sum(counts.values())
    segments = [
        {
            "id": tag,
            "value": counts.get(tag, 0),
            "pct": round(100 * counts.get(tag, 0) / total_tags) if total_tags else 0,
            "label": TAG_LABELS[tag],
            "shortLabel": TAG_SHORT[tag],
            "tone": TAG_TONES[tag],
            "color": TAG_COLORS[tag],
            "description": TAG_DESCRIPTIONS[tag],
        }
        for tag in TAG_LABELS
        if counts.get(tag, 0) > 0
    ]
    segments.sort(key=lambda s: s["value"], reverse=True)
    return segments


COLOR_HEX: dict[str, str] = {
    "gray": "#8a8a8a",
    "purple": "#9386F2",
    "green": "#3FA266",
    "yellow": "#F1B467",
    "pink": "#B48EAD",
    "blue": "#7BAFE9",
    "orange": "#D08770",
}


def render_canvas_tsx(meta: dict, players: list[dict], counts: dict[str, int]) -> str:
    meta_json = json.dumps(meta, indent=2)
    players_json = json.dumps(players, indent=2)
    tag_labels_json = json.dumps(TAG_LABELS, indent=2)
    tag_tones_json = json.dumps(TAG_TONES, indent=2)
    tag_desc_json = json.dumps(TAG_DESCRIPTIONS, indent=2)
    segments = build_tag_segments(counts)
    segments_json = json.dumps(segments, indent=2)
    total_tags = sum(counts.values())

    return f"""import {{
  BarChart,
  Card,
  CardBody,
  CollapsibleSection,
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

const TAG_LABELS: Record<string, string> = {tag_labels_json};
const TAG_TONES: Record<string, string> = {tag_tones_json};
const TAG_DESCRIPTIONS: Record<string, string> = {tag_desc_json};

type PlayerRow = {{
  aid: string;
  name: string;
  agent: string;
  ticket: string;
  tags: string[];
  feedback: string;
  lifetimePurchased: string;
  purchasedBefore: string;
  purchasedAfter: string;
  ngrBefore: string;
  ngrAfter: string;
  purchaseDelta: string;
  ngrDelta: string;
  ngrBeforeAfter: string;
}};

const PLAYERS: PlayerRow[] = {players_json};

const TAG_SEGMENTS = {segments_json};
const TAG_TOTAL = {total_tags};

type TagSegment = (typeof TAG_SEGMENTS)[number];

function polar(cx: number, cy: number, r: number, deg: number) {{
  const rad = ((deg - 90) * Math.PI) / 180;
  return {{ x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) }};
}}

function slicePath(cx: number, cy: number, r: number, start: number, end: number) {{
  if (end - start >= 359.99) {{
    return `M ${{cx - r}} ${{cy}} A ${{r}} ${{r}} 0 1 1 ${{cx + r}} ${{cy}} A ${{r}} ${{r}} 0 1 1 ${{cx - r}} ${{cy}} Z`;
  }}
  const s = polar(cx, cy, r, start);
  const e = polar(cx, cy, r, end);
  const large = end - start > 180 ? 1 : 0;
  return `M ${{cx}} ${{cy}} L ${{s.x}} ${{s.y}} A ${{r}} ${{r}} 0 ${{large}} 1 ${{e.x}} ${{e.y}} Z`;
}}

function LabeledPie({{
  segments,
  size,
  activeTag,
  onTagClick,
}}: {{
  segments: readonly TagSegment[];
  size: number;
  activeTag: string;
  onTagClick: (tagId: string) => void;
}}) {{
  const theme = useHostTheme();
  const cx = size / 2;
  const cy = size / 2;
  const r = size / 2 - 8;
  const total = segments.reduce((sum, seg) => sum + seg.value, 0);
  let cursor = 0;
  const slices = segments.map((seg) => {{
    const sweep = total ? (seg.value / total) * 360 : 0;
    const start = cursor;
    const end = cursor + sweep;
    cursor = end;
    const mid = start + sweep / 2;
    const labelPos = polar(cx, cy, r * 0.55, mid);
    return {{ ...seg, start, end, labelPos, sweep }};
  }});

  const toggleTag = (id: string) => {{
    onTagClick(activeTag === id ? "all" : id);
  }};

  return (
    <svg width={{size}} height={{size}} viewBox={{`0 0 ${{size}} ${{size}}`}} style={{{{ flexShrink: 0 }}}}>
      {{slices.map((s) => {{
        const isActive = activeTag === s.id;
        const isDimmed = activeTag !== "all" && !isActive;
        const showLabel = s.pct >= 5 || s.sweep >= 18;
        return (
          <g
            key={{s.id}}
            onClick={{() => toggleTag(s.id)}}
            style={{{{ cursor: "pointer" }}}}
          >
            <path
              d={{slicePath(cx, cy, r, s.start, s.end)}}
              fill={{theme.category[s.color as keyof typeof theme.category]}}
              stroke={{isActive ? theme.accent.primary : theme.bg.editor}}
              strokeWidth={{isActive ? 3 : 2}}
              opacity={{isDimmed ? 0.38 : 1}}
            />
            {{showLabel ? (
              <text
                x={{s.labelPos.x}}
                y={{s.labelPos.y}}
                textAnchor="middle"
                dominantBaseline="middle"
                fill={{theme.text.primary}}
                fontSize={{s.pct >= 12 ? 11 : 9}}
                fontWeight={{600}}
                style={{{{ pointerEvents: "none" }}}}
              >
                <tspan x={{s.labelPos.x}} dy={{s.pct >= 10 ? -5 : 0}}>{{s.shortLabel}}</tspan>
                {{s.pct >= 8 ? <tspan x={{s.labelPos.x}} dy={{14}}>{{s.pct}}%</tspan> : null}}
              </text>
            ) : null}}
          </g>
        );
      }})}}
    </svg>
  );
}}

const TAG_OPTIONS = [
  {{ value: "all", label: "All Tags" }},
  ...Object.entries(TAG_LABELS).map(([value, label]) => ({{ value, label }})),
];

function matchesSearch(row: PlayerRow, query: string): boolean {{
  if (!query.trim()) return true;
  const q = query.trim().toLowerCase();
  return (
    row.name.toLowerCase().includes(q) ||
    row.aid.includes(q) ||
    row.agent.toLowerCase().includes(q) ||
    row.feedback.toLowerCase().includes(q) ||
    row.tags.some((t) => (TAG_LABELS[t] || t).toLowerCase().includes(q))
  );
}}

export default function EliteFeedbackCro() {{
  const theme = useHostTheme();
  const [search, setSearch] = useCanvasState("search", "");
  const [tag, setTag] = useCanvasState("tag", "all");

  const filtered = PLAYERS.filter((row) => {{
    if (tag !== "all" && !row.tags.includes(tag)) return false;
    return matchesSearch(row, search);
  }});

  const filterActive = search.trim() !== "" || tag !== "all";

  return (
    <Stack gap={{16}} style={{{{ padding: 20, maxWidth: 1180, background: theme.bg.editor }}}}>
      <Stack gap={{8}}>
        <H1>Elite Negative Feedback</H1>
        <Stack gap={{4}}>
          <Text tone="tertiary" size="small">
            Before · 22 Apr – 18 May 2026
          </Text>
          <Text tone="tertiary" size="small">
            After · 19 May – 15 Jun 2026
          </Text>
          <Text tone="quaternary" size="small">
            {{META.totalFeedbackEntries}} feedback entries · {{META.playerCount}} negative players
          </Text>
        </Stack>
      </Stack>

      <Grid columns={{4}} gap={{12}}>
        <Stat label="Total Feedback Entries" value={{String(META.totalFeedbackEntries)}} tone="neutral" />
        <Stat label="Negative Players" value={{String(META.playerCount)}} tone="danger" />
        <Stat label="Cohort Purchased Before → After" value={{`${{META.cohortPurchasedBefore}} → ${{META.cohortPurchasedAfter}}`}} tone="warning" />
        <Stat label="Cohort NGR Before → After" value={{`${{META.cohortNgrBefore}} → ${{META.cohortNgrAfter}}`}} tone="info" />
      </Grid>
      <Grid columns={{2}} gap={{12}}>
        <Stat label="Cohort Purchased Change" value={{META.cohortPurchaseDelta}} tone="warning" />
        <Stat label="Cohort NGR Change" value={{META.cohortNgrDelta}} tone="danger" />
      </Grid>

      <Grid columns={{2}} gap={{16}} style={{{{ alignItems: "start" }}}}>
        <Stack gap={{8}}>
          <H2>Cohort Purchased & NGR</H2>
          <Text tone="quaternary" size="small">
            Equal 27-day windows · negative-feedback cohort only · Source: daily_player_revenue_kpis
          </Text>
          <BarChart
            categories={{["Purchased", "NGR"]}}
            series={{[
              {{
                name: "Before 22 Apr – 18 May",
                data: [META.cohortPurchasedBeforeNum, META.cohortNgrBeforeNum],
                tone: "neutral",
              }},
              {{
                name: "After 19 May – 15 Jun",
                data: [META.cohortPurchasedAfterNum, META.cohortNgrAfterNum],
                tone: "danger",
              }},
            ]}}
            valuePrefix="$"
            height={{220}}
          />
        </Stack>

        <Stack gap={{8}}>
          <H2>What Players Complain About</H2>
          <Text tone="quaternary" size="small">
            Click a slice or legend row to filter players by tag
          </Text>
          <Card>
            <CardBody>
              <Row gap={{24}} align="center" wrap style={{{{ justifyContent: "center" }}}}>
                <LabeledPie
                  segments={{TAG_SEGMENTS}}
                  size={{300}}
                  activeTag={{tag}}
                  onTagClick={{setTag}}
                />
                <Stack gap={{8}} style={{{{ flex: 1, minWidth: 260, maxWidth: 420 }}}}>
                  {{TAG_SEGMENTS.map((s) => {{
                    const isActive = tag === s.id;
                    const isDimmed = tag !== "all" && !isActive;
                    return (
                      <Row
                        key={{s.id}}
                        gap={{10}}
                        align="start"
                        onClick={{() => setTag(tag === s.id ? "all" : s.id)}}
                        style={{{{
                          cursor: "pointer",
                          opacity: isDimmed ? 0.45 : 1,
                          padding: "4px 6px",
                          borderRadius: 6,
                          outline: isActive ? `1px solid ${{theme.accent.primary}}` : "none",
                        }}}}
                      >
                        <Swatch color={{s.color as "gray" | "purple" | "green" | "yellow" | "pink" | "blue" | "orange"}} />
                        <Stack gap={{2}} style={{{{ flex: 1 }}}}>
                          <Row gap={{8}} align="center" wrap>
                            <Text size="small" weight="medium">{{s.label}}</Text>
                            <Text size="small" tone="tertiary">{{s.pct}}% · {{s.value}} mentions</Text>
                          </Row>
                          <Text size="small" tone="tertiary">{{s.description}}</Text>
                        </Stack>
                      </Row>
                    );
                  }})}}
                </Stack>
              </Row>
            </CardBody>
          </Card>
        </Stack>
      </Grid>

      <Stack gap={{8}}>
        <Row gap={{6}} wrap align="center">
          <Pill active={{tag === "all"}} onClick={{() => setTag("all")}} size="sm">
            All Tags
          </Pill>
          {{TAG_SEGMENTS.map((s) => (
            <Pill
              key={{s.id}}
              active={{tag === s.id}}
              onClick={{() => setTag(tag === s.id ? "all" : s.id)}}
              size="sm"
            >
              {{s.label}} · {{s.value}}
            </Pill>
          ))}}
        </Row>
      </Stack>

      <Stack gap={{8}}>
        <Row gap={{8}} align="center" wrap>
          <H2>Players & Feedback</H2>
          <Spacer />
          <Text tone="tertiary" size="small">
            {{filterActive ? `Showing ${{filtered.length}} of ${{PLAYERS.length}}` : `${{PLAYERS.length}} players`}}
          </Text>
        </Row>

        <Row gap={{8}} align="center" wrap>
          <TextInput
            value={{search}}
            onChange={{setSearch}}
            placeholder="Search AID, name, agent, feedback…"
            type="search"
            style={{{{ flex: "1 1 220px", minWidth: 200 }}}}
          />
          <Select
            value={{tag}}
            onChange={{setTag}}
            options={{TAG_OPTIONS}}
            style={{{{ flex: "0 0 180px" }}}}
          />
        </Row>

        <Table
          headers={{[
            "AID",
            "Agent",
            "Name",
            "Tags",
            "Feedback",
            "Lifetime Purchased",
            "Purchased Before",
            "Purchased After",
            "Purchased Change",
            "NGR Before",
            "NGR After",
            "NGR Change",
          ]}}
          rows={{filtered.map((p) => [
            p.aid,
            p.agent,
            p.name,
            p.tags.map((t) => TAG_LABELS[t] || t).join(", "),
            p.feedback,
            p.lifetimePurchased,
            p.purchasedBefore,
            p.purchasedAfter,
            p.purchaseDelta,
            p.ngrBefore,
            p.ngrAfter,
            p.ngrDelta,
          ])}}
          columnAlign={{[
            "left", "left", "left", "left", "left", "right", "right", "right", "right",
            "right", "right", "right",
          ]}}
          striped
          stickyHeader
          emptyMessage="No players match the current filters."
        />

        <Stack gap={{4}}>
          <Text tone="tertiary" size="small" weight="medium">
            Full Feedback
          </Text>
          {{filtered.map((p) => (
            <CollapsibleSection
              key={{p.aid}}
              title={{`${{p.name}} · AID ${{p.aid}} · Purchased ${{p.purchaseDelta}} · NGR ${{p.ngrDelta}}`}}
              count={{p.tags.length}}
              trailing={{(
                <Text size="small" tone="tertiary">
                  {{p.tags.map((t) => TAG_LABELS[t] || t).join(" · ")}}
                </Text>
              )}}
            >
              {{p.ticket ? (
                <Text size="small" tone="quaternary" style={{{{ marginBottom: 6 }}}}>
                  Ticket {{p.ticket}} · Agent {{p.agent}}
                </Text>
              ) : (
                <Text size="small" tone="quaternary" style={{{{ marginBottom: 6 }}}}>
                  Agent {{p.agent}}
                </Text>
              )}}
              <Text size="small" tone="secondary" style={{{{ whiteSpace: "pre-wrap", marginBottom: 8 }}}}>
                {{p.feedback}}
              </Text>
              <Text size="small" tone="tertiary">
                Purchased {{p.purchasedBefore}} → {{p.purchasedAfter}} ({{p.purchaseDelta}}) ·
                NGR {{p.ngrBefore}} → {{p.ngrAfter}} ({{p.ngrDelta}})
              </Text>
            </CollapsibleSection>
          ))}}
        </Stack>
      </Stack>
    </Stack>
  );
}}
"""


def build_markdown_export(
    meta: dict,
    players: list[dict],
    counts: dict[str, int],
    excluded: list[dict],
) -> str:
    total_tags = sum(counts.values())
    lines = [
        "# Elite Negative Feedback Export",
        "",
        f"**Before:** 22 Apr – 18 May 2026  ",
        f"**After:** 19 May – 15 Jun 2026",
        "",
        "## Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total feedback entries | {meta['totalFeedbackEntries']} |",
        f"| Negative feedback entries | {meta['negativeFeedbackEntries']} |",
        f"| Negative players | {meta['playerCount']} |",
        f"| Unique players in file | {meta['totalPlayers']} |",
        f"| Excluded positive or empty | {meta['excludedCount']} |",
        f"| Cohort purchased before → after | {meta['cohortPurchasedBefore']} → {meta['cohortPurchasedAfter']} |",
        f"| Cohort purchased change | {meta['cohortPurchaseDelta']} |",
        f"| Cohort NGR before → after | {meta['cohortNgrBefore']} → {meta['cohortNgrAfter']} |",
        f"| Cohort NGR change | {meta['cohortNgrDelta']} |",
        "",
        "## Issue Themes",
        "",
    ]
    segments = sorted(
        ((tag, counts[tag]) for tag in TAG_LABELS if counts.get(tag)),
        key=lambda x: x[1],
        reverse=True,
    )
    for tag, n in segments:
        pct = round(100 * n / total_tags) if total_tags else 0
        lines.append(f"- **{TAG_LABELS[tag]}** — {n} mentions · {pct}% — {TAG_DESCRIPTIONS[tag]}")
    lines.extend(["", "## Excluded Players", ""])
    if excluded:
        for p in excluded:
            fb = p.get("feedback") or "(empty)"
            lines.append(f"- AID {p['aid']} · {p['name']} · {fb}")
    else:
        lines.append("- None")
    lines.extend(["", "## Negative Players", ""])
    for p in players:
        tags = ", ".join(TAG_LABELS[t] for t in p.get("tags", []))
        lines.extend(
            [
                f"### {p['name']} · AID {p['aid']}",
                "",
                f"- **Agent:** {p['agent']}",
                f"- **Ticket:** {p['ticket'] or '—'}",
                f"- **Tags:** {tags}",
                f"- **Lifetime purchased:** {p['lifetimePurchased']}",
                f"- **Purchased before → after:** {p['purchasedBefore']} → {p['purchasedAfter']} · {p['purchaseDelta']}",
                f"- **NGR before → after:** {p['ngrBefore']} → {p['ngrAfter']} · {p['ngrDelta']}",
                f"- **Feedback:** {p['feedback']}",
                "",
            ]
        )
    lines.extend(
        [
            "---",
            "",
            "Regenerate: `python feedback_cro/generate_elite_feedback_cro_canvas.py`",
            "",
            "Canvas: `~/.cursor/projects/<workspace>/canvases/elite-feedback-cro.canvas.tsx`",
            "",
        ]
    )
    return "\n".join(lines)


def build_html_export(meta: dict, players: list[dict], counts: dict[str, int]) -> str:
    segments = build_tag_segments(counts)
    data_blob = json.dumps(
        {
            "meta": meta,
            "segments": segments,
            "players": players,
            "tagLabels": TAG_LABELS,
            "colors": COLOR_HEX,
        },
        ensure_ascii=False,
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Elite Negative Feedback</title>
  <style>
    :root {{
      --bg: #181818;
      --text: #e4e4e4;
      --text-2: rgba(228,228,228,0.55);
      --text-3: rgba(228,228,228,0.36);
      --stroke: rgba(228,228,228,0.12);
      --fill: rgba(228,228,228,0.07);
      --accent: #599ce7;
      --danger: #d08770;
      --warning: #f1b467;
      --info: #7bafe9;
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
    .wrap {{ max-width: 1180px; margin: 0 auto; padding: 20px; }}
    h1 {{ margin: 0 0 8px; font-size: 24px; font-weight: 600; }}
    h2 {{ margin: 0 0 8px; font-size: 16px; font-weight: 600; }}
    .sub {{ color: var(--text-2); font-size: 13px; margin: 2px 0; }}
    .sub-faint {{ color: var(--text-3); font-size: 13px; margin-top: 4px; }}
    .stats4, .stats2 {{
      display: grid; gap: 12px; margin: 16px 0;
    }}
    .stats4 {{ grid-template-columns: repeat(4, minmax(0, 1fr)); }}
    .stats2 {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    .stat {{
      background: var(--fill);
      border: 1px solid var(--stroke);
      border-radius: 8px;
      padding: 12px;
    }}
    .stat label {{
      display: block;
      color: var(--text-3);
      font-size: 12px;
      margin-bottom: 6px;
    }}
    .stat .val {{ font-size: 17px; font-weight: 600; }}
    .stat.warn .val {{ color: var(--warning); }}
    .stat.danger .val {{ color: var(--danger); }}
    .stat.info .val {{ color: var(--info); }}
    .grid2 {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
      align-items: start;
      margin: 16px 0;
    }}
    @media (max-width: 900px) {{
      .stats4 {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .grid2 {{ grid-template-columns: 1fr; }}
    }}
    .card {{
      background: var(--fill);
      border: 1px solid var(--stroke);
      border-radius: 8px;
      padding: 16px;
    }}
    .caption {{ color: var(--text-3); font-size: 12px; margin-bottom: 10px; }}
    .chart-row {{
      display: flex; gap: 24px; align-items: center; justify-content: center; flex-wrap: wrap;
    }}
    .legend {{ flex: 1; min-width: 260px; max-width: 420px; display: flex; flex-direction: column; gap: 8px; }}
    .legend-item {{
      display: flex; gap: 10px; align-items: flex-start;
      padding: 4px 6px; border-radius: 6px; cursor: pointer;
    }}
    .legend-item.active {{ outline: 1px solid var(--accent); }}
    .legend-item.dim {{ opacity: 0.45; }}
    .swatch {{ width: 10px; height: 10px; border-radius: 2px; margin-top: 4px; flex-shrink: 0; }}
    .legend-title {{ font-weight: 600; font-size: 13px; }}
    .legend-meta {{ color: var(--text-3); font-size: 12px; }}
    .legend-desc {{ color: var(--text-3); font-size: 12px; margin-top: 2px; }}
    .bars {{ display: flex; gap: 28px; align-items: flex-end; height: 220px; padding: 12px 8px 0; }}
    .bar-group {{ display: flex; flex-direction: column; align-items: center; gap: 8px; flex: 1; }}
    .bar-pair {{ display: flex; gap: 8px; align-items: flex-end; height: 180px; }}
    .bar {{
      width: 36px; border-radius: 4px 4px 0 0; min-height: 2px;
    }}
    .bar.before {{ background: rgba(228,228,228,0.35); }}
    .bar.after {{ background: var(--danger); }}
    .bar-label {{ color: var(--text-3); font-size: 12px; }}
    .bar-val {{ font-size: 11px; color: var(--text-2); margin-top: 4px; text-align: center; }}
    .bar-legend {{ display: flex; gap: 16px; margin-top: 10px; font-size: 12px; color: var(--text-3); }}
    .dot {{ display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 6px; vertical-align: -1px; }}
    .pills {{ display: flex; flex-wrap: wrap; gap: 6px; margin: 12px 0; }}
    .pill {{
      background: var(--fill); border: 1px solid var(--stroke); color: var(--text-2);
      border-radius: 999px; padding: 4px 10px; font-size: 12px; cursor: pointer;
    }}
    .pill.active {{ border-color: var(--accent); color: var(--text); }}
    .toolbar {{ display: flex; gap: 8px; flex-wrap: wrap; margin: 12px 0; }}
    .toolbar input, .toolbar select {{
      background: var(--fill); border: 1px solid var(--stroke); color: var(--text);
      border-radius: 6px; padding: 8px 10px; font-size: 13px;
    }}
    .toolbar input {{ flex: 1 1 220px; min-width: 200px; }}
    .toolbar select {{ flex: 0 0 180px; }}
    .section-head {{ display: flex; justify-content: space-between; align-items: center; gap: 8px; margin: 8px 0; }}
    .count {{ color: var(--text-3); font-size: 12px; }}
    .table-wrap {{ overflow: auto; border: 1px solid var(--stroke); border-radius: 8px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
    th, td {{ padding: 8px 10px; border-bottom: 1px solid var(--stroke); vertical-align: top; }}
    th {{
      position: sticky; top: 0; background: #1f1f1f; text-align: left; font-weight: 600;
    }}
    tr:nth-child(even) td {{ background: rgba(255,255,255,0.02); }}
    td.num {{ text-align: right; white-space: nowrap; }}
    td.feedback {{ min-width: 240px; max-width: 360px; white-space: pre-wrap; }}
    details {{
      border: 1px solid var(--stroke); border-radius: 6px; padding: 8px 10px; margin-top: 6px;
      background: rgba(255,255,255,0.02);
    }}
    summary {{ cursor: pointer; font-size: 13px; font-weight: 600; }}
    .detail-meta {{ color: var(--text-3); font-size: 12px; margin: 6px 0; }}
    .detail-body {{ color: var(--text-2); font-size: 13px; white-space: pre-wrap; margin-top: 8px; }}
    #pie svg {{ cursor: pointer; }}
    .slice-dim {{ opacity: 0.38; }}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>Elite Negative Feedback</h1>
    <p class="sub">Before · 22 Apr – 18 May 2026</p>
    <p class="sub">After · 19 May – 15 Jun 2026</p>
    <p class="sub-faint" id="entryLine"></p>

    <div class="stats4" id="stats4"></div>
    <div class="stats2" id="stats2"></div>

    <div class="grid2">
      <div>
        <h2>Cohort Purchased &amp; NGR</h2>
        <p class="caption">Equal 27-day windows · negative-feedback cohort only</p>
        <div class="card" id="barChart"></div>
      </div>
      <div>
        <h2>What Players Complain About</h2>
        <p class="caption">Click a slice or legend row to filter players by tag</p>
        <div class="card">
          <div class="chart-row">
            <div id="pie"></div>
            <div class="legend" id="legend"></div>
          </div>
        </div>
      </div>
    </div>

    <div class="pills" id="pills"></div>

    <div class="section-head">
      <h2>Players &amp; Feedback</h2>
      <span class="count" id="playerCount"></span>
    </div>
    <div class="toolbar">
      <input id="search" type="search" placeholder="Search AID, name, agent, feedback…" />
      <select id="tagSelect"></select>
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>AID</th><th>Agent</th><th>Name</th><th>Tags</th><th>Feedback</th>
            <th>Lifetime Purchased</th><th>Purchased Before</th><th>Purchased After</th><th>Purchased Change</th>
            <th>NGR Before</th><th>NGR After</th><th>NGR Change</th>
          </tr>
        </thead>
        <tbody id="tableBody"></tbody>
      </table>
    </div>
    <h2 style="margin-top:20px;font-size:14px;color:var(--text-3)">Full Feedback</h2>
    <div id="details"></div>
  </div>
  <script>
    const DATA = {data_blob};
    const META = DATA.meta;
    const TAG_SEGMENTS = DATA.segments;
    const PLAYERS = DATA.players;
    const TAG_LABELS = DATA.tagLabels;
    const COLORS = DATA.colors;

    let activeTag = "all";
    let search = "";

    function polar(cx, cy, r, deg) {{
      const rad = ((deg - 90) * Math.PI) / 180;
      return {{ x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) }};
    }}

    function slicePath(cx, cy, r, start, end) {{
      if (end - start >= 359.99) {{
        return `M ${{cx - r}} ${{cy}} A ${{r}} ${{r}} 0 1 1 ${{cx + r}} ${{cy}} A ${{r}} ${{r}} 0 1 1 ${{cx - r}} ${{cy}} Z`;
      }}
      const s = polar(cx, cy, r, start);
      const e = polar(cx, cy, r, end);
      const large = end - start > 180 ? 1 : 0;
      return `M ${{cx}} ${{cy}} L ${{s.x}} ${{s.y}} A ${{r}} ${{r}} 0 ${{large}} 1 ${{e.x}} ${{e.y}} Z`;
    }}

    function setTag(tag) {{
      activeTag = tag;
      render();
    }}

    function toggleTag(id) {{
      setTag(activeTag === id ? "all" : id);
    }}

    function matchesSearch(row) {{
      if (!search.trim()) return true;
      const q = search.trim().toLowerCase();
      return (
        row.name.toLowerCase().includes(q) ||
        row.aid.includes(q) ||
        row.agent.toLowerCase().includes(q) ||
        row.feedback.toLowerCase().includes(q) ||
        row.tags.some((t) => (TAG_LABELS[t] || t).toLowerCase().includes(q))
      );
    }}

    function filteredPlayers() {{
      return PLAYERS.filter((row) => {{
        if (activeTag !== "all" && !row.tags.includes(activeTag)) return false;
        return matchesSearch(row);
      }});
    }}

    function renderStats() {{
      document.getElementById("entryLine").textContent =
        `${{META.totalFeedbackEntries}} feedback entries · ${{META.playerCount}} negative players`;
      document.getElementById("stats4").innerHTML = `
        <div class="stat"><label>Total Feedback Entries</label><div class="val">${{META.totalFeedbackEntries}}</div></div>
        <div class="stat danger"><label>Negative Players</label><div class="val">${{META.playerCount}}</div></div>
        <div class="stat warn"><label>Cohort Purchased Before → After</label><div class="val">${{META.cohortPurchasedBefore}} → ${{META.cohortPurchasedAfter}}</div></div>
        <div class="stat info"><label>Cohort NGR Before → After</label><div class="val">${{META.cohortNgrBefore}} → ${{META.cohortNgrAfter}}</div></div>`;
      document.getElementById("stats2").innerHTML = `
        <div class="stat warn"><label>Cohort Purchased Change</label><div class="val">${{META.cohortPurchaseDelta}}</div></div>
        <div class="stat danger"><label>Cohort NGR Change</label><div class="val">${{META.cohortNgrDelta}}</div></div>`;
    }}

    function renderBarChart() {{
      const vals = [
        {{ label: "Purchased", before: META.cohortPurchasedBeforeNum, after: META.cohortPurchasedAfterNum }},
        {{ label: "NGR", before: META.cohortNgrBeforeNum, after: META.cohortNgrAfterNum }},
      ];
      const max = Math.max(...vals.flatMap((v) => [v.before, v.after]), 1);
      const fmt = (n) => "$" + Math.round(n).toLocaleString();
      document.getElementById("barChart").innerHTML = `
        <div class="bars">${{vals.map((v) => `
          <div class="bar-group">
            <div class="bar-pair">
              <div>
                <div class="bar before" style="height:${{Math.max(4, (v.before / max) * 170)}}px" title="Before ${{fmt(v.before)}}"></div>
                <div class="bar-val">${{fmt(v.before)}}</div>
              </div>
              <div>
                <div class="bar after" style="height:${{Math.max(4, (v.after / max) * 170)}}px" title="After ${{fmt(v.after)}}"></div>
                <div class="bar-val">${{fmt(v.after)}}</div>
              </div>
            </div>
            <div class="bar-label">${{v.label}}</div>
          </div>`).join("")}}
        </div>
        <div class="bar-legend">
          <span><span class="dot" style="background:rgba(228,228,228,0.35)"></span>Before 22 Apr – 18 May</span>
          <span><span class="dot" style="background:var(--danger)"></span>After 19 May – 15 Jun</span>
        </div>`;
    }}

    function renderPie() {{
      const size = 300;
      const cx = size / 2;
      const cy = size / 2;
      const r = size / 2 - 8;
      const total = TAG_SEGMENTS.reduce((s, seg) => s + seg.value, 0);
      let cursor = 0;
      const slices = TAG_SEGMENTS.map((seg) => {{
        const sweep = total ? (seg.value / total) * 360 : 0;
        const start = cursor;
        const end = cursor + sweep;
        cursor = end;
        const mid = start + sweep / 2;
        const labelPos = polar(cx, cy, r * 0.55, mid);
        return {{ ...seg, start, end, labelPos, sweep }};
      }});
      const svg = slices.map((s) => {{
        const isActive = activeTag === s.id;
        const isDimmed = activeTag !== "all" && !isActive;
        const showLabel = s.pct >= 5 || s.sweep >= 18;
        const fill = COLORS[s.color] || "#888";
        const label = showLabel ? `
          <text x="${{s.labelPos.x}}" y="${{s.labelPos.y}}" text-anchor="middle" dominant-baseline="middle"
            fill="#e4e4e4" font-size="${{s.pct >= 12 ? 11 : 9}}" font-weight="600" pointer-events="none">
            <tspan x="${{s.labelPos.x}}" dy="${{s.pct >= 10 ? -5 : 0}}">${{s.shortLabel}}</tspan>
            ${{s.pct >= 8 ? `<tspan x="${{s.labelPos.x}}" dy="14">${{s.pct}}%</tspan>` : ""}}
          </text>` : "";
        return `<g class="${{isDimmed ? "slice-dim" : ""}}" onclick="toggleTag('${{s.id}}')">
          <path d="${{slicePath(cx, cy, r, s.start, s.end)}}" fill="${{fill}}"
            stroke="${{isActive ? "#599ce7" : "#181818"}}" stroke-width="${{isActive ? 3 : 2}}"></path>
          ${{label}}
        </g>`;
      }}).join("");
      document.getElementById("pie").innerHTML =
        `<svg width="${{size}}" height="${{size}}" viewBox="0 0 ${{size}} ${{size}}">${{svg}}</svg>`;
    }}

    function renderLegend() {{
      document.getElementById("legend").innerHTML = TAG_SEGMENTS.map((s) => {{
        const isActive = activeTag === s.id;
        const isDimmed = activeTag !== "all" && !isActive;
        return `<div class="legend-item ${{isActive ? "active" : ""}} ${{isDimmed ? "dim" : ""}}"
          onclick="toggleTag('${{s.id}}')">
          <span class="swatch" style="background:${{COLORS[s.color]}}"></span>
          <div>
            <div><span class="legend-title">${{s.label}}</span>
              <span class="legend-meta">${{s.pct}}% · ${{s.value}} mentions</span></div>
            <div class="legend-desc">${{s.description}}</div>
          </div>
        </div>`;
      }}).join("");
    }}

    function renderPills() {{
      const pills = [`<button class="pill ${{activeTag === "all" ? "active" : ""}}" onclick="setTag('all')">All Tags</button>`]
        .concat(TAG_SEGMENTS.map((s) =>
          `<button class="pill ${{activeTag === s.id ? "active" : ""}}" onclick="toggleTag('${{s.id}}')">${{s.label}} · ${{s.value}}</button>`
        ));
      document.getElementById("pills").innerHTML = pills.join("");
      const opts = [`<option value="all">All Tags</option>`]
        .concat(Object.entries(TAG_LABELS).map(([v, l]) =>
          `<option value="${{v}}" ${{activeTag === v ? "selected" : ""}}>${{l}}</option>`
        ));
      document.getElementById("tagSelect").innerHTML = opts.join("");
    }}

    function esc(s) {{
      return String(s)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
    }}

    function renderTable() {{
      const rows = filteredPlayers();
      const filterActive = search.trim() !== "" || activeTag !== "all";
      document.getElementById("playerCount").textContent = filterActive
        ? `Showing ${{rows.length}} of ${{PLAYERS.length}}`
        : `${{PLAYERS.length}} players`;
      document.getElementById("tableBody").innerHTML = rows.map((p) => `
        <tr>
          <td>${{esc(p.aid)}}</td>
          <td>${{esc(p.agent)}}</td>
          <td>${{esc(p.name)}}</td>
          <td>${{esc(p.tags.map((t) => TAG_LABELS[t] || t).join(", "))}}</td>
          <td class="feedback">${{esc(p.feedback)}}</td>
          <td class="num">${{esc(p.lifetimePurchased)}}</td>
          <td class="num">${{esc(p.purchasedBefore)}}</td>
          <td class="num">${{esc(p.purchasedAfter)}}</td>
          <td class="num">${{esc(p.purchaseDelta)}}</td>
          <td class="num">${{esc(p.ngrBefore)}}</td>
          <td class="num">${{esc(p.ngrAfter)}}</td>
          <td class="num">${{esc(p.ngrDelta)}}</td>
        </tr>`).join("");
      document.getElementById("details").innerHTML = rows.map((p) => `
        <details>
          <summary>${{esc(p.name)}} · AID ${{esc(p.aid)}} · Purchased ${{esc(p.purchaseDelta)}} · NGR ${{esc(p.ngrDelta)}}</summary>
          <div class="detail-meta">${{p.ticket ? `Ticket ${{esc(p.ticket)}} · ` : ""}}Agent ${{esc(p.agent)}} · ${{esc(p.tags.map((t) => TAG_LABELS[t] || t).join(" · "))}}</div>
          <div class="detail-body">${{esc(p.feedback)}}</div>
          <div class="detail-meta">Purchased ${{esc(p.purchasedBefore)}} → ${{esc(p.purchasedAfter)}} · NGR ${{esc(p.ngrBefore)}} → ${{esc(p.ngrAfter)}}</div>
        </details>`).join("");
    }}

    function render() {{
      renderStats();
      renderBarChart();
      renderPie();
      renderLegend();
      renderPills();
      renderTable();
    }}

    document.getElementById("search").addEventListener("input", (e) => {{
      search = e.target.value;
      renderTable();
    }});
    document.getElementById("tagSelect").addEventListener("change", (e) => {{
      setTag(e.target.value);
    }});

    render();
  </script>
</body>
</html>"""


def write_exports(
    meta: dict,
    players: list[dict],
    counts: dict[str, int],
    excluded: list[dict],
    canvas_path: Path,
    copy_desktop: bool = False,
) -> dict[str, Path]:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    HANDOFFS_DIR.mkdir(parents=True, exist_ok=True)
    md_path = EXPORT_DIR / "elite-feedback-cro-export.md"
    html_path = EXPORT_DIR / "elite-feedback-cro-export.html"
    handoff_canvas = HANDOFFS_DIR / "elite-feedback-cro.canvas.tsx"
    md_path.write_text(build_markdown_export(meta, players, counts, excluded), encoding="utf-8")
    html_path.write_text(build_html_export(meta, players, counts), encoding="utf-8")
    shutil.copy2(canvas_path, handoff_canvas)
    paths = {"markdown": md_path, "html": html_path, "canvas_backup": handoff_canvas}
    if copy_desktop:
        DESKTOP_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        desktop_html = DESKTOP_EXPORT_DIR / "Elite-Feedback-CRO-Export.html"
        desktop_md = DESKTOP_EXPORT_DIR / "Elite-Feedback-CRO-Export.md"
        shutil.copy2(html_path, desktop_html)
        shutil.copy2(md_path, desktop_md)
        paths["desktop_html"] = desktop_html
        paths["desktop_md"] = desktop_md
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Elite feedback CRO canvas")
    parser.add_argument("--xlsx", type=Path, default=DEFAULT_XLSX)
    parser.add_argument("--canvas-dir", type=Path, default=DEFAULT_CANVAS_DIR)
    parser.add_argument("--no-query", action="store_true", help="Skip BigQuery (dry run)")
    parser.add_argument("--before-start", type=date.fromisoformat, default=DEFAULT_BEFORE_START)
    parser.add_argument("--before-end", type=date.fromisoformat, default=DEFAULT_BEFORE_END)
    parser.add_argument("--after-start", type=date.fromisoformat, default=DEFAULT_AFTER_START)
    parser.add_argument("--after-end", type=date.fromisoformat, default=date.today())
    parser.add_argument(
        "--copy-desktop",
        action="store_true",
        help="Copy HTML + MD to Desktop/VIP/Cursor",
    )
    args = parser.parse_args()
    if args.before_start > args.before_end:
        parser.error("--before-start must be on or before --before-end")
    if args.after_start > args.after_end:
        parser.error("--after-start must be on or before --after-end")

    xlsx_path = copy_xlsx_if_needed(args.xlsx)
    rows = read_xlsx(xlsx_path)
    records = parse_feedback_rows(rows)
    entry_stats = summarize_entries(records)
    records = dedupe_by_aid(records)

    negative = [r for r in records if is_negative(r["feedback"])]
    excluded = [r for r in records if r not in negative]
    for p in negative:
        p["tags"] = assign_tags(p["feedback"])

    aids = [p["aid"] for p in negative]
    metrics = (
        {}
        if args.no_query
        else fetch_metrics(
            aids,
            args.before_start,
            args.before_end,
            args.after_start,
            args.after_end,
        )
    )
    player_rows = build_player_rows(negative, metrics)
    counts = tag_counts(negative)

    cohort_pb = sum(float(metrics.get(a, {}).get("purchased_before") or 0) for a in aids)
    cohort_pa = sum(float(metrics.get(a, {}).get("purchased_after") or 0) for a in aids)
    cohort_nb = sum(float(metrics.get(a, {}).get("ngr_before") or 0) for a in aids)
    cohort_na = sum(float(metrics.get(a, {}).get("ngr_after") or 0) for a in aids)
    cohort_delta = cohort_pa - cohort_pb
    cohort_delta_pct = (cohort_delta / cohort_pb * 100) if cohort_pb else None
    cohort_ngr_delta = cohort_na - cohort_nb

    meta = {
        "beforeWindow": f"Before: {args.before_start.strftime('%d %b')} – {args.before_end.strftime('%d %b %Y')}",
        "afterWindow": f"After: {args.after_start.strftime('%d %b')} – {args.after_end.strftime('%d %b %Y')}",
        "totalFeedbackEntries": entry_stats["totalEntries"],
        "negativeFeedbackEntries": entry_stats["negativeEntries"],
        "playerCount": len(negative),
        "totalPlayers": len(records),
        "excludedCount": len(excluded),
        "cohortPurchasedBefore": fmt_money(cohort_pb),
        "cohortPurchasedAfter": fmt_money(cohort_pa),
        "cohortNgrBefore": fmt_money(cohort_nb),
        "cohortNgrAfter": fmt_money(cohort_na),
        "cohortPurchasedBeforeNum": round(cohort_pb),
        "cohortPurchasedAfterNum": round(cohort_pa),
        "cohortNgrBeforeNum": round(cohort_nb),
        "cohortNgrAfterNum": round(cohort_na),
        "cohortPurchaseDelta": fmt_delta(cohort_delta, cohort_delta_pct),
        "cohortNgrDelta": fmt_delta(cohort_ngr_delta),
    }

    args.canvas_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.canvas_dir / "elite-feedback-cro.canvas.tsx"
    out_path.write_text(render_canvas_tsx(meta, player_rows, counts), encoding="utf-8")
    export_paths = write_exports(
        meta, player_rows, counts, excluded, out_path, copy_desktop=args.copy_desktop
    )

    tmp = Path(__file__).resolve().parent / "_tmp_elite_feedback.xlsx"
    if tmp.exists() and tmp != args.xlsx:
        try:
            tmp.unlink()
        except OSError:
            pass

    print(f"Feedback entries: {entry_stats['totalEntries']} ({entry_stats['negativeEntries']} negative entries)")
    print(f"Negative players: {len(negative)} / {len(records)} unique ({len(excluded)} excluded)")
    print(f"Tag counts: {counts}")
    print(f"Cohort purchase delta: {meta['cohortPurchaseDelta']}")
    print(f"Cohort NGR delta: {meta['cohortNgrDelta']}")
    print(f"Canvas: {out_path}")
    print(f"Export MD: {export_paths['markdown']}")
    print(f"Export HTML: {export_paths['html']}")
    print(f"Canvas backup: {export_paths['canvas_backup']}")
    if args.copy_desktop:
        print(f"Desktop HTML: {export_paths['desktop_html']}")
        print(f"Desktop MD: {export_paths['desktop_md']}")


if __name__ == "__main__":
    main()
