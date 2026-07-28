"""Elite AM Brief canvas TSX — design parity with Elite Daily Decline."""

from __future__ import annotations

import json


def render_am_brief_canvas(payload: dict) -> str:
    report = payload["report"]
    fn = report["date"].replace("-", "")
    day = report["weekday"]
    titles = {
        "thisPurchase": f"This {day} Purchase",
        "priorPurchase": f"Prior {day} Purchase",
        "purchase7d": "7D Purchase",
        "lifetimePurchase": "LT Purchase",
        "lifetimeHold": "Lifetime Hold",
        "favouriteGame7d": "Favourite Game (7D)",
    }
    report_json = json.dumps(payload["report"], indent=2)
    overview_json = json.dumps(payload["overview"], indent=2)
    agents_json = json.dumps(payload["agents"], indent=2)
    am_shares_json = json.dumps(payload.get("amShares") or [], indent=2)
    am_order_json = json.dumps(payload["amOrder"])
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
const OVERVIEW = {overview_json};
const AGENTS = {agents_json};
const AM_SHARES = {am_shares_json};
const AM_ORDER: string[] = {am_order_json};
const TITLES = {titles_json};

type Focus = {{
  openZd: number;
  locked: number;
  takeABreak: number;
  selfExclusion: number;
  otherLocked: number;
  rdOver5k: number;
  birthdays: number;
  declineCount: number;
}};

type AidRow = {{
  aid: string;
  aidUrl: string;
  name: string;
  agent?: string;
  agentName?: string;
  tone?: "success" | "danger" | "warning" | "info" | "neutral";
  [key: string]: unknown;
}};

