"""TSX — shared types + generic cell renderers (Reason/Action/Money/Hold/Ticket cells, AidLink, WowCell, RichText, sort/search helpers). Extracted verbatim from am_brief_canvas.py (Batch 1 editability split)."""
from __future__ import annotations

CELLS_TSX = f"""type AidRow = {{
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
  goals?: {{
    available?: boolean;
    monthLabel?: string;
    asOf?: string;
    elapsedDays?: number;
    daysInMonth?: number;
    weightedTrackedDisplay?: string;
    score?: {{
      kpiPoints: number;
      kpiPointsMax: number;
      kpiPointsDisplay: string;
      managerScored: boolean;
      managerPoints?: number | null;
      managerPointsMax: number;
      managerPointsDisplay: string;
      managerNote?: string;
      totalPoints: number;
      totalPointsMax: number;
      totalDisplay: string;
      scoreSubline: string;
      scoreNote?: string;
    }};
    achievementCapNote?: string;
    upgradesNote?: string;
    definitionsNote?: string;
    kpis?: {{
      key: string;
      label: string;
      weightLabel: string;
      goalDisplay: string;
      actualDisplay: string;
      paceDisplay: string;
      gapDisplay: string;
      status: string;
      statusTone?: string;
      note?: string;
    }}[];
  }} | null;
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

function AgingCell({{
  created,
  daysPending,
  agingFlag,
}}: {{
  created: string;
  daysPending?: number | null;
  agingFlag?: boolean;
}}) {{
  const suffix = typeof daysPending === "number" ? ` (${{daysPending}}d ago)` : "";
  return (
    <Text
      as="span"
      size="small"
      weight={{agingFlag ? "semibold" : "normal"}}
      tone={{agingFlag ? "danger" : undefined}}
    >
      {{created}}{{suffix}}
    </Text>
  );
}}

function BigWinCell({{ won, bigWinner }}: {{ won: string; bigWinner?: boolean }}) {{
  if (!bigWinner) {{
    return <Text as="span" size="small" tone="tertiary">{{won}}</Text>;
  }}
  return (
    <Text as="span" size="small" weight="semibold" tone="danger">
      {{won}} · Big Winner
    </Text>
  );
}}

// Blank when nothing is flagged. The absence of a missing-document ticket is
// not proof the documents are complete, so the board says nothing rather than
// showing an all-clear an AM might repeat to a player awaiting a withdrawal.
function DocsCell({{ status }}: {{ status: string }}) {{
  if (!status) {{
    return <Text as="span" tone="quaternary">—</Text>;
  }}
  return (
    <Text as="span" size="small" weight="semibold" tone="warning">
      {{status}}
    </Text>
  );
}}

function TicketDraftCell({{ player, onDraft, disabledReason }}: {{ player: PlayerRow; onDraft: (p: PlayerRow) => void; disabledReason?: string }}) {{
  if (!player.ticketEnabled) {{
    const reason = disabledReason || (player as any).ticketDisabledReason;
    return reason ? (
      <Text tone="quaternary" size="small">{{reason}}</Text>
    ) : (
      <Text tone="quaternary">—</Text>
    );
  }}
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
  player: {{ aid: string; name: string }} | null;
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

/** Locked/Take A Break: soonest unlock first (today/overdue floats to the
 * top since remaining <= 0). Rows with no calculable unlock (self-exclusion,
 * other locked, or a break with no locked_at) sort last, always — unlike
 * sortByNumKey, null here means "no countdown", not zero. */
function sortBySoonestUnlock(rows: AidRow[]): AidRow[] {{
  const copy = [...rows];
  copy.sort((a, b) => {{
    const av = a.unlockRemainingDays as number | null | undefined;
    const bv = b.unlockRemainingDays as number | null | undefined;
    const aNone = av == null;
    const bNone = bv == null;
    if (aNone && bNone) return 0;
    if (aNone) return 1;
    if (bNone) return -1;
    return (av as number) - (bv as number);
  }});
  return copy;
}}

function UnlockCell({{ detail, remainingDays }}: {{ detail: string; remainingDays?: number | null }}) {{
  if (!detail) return <Text tone="quaternary">—</Text>;
  const urgent = typeof remainingDays === "number" && remainingDays <= 0;
  return (
    <Text as="span" weight={{urgent ? "semibold" : "normal"}} tone={{urgent ? "danger" : undefined}}>
      {{detail}}
    </Text>
  );
}}

/** Generic numeric-key sort for AidRow[] tables (SearchableTable's sortFn).
 * `desc` true = highest first (default). Missing/NaN values sort last. */
function sortByNumKey(rows: AidRow[], key: string, desc = true): AidRow[] {{
  const copy = [...rows];
  copy.sort((a, b) => {{
    const av = Number(a[key]);
    const bv = Number(b[key]);
    const aNan = Number.isNaN(av);
    const bNan = Number.isNaN(bv);
    if (aNan && bNan) return 0;
    if (aNan) return 1;
    if (bNan) return -1;
    return desc ? bv - av : av - bv;
  }});
  return copy;
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

"""
