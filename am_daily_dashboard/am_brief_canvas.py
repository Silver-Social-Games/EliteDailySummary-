"""Elite AM Brief canvas TSX — design parity with Elite Daily Decline.

Split (Batch 1, editability refactor): generic building blocks live in
canvas_parts/ (cells.py, tables.py) and the per-AM-tab section
composition lives in canvas_parts/sections.py (AgentPanel). This file
keeps only the JSON payload wiring and the top-level App component
(tab switcher + Overview layout).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
if str(PACKAGE_DIR) not in sys.path:
    sys.path.insert(0, str(PACKAGE_DIR))

from canvas_parts.cells import CELLS_TSX  # noqa: E402
from canvas_parts.tables import TABLES_TSX  # noqa: E402
from canvas_parts.sections import SECTIONS_TSX  # noqa: E402


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
    single_am = bool(payload.get("singleAm"))
    single_am_name = payload.get("singleAmName") or (
        (payload.get("amOrder") or [None])[0]
    )
    default_tab = (
        json.dumps(single_am_name)
        if single_am and single_am_name
        else '"Overview"'
    )

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
const SINGLE_AM = {json.dumps(single_am)};

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

{CELLS_TSX}{TABLES_TSX}{SECTIONS_TSX}export default function EliteAmBrief{fn}() {{
  const theme = useHostTheme();
  const [tab, setTab] = useCanvasState("amTab", {default_tab} as string);
  const [ticketPlayer, setTicketPlayer] = useCanvasState<any>("ticketPlayer", null);
  const [ticketSubject, setTicketSubject] = useCanvasState("ticketSubject", "");
  const [ticketBody, setTicketBody] = useCanvasState("ticketBody", "");

  const openDraft = (player: any) => {{
    setTicketPlayer(player);
    setTicketSubject(player.ticketSubject || "");
    setTicketBody(player.ticketBody || "");
  }};

  const active = AGENTS.find((a) => a.agentName === tab) as AgentBlock | undefined;
  const segments = (REPORT as any).segments || [];
  const dayShort = (REPORT as any).dayShort || String(REPORT.weekday || "").slice(0, 3);
  const showOverview = !SINGLE_AM && tab === "Overview";

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

      {{!SINGLE_AM ? (
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
      ) : null}}

      {{showOverview ? (
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
                headers={{["AM", "Purchase $", "Share", "Purchased Of Portfolio"]}}
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
                "Purchased Of Portfolio",
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