type PlayerRow = {{
  aid: string;
  aidUrl: string;
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

type AgentBlock = {{
  agentName: string;
  greetingLines: string[];
  purchase: string;
  purchasedPlayers: number;
  totalPlayers?: number;
  purchasedOfBook?: string;
  bookPurchaseRate?: string;
  purchaseShare?: string;
  playerShare?: string;
  focus: Focus;
  top10: AidRow[];
  decline: PlayerRow[];
  rdOver5k: AidRow[];
  rdFirstTime: AidRow[];
  birthdays: AidRow[];
  zendesk: AidRow[];
  locks: AidRow[];
}};

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

function AidLink({{ row }}: {{ row: {{ aid: string; aidUrl?: string }} }}) {{
  if (row.aidUrl) {{
    return (
      <a href={{row.aidUrl}} target="_blank" rel="noopener noreferrer">
        {{row.aid}}
      </a>
    );
  }}
  return <span>{{row.aid}}</span>;
}}

type SortMode = "urgency" | "priorHigh" | "lifetimeHigh" | "gapHigh";
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

function matchesDeclineSearch(row: PlayerRow, query: string): boolean {{
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

function matchesAidSearch(row: AidRow, query: string, extraKeys: string[] = []): boolean {{
  if (!query.trim()) return true;
  const q = query.trim().toLowerCase();
  if ((row.name || "").toLowerCase().includes(q) || row.aid.includes(q)) return true;
  for (const k of extraKeys) {{
    const v = row[k];
    if (v != null && String(v).toLowerCase().includes(q)) return true;
  }}
  return false;
}}

function WowCell({{ value }}: {{ value: string }}) {{
  const v = (value || "").trim();
  const pctMatch = v.match(/\\(([+-]?\\d+(?:\\.\\d+)?)%\\)/);
  const pct = pctMatch ? Number(pctMatch[1]) : NaN;
  const up =
    (!Number.isNaN(pct) && pct > 0) ||
    (v.startsWith("+") && !v.startsWith("+$0") && !v.startsWith("+0"));
  const down =
    (!Number.isNaN(pct) && pct < 0) ||
    v.startsWith("-") ||
    v.startsWith("$-") ||
    /^-\\$?\\d/.test(v);
  const tone = up ? "success" : down ? "danger" : undefined;
  return (
    <Text
      as="span"
      weight={{up || down ? "semibold" : "normal"}}
      tone={{tone}}
      style={{{{
        color: up
          ? "var(--marker-success, #1F8A65)"
          : down
            ? "var(--marker-danger, #C75050)"
            : undefined,
      }}}}
    >
      {{value}}
    </Text>
  );
}}

function RichText({{ text, weight }}: {{ text: string; weight?: "semibold" | "normal" }}) {{
  const parts = String(text || "").split(/(\\*\\*[^*]+\\*\\*)/g);
  return (
    <Text weight={{weight || "normal"}} style={{{{ lineHeight: 1.55 }}}}>
      {{parts.map((part, i) => {{
        if (part.startsWith("**") && part.endsWith("**") && part.length >= 4) {{
          return (
            <Text as="span" key={{i}} weight="semibold" tone="success">
              {{part.slice(2, -2)}}
            </Text>
          );
        }}
        return <Text as="span" key={{i}}>{{part}}</Text>;
      }})}}
    </Text>
  );
}}

function scrollToSection(id: string) {{
  if (!id || typeof document === "undefined") return;
  const el = document.getElementById(id);
  if (!el) return;
  el.scrollIntoView({{ behavior: "smooth", block: "start", inline: "nearest" }});
}}

function WeekdaySegmentTable({{
  title,
  segments,
  dayShort,
  headline,
}}: {{
  title: string;
  segments: any[];
  dayShort: string;
  headline?: string;
}}) {{
  return (
    <Stack gap={{8}}>
      <H2>{{title}}</H2>
      <Table
        headers={{[
          "Segment",
          `This ${{dayShort}} Purchase`,
          `Prior ${{dayShort}} Purchase`,
          "Purchase WoW",
          `This ${{dayShort}} Purchased Players`,
          `Prior ${{dayShort}} Purchased Players`,
          "Purchased Players WoW",
          "Share",
        ]}}
        rows={{segments.map((s: any) => [
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
        rowTone={{segments.map((s: any) => s.tone)}}
        striped
        stickyHeader
      />
      {{headline ? <Text tone="tertiary" size="small">{{headline}}</Text> : null}}
    </Stack>
  );
}}

function TicketIdsCell({{ tickets, fallback }}: {{
  tickets?: {{ id: string; url: string }}[];
  fallback?: string;
}}) {{
  const list = tickets && tickets.length ? tickets : [];
  if (!list.length) {{
    return <Text tone="quaternary">{{fallback || "—"}}</Text>;
  }}
  return (
    <Text size="small" style={{{{ whiteSpace: "normal", display: "block", lineHeight: 1.45 }}}}>
      {{list.map((t, i) => (
        <Text as="span" key={{t.id}}>
          {{i > 0 ? ", " : ""}}
          <a href={{t.url}} target="_blank" rel="noopener noreferrer">{{t.id}}</a>
        </Text>
      ))}}
    </Text>
  );
}}

function MorningChecklist({{ focus, prefix }}: {{ focus: Focus; prefix: string }}) {{
  const rows: {{ label: string; value: number; tone: "success" | "warning" | "info" | "neutral"; sectionId: string }}[] = [
    {{ label: "Open Tickets", value: focus.openZd, tone: focus.openZd ? "info" : "success", sectionId: `${{prefix}}-zendesk` }},
    {{ label: "Take A Break (Past Day)", value: focus.takeABreak, tone: focus.takeABreak ? "warning" : "success", sectionId: `${{prefix}}-locks` }},
    {{ label: "Other Locked", value: focus.otherLocked, tone: focus.otherLocked ? "warning" : "success", sectionId: `${{prefix}}-locks` }},
    {{ label: "Self-Exclusion", value: focus.selfExclusion, tone: "neutral", sectionId: `${{prefix}}-locks` }},
    {{ label: "Pending Redemptions", value: focus.rdOver5k, tone: focus.rdOver5k ? "warning" : "success", sectionId: `${{prefix}}-pending-rd` }},
    {{ label: "Birthdays (3d)", value: focus.birthdays, tone: "success", sectionId: `${{prefix}}-birthdays` }},
    {{ label: "Top 20 Decline", value: focus.declineCount, tone: focus.declineCount ? "warning" : "success", sectionId: `${{prefix}}-top20` }},
  ];
  return (
    <Table
      headers={{["Metric", "Count"]}}
      rows={{rows.map((r) => [
        <a
          href={{`#${{r.sectionId}}`}}
          onClick={{(e) => {{
            e.preventDefault();
            scrollToSection(r.sectionId);
          }}}}
          style={{{{
            color: "var(--marker-info, #3685BF)",
            cursor: "pointer",
            textDecoration: "underline",
          }}}}
        >
          {{r.label}}
        </a>,
        <Text weight="semibold" tone={{r.tone}}>{{r.value}}</Text>,
      ])}}
      columnAlign={{["left", "right"]}}
      rowTone={{rows.map((r) => r.tone)}}
      striped
      stickyHeader
    />
  );
}}

function Top20DeclineTable({{
  players,
  stateKey,
  onDraft,
  showAgentSelect,
}}: {{
  players: PlayerRow[];
  stateKey: string;
  onDraft: (p: PlayerRow) => void;
  showAgentSelect: boolean;
}}) {{
  const [search, setSearch] = useCanvasState(`${{stateKey}}_search`, "");
  const [agent, setAgent] = useCanvasState(`${{stateKey}}_agent`, "all");
  const [reason, setReason] = useCanvasState(`${{stateKey}}_reason`, "all");
  const [sortBy, setSortBy] = useCanvasState(`${{stateKey}}_sortBy`, "urgency");

  const agentOptions = Array.from(new Set(players.map((p) => p.agent))).sort();
  const reasons = Array.from(new Set(players.map((p) => p.reason))).sort();

  const filtered = sortPlayers(players.filter((row) => {{
    if (showAgentSelect && agent !== "all" && row.agent !== agent) return false;
    if (reason !== "all" && row.reason !== reason) return false;
    return matchesDeclineSearch(row, search);
  }}), sortBy as SortMode);

  const priorTotal = filtered.reduce((sum, p) => sum + p.priorPriorNum, 0);
  const filterActive =
    search.trim() !== "" ||
    (showAgentSelect && agent !== "all") ||
    reason !== "all" ||
    sortBy !== "urgency";

  return (
    <Stack gap={{8}}>
      <Row gap={{8}} align="center" wrap>
        <H2>Top 20 · WoW Purchase Gaps</H2>
        <Spacer />
        <Text tone="tertiary" size="small">
          {{filterActive ? `Showing ${{filtered.length}} of ${{players.length}}` : `${{players.length}} players`}}
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
        {{showAgentSelect ? (
          <Select
            value={{agent}}
            onChange={{setAgent}}
            options={{[
              {{ value: "all", label: "All agents" }},
              ...agentOptions.map((a) => ({{ value: a, label: a }})),
            ]}}
            style={{{{ flex: "0 0 140px" }}}}
          />
        ) : null}}
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
        {{reasons.map((r) => (
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
            <TicketDraftCell player={{p}} onDraft={{onDraft}} />,
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
        rowTone={{[...filtered.map((p) => p.tone), ...(filtered.length ? ["neutral" as const] : [])]}}
        striped
        stickyHeader
        style={{{{ minWidth: 2950, width: "max-content" }}}}
        emptyMessage="No players match the current filters."
      />
    </Stack>
  );
}}

function SearchableTable({{
  title,
  rows,
  stateKey,
  sectionId,
  extraSearchKeys,
  headers,
  renderRow,
  columnAlign,
  keepWhenEmpty,
}}: {{
  title: string;
  rows: AidRow[];
  stateKey: string;
  sectionId?: string;
  extraSearchKeys?: string[];
  headers: string[];
  renderRow: (row: AidRow, i: number) => unknown[];
  columnAlign?: ("left" | "right" | "center")[];
  keepWhenEmpty?: boolean;
}}) {{
  const [search, setSearch] = useCanvasState(`${{stateKey}}_q`, "");
  const filtered = rows.filter((r) => matchesAidSearch(r, search, extraSearchKeys || []));
  const filterActive = search.trim() !== "";
  return (
    <div id={{sectionId || undefined}} style={{{{ scrollMarginTop: 24 }}}}>
    <Stack gap={{8}}>
      <Row gap={{8}} align="center" wrap>
        <H2>{{title}}</H2>
        <Spacer />
        <Text tone="tertiary" size="small">
          {{filterActive ? `Showing ${{filtered.length}} of ${{rows.length}}` : `${{rows.length}} players`}}
        </Text>
      </Row>
      <TextInput
        value={{search}}
        onChange={{setSearch}}
        placeholder="Search name, AID…"
        type="search"
        style={{{{ maxWidth: 360 }}}}
      />
      <Table
        headers={{headers}}
        rows={{filtered.map((r, i) => renderRow(r, i))}}
        columnAlign={{columnAlign}}
        rowTone={{filtered.map((r) => (r.tone as any) || "neutral")}}
        striped
        stickyHeader
        emptyMessage={{keepWhenEmpty ? undefined : "No players match the current filters."}}
      />
    </Stack>
    </div>
  );
}}

function AgentPanel({{
  block,
  onDraft,
  segments,
  dayShort,
  segmentTitle,
  headline,
}}: {{
  block: AgentBlock;
  onDraft: (p: PlayerRow) => void;
  segments: any[];
  dayShort: string;
  segmentTitle: string;
  headline?: string;
}}) {{
  const prefix = `am-${{block.agentName}}`;
  return (
    <Stack gap={{16}}>
      <Stack gap={{6}}>
        {{block.greetingLines.map((line, i) => (
          <RichText key={{i}} text={{line}} weight={{i === 0 ? "semibold" : "normal"}} />
        ))}}
      </Stack>

      <WeekdaySegmentTable
        title={{segmentTitle}}
        segments={{segments}}
        dayShort={{dayShort}}
        headline={{headline}}
      />

      <Stack gap={{8}}>
        <H2>Morning Checklist</H2>
        <MorningChecklist focus={{block.focus}} prefix={{prefix}} />
      </Stack>

      <SearchableTable
        title="Top 10 Purchasers"
        rows={{block.top10}}
        stateKey={{`t10_${{block.agentName}}`}}
        sectionId={{`${{prefix}}-top10`}}
        extraSearchKeys={{["offerCode", "offerTitle"]}}
        headers={{["#", "AID", "Name", "Purchased $", "Purchases (#)", "Top Offer"]}}
        columnAlign={{["center", "left", "left", "right", "right", "left"]}}
        renderRow={{(p) => [
          p.rank,
          <AidLink row={{p}} />,
          p.name,
          <Text tone="success">{{p.purchased as string}}</Text>,
          p.orderCount,
          p.offerCode,
        ]}}
      />

      <div id={{`${{prefix}}-top20`}} style={{{{ scrollMarginTop: 24 }}}}>
        <Top20DeclineTable
          players={{block.decline}}
          stateKey={{`dec_${{block.agentName}}`}}
          onDraft={{onDraft}}
          showAgentSelect={{false}}
        />
      </div>

      <SearchableTable
        title="Pending Redemptions"
        rows={{block.rdOver5k}}
        stateKey={{`rd5_${{block.agentName}}`}}
        sectionId={{`${{prefix}}-pending-rd`}}
        headers={{["AID", "Name", "RD ID", "Amount", "Status", "Created"]}}
        columnAlign={{["left", "left", "left", "right", "left", "left"]}}
        renderRow={{(p) => [
          <AidLink row={{p}} />,
          p.name,
          p.redeemId,
          <Text tone="warning">{{p.amount as string}}</Text>,
          p.status,
          p.created,
        ]}}
      />

      <SearchableTable
        title="First-Time Locked RD"
        rows={{block.rdFirstTime}}
        stateKey={{`rdf_${{block.agentName}}`}}
        sectionId={{`${{prefix}}-first-rd`}}
        keepWhenEmpty
        headers={{["AID", "Name", "RD ID", "Amount", "Status", "Created"]}}
        columnAlign={{["left", "left", "left", "right", "left", "left"]}}
        renderRow={{(p) => [
          <AidLink row={{p}} />,
          p.name,
          p.redeemId,
          <Text tone="warning">{{p.amount as string}}</Text>,
          p.status,
          p.created,
        ]}}
      />

      <SearchableTable
        title="Birthdays · Last 3 Days"
        rows={{block.birthdays}}
        stateKey={{`bd_${{block.agentName}}`}}
        sectionId={{`${{prefix}}-birthdays`}}
        headers={{["AID", "Name", "Email", "DOB", "Age"]}}
        columnAlign={{["left", "left", "left", "left", "right"]}}
        renderRow={{(p) => [
          <AidLink row={{p}} />,
          p.name,
          p.email,
          <Text tone="success">{{p.dob as string}}</Text>,
          p.age ?? "—",
        ]}}
      />

      <SearchableTable
        title="Open Tickets"
        rows={{block.zendesk}}
        stateKey={{`zd_${{block.agentName}}`}}
        sectionId={{`${{prefix}}-zendesk`}}
        extraSearchKeys={{["ticketIds"]}}
        headers={{["AID", "Name", "LTP", "Hold", "7D Purchase", "Open Tickets", "Ticket"]}}
        columnAlign={{["left", "left", "right", "right", "right", "right", "left"]}}
        renderRow={{(p) => [
          <AidLink row={{p}} />,
          p.name,
          <MoneyCell value={{(p.lifetimePurchase as string) || "$0"}} emphasize={{Number(p.lifetimePurchasedNum || 0) >= 50000}} />,
          <HoldCell value={{(p.lifetimeHold as string) || "n/a"}} />,
          <MoneyCell value={{(p.purchase7d as string) || "$0"}} />,
          p.openTickets,
          <TicketIdsCell tickets={{p.tickets as {{ id: string; url: string }}[] | undefined}} fallback={{(p.ticketIds as string) || "—"}} />,
        ]}}
      />

      <SearchableTable
        title="Locked And Take A Break"
        rows={{block.locks}}
        stateKey={{`lk_${{block.agentName}}`}}
        sectionId={{`${{prefix}}-locks`}}
        extraSearchKeys={{["lockReason", "unlockDetail"]}}
        headers={{["AID", "Name", "Lock Reason", "Days Remaining / Unlock"]}}
        columnAlign={{["left", "left", "left", "left"]}}
        renderRow={{(p) => [
          <AidLink row={{p}} />,
          p.name,
          <Text tone={{(p.tone as any) || "warning"}}>{{p.lockReason as string}}</Text>,
          (p.unlockDetail as string) || "—",
        ]}}
      />
    </Stack>
  );
}}

export default function EliteAmBrief{fn}() {{
  const theme = useHostTheme();
  const [tab, setTab] = useCanvasState("amTab", "Overview");
  const [ticketPlayer, setTicketPlayer] = useCanvasState<PlayerRow | null>("ticketPlayer", null);
  const [ticketSubject, setTicketSubject] = useCanvasState("ticketSubject", "");
  const [ticketBody, setTicketBody] = useCanvasState("ticketBody", "");

  const openDraft = (player: PlayerRow) => {{
    setTicketPlayer(player);
    setTicketSubject(player.ticketSubject || "");
    setTicketBody(player.ticketBody || "");
  }};

  const active = AGENTS.find((a) => a.agentName === tab) as AgentBlock | undefined;
  const segments = (REPORT as any).segments || [];
  const dayShort = (REPORT as any).dayShort || String(REPORT.weekday || "").slice(0, 3);

  return (
    <Stack gap={{16}} style={{{{ padding: 20, maxWidth: "100%", width: "100%", background: theme.bg.editor }}}}>
      <TicketDraftModal
        player={{ticketPlayer}}
        subject={{ticketSubject}}
        body={{ticketBody}}
        onSubject={{setTicketSubject}}
        onBody={{setTicketBody}}
        onClose={{() => setTicketPlayer(null)}}
      />
      <Stack gap={{4}}>
        <H1>{{REPORT.title}}</H1>
        <Text tone="tertiary" size="small">{{REPORT.subtitle}}</Text>
      </Stack>

      <Row gap={{8}} wrap>
        <Pill active={{tab === "Overview"}} onClick={{() => setTab("Overview")}} size="sm">
          Overview
        </Pill>
        {{AM_ORDER.map((name) => (
          <Pill key={{name}} active={{tab === name}} onClick={{() => setTab(name)}} size="sm">
            {{name}}
          </Pill>
        ))}}
      </Row>

      {{tab === "Overview" ? (
        <Stack gap={{16}}>
          <Stack gap={{2}}>
            {{REPORT.overviewGreetingLines.map((line: string, i: number) => (
              <Text key={{i}} weight={{i === 0 ? "semibold" : "normal"}}>{{line}}</Text>
            ))}}
          </Stack>

          <Row gap={{16}} align="start" wrap style={{{{ alignItems: "stretch" }}}}>
            <Stack gap={{8}} style={{{{ flex: "1 1 560px", minWidth: 480 }}}}>
              <WeekdaySegmentTable
                title={{(REPORT as any).segmentTitle || `${{REPORT.weekday}} vs last ${{REPORT.weekday}} · Elite & Jackpota`}}
                segments={{segments}}
                dayShort={{dayShort}}
                headline={{(REPORT as any).headline || ""}}
              />
            </Stack>

            <Stack gap={{8}} style={{{{ flex: "0 1 460px", minWidth: 320 }}}}>
              <H2>AM Share Of Elite</H2>
              <Table
                headers={{["AM", "Purchase $", "Share", "Purchased / Book"]}}
                rows={{AM_SHARES.map((r: any) => [
                  <Pill size="sm" onClick={{() => setTab(r.agentName)}}>{{r.agentName}}</Pill>,
                  <Text tone="success">{{r.purchase}}</Text>,
                  r.purchaseShare,
                  r.purchasedOfBook || `${{r.purchasedPlayers}}`,
                ])}}
                columnAlign={{["left", "right", "right", "right"]}}
                rowTone={{AM_SHARES.map(() => "success" as const)}}
                striped
                stickyHeader
              />
            </Stack>
          </Row>

          <Stack gap={{8}}>
            <H2>AM Overview</H2>
            <Table
              headers={{[
                "AM",
                "Purchase $",
                "Purchased / Book",
                "Open Tickets",
                "Take A Break",
                "Locked",
                "Pending RD",
                "Birthdays",
                "Top 20 Decline",
              ]}}
              rows={{OVERVIEW.map((r) => [
                <Pill size="sm" onClick={{() => setTab(r.agentName)}}>{{r.agentName}}</Pill>,
                <Text tone="success">{{r.purchase}}</Text>,
                (r as any).purchasedOfBook || r.purchasedPlayers,
                r.openZd,
                r.takeABreak,
                r.locked,
                r.rdOver5k,
                <Text tone="success">{{r.birthdays}}</Text>,
                r.declineCount,
              ])}}
              columnAlign={{["left", "right", "right", "right", "right", "right", "right", "right", "right"]}}
              rowTone={{OVERVIEW.map(() => "success" as const)}}
              striped
              stickyHeader
            />
          </Stack>
        </Stack>
      ) : active ? (
        <AgentPanel
          block={{active}}
          onDraft={{openDraft}}
          segments={{segments}}
          dayShort={{dayShort}}
          segmentTitle={{(REPORT as any).segmentTitle || `${{REPORT.weekday}} vs last ${{REPORT.weekday}} · Elite & Jackpota`}}
          headline={{(REPORT as any).headline || ""}}
        />
      ) : null}}
    </Stack>
  );
}}
"""
