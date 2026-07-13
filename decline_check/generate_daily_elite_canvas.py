"""Generate Elite daily summary canvas beside chat in Cursor."""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from generate_daily_elite_summary import weekday_label

DEFAULT_CANVAS_DIR = Path(
    r"C:\Users\Owner\.cursor\projects\c-Users-Owner-Downloads-Elite\canvases"
)

REASON_TONE: dict[str, str] = {
    # Critical — act today / escalate (red)
    "redemption_in_progress": "danger",
    "payment_failed": "danger",
    "churn_lapsed": "danger",
    "self_exclusion": "danger",
    "account_locked": "danger",
    "red_flag": "danger",
    # Medium — watch / soft action (yellow)
    "same_weekday_skip": "warning",
    "general_spend_softening": "warning",
    # All good — no purchase chase (green)
    "big_win_day_before": "success",
}


def tone_for_reason(code: str | None) -> str:
    if not code:
        return "warning"
    return REASON_TONE.get(code, "warning")


def fmt_money_short(v) -> str:
    if v is None:
        return "$0"
    return f"${round(float(v)):,}"


def _day_row(rows: list[dict], d: date) -> dict:
    return next((r for r in rows if str(r.get("date"))[:10] == d.isoformat()), {})


def _fmt_wow_money(this: float, prior: float) -> str:
    chg = this - prior
    pct = (chg / prior * 100) if prior else 0
    sign = "+" if chg >= 0 else ""
    return f"{sign}${round(chg):,} ({pct:+.1f}%)"


def _fmt_wow_count(this: int, prior: int) -> str:
    chg = this - prior
    pct = (chg / prior * 100) if prior else 0
    return f"{chg:+d} ({pct:+.1f}%)"


def _wow_tone(chg: float) -> str:
    if chg > 0:
        return "success"
    if chg < 0:
        return "danger"
    return "neutral"


def build_report(report_date: date, day_rows: list[dict], overall_rows: list[dict]) -> dict:
    prior_day = report_date - timedelta(days=7)
    day_name = weekday_label(report_date)
    elite_this = _day_row(day_rows, report_date)
    elite_prior = _day_row(day_rows, prior_day)
    overall_this = _day_row(overall_rows, report_date)
    overall_prior = _day_row(overall_rows, prior_day)

    elite_rev_this = float(elite_this.get("revenue") or 0)
    elite_rev_prior = float(elite_prior.get("revenue") or 0)
    overall_rev_this = float(overall_this.get("revenue") or 0)
    overall_rev_prior = float(overall_prior.get("revenue") or 0)
    elite_ply_this = int(elite_this.get("players") or 0)
    elite_ply_prior = int(elite_prior.get("players") or 0)
    overall_ply_this = int(overall_this.get("players") or 0)
    overall_ply_prior = int(overall_prior.get("players") or 0)
    elite_share = (elite_rev_this / overall_rev_this * 100) if overall_rev_this else 0
    elite_rev_chg = elite_rev_this - elite_rev_prior
    overall_rev_chg = overall_rev_this - overall_rev_prior

    segments = [
        {
            "label": "Jackpota",
            "revThis": fmt_money_short(overall_rev_this),
            "revPrior": fmt_money_short(overall_rev_prior),
            "revWow": _fmt_wow_money(overall_rev_this, overall_rev_prior),
            "plyThis": str(overall_ply_this),
            "plyPrior": str(overall_ply_prior),
            "plyWow": _fmt_wow_count(overall_ply_this, overall_ply_prior),
            "share": "",
            "tone": _wow_tone(overall_rev_chg),
        },
        {
            "label": "Elite",
            "revThis": fmt_money_short(elite_rev_this),
            "revPrior": fmt_money_short(elite_rev_prior),
            "revWow": _fmt_wow_money(elite_rev_this, elite_rev_prior),
            "plyThis": str(elite_ply_this),
            "plyPrior": str(elite_ply_prior),
            "plyWow": _fmt_wow_count(elite_ply_this, elite_ply_prior),
            "share": f"{elite_share:.1f}% of Jackpota",
            "tone": _wow_tone(elite_rev_chg),
        },
    ]

    overall_pct = ((overall_rev_this - overall_rev_prior) / overall_rev_prior * 100) if overall_rev_prior else 0
    elite_pct = ((elite_rev_this - elite_rev_prior) / elite_rev_prior * 100) if elite_rev_prior else 0

    return {
        "date": report_date.isoformat(),
        "weekday": day_name,
        "priorDate": prior_day.isoformat(),
        "headline": (
            f"Jackpota revenue {overall_pct:+.1f}% vs last {day_name} · "
            f"Elite revenue {elite_pct:+.1f}% vs last {day_name} · "
            f"Elite share {elite_share:.1f}% of Jackpota"
        ),
        "segments": segments,
    }


