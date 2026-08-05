"""Combined multi-day Elite decline canvas — same layout as daily (07/07 reference)."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from daily_summary.generate_daily_elite_canvas import (
    DEFAULT_CANVAS_DIR,
    build_day_summary,
    build_report,
    build_top10_rows,
    build_weekend_report,
    render_canvas_tsx,
)
from daily_summary.generate_daily_elite_summary import weekday_label
from wow_drop_analysis.wow_drop_reason import format_agent_name


def _block_titles(day_name: str) -> dict[str, str]:
    """Same camelCase keys as daily canvas TITLES (07/07 reference)."""
    return {
        "thisPurchase": f"This {day_name} Purchase",
        "priorPurchase": f"Prior {day_name} Purchase",
        "purchase7d": "7D Purchase",
        "lifetimePurchase": "LT Purchase",
        "lifetimeHold": "Lifetime Hold",
        "favouriteGame7d": "Favourite Game (7D)",
    }


def _extract_shared_tsx_helpers() -> str:
    """Components + sort/search helpers — exclude daily AGENTS/TOP10/REASONS."""
    dummy_report = {
        "date": "2099-01-01",
        "weekday": "Monday",
        "priorDate": "2098-12-25",
        "headline": "",
        "segments": [],
    }
    fake_player = {
        "aid": "0",
        "aidUrl": "",
        "name": "n",
        "agent": "a",
        "agentName": "A",
        "thisDay": "$0",
        "priorDay": "$0",
        "priorPriorNum": 0,
        "sortGap": 0,
        "zeroDay": True,
        "purchase7d": "None In 7D",
        "lifetimePurchase": "$0",
        "lifetimeHold": "0",
        "lifetimePurchasedNum": 0,
        "favouriteGame7d": "—",
        "urgency": "Watch",
        "reason": "same_weekday_skip",
        "reasonTable": "Same weekday skip",
        "reasonParts": ["Same weekday skip"],
        "recommendation": "No action",
        "ticketEnabled": False,
        "tone": "warning",
    }
    full = render_canvas_tsx(dummy_report, [fake_player], ["a"])
    start = full.index("const REASON_EMPHASIS = [")
    agents_idx = full.index("const AGENTS: string[] = ")
    urgency_idx = full.index("const URGENCY_RANK", agents_idx)
    end = full.index("export default function EliteDailySummary")
    return full[start:agents_idx] + full[urgency_idx:end]


def build_day_block(
    report_date: date,
    day_rows: list[dict],
    overall_rows: list[dict],
    top20: list[dict],
) -> dict:
    day_name = weekday_label(report_date)
    report = build_report(report_date, day_rows, overall_rows)
    return {
        "report": report,
        "segments": report["segments"],
        "titles": _block_titles(day_name),
        "players": build_top10_rows(top20),
        "dayShort": day_name[:3],
    }


def render_weekend_canvas_tsx(
    report: dict,
    day_blocks: list[dict],
    agent_options: list[dict[str, str]],
) -> str:
    report_json = json.dumps(report, indent=2)
    day_blocks_json = json.dumps(day_blocks, indent=2)
    agent_options_json = json.dumps(agent_options, indent=2)
    fn_suffix = report["dateEnd"].replace("-", "")
    helpers = _extract_shared_tsx_helpers()

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
const DAY_BLOCKS = {day_blocks_json};
const AGENT_OPTIONS: {{ value: string; label: string }}[] = {agent_options_json};

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

type Titles = {{
  thisPurchase: string;
  priorPurchase: string;
  purchase7d: string;
  lifetimePurchase: string;
  lifetimeHold: string;
  favouriteGame7d: string;
}};

type PlayerRow = {{
  aid: string;
  aidUrl?: string;
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

type DayBlock = {{
  report: {{
    date: string;
    weekday: string;
    priorDate: string;
    headline: string;
    segments: SegmentRow[];
  }};
  segments: SegmentRow[];
  titles: Titles;
  players: PlayerRow[];
  dayShort: string;
}};

{helpers}
const ALL_PLAYERS: PlayerRow[] = DAY_BLOCKS.flatMap((b) => b.players);
const REASONS = Array.from(new Set(ALL_PLAYERS.map((p) => p.reason))).sort();

function filterPlayers(rows: PlayerRow[], search: string, agent: string, reason: string): PlayerRow[] {{
  return rows.filter((row) => {{
    if (agent !== "all" && row.agent !== agent) return false;
    if (reason !== "all" && row.reason !== reason) return false;
    return matchesSearch(row, search);
  }});
}}

function dayMatchesFilter(block: DayBlock, dayFilter: string): boolean {{
  return dayFilter === "all" || block.report.date === dayFilter;
}}

function renderSegmentBlock(block: DayBlock) {{
  const short = block.dayShort;
  return (
    <Stack key={{`seg-${{block.report.date}}`}} gap={{8}}>
      <H2>{{block.report.weekday}} vs last {{block.report.weekday}} · Elite &amp; Jackpota</H2>
      <Table
        headers={{[
          "Segment",
          `This ${{short}} Purchase`,
          `Prior ${{short}} Purchase`,
          "Purchase WoW",
          `This ${{short}} Purchased Players`,
          `Prior ${{short}} Purchased Players`,
          "Purchased Players WoW",
          "Share",
        ]}}
        rows={{block.segments.map((s) => [
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
        rowTone={{block.segments.map((s) => s.tone)}}
        striped
        stickyHeader
      />
    </Stack>
  );
}}

export default function EliteWeekendSummary{fn_suffix}() {{
  const theme = useHostTheme();
  const [search, setSearch] = useCanvasState("search", "");
  const [agent, setAgent] = useCanvasState("agent", "all");
  const [reason, setReason] = useCanvasState("reason", "all");
  const [sortBy, setSortBy] = useCanvasState("sortBy", "urgency");
  const [dayFilter, setDayFilter] = useCanvasState("dayFilter", "all");
  const [ticketPlayer, setTicketPlayer] = useCanvasState<PlayerRow | null>("ticketPlayer", null);
  const [ticketSubject, setTicketSubject] = useCanvasState("ticketSubject", "");
  const [ticketBody, setTicketBody] = useCanvasState("ticketBody", "");

  const openTicketDraft = (player: PlayerRow) => {{
    setTicketPlayer(player);
    setTicketSubject(player.ticketSubject || "");
    setTicketBody(player.ticketBody || "");
  }};
  const closeTicketDraft = () => setTicketPlayer(null);

  const filterActive = search.trim() !== "" || agent !== "all" || reason !== "all" || sortBy !== "urgency";
  const visibleBlocks = DAY_BLOCKS.filter((b) => dayMatchesFilter(b, dayFilter));
  const visibleCount = visibleBlocks.reduce((sum, block) => {{
    return sum + filterPlayers(block.players, search, agent, reason).length;
  }}, 0);

  const daySelectOptions = [
    {{ value: "all", label: "All days" }},
    ...DAY_BLOCKS.map((b) => ({{
      value: b.report.date,
      label: `${{b.report.weekday}} ${{b.report.date.slice(8, 10)}} ${{["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][parseInt(b.report.date.slice(5, 7), 10) - 1]}}`,
    }})),
  ];

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
      </Stack>

      <Stack gap={{16}}>
        {{DAY_BLOCKS.map((block) => renderSegmentBlock(block))}}
      </Stack>

      <Stack gap={{8}}>
        <Row gap={{8}} align="center" wrap>
          <H2>Top 20 · WoW Purchase Gaps</H2>
          <Spacer />
          <Text tone="tertiary" size="small">
            {{filterActive
              ? `Showing ${{visibleCount}} of ${{REPORT.playerCount}}`
              : `${{REPORT.playerCount}} players`}}
          </Text>
        </Row>
        <Row gap={{6}} wrap align="center">
          <Pill active={{dayFilter === "all"}} onClick={{() => setDayFilter("all")}} size="sm">
            All
          </Pill>
          {{DAY_BLOCKS.map((b) => (
            <Pill
              key={{b.report.date}}
              active={{dayFilter === b.report.date}}
              onClick={{() => setDayFilter(b.report.date)}}
              size="sm"
            >
              {{b.dayShort}}
            </Pill>
          ))}}
          <Select
            value={{dayFilter}}
            onChange={{setDayFilter}}
            options={{daySelectOptions}}
            style={{{{ flex: "0 0 180px", marginLeft: 8 }}}}
          />
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
              ...AGENT_OPTIONS,
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
      </Stack>

      {{visibleBlocks.map((block) => {{
        const filtered = sortPlayers(
          filterPlayers(block.players, search, agent, reason),
          sortBy as SortMode,
        );
        const priorTotal = filtered.reduce((sum, p) => sum + p.priorPriorNum, 0);
        const T = block.titles;
        return (
          <Stack key={{block.report.date}} gap={{8}}>
            <Row gap={{8}} align="center" wrap>
              <H2>{{block.report.weekday}} · Top 20</H2>
              <Spacer />
              <Text tone="tertiary" size="small">
                {{filterActive
                  ? `Showing ${{filtered.length}} of ${{block.players.length}}`
                  : `${{block.players.length}} players`}}
              </Text>
            </Row>
            <Table
              headers={{["#", "Agent Name", "AID", "Name", T.lifetimePurchase, T.lifetimeHold, T.thisPurchase, T.priorPurchase, T.purchase7d, T.favouriteGame7d, "Urgency", "Reason", "Recommendation", "Ticket"]}}
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
                  <Text weight={{p.urgency === "Today" ? "semibold" : "normal"}} tone={{p.urgency === "Today" ? "danger" : undefined}}>
                    {{p.urgency === "Today" ? "⚡ Today" : p.urgency}}
                  </Text>,
                  <ReasonCell text={{p.reasonTable}} parts={{p.reasonParts}} />,
                  <ActionCell text={{p.recommendation}} />,
                  <TicketDraftCell player={{p}} onDraft={{openTicketDraft}} />,
                ]),
                ...(filtered.length
                  ? [[
                      "",
                      "",
                      "",
                      <Text weight="semibold">Total ({{filtered.length}})</Text>,
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
                    ]]
                  : []),
              ]}}
              columnAlign={{["center", "left", "left", "left", "right", "right", "right", "right", "left", "left", "center", "left", "left", "center"]}}
              rowTone={{[...filtered.map((p) => p.tone), ...(filtered.length ? ["neutral"] : [])]}}
              striped
              stickyHeader
              style={{{{ minWidth: 2950, width: "max-content" }}}}
              emptyMessage="No players match the current filters."
            />
          </Stack>
        );
      }})}}
    </Stack>
  );
}}
"""


