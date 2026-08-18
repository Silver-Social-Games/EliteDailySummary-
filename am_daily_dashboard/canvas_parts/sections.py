"""TSX — AgentPanel: the actual per-AM-tab section composition (Top 10 Purchasers, Top 20 WoW Gaps, Pending RD, First-Time Locked RD, Birthdays, Open Tickets, Locked/Take A Break). This is the file to edit when tweaking one section's columns, filter, or thresholds. Extracted from am_brief_canvas.py (Batch 1 editability split)."""
from __future__ import annotations

SECTIONS_TSX = f"""function GoalsTable({{ goals }}: {{ goals: AgentBlock["goals"] }}) {{
  if (!goals) return null;
  if (!goals.available) {{
    return (
      <Stack gap={{8}}>
        <H2>Elite Goals</H2>
        <Text tone="tertiary">{{(goals as any).note || "No goals for this AM."}}</Text>
      </Stack>
    );
  }}
  const kpis = goals.kpis || [];
  const subtitle = [
    goals.monthLabel || "",
    goals.asOf ? `as of ${{goals.asOf}}` : "",
    goals.elapsedDays && goals.daysInMonth
      ? `day ${{goals.elapsedDays}} of ${{goals.daysInMonth}}`
      : "",
  ]
    .filter(Boolean)
    .join(" · ");
  return (
    <Stack gap={{8}}>
      <Row gap={{8}} align="center" wrap>
        <H2>Elite Goals</H2>
        <Text tone="tertiary" size="small">{{subtitle}}</Text>
        <div style={{{{ flex: 1 }}}} />
        <Text weight="semibold">{{goals.weightedTrackedDisplay || "—"}}</Text>
      </Row>
      <Table
        headers={{["KPI", "Weight", "Goal", "Actual", "Pace", "Gap", "Status"]}}
        rows={{kpis.map((k) => [
          k.label,
          k.weightLabel,
          k.goalDisplay,
          k.actualDisplay,
          k.paceDisplay,
          k.gapDisplay,
          <Text tone={{(k.statusTone as any) || "neutral"}}>{{k.status}}</Text>,
        ])}}
        columnAlign={{["left", "right", "right", "right", "right", "right", "left"]}}
        rowTone={{kpis.map((k) => (k.statusTone as any) || ("neutral" as const))}}
        striped
        stickyHeader
        style={{{{ width: "max-content", maxWidth: "100%" }}}}
      />
      <Text tone="tertiary" size="small">
        {{(goals as any).definitionsNote || ""}}
      </Text>
      <Text tone="tertiary" size="small">
        {{goals.achievementCapNote || ""}}
      </Text>
    </Stack>
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

      <GoalsTable goals={{block.goals}} />

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
        tableStyle={{{{ width: "max-content", maxWidth: "100%" }}}}
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
        showSearch={{false}}
        sortOptions={{[
          {{ value: "amount", label: "Sort: Amount ↓" }},
          {{ value: "oldest", label: "Sort: Oldest first" }},
        ]}}
        defaultSort="amount"
        sortFn={{(rows, sortBy) =>
          sortBy === "oldest"
            ? sortByNumKey(rows, "daysPending", true)
            : sortByNumKey(rows, "amountNum", true)
        }}
        headers={{["AID", "Name", "RD ID", "Amount", "Status", "Created"]}}
        columnAlign={{["left", "left", "left", "right", "left", "left"]}}
        renderRow={{(p) => [
          <AidLink row={{p}} />,
          p.name,
          p.redeemId,
          <Text tone="warning">{{p.amount as string}}</Text>,
          p.status,
          <AgingCell created={{p.created as string}} daysPending={{p.daysPending as number | null}} agingFlag={{p.agingFlag as boolean}} />,
        ]}}
      />

      <SearchableTable
        title="First-Time Locked RD"
        rows={{block.rdFirstTime}}
        stateKey={{`rdf_${{block.agentName}}`}}
        sectionId={{`${{prefix}}-first-rd`}}
        keepWhenEmpty
        showSearch={{false}}
        headers={{["AID", "Name", "RD ID", "Amount", "Status", "Created", "Ticket"]}}
        columnAlign={{["left", "left", "left", "right", "left", "left", "center"]}}
        renderRow={{(p) => [
          <AidLink row={{p}} />,
          p.name,
          p.redeemId,
          <Text tone="warning">{{p.amount as string}}</Text>,
          p.status,
          p.created,
          <TicketDraftCell player={{p as any}} onDraft={{onDraft as any}} />,
        ]}}
      />

      <SearchableTable
        title="Birthdays · Last 3 Days"
        rows={{block.birthdays}}
        stateKey={{`bd_${{block.agentName}}`}}
        sectionId={{`${{prefix}}-birthdays`}}
        showSearch={{false}}
        headers={{["AID", "Name", "Email", "DOB", "Age", "Ticket"]}}
        columnAlign={{["left", "left", "left", "left", "right", "center"]}}
        renderRow={{(p) => [
          <AidLink row={{p}} />,
          p.name,
          p.email,
          <Text tone="success">{{p.dob as string}}</Text>,
          p.age ?? "—",
          <TicketDraftCell player={{p as any}} onDraft={{onDraft as any}} />,
        ]}}
      />

      <SearchableTable
        title="Open Tickets"
        rows={{block.zendesk}}
        stateKey={{`zd_${{block.agentName}}`}}
        sectionId={{`${{prefix}}-zendesk`}}
        extraSearchKeys={{["ticketIds"]}}
        sortOptions={{[
          {{ value: "ltp", label: "Sort: LTP ↓" }},
          {{ value: "tickets", label: "Sort: Open Tickets ↓" }},
          {{ value: "purchase7d", label: "Sort: 7D Purchase ↓" }},
        ]}}
        defaultSort="ltp"
        sortFn={{(rows, sortBy) =>
          sortBy === "tickets"
            ? sortByNumKey(rows, "openTickets", true)
            : sortBy === "purchase7d"
            ? sortByNumKey(rows, "purchase7dNum", true)
            : sortByNumKey(rows, "lifetimePurchasedNum", true)
        }}
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
        showSearch={{false}}
        sortFn={{(rows) => sortBySoonestUnlock(rows)}}
        headers={{["AID", "Name", "Lock Reason", "Days Remaining / Unlock"]}}
        columnAlign={{["left", "left", "left", "left"]}}
        renderRow={{(p) => [
          <AidLink row={{p}} />,
          p.name,
          <Text tone={{(p.tone as any) || "warning"}}>{{p.lockReason as string}}</Text>,
          <UnlockCell detail={{(p.unlockDetail as string) || ""}} remainingDays={{p.unlockRemainingDays as number | null}} />,
        ]}}
      />
    </Stack>
  );
}}

"""