def build_top10_rows(top10: list[dict]) -> list[dict]:
    from generate_daily_elite_summary import looker_account_portal_url
    from wow_drop_reason import M_NONE_IN_7D, format_agent_name, split_reason_parts

    rows = []
    for r in top10:
        tone = tone_for_reason(r.get("reason_code"))
        reason_raw = r.get("reason_table") or r.get("reason_detail") or "n/a"
        aid = str(r.get("AID", ""))
        row = {
            "aid": aid,
            "aidUrl": looker_account_portal_url(aid),
            "name": r.get("name") or "n/a",
            "agent": r.get("agent") or "n/a",
            "agentName": format_agent_name(r),
            "thisDay": fmt_money_short(r.get("this_weekday")),
            "priorDay": fmt_money_short(r.get("prior_weekday")),
            "priorPriorNum": float(r.get("prior_weekday") or 0),
            "sortGap": float(r.get("delta") or 0),
            "zeroDay": float(r.get("this_weekday") or 0) <= 0,
            "purchase7d": r.get("purchase_7d_combined") or r.get("purchase_calendar") or M_NONE_IN_7D,
            "lifetimePurchase": r.get("lifetime_purchased_fmt") or fmt_money_short(r.get("lifetime_purchased")),
            "lifetimeHold": r.get("lifetime_hold_pct") or "n/a",
            "lifetimePurchasedNum": float(r.get("lifetime_purchased") or 0),
            "favouriteGame7d": r.get("favourite_game_7d") or "—",
            "urgency": r.get("urgency") or "n/a",
            "reason": r.get("reason") or "n/a",
            "reasonTable": reason_raw,
            "reasonParts": split_reason_parts(reason_raw),
            "recommendation": r.get("recommendation") or r.get("action") or "n/a",
            "ticketEnabled": bool(r.get("ticketEnabled")),
            "ticketSubject": r.get("ticketSubject") or "",
            "ticketBody": r.get("ticketBody") or "",
            "zendeskUrl": r.get("zendeskUrl") or "",
            "tone": tone,
        }
        rows.append(row)
    return rows