def write_weekend_canvas(
    dates: list[date],
    bundles: list[tuple[date, list[dict], list[dict], list[dict]]],
    canvas_dir: Path | None = None,
) -> Path:
    """bundles: (report_date, day_rows, overall_rows, top20) per day."""
    out_dir = canvas_dir or DEFAULT_CANVAS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    day_blocks = [
        build_day_block(rd, day_rows, overall_rows, top20)
        for rd, day_rows, overall_rows, top20 in bundles
    ]
    all_players = [p for block in day_blocks for p in block["players"]]
    day_summaries = [
        build_day_summary(rd, day_rows, overall_rows)
        for rd, day_rows, overall_rows, _ in bundles
    ]
    report = build_weekend_report(dates, day_summaries, player_count=len(all_players))
    agent_tags = sorted({p["agent"] for p in all_players if p.get("agent")})
    agent_options = [
        {"value": tag, "label": format_agent_name({"agent": tag})}
        for tag in agent_tags
    ]

    slug = f"{dates[0].isoformat()}_to_{dates[-1].isoformat()}"
    content = render_weekend_canvas_tsx(report, day_blocks, agent_options)
    out_path = out_dir / f"elite-weekend-summary-{slug}.canvas.tsx"
    out_path.write_text(content, encoding="utf-8")
    return out_path
