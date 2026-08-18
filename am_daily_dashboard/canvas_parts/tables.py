"""TSX — generic composite table shells (WeekdaySegmentTable, MorningChecklist, Top20DeclineTable, SearchableTable). Extracted verbatim from am_brief_canvas.py (Batch 1 editability split)."""
from __future__ import annotations

TABLES_TSX = f"""function scrollToSection(id: string) {{
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
    {{ label: "Churned (7d)", value: focus.churned, tone: focus.churned ? "warning" : "success", sectionId: `${{prefix}}-churned` }},
    {{ label: "Active Decliners", value: focus.activeDecliners, tone: focus.activeDecliners ? "warning" : "success", sectionId: `${{prefix}}-active-decliners` }},
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
      style={{{{ width: "max-content", maxWidth: "100%" }}}}
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
  showSearch,
  sortOptions,
  defaultSort,
  sortFn,
  tableStyle,
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
  /** Show the search box. Default true; set false for sections that are
   * always short (typically well under 10 rows per AM tab) so the filter
   * bar doesn't add a step with no payoff. */
  showSearch?: boolean;
  /** When provided, renders a sort <Select>. Omit to apply sortFn silently
   * with no visible control — e.g. Locked/Take A Break sorts by soonest
   * unlock unconditionally, no extra filter row needed. */
  sortOptions?: {{ value: string; label: string }}[];
  defaultSort?: string;
  sortFn?: (rows: AidRow[], sortBy: string) => AidRow[];
  /** Passed straight to the underlying <Table>'s style. Use for a short,
   * few-column table (e.g. Top 10 Purchasers) that shouldn't stretch to
   * fill the panel width — most sections omit this and stretch normally. */
  tableStyle?: any;
}}) {{
  const searchEnabled = showSearch !== false;
  const sortSelectEnabled = !!(sortOptions && sortOptions.length && sortFn);
  const [search, setSearch] = useCanvasState(`${{stateKey}}_q`, "");
  const [sortBy, setSortBy] = useCanvasState(
    `${{stateKey}}_sort`,
    defaultSort || (sortOptions && sortOptions[0] ? sortOptions[0].value : "")
  );
  const searched = searchEnabled
    ? rows.filter((r) => matchesAidSearch(r, search, extraSearchKeys || []))
    : rows;
  const filtered = sortFn ? sortFn(searched, sortBy) : searched;
  const filterActive = searchEnabled && search.trim() !== "";
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
      {{searchEnabled || sortSelectEnabled ? (
        <Row gap={{8}} align="center" wrap>
          {{searchEnabled ? (
            <TextInput
              value={{search}}
              onChange={{setSearch}}
              placeholder="Search name, AID…"
              type="search"
              style={{{{ maxWidth: 360 }}}}
            />
          ) : null}}
          {{sortSelectEnabled ? (
            <Select
              value={{sortBy}}
              onChange={{setSortBy}}
              options={{sortOptions!}}
              style={{{{ flex: "0 0 200px" }}}}
            />
          ) : null}}
        </Row>
      ) : null}}
      <Table
        headers={{headers}}
        rows={{filtered.map((r, i) => renderRow(r, i))}}
        columnAlign={{columnAlign}}
        rowTone={{filtered.map((r) => (r.tone as any) || "neutral")}}
        striped
        stickyHeader
        style={{tableStyle}}
        emptyMessage={{keepWhenEmpty ? undefined : "No players match the current filters."}}
      />
    </Stack>
    </div>
  );
}}

"""