def render_canvas_tsx(report: dict, top10: list[dict], agents: list[str]) -> str:
    from wow_drop_reason import format_urgency_legend_one_line

    report_json = json.dumps(report, indent=2)
    top10_json = json.dumps(top10, indent=2)
    agents_json = json.dumps(sorted(agents), indent=2)
    urgency_legend = format_urgency_legend_one_line()
    fn_suffix = report["date"].replace("-", "")
    segments = report["segments"]
    day = report["weekday"]
    day_short = day[:3]
    titles = {
        "thisPurchase": f"This {day} Purchase",
        "priorPurchase": f"Prior {day} Purchase",
        "purchase7d": "7D Purchase",
        "lifetimePurchase": "LT Purchase",
        "lifetimeHold": "Lifetime Hold",
        "favouriteGame7d": "Favourite Game (7D)",
    }
    titles_json = json.dumps(titles)

    return f"""import {{
  H1,
  H2,
  Pill,
  Row,
  Select,
  Spacer,
  Stack,
  Table,
  Text,
  TextInput,
  useCanvasState,
  useHostTheme,
}} from "cursor/canvas";

const REPORT = {report_json};
const TITLES = {titles_json};

type SegmentRow = {{
  label: string;
  revThis: string;
  revPrior: string;
  revWow: string;
  plyThis: string;
  plyPrior: string;
  plyWow: string;
  share: string;
  tone: "success" | "danger" | "warning" | "info" | "neutral";
}};

type PlayerRow = {{
  aid: string;
  name: string;
  agent: string;
  agentName: string;
  thisDay: string;
  priorDay: string;
  priorPriorNum: number;
  sortGap: number;
  purchase7d: string;
  lifetimePurchase: string;
  lifetimeHold: string;
  lifetimePurchasedNum: number;
  favouriteGame7d: string;
  urgency: string;
  reason: string;
  reasonTable: string;
  reasonParts?: string[];
  recommendation: string;
  ticketEnabled?: boolean;
  ticketSubject?: string;
  ticketBody?: string;
  zendeskUrl?: string;
  zeroDay?: boolean;
  tone?: "success" | "danger" | "warning" | "info" | "neutral";
}};

const SEGMENTS: SegmentRow[] = {json.dumps(segments, indent=2)};
const TOP10: PlayerRow[] = {top10_json};

const REASON_EMPHASIS = [
  "Redemption Blocked",
  "Redemption in progress",
  "Red flag",
  "Needs ",
  "Same weekday skip",
  "Spend Softening",
  "Offline Since",
  "Pending RD",
  "RD $",
  "Redeem Status ",
  "Take a break",
  "No Purchases",
  "Played Today",
  "Account locked",
];

function reasonPartEmoji(part: string): string {{
  const pl = part.toLowerCase();
  if (part.startsWith("Red flag")) return "🚩 ";
  if (part.startsWith("Redemption Blocked")) return "🚫 ";
  if (part.startsWith("Redemption in progress")) return "⏳ ";
  if (part.startsWith("Account locked") || part.includes("Suspended")) return "🔒 ";
  if (part.startsWith("Needs Recent Acceptable POA") || pl.includes("poa")) return "📄 ";
  if (part.startsWith("Needs KYC") || pl.includes("verification document")) return "📋 ";
  if (part.startsWith("RD $") || part.startsWith("Pending RD")) return "💸 ";
  if (part.startsWith("Same weekday skip")) return "📅 ";
  if (part.startsWith("Payment failed")) return "❌ ";
  if (part.startsWith("No Purchases")) return "⚠️ ";
  if (part.startsWith("Played Today")) return "🎰 ";
  if (part.startsWith("Redeem Status")) return "📋 ";
  if (part.startsWith("Take a break")) return "⏰ ";
  if (part.startsWith("Spend Softening")) return "📉 ";
  return "";
}}

function actionHeadEmoji(head: string): string {{
  const hl = head.toLowerCase();
  if (head.startsWith("Escalate Ops")) return "➡️ ";
  if (head.startsWith("Escalate Compliance")) return "⚖️ ";
  if (head.startsWith("Push purchase")) return "💰 ";
  if (head.startsWith("Fix payment method")) return "💳 ";
  if (head.startsWith("Remove restriction")) return "🔓 ";
  if (head.startsWith("Send to Ops")) return "🔧 ";
  if (head.startsWith("Soft check-in")) return "💬 ";
  if (head.startsWith("Agent call")) return "📞 ";
  if (head.startsWith("Reactivation")) return "📞 ";
  if (head.startsWith("No action")) return "✓ ";
  if (hl.includes("no outreach") || hl.includes("no purchase push")) return "🛑 ";
  return "";
}}

function reasonPartTone(part: string): "warning" | "danger" | "info" | undefined {{
  if (part.startsWith("Red flag")) return "danger";
  if (part.startsWith("Needs ") || part.includes("Blocked")) return "warning";
  if (part.startsWith("Escalate") || part.includes("Suspended")) return "danger";
  if (part.startsWith("Same weekday skip") || part.startsWith("Played Today")) return "info";
  return undefined;
}}

function ReasonCell({{ text, parts }}: {{ text: string; parts?: string[] }}) {{
  const segments = (parts && parts.length > 0 ? parts : text.split("●").map((p) => p.trim()).filter(Boolean));
  return (
    <Text size="small" style={{{{ minWidth: 420, maxWidth: 620, whiteSpace: "normal", display: "block", lineHeight: 1.6 }}}}>
      {{segments.map((part, i) => {{
        const emphasize = i === 0 || REASON_EMPHASIS.some((pfx) => part.startsWith(pfx));
        const emoji = reasonPartEmoji(part) || "";
        const label = emphasize ? `${{emoji}}${{part}}` : part;
        return (
        <Text as="span" key={{`${{part}}-${{i}}`}}>
          {{i > 0 && (
            <Text as="span" weight="bold" tone="tertiary" style={{{{ padding: "0 8px", fontSize: 15 }}}}>●</Text>
          )}}
          <Text
            as="span"
            weight={{emphasize ? "semibold" : "normal"}}
            tone={{reasonPartTone(part)}}
          >
            {{label}}
          </Text>
        </Text>
      );}})}}
    </Text>
  );
}}

function ActionCell({{ text }}: {{ text: string }}) {{
  const chunks = text.split(" · ").filter(Boolean);
  const head = chunks[0] ?? text;
  const tail = chunks.slice(1).join(" · ");
  return (
    <Text size="small" style={{{{ minWidth: 280, maxWidth: 420, whiteSpace: "normal", display: "block", lineHeight: 1.5 }}}}>
      <Text as="span" weight="semibold">{{actionHeadEmoji(head)}}{{head}}</Text>
      {{tail ? <> · {{tail}}</> : null}}
    </Text>
  );
}}

function MoneyCell({{ value, emphasize }}: {{ value: string; emphasize?: boolean }}) {{
  return (
    <Text as="span" weight={{emphasize ? "semibold" : "normal"}} tone={{emphasize ? "danger" : undefined}}>
      {{value}}
    </Text>
  );
}}

function Purchase7dCell({{ value }}: {{ value: string }}) {{
  const none = value === "None In 7D";
  return (
    <Text size="small" weight={{none ? "semibold" : "normal"}} tone={{none ? "warning" : undefined}} style={{{{ minWidth: 160, maxWidth: 220, whiteSpace: "normal", display: "block", lineHeight: 1.45 }}}}>
      {{value}}
    </Text>
  );
}}

function HoldCell({{ value }}: {{ value: string }}) {{
  const pct = parseFloat(value);
  const high = !Number.isNaN(pct) && pct >= 70;
  return (
    <Text as="span" weight={{high ? "semibold" : "normal"}} tone={{high ? "success" : undefined}}>
      {{value}}
    </Text>
  );
}}

function TicketDraftCell({{ player, onDraft }}: {{ player: PlayerRow; onDraft: (p: PlayerRow) => void }}) {{
  if (!player.ticketEnabled) return <Text tone="quaternary">—</Text>;
  const preview = (player.ticketSubject || "").length > 28
    ? `${{player.ticketSubject!.slice(0, 27)}}…`
    : (player.ticketSubject || "Draft");
  return (
    <Stack gap={{2}}>
      <Text
        as="span"
        size="small"
        style={{{{ color: "var(--marker-info, #3685BF)", cursor: "pointer", textDecoration: "underline" }}}}
        onClick={{() => onDraft(player)}}
      >
        Draft
      </Text>
      <Text tone="quaternary" size="small" style={{{{ maxWidth: 140, lineHeight: 1.35 }}}}>
        {{preview}}
      </Text>
    </Stack>
  );
}}

function TicketDraftModal({{
  player,
  subject,
  body,
  onSubject,
  onBody,
  onClose,
}}: {{
  player: PlayerRow | null;
  subject: string;
  body: string;
  onSubject: (v: string) => void;
  onBody: (v: string) => void;
  onClose: () => void;
}}) {{
  if (!player) return null;
  const copyText = async (text: string) => {{
    try {{ await navigator.clipboard.writeText(text); }} catch {{ /* ignore */ }}
  }};
  return (
    <div
      style={{{{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.45)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
        padding: 20,
      }}}}
      onClick={{onClose}}
    >
      <div
        style={{{{
          background: "var(--bg-editor, #FCFCFC)",
          borderRadius: 12,
          padding: 20,
          maxWidth: 680,
          width: "100%",
          maxHeight: "90vh",
          overflow: "auto",
          boxShadow: "0 8px 32px rgba(0,0,0,0.2)",
        }}}}
        onClick={{(e) => e.stopPropagation()}}
      >
        <Text weight="semibold">Zendesk ticket draft · {{player.name}} (AID {{player.aid}})</Text>
        <Text tone="quaternary" size="small" style={{{{ marginTop: 4, marginBottom: 12 }}}}>
          Review only. Edit, copy, then open Zendesk and send manually. Never auto-sent.
        </Text>
        <Text size="small" weight="medium">Subject</Text>
        <input
          value={{subject}}
          onChange={{(e) => onSubject(e.target.value)}}
          style={{{{
            width: "100%",
            marginTop: 4,
            marginBottom: 12,
            padding: "8px 10px",
            fontSize: 13,
            borderRadius: 6,
            border: "1px solid var(--stroke-secondary, #1414141F)",
          }}}}
        />
        <Text size="small" weight="medium">Message</Text>
        <textarea
          value={{body}}
          onChange={{(e) => onBody(e.target.value)}}
          rows={{10}}
          style={{{{
            width: "100%",
            marginTop: 4,
            marginBottom: 12,
            padding: "8px 10px",
            fontSize: 13,
            borderRadius: 6,
            border: "1px solid var(--stroke-secondary, #1414141F)",
            fontFamily: "inherit",
            resize: "vertical",
          }}}}
        />
        <Row gap={{8}} wrap>
          <Pill size="sm" onClick={{() => copyText(subject)}}>Copy subject</Pill>
          <Pill size="sm" onClick={{() => copyText(body)}}>Copy message</Pill>
          <Pill size="sm" onClick={{() => copyText(`Subject: ${{subject}}\\n\\n${{body}}`)}}>Copy subject + message</Pill>
          <Pill size="sm" onClick={{() => player.zendeskUrl && window.open(player.zendeskUrl, "_blank", "noopener,noreferrer")}}>
            Open Zendesk
          </Pill>
          <Spacer />
          <Pill size="sm" onClick={{onClose}}>Close</Pill>
        </Row>
      </div>
    </div>
  );
}}

function fmtTotalMoney(n: number): string {{
  return `$${{Math.round(n).toLocaleString()}}`;
}}

function WowCell({{ value }}: {{ value: string }}) {{
  const v = (value || "").trim();
  const up = v.startsWith("+") && !v.startsWith("+$0 (");
  const down = v.startsWith("-") || v.startsWith("$-");
  return (
    <Text as="span" weight={{up || down ? "semibold" : "normal"}} tone={{up ? "success" : down ? "danger" : undefined}}>
      {{value}}
    </Text>
  );
}}

type SortMode = "urgency" | "priorHigh" | "lifetimeHigh" | "gapHigh";

const AGENTS: string[] = {agents_json};
const REASONS = Array.from(new Set(TOP10.map((p) => p.reason))).sort();
const URGENCY_RANK: Record<string, number> = {{ Today: 0, "48h": 1, Watch: 2, None: 3 }};

function sortPlayers(rows: PlayerRow[], mode: SortMode): PlayerRow[] {{
  const copy = [...rows];
  if (mode === "priorHigh") {{
    return copy.sort((a, b) => b.priorPriorNum - a.priorPriorNum);
  }}
  if (mode === "lifetimeHigh") {{
    return copy.sort((a, b) => b.lifetimePurchasedNum - a.lifetimePurchasedNum);
  }}
  if (mode === "gapHigh") {{
    return copy.sort((a, b) => b.sortGap - a.sortGap);
  }}
  return copy.sort((a, b) => {{
    const ra = URGENCY_RANK[a.urgency] ?? 9;
    const rb = URGENCY_RANK[b.urgency] ?? 9;
    if (ra !== rb) return ra - rb;
    return b.sortGap - a.sortGap;
  }});
}}

function matchesSearch(row: PlayerRow, query: string): boolean {{
  if (!query.trim()) return true;
  const q = query.trim().toLowerCase();
  return (
    row.name.toLowerCase().includes(q) ||
    row.aid.includes(q) ||
    row.agent.toLowerCase().includes(q) ||
    row.agentName.toLowerCase().includes(q) ||
    row.reason.toLowerCase().includes(q) ||
    row.reasonTable.toLowerCase().includes(q) ||
    row.purchase7d.toLowerCase().includes(q) ||
    row.favouriteGame7d.toLowerCase().includes(q) ||
    row.recommendation.toLowerCase().includes(q)
  );
}}

export default function EliteDailySummary{fn_suffix}() {{
  const theme = useHostTheme();
  const [search, setSearch] = useCanvasState("search", "");
  const [agent, setAgent] = useCanvasState("agent", "all");
  const [reason, setReason] = useCanvasState("reason", "all");
  const [sortBy, setSortBy] = useCanvasState("sortBy", "urgency");
  const [ticketPlayer, setTicketPlayer] = useCanvasState<PlayerRow | null>("ticketPlayer", null);
  const [ticketSubject, setTicketSubject] = useCanvasState("ticketSubject", "");
  const [ticketBody, setTicketBody] = useCanvasState("ticketBody", "");

  const openTicketDraft = (player: PlayerRow) => {{
    setTicketPlayer(player);
    setTicketSubject(player.ticketSubject || "");
    setTicketBody(player.ticketBody || "");
  }};
  const closeTicketDraft = () => setTicketPlayer(null);

  const filtered = sortPlayers(TOP10.filter((row) => {{
    if (agent !== "all" && row.agent !== agent) return false;
    if (reason !== "all" && row.reason !== reason) return false;
    return matchesSearch(row, search);
  }}), sortBy as SortMode);

  const priorTotal = filtered.reduce((sum, p) => sum + p.priorPriorNum, 0);
  const filterActive = search.trim() !== "" || agent !== "all" || reason !== "all" || sortBy !== "urgency";

  return (
    <Stack gap={{16}} style={{{{ padding: 20, maxWidth: "100%", width: "100%", background: theme.bg.editor }}}}>
      <TicketDraftModal
        player={{ticketPlayer}}
        subject={{ticketSubject}}
        body={{ticketBody}}
        onSubject={{setTicketSubject}}
        onBody={{setTicketBody}}
        onClose={{closeTicketDraft}}
      />
      <Stack gap={{4}}>
        <H1>Elite Daily Decline Dashboard</H1>
        <Text tone="tertiary" size="small">
          {{REPORT.weekday}} {{REPORT.date}} vs prior {{REPORT.weekday}} {{REPORT.priorDate}}
        </Text>
      </Stack>

      <Stack gap={{8}}>
        <H2>{{REPORT.weekday}} vs last {{REPORT.weekday}} · Elite &amp; Jackpota</H2>
        <Table
          headers={{[
            "Segment",
            "This {day_short} Purchase",
            "Prior {day_short} Purchase",
            "Purchase WoW",
            "This {day_short} Purchased Players",
            "Prior {day_short} Purchased Players",
            "Purchased Players WoW",
            "Share",
          ]}}
          rows={{SEGMENTS.map((s) => [
            s.label,
            s.revThis,
            s.revPrior,
            <WowCell value={{s.revWow}} />,
            s.plyThis,
            s.plyPrior,
            <WowCell value={{s.plyWow}} />,
            s.share,
          ])}}
          columnAlign={{["left", "right", "right", "right", "right", "right", "right", "left"]}}
          rowTone={{SEGMENTS.map((s) => s.tone)}}
          striped
          stickyHeader
        />
        <Text tone="tertiary" size="small">
          {{REPORT.headline}}
        </Text>
      </Stack>

      <Stack gap={{8}}>
        <Row gap={{8}} align="center" wrap>
          <H2>Top 20 · WoW Purchase Gaps</H2>
          <Spacer />
          <Text tone="tertiary" size="small">
            {{filterActive ? `Showing ${{filtered.length}} of ${{TOP10.length}}` : `${{TOP10.length}} players`}}
          </Text>
        </Row>

        <Row gap={{8}} align="center" wrap>
          <TextInput
            value={{search}}
            onChange={{setSearch}}
            placeholder="Search name, AID, agent, reason…"
            type="search"
            style={{{{ flex: "1 1 220px", minWidth: 200 }}}}
          />
          <Select
            value={{agent}}
            onChange={{setAgent}}
            options={{[
              {{ value: "all", label: "All agents" }},
              ...AGENTS.map((a) => ({{ value: a, label: a }})),
            ]}}
            style={{{{ flex: "0 0 140px" }}}}
          />
          <Select
            value={{sortBy}}
            onChange={{setSortBy}}
            options={{[
              {{ value: "urgency", label: "Sort: Urgency + gap" }},
              {{ value: "priorHigh", label: "Prior purchase ↓" }},
              {{ value: "lifetimeHigh", label: "Lifetime purchase ↓" }},
              {{ value: "gapHigh", label: "WoW gap ↓" }},
            ]}}
            style={{{{ flex: "0 0 180px" }}}}
          />
        </Row>

        <Row gap={{6}} wrap>
          <Pill active={{reason === "all"}} onClick={{() => setReason("all")}} size="sm">
            All reasons
          </Pill>
          {{REASONS.map((r) => (
            <Pill key={{r}} active={{reason === r}} onClick={{() => setReason(r)}} size="sm">
              {{r}}
            </Pill>
          ))}}
        </Row>

        <Table
          headers={{["#", "Agent Name", "AID", "Name", TITLES.lifetimePurchase, TITLES.lifetimeHold, TITLES.thisPurchase, TITLES.priorPurchase, TITLES.purchase7d, TITLES.favouriteGame7d, "Urgency", "Reason", "Recommendation", "Ticket"]}}
          rows={{[
            ...filtered.map((p, i) => [
            String(i + 1),
            p.agentName,
            <a href={{p.aidUrl}} target="_blank" rel="noopener noreferrer">{{p.aid}}</a>,
            p.name,
            <MoneyCell value={{p.lifetimePurchase}} emphasize={{p.lifetimePurchasedNum >= 50000}} />,
            <HoldCell value={{p.lifetimeHold}} />,
            <MoneyCell value={{p.thisDay}} emphasize={{p.zeroDay}} />,
            <MoneyCell value={{p.priorDay}} emphasize={{p.sortGap >= 2000}} />,
            <Purchase7dCell value={{p.purchase7d}} />,
            p.favouriteGame7d,
            <Text weight={{p.urgency === "Today" ? "semibold" : "normal"}} tone={{p.urgency === "Today" ? "danger" : undefined}}>{{p.urgency === "Today" ? "⚡ Today" : p.urgency}}</Text>,
            <ReasonCell text={{p.reasonTable}} parts={{p.reasonParts}} />,
            <ActionCell text={{p.recommendation}} />,
            <TicketDraftCell player={{p}} onDraft={{openTicketDraft}} />,
          ]),
            ...(filtered.length ? [[
              "",
              "",
              "",
              <Text weight="semibold">Total</Text>,
              "",
              "",
              "",
              <Text weight="semibold">{{fmtTotalMoney(priorTotal)}}</Text>,
              "",
              "",
              "",
              "",
              "",
              "",
            ]] : []),
          ]}}
          columnAlign={{["center", "left", "left", "left", "right", "right", "right", "right", "left", "left", "center", "left", "left", "center"]}}
          rowTone={{[...filtered.map((p) => p.tone), ...(filtered.length ? ["neutral"] : [])]}}
          striped
          stickyHeader
          style={{{{ minWidth: 2950, width: "max-content" }}}}
          emptyMessage="No players match the current filters."
        />
      </Stack>
    </Stack>
  );
}}
"""


def write_daily_canvas(
    report_date: date,
    day_rows: list[dict],
    overall_rows: list[dict],
    top10: list[dict],
    canvas_dir: Path | None = None,
) -> Path:
    out_dir = canvas_dir or DEFAULT_CANVAS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    report = build_report(report_date, day_rows, overall_rows)
    players = build_top10_rows(top10)
    agents = sorted({p["agent"] for p in players if p.get("agent")})

    content = render_canvas_tsx(report, players, agents)
    out_path = out_dir / f"elite-daily-summary-{report_date.isoformat()}.canvas.tsx"
    out_path.write_text(content, encoding="utf-8")
    return out_path


def build_stakeholder_payload(
    report_date: date, day_rows: list[dict], overall_rows: list[dict]
) -> dict:
    prior_day = report_date - timedelta(days=7)
    day_name = weekday_label(report_date)
    elite_this = _day_row(day_rows, report_date)
    elite_prior = _day_row(day_rows, prior_day)
    overall_this = _day_row(overall_rows, report_date)
    overall_prior = _day_row(overall_rows, prior_day)

    elite_rev_this = float(elite_this.get("revenue") or 0)
    elite_rev_prior = float(elite_prior.get("revenue") or 0)
    overall_rev_this = float(overall_this.get("revenue") or 0)
    overall_rev_prior = float(overall_prior.get("revenue") or 0)
    elite_ply_this = int(elite_this.get("players") or 0)
    elite_ply_prior = int(elite_prior.get("players") or 0)
    overall_ply_this = int(overall_this.get("players") or 0)
    overall_ply_prior = int(overall_prior.get("players") or 0)

    overall_rev_pct = (
        (overall_rev_this - overall_rev_prior) / overall_rev_prior * 100
        if overall_rev_prior
        else 0
    )
    elite_rev_pct = (
        (elite_rev_this - elite_rev_prior) / elite_rev_prior * 100 if elite_rev_prior else 0
    )
    overall_ply_pct = (
        (overall_ply_this - overall_ply_prior) / overall_ply_prior * 100
        if overall_ply_prior
        else 0
    )
    elite_ply_pct = (
        (elite_ply_this - elite_ply_prior) / elite_ply_prior * 100 if elite_ply_prior else 0
    )
    elite_share = (elite_rev_this / overall_rev_this * 100) if overall_rev_this else 0

    if overall_rev_pct < 0 and elite_rev_pct >= 0:
        takeaway = (
            f"Platform revenue fell {abs(overall_rev_pct):.1f}% compared to last {day_name}, "
            f"while Elite revenue was {'flat' if abs(elite_rev_pct) < 1 else f'up {elite_rev_pct:.1f}%'}. "
            f"Elite represents {elite_share:.1f}% of platform revenue."
        )
        callout_tone = "warning"
    elif overall_rev_pct >= 0 and elite_rev_pct >= 0:
        takeaway = (
            f"Both platform and Elite revenue grew vs last {day_name} "
            f"({overall_rev_pct:+.1f}% platform, {elite_rev_pct:+.1f}% Elite). "
            f"Elite represents {elite_share:.1f}% of platform revenue."
        )
        callout_tone = "success"
    else:
        takeaway = (
            f"Platform revenue changed {overall_rev_pct:+.1f}% and Elite revenue changed "
            f"{elite_rev_pct:+.1f}% vs last {day_name}. "
            f"Elite represents {elite_share:.1f}% of platform revenue."
        )
        callout_tone = "neutral"

    return {
        "dateLine": (
            f"{day_name} {report_date.strftime('%d %b %Y')} "
            f"compared to {day_name} {prior_day.strftime('%d %b %Y')}"
        ),
        "takeaway": takeaway,
        "calloutTone": callout_tone,
        "platformRev": fmt_money_short(overall_rev_this),
        "platformRevPrior": fmt_money_short(overall_rev_prior),
        "platformRevWow": f"{overall_rev_pct:+.1f}%",
        "platformRevWowTone": _wow_tone(overall_rev_this - overall_rev_prior),
        "eliteRev": fmt_money_short(elite_rev_this),
        "eliteRevPrior": fmt_money_short(elite_rev_prior),
        "eliteRevWow": f"{elite_rev_pct:+.1f}%",
        "eliteRevWowTone": _wow_tone(elite_rev_this - elite_rev_prior),
        "platformPly": f"{overall_ply_this:,}",
        "platformPlyPrior": f"{overall_ply_prior:,}",
        "platformPlyWow": f"{overall_ply_pct:+.1f}%",
        "elitePly": f"{elite_ply_this:,}",
        "elitePlyPrior": f"{elite_ply_prior:,}",
        "elitePlyWow": f"{elite_ply_pct:+.1f}%",
        "eliteShare": f"{elite_share:.1f}%",
        "weekday": day_name,
    }


def render_stakeholder_canvas_tsx(payload: dict, report_date: date) -> str:
    data_json = json.dumps(payload, indent=2)
    fn_suffix = report_date.isoformat().replace("-", "")

    return f"""import {{
  Callout,
  Grid,
  H1,
  H2,
  Stack,
  Stat,
  Table,
  Text,
  useHostTheme,
}} from "cursor/canvas";

const DATA = {data_json};

export default function EliteStakeholderSummary{fn_suffix}() {{
  const theme = useHostTheme();

  return (
    <Stack gap={{20}} style={{{{ padding: 24, maxWidth: 880, background: theme.bg.editor }}}}>
      <Stack gap={{4}}>
        <H1>Elite Daily Snapshot</H1>
        <Text tone="tertiary" size="small">{{DATA.dateLine}}</Text>
        <Text tone="quaternary" size="small">
          Source: BigQuery · same weekday comparison
        </Text>
      </Stack>

      <Callout tone={{DATA.calloutTone}} title="At a glance">
        {{DATA.takeaway}}
      </Callout>

      <Stack gap={{8}}>
        <H2>Revenue</H2>
        <Grid columns={{2}} gap={{12}}>
          <Stat label={{`Platform revenue, this ${{DATA.weekday}}`}} value={{DATA.platformRev}} tone="neutral" />
          <Stat
            label={{`vs last ${{DATA.weekday}} (${{DATA.platformRevPrior}})`}}
            value={{DATA.platformRevWow}}
            tone={{DATA.platformRevWowTone}}
          />
          <Stat label={{`Elite revenue, this ${{DATA.weekday}}`}} value={{DATA.eliteRev}} tone="info" />
          <Stat
            label={{`vs last ${{DATA.weekday}} (${{DATA.eliteRevPrior}})`}}
            value={{DATA.eliteRevWow}}
            tone={{DATA.eliteRevWowTone}}
          />
        </Grid>
      </Stack>

      <Stack gap={{8}}>
        <H2>Purchased players</H2>
        <Grid columns={{2}} gap={{12}}>
          <Stat label={{`Platform purchasers, this ${{DATA.weekday}}`}} value={{DATA.platformPly}} tone="neutral" />
          <Stat
            label={{`vs last ${{DATA.weekday}} (${{DATA.platformPlyPrior}})`}}
            value={{DATA.platformPlyWow}}
            tone={{DATA.platformRevWowTone}}
          />
          <Stat label={{`Elite purchasers, this ${{DATA.weekday}}`}} value={{DATA.elitePly}} tone="info" />
          <Stat
            label={{`vs last ${{DATA.weekday}} (${{DATA.elitePlyPrior}})`}}
            value={{DATA.elitePlyWow}}
            tone={{DATA.eliteRevWowTone}}
          />
        </Grid>
      </Stack>

      <Stack gap={{8}}>
        <H2>Side-by-side</H2>
        <Table
          headers={{["Segment", "Revenue", "Last week", "Change", "Purchasers", "Last week", "Change"]}}
          rows={{[
            [
              "Platform",
              DATA.platformRev,
              DATA.platformRevPrior,
              DATA.platformRevWow,
              DATA.platformPly,
              DATA.platformPlyPrior,
              DATA.platformPlyWow,
            ],
            [
              "Elite",
              DATA.eliteRev,
              DATA.eliteRevPrior,
              DATA.eliteRevWow,
              DATA.elitePly,
              DATA.elitePlyPrior,
              DATA.elitePlyWow,
            ],
          ]}}
          columnAlign={{["left", "right", "right", "right", "right", "right", "right"]}}
          rowTone={{["neutral", "info"]}}
          striped
        />
        <Text tone="quaternary" size="small">
          Elite = managed book · Purchasers = distinct accounts that purchased that day · Elite share of platform revenue: {{DATA.eliteShare}}
        </Text>
      </Stack>
    </Stack>
  );
}}
"""


def write_stakeholder_canvas(
    report_date: date,
    day_rows: list[dict],
    overall_rows: list[dict],
    canvas_dir: Path | None = None,
) -> Path:
    out_dir = canvas_dir or DEFAULT_CANVAS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    payload = build_stakeholder_payload(report_date, day_rows, overall_rows)
    content = render_stakeholder_canvas_tsx(payload, report_date)
    out_path = out_dir / f"elite-stakeholder-summary-{report_date.isoformat()}.canvas.tsx"
    out_path.write_text(content, encoding="utf-8")
    return out_path


def build_day_summary(report_date: date, day_rows: list[dict], overall_rows: list[dict]) -> dict:
    report = build_report(report_date, day_rows, overall_rows)
    jp = report["segments"][0]
    el = report["segments"][1]
    return {
        "weekday": report["weekday"],
        "date": report["date"],
        "priorDate": report["priorDate"],
        "headline": report["headline"],
        "jackpotaRevThis": jp["revThis"],
        "jackpotaRevPrior": jp["revPrior"],
        "jackpotaRevWow": jp["revWow"],
        "jackpotaPlyWow": jp["plyWow"],
        "eliteRevThis": el["revThis"],
        "eliteRevPrior": el["revPrior"],
        "eliteRevWow": el["revWow"],
        "elitePlyWow": el["plyWow"],
        "eliteShare": el["share"],
        "jackpotaTone": jp["tone"],
        "eliteTone": el["tone"],
    }


def build_weekend_report(
    dates: list[date],
    day_summaries: list[dict],
    *,
    player_count: int | None = None,
) -> dict:
    start, end = dates[0], dates[-1]
    n_days = len(dates)
    count = player_count if player_count is not None else n_days * 20
    return {
        "mode": "weekend",
        "dateStart": start.isoformat(),
        "dateEnd": end.isoformat(),
        "title": "Elite Daily Decline Dashboard",
        "subtitle": (
            f"{weekday_label(start)} {start.strftime('%d %b')} – "
            f"{weekday_label(end)} {end.strftime('%d %b %Y')}"
        ),
        "playerCount": count,
        "daysPerReport": 20,
        "dayCount": n_days,
        "daySummaries": day_summaries,
    }


def build_weekend_players(bundles: list[tuple[date, list[dict]]]) -> list[dict]:
    players: list[dict] = []
    for report_date, top20 in bundles:
        day_name = weekday_label(report_date)
        for rank, row in enumerate(build_top10_rows(top20), 1):
            row["reportDay"] = day_name
            row["reportDate"] = report_date.isoformat()
            row["dayRank"] = rank
            row["dayKey"] = report_date.isoformat()
            players.append(row)
    return players
