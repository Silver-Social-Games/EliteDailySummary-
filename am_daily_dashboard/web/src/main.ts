// @ts-nocheck
import { AGENTS, AM_ORDER, AM_SHARES, GATE_TOKEN, OVERVIEW, REPORT, SINGLE_AM,
  TEAM_GOALS, TITLES, day, dayShort } from "./payload";
import { app, gateToken, getState, go, rememberGate, setPage, setRenderHook,
  setState, takeFocusKey } from "./state";
import { agentBlock, rowsFor } from "./selectors";
import { compactMoney, esc, icon, initials, money, richText, toNum } from "./format";
import { toast } from "./toast";
import { agingHtml, aidHtml, bigWinHtml, docsHtml, holdHtml, moneyHtml, p7dHtml,
  scoreLegendHtml, scoreMeterHtml, ticketHtml, ticketIdsHtml, unlockHtml,
  urgencyHtml, wowHtml } from "./cells";
import { renderAction, renderReason } from "./reason";
import { matchesDecline, sortByNumKey, sortBySoonestUnlock, sortPlayers } from "./filters";
import { paginate, tableCard, tableHtml } from "./table";
    /* ---------------- section registry: drives nav + routing ---------------- */
    const GROUP_ORDER = ["Command", "Today", "Performance", "Risk", "Operations", "Care"];
    const VIEWS = {
      dashboard: { label: "Manager Dashboard", short: "Dashboard", icon: "gauge",
                   group: "Command", managerOnly: true, gated: true,
                   sub: "Cross-AM roll-up — manager only" },
      team:      { label: "Team Goals", icon: "target", group: "Command",
                   managerOnly: true, gated: true,
                   sub: "Your team as one book — manager only" },
      home:      { label: "Morning Brief", icon: "sunrise", group: "Today",
                   sub: "Where to start today" },
      goals:     { label: "Elite Goals", icon: "target", group: "Performance",
                   sub: "Month to date against target" },
      top10:     { label: "Top 10 Purchasers", icon: "crown", group: "Performance",
                   key: "top10", sub: "Yesterday's biggest spenders" },
      top20:     { label: "Top 20 · WoW Gaps", icon: "trend-down", group: "Risk",
                   key: "decline", sub: `Same-weekday drops vs last ${day}` },
      rd:        { label: "Pending Redemptions", icon: "banknote", group: "Operations",
                   key: "rdOver5k", sub: "Locked withdrawals awaiting release" },
      rdfirst:   { label: "First-Time Locked RD", icon: "sparkles", group: "Operations",
                   key: "rdFirstTime", sub: "First-ever redemption — under review" },
      tickets:   { label: "Open Tickets", icon: "ticket", group: "Operations",
                   key: "zendesk", sub: "Open Zendesk tickets on your book" },
      locks:     { label: "Locked & Take A Break", icon: "lock", group: "Operations",
                   key: "locks", sub: "New locks and breaks due to end" },
      birthdays: { label: "Birthdays · Last 3 Days", short: "Birthdays", icon: "gift",
                   group: "Care", key: "birthdays", sub: "A reason to reach out" },
    };
    const NAV_ORDER = ["dashboard", "team", "home", "goals", "top10", "top20",
                       "rd", "rdfirst", "tickets", "locks", "birthdays"];

    /* ---------------- shared blocks ---------------- */
    function segmentCard() {
      const segments = REPORT.segments || [];
      const title = REPORT.segmentTitle || `${day} vs last ${day} · Elite & Jackpota`;
      const rows = segments.map(s => [
        esc(s.label), esc(s.revThis), esc(s.revPrior), wowHtml(s.revWow),
        esc(s.plyThis), esc(s.plyPrior), wowHtml(s.plyWow), esc(s.share || ""),
      ]);
      return `<div class="card">
        <div class="card-head">
          <span class="card-icon info">${icon("pie", "ic-sm")}</span>
          <div><div class="card-title">${esc(title)}</div>
          ${REPORT.headline ? `<div class="card-sub">${esc(REPORT.headline)}</div>` : ""}</div>
        </div>
        ${tableHtml(
          ["Segment", `This ${dayShort} Purchase`, `Prior ${dayShort} Purchase`, "Purchase WoW",
           `This ${dayShort} Purchased Players`, `Prior ${dayShort} Purchased Players`,
           "Purchased Players WoW", "Share"],
          rows, ["left", "right", "right", "right", "right", "right", "right", "right"],
          segments.map(s => s.tone || "neutral"),
          { markerCol: 0, empty: "No segment data." }
        )}
      </div>`;
    }

    function statCard(o) {
      const tag = o.view ? "button" : "div";
      const attrs = o.view ? ` data-go="${esc(o.view)}"` : ' class-flat';
      return `<${tag} class="stat t-${o.tone || "neutral"}${o.view ? "" : " flat"}"${o.view ? ` data-go="${esc(o.view)}"` : ""}>
        <div class="stat-top">
          <span class="stat-chip">${icon(o.icon, "ic-sm")}</span>
          <span class="stat-label">${esc(o.label)}</span>
        </div>
        <div class="stat-value ${o.small ? "sm" : ""}">${esc(o.value)}</div>
        ${o.foot ? `<div class="stat-foot">${o.foot}</div>` : ""}
      </${tag}>`;
    }

    /* ---------------- views ---------------- */
    function viewHome() {
      const b = agentBlock();
      const f = b.focus || {};
      const greet = (b.greetingLines || []).map((line, i) => richText(line, i === 0)).join("");
      const cards = [
        { label: "Open Tickets", value: f.openZd ?? 0, icon: "ticket", view: "tickets",
          tone: f.openZd ? "info" : "success" },
        { label: "Top 20 Decline", value: f.declineCount ?? 0, icon: "trend-down", view: "top20",
          tone: f.declineCount ? "warning" : "success" },
        { label: "Pending RD", value: f.rdOver5k ?? 0, icon: "banknote", view: "rd",
          tone: f.rdOver5k ? "warning" : "success" },
        { label: "Take A Break", value: f.takeABreak ?? 0, icon: "clock", view: "locks",
          tone: f.takeABreak ? "warning" : "success" },
        { label: "Other Locked", value: f.otherLocked ?? 0, icon: "lock", view: "locks",
          tone: f.otherLocked ? "warning" : "success" },
        { label: "Self-Exclusion", value: f.selfExclusion ?? 0, icon: "shield", view: "locks",
          tone: "neutral" },
        { label: "Birthdays (3d)", value: f.birthdays ?? 0, icon: "gift", view: "birthdays",
          tone: f.birthdays ? "brand" : "neutral" },
      ];
      return `<div class="stack">
        ${greet ? `<div class="hero"><div class="stack-6">${greet}</div></div>` : ""}
        <div class="stats">${cards.map(statCard).join("")}</div>
        ${goalsSummaryCard(b.goals)}
        ${segmentCard()}
      </div>`;
    }

    function goalsSummaryCard(goals) {
      if (!goals || !goals.available) return "";
      const score = goals.score || {};
      const pct = Number(goals.weightedTrackedPct);
      const kpis = goals.kpis || [];
      const onTrack = kpis.filter(k => k.statusTone === "success").length;
      const behind = kpis.filter(k => k.statusTone === "danger" || k.statusTone === "warning").length;
      const meterTone = pct >= 90 ? "success" : pct >= 70 ? "warning" : "danger";
      return `<div class="card">
        <div class="card-head">
          <span class="card-icon ${meterTone}">${icon("target", "ic-sm")}</span>
          <div><div class="card-title">Elite Goals</div>
          <div class="card-sub">${esc(goals.monthLabel || "")}${goals.asOf ? ` · as of ${esc(goals.asOf)}` : ""}</div></div>
          <div class="spacer"></div>
          <button type="button" class="btn" data-go="goals">Open ${icon("chev-right", "ic-xs")}</button>
        </div>
        <div class="card-body stack-10">
          <div class="goal-score">
            <span class="goal-pct t-${meterTone}">${esc(score.totalPoints ?? "—")}</span>
            <span class="t-tertiary">of ${esc(score.totalPointsMax ?? 80)} · ${esc(score.scoreSubline || "")}</span>
          </div>
          ${scoreMeterHtml(score, meterTone)}
          ${scoreLegendHtml(score, meterTone)}
          <div class="row">
            <span class="badge success">${icon("check-circle", "ic-xs")}${onTrack} on track</span>
            <span class="badge ${behind ? "danger" : ""}">${icon("alert", "ic-xs")}${behind} need attention</span>
          </div>
        </div>
      </div>`;
    }

    function viewGoals() {
      const goals = agentBlock().goals;
      if (!goals) {
        return emptyState("target", "No goals for this AM",
          "Goals are tracked for Coral, Gabriel, Lee and Rachel.");
      }
      if (!goals.available) {
        return emptyState("target", "Goals unavailable", goals.note || "No goals for this AM.");
      }
      const kpis = goals.kpis || [];
      const score = goals.score || {};
      const pct = Number(goals.weightedTrackedPct);
      const meterTone = pct >= 90 ? "success" : pct >= 70 ? "warning" : "danger";
      const subtitle = [
        goals.monthLabel || "",
        goals.asOf ? `as of ${goals.asOf}` : "",
        (goals.elapsedDays && goals.daysInMonth) ? `day ${goals.elapsedDays} of ${goals.daysInMonth}` : "",
      ].filter(Boolean).join(" · ");
      const rows = kpis.map(k => [
        esc(k.label), esc(k.weightLabel), esc(k.goalDisplay), esc(k.actualDisplay),
        esc(k.paceDisplay), esc(k.gapDisplay),
        `<span class="badge ${k.statusTone || ""}">${esc(k.status)}</span>`,
      ]);
      return `<div class="stack">
        <div class="card">
          <div class="card-body stack-10">
            <div class="row">
              <div class="goal-score">
                <span class="goal-pct t-${meterTone}">${esc(score.totalDisplay || "—")}</span>
                <span class="t-tertiary">${esc(score.scoreSubline || "")}</span>
              </div>
              <div class="spacer"></div>
              <span class="badge">${esc(subtitle)}</span>
            </div>
            ${scoreMeterHtml(score, meterTone)}
            ${scoreLegendHtml(score, meterTone)}
          </div>
        </div>
        <div class="card">
          ${tableHtml(["KPI", "Weight", "Goal", "Actual", "Pace", "Gap", "Status"], rows,
            ["left", "right", "right", "right", "right", "right", "left"],
            kpis.map(k => k.statusTone || "neutral"), { markerCol: 0 })}
        </div>
        <div class="note">${esc(goals.definitionsNote || "")}</div>
        <div class="note">${esc(goals.achievementCapNote || "")}</div>
        <div class="note">${esc(score.scoreNote || "")}</div>
      </div>`;
    }

    /* Manager-only. Deliberately has no 80 + 20 score meter: the manager's 20
       points are an award they make to an AM, and there is nobody to award the
       team's, so the KPI table stands on its own. */
    function teamKpi(key) {
      return (TEAM_GOALS && (TEAM_GOALS.kpis || []).find(k => k.key === key)) || null;
    }

    function teamGoalsCard() {
      if (!TEAM_GOALS || !TEAM_GOALS.available) return "";
      const kpis = TEAM_GOALS.kpis || [];
      const onTrack = kpis.filter(k => k.statusTone === "success").length;
      const behind = kpis.filter(k => k.statusTone === "danger" || k.statusTone === "warning").length;
      const headline = ["daily_avg_purchase", "daily_avg_net_purchase", "monthly_purchasers"]
        .map(teamKpi).filter(Boolean);
      return `<div class="card">
        <div class="card-head">
          <span class="card-icon ${behind ? "warning" : "success"}">${icon("target", "ic-sm")}</span>
          <div><div class="card-title">Team Goals</div>
          <div class="card-sub">Your targets — the whole managed book · ${esc(TEAM_GOALS.monthLabel || "")}</div></div>
          <div class="spacer"></div>
          <button type="button" class="btn" data-go="team">Open ${icon("chev-right", "ic-xs")}</button>
        </div>
        <div class="card-body stack-10">
          ${tableHtml(["KPI", "Goal", "Pace", "Status"],
            headline.map(k => [
              esc(k.label), esc(k.goalDisplay), esc(k.paceDisplay),
              `<span class="badge ${k.statusTone || ""}">${esc(k.status)}</span>`,
            ]),
            ["left", "right", "right", "left"],
            headline.map(k => k.statusTone || "neutral"), { markerCol: 0 })}
          <div class="row">
            <span class="badge success">${icon("check-circle", "ic-xs")}${onTrack} on track</span>
            <span class="badge ${behind ? "danger" : ""}">${icon("alert", "ic-xs")}${behind} need attention</span>
          </div>
        </div>
      </div>`;
    }

    function viewTeamGoals() {
      if (!app.unlocked) return gateHtml();
      if (!TEAM_GOALS) {
        return emptyState("target", "No team goals in this brief",
          "Add a team row for this month to data/elite_goals.tsv and re-run the generator.");
      }
      if (!TEAM_GOALS.available) {
        return emptyState("target", "Team goals unavailable",
          TEAM_GOALS.note || "No team target row for this month.");
      }
      const g = TEAM_GOALS;
      const kpis = g.kpis || [];
      const subtitle = [
        g.monthLabel || "",
        g.asOf ? `as of ${g.asOf}` : "",
        (g.elapsedDays && g.daysInMonth) ? `day ${g.elapsedDays} of ${g.daysInMonth}` : "",
      ].filter(Boolean).join(" · ");

      const cards = [
        { label: "Team Book", value: (g.portfolioSize || 0).toLocaleString(), icon: "list",
          tone: "neutral", foot: `${(g.portfolioLocked || 0).toLocaleString()} locked, still counted` },
        { label: "MTD Purchase", value: compactMoney(g.mtdPurchase || 0), icon: "dollar",
          tone: "success", foot: money(g.mtdPurchase || 0) },
        { label: "MTD Net Purchase", value: compactMoney(g.mtdNetPurchase || 0), icon: "banknote",
          tone: "brand", foot: money(g.mtdNetPurchase || 0) },
        { label: "Purchasers", value: (teamKpi("monthly_purchasers") || {}).actualDisplay || "—",
          icon: "users", tone: "brand", foot: "Distinct across the whole managed book" },
      ];

      const rows = kpis.map(k => [
        esc(k.label), esc(k.weightLabel), esc(k.goalDisplay), esc(k.actualDisplay),
        esc(k.paceDisplay), esc(k.gapDisplay),
        `<span class="badge ${k.statusTone || ""}">${esc(k.status)}</span>`,
      ]);

      /* No per-AM breakdown here, by the user's decision: these are their own
         goals, not a roll-up of their employees', and the Goals Leaderboard on
         the Dashboard already covers who contributed what. */
      return `<div class="stack">
        <div class="card">
          <div class="card-head">
            <span class="card-icon">${icon("target", "ic-sm")}</span>
            <div><div class="card-title">Elite Goals · Team</div>
            <div class="card-sub">Your own targets, measured over the whole managed book</div></div>
            <div class="spacer"></div>
            <span class="badge">${esc(subtitle)}</span>
          </div>
        </div>
        <div class="stats">${cards.map(statCard).join("")}</div>
        <div class="card">
          ${tableHtml(["KPI", "Weight", "Goal", "Actual", "Pace", "Gap", "Status"], rows,
            ["left", "right", "right", "right", "right", "right", "left"],
            kpis.map(k => k.statusTone || "neutral"), { markerCol: 0 })}
        </div>
        <div class="note">These are your own targets, loaded as given — never derived
          from the AMs' targets. Progress is measured over the whole managed book,
          Alon's portfolio included: Purchasers, Reactivation and % Active are counted
          as distinct accounts across the book, and ARPPU and % Active are rebuilt from
          the book totals rather than averaged across the AMs.</div>
        <div class="note">${esc(g.definitionsNote || "")}</div>
        <div class="note">${esc(g.achievementCapNote || "")}</div>
      </div>`;
    }

    function viewTop20() {
      const players = rowsFor("decline");
      const stateKey = `dec_${app.agent}`;
      const search = getState(stateKey + "_search", "");
      const reason = getState(stateKey + "_reason", "all");
      const sortBy = getState(stateKey + "_sortBy", "urgency");
      const reasons = [...new Set(players.map(p => p.reason).filter(Boolean))].sort();
      const ordered = sortPlayers(players.filter(row =>
        (reason === "all" || row.reason === reason) && matchesDecline(row, search)), sortBy);
      const { slice, pager, total } = paginate(ordered, stateKey);
      const priorTotal = ordered.reduce((sum, p) => sum + (p.priorPriorNum || 0), 0);
      const active = search.trim() !== "" || reason !== "all";

      const headers = ["#", "Agent Name", "AID", "Name", TITLES.lifetimePurchase, TITLES.lifetimeHold,
        TITLES.thisPurchase, TITLES.priorPurchase, TITLES.purchase7d, TITLES.favouriteGame7d,
        "Urgency", "Reason", "Recommendation", "Ticket"];
      const rows = slice.map((p, i) => [
        String(ordered.indexOf(p) + 1),
        esc(p.agentName), aidHtml(p), esc(p.name),
        moneyHtml(p.lifetimePurchase, (p.lifetimePurchasedNum || 0) >= 50000),
        holdHtml(p.lifetimeHold),
        moneyHtml(p.thisDay, p.zeroDay),
        moneyHtml(p.priorDay, (p.sortGap || 0) >= 2000),
        p7dHtml(p.purchase7d), esc(p.favouriteGame7d), urgencyHtml(p.urgency),
        `<div class="reason-cell">${renderReason(p.reasonParts, p.reasonTable || p.reason)}</div>`,
        `<div class="action-cell">${renderAction(p.recommendation)}</div>`,
        ticketHtml(p),
      ]);
      const tones = slice.map(p => p.tone || "neutral");
      if (rows.length) {
        rows.push(["", "", "", "Total (all filtered)", "", "", "", money(priorTotal), "", "", "", "", "", ""]);
        tones.push("neutral");
      }
      return `<div class="card">
        <div class="toolbar">
          <label class="search">${icon("search", "ic-sm")}
            <input type="search" placeholder="Search name, AID, reason…" value="${esc(search)}" data-state="${esc(stateKey + "_search")}">
          </label>
          <span class="select-wrap"><select data-state="${esc(stateKey + "_sortBy")}">
            <option value="urgency" ${sortBy === "urgency" ? "selected" : ""}>Sort: Urgency + gap</option>
            <option value="priorHigh" ${sortBy === "priorHigh" ? "selected" : ""}>Prior purchase ↓</option>
            <option value="lifetimeHigh" ${sortBy === "lifetimeHigh" ? "selected" : ""}>Lifetime purchase ↓</option>
            <option value="gapHigh" ${sortBy === "gapHigh" ? "selected" : ""}>WoW gap ↓</option>
          </select>${icon("chev-down", "ic-xs")}</span>
          <div class="spacer"></div>
          <span class="badge ${active ? "brand" : ""}">${active ? `${ordered.length} of ${players.length}` : `${players.length} players`}</span>
        </div>
        ${reasons.length ? `<div class="chip-row">
          <button type="button" class="chip ${reason === "all" ? "active" : ""}" data-reason-state="${esc(stateKey + "_reason")}" data-reason="all">All reasons</button>
          ${reasons.map(r => `<button type="button" class="chip ${reason === r ? "active" : ""}" data-reason-state="${esc(stateKey + "_reason")}" data-reason="${esc(r)}">${esc(r)}</button>`).join("")}
        </div>` : ""}
        ${tableHtml(headers, rows,
          ["center", "left", "left", "left", "right", "right", "right", "right", "left", "left", "center", "left", "left", "center"],
          tones,
          { tableClass: "players-table", totalRowIndex: rows.length - 1,
            empty: "No players match the current filters." })}
        ${total ? pager : ""}
      </div>`;
    }

    function viewTop10() {
      return tableCard({
        rows: rowsFor("top10"), stateKey: `t10_${app.agent}`,
        extraKeys: ["offerCode", "offerTitle"], compact: true,
        headers: ["#", "AID", "Name", "Purchased $", "Purchases (#)", "Top Offer", "Price", "Usual → Ceiling (30D)"],
        align: ["center", "left", "left", "right", "right", "left", "right", "left"], markerCol: 3,
        empty: "No purchasers yesterday.",
        renderRow: p => [esc(p.rank), aidHtml(p), esc(p.name),
          `<span class="t-success w-semibold">${esc(p.purchased)}</span>`,
          esc(p.orderCount), esc(p.offerCode),
          `<span class="${p.offerPriceVaries ? "t-warning" : ""}">${esc(p.offerPrice)}${p.offerPriceVaries ? " avg" : ""}</span>`,
          esc(p.packageFit)],
      });
    }

    function viewPendingRd() {
      return tableCard({
        rows: rowsFor("rdOver5k"), stateKey: `rd5_${app.agent}`, showSearch: false,
        sortOptions: [
          { value: "amount", label: "Sort: Amount ↓" },
          { value: "won", label: "Sort: Won Yesterday ↓" },
          { value: "oldest", label: "Sort: Oldest first" },
        ],
        defaultSort: "amount",
        sortFn: (rows, s) => s === "oldest" ? sortByNumKey(rows, "daysPending", true)
          : s === "won" ? sortByNumKey(rows, "wonYesterdayNum", true)
          : sortByNumKey(rows, "amountNum", true),
        headers: ["AID", "Name", "RD ID", "Amount", "Status", "Created", "Won Yesterday", "Docs", "LTP", "Hold", "7D Purchase"],
        align: ["left", "left", "left", "right", "left", "left", "right", "left", "right", "right", "right"], markerCol: 3,
        empty: "No pending redemptions.",
        renderRow: p => [aidHtml(p), esc(p.name), esc(p.redeemId),
          `<span class="t-warning w-semibold">${esc(p.amount)}</span>`, esc(p.status),
          agingHtml(p.created, p.daysPending, p.agingFlag),
          bigWinHtml(p), docsHtml(p.docsStatus),
          esc(p.lifetimePurchase || "—"), esc(p.lifetimeHold || "—"), esc(p.purchase7d || "—")],
      });
    }

    function viewFirstRd() {
      return tableCard({
        rows: rowsFor("rdFirstTime"), stateKey: `rdf_${app.agent}`, showSearch: false,
        headers: ["AID", "Name", "RD ID", "Amount", "Status", "Created", "Ticket"],
        align: ["left", "left", "left", "right", "left", "left", "center"], markerCol: 3,
        empty: "No first-time redemptions today.",
        renderRow: p => [aidHtml(p), esc(p.name), esc(p.redeemId),
          `<span class="t-warning w-semibold">${esc(p.amount)}</span>`, esc(p.status),
          esc(p.created), ticketHtml(p)],
      });
    }

    function viewBirthdays() {
      return tableCard({
        rows: rowsFor("birthdays"), stateKey: `bd_${app.agent}`, showSearch: false,
        headers: ["AID", "Name", "Email", "DOB", "Age", "Ticket"],
        align: ["left", "left", "left", "left", "right", "center"], markerCol: 3,
        empty: "No birthdays in the last 3 days.",
        renderRow: p => [aidHtml(p), esc(p.name), esc(p.email),
          `<span class="t-success w-semibold">${esc(p.dob)}</span>`, esc(p.age ?? "—"), ticketHtml(p)],
      });
    }

    function viewTickets() {
      return tableCard({
        rows: rowsFor("zendesk"), stateKey: `zd_${app.agent}`, extraKeys: ["ticketIds"],
        sortOptions: [
          { value: "ltp", label: "Sort: LTP ↓" },
          { value: "tickets", label: "Sort: Open Tickets ↓" },
          { value: "purchase7d", label: "Sort: 7D Purchase ↓" },
        ],
        defaultSort: "ltp",
        sortFn: (rows, s) => s === "tickets" ? sortByNumKey(rows, "openTickets", true)
          : s === "purchase7d" ? sortByNumKey(rows, "purchase7dNum", true)
          : sortByNumKey(rows, "lifetimePurchasedNum", true),
        headers: ["AID", "Name", "LTP", "Hold", "7D Purchase", "Open Tickets", "Ticket"],
        align: ["left", "left", "right", "right", "right", "right", "left"], markerCol: 2,
        empty: "No open tickets.",
        renderRow: p => [aidHtml(p), esc(p.name),
          moneyHtml(p.lifetimePurchase || "$0", (p.lifetimePurchasedNum || 0) >= 50000),
          holdHtml(p.lifetimeHold || "n/a"), moneyHtml(p.purchase7d || "$0"),
          esc(p.openTickets), ticketIdsHtml(p)],
      });
    }

    function viewLocks() {
      return tableCard({
        rows: rowsFor("locks"), stateKey: `lk_${app.agent}`, showSearch: false,
        sortFn: rows => sortBySoonestUnlock(rows),
        headers: ["AID", "Name", "Lock Reason", "Days Remaining / Unlock"],
        align: ["left", "left", "left", "left"], markerCol: 2,
        empty: "No new locks and no breaks due to end.",
        renderRow: p => [aidHtml(p), esc(p.name),
          `<span class="t-${p.tone || "warning"}">${esc(p.lockReason)}</span>`,
          unlockHtml(p.unlockDetail, p.unlockRemainingDays)],
      });
    }

    function emptyState(ico, title, body) {
      return `<div class="card"><div class="card-body" style="text-align:center;padding:48px 20px">
        <div class="card-icon neutral" style="margin:0 auto 12px;width:44px;height:44px">${icon(ico, "ic-lg")}</div>
        <div class="card-title" style="margin-bottom:5px">${esc(title)}</div>
        <div class="t-tertiary t-small">${esc(body)}</div>
      </div></div>`;
    }

    /* ---------------- manager dashboard ---------------- */
    function viewDashboard() {
      if (!app.unlocked) return gateHtml();

      const purchase = AM_SHARES.reduce((s, r) => s + toNum(r.purchase), 0);
      const purchasedPlayers = AM_SHARES.reduce((s, r) => s + (Number(r.purchasedPlayers) || 0), 0);
      const book = AM_SHARES.reduce((s, r) => s + (Number(r.totalPlayers) || 0), 0);
      const sum = k => OVERVIEW.reduce((s, r) => s + (Number(r[k]) || 0), 0);
      const openZd = sum("openZd"), rd = sum("rdOver5k"), locked = sum("locked");
      const decline = sum("declineCount"), birthdays = sum("birthdays");
      const rate = book ? (purchasedPlayers / book) * 100 : 0;

      const cards = [
        { label: `Elite Purchase · ${dayShort}`, value: compactMoney(purchase), icon: "dollar", tone: "success",
          foot: `${money(purchase)} across ${AM_SHARES.length} AMs` },
        { label: "Purchased Players", value: purchasedPlayers.toLocaleString(), icon: "users", tone: "brand",
          foot: `${rate.toFixed(1)}% of the book` },
        { label: "Book Size", value: book.toLocaleString(), icon: "list", tone: "neutral",
          foot: "Tagged Elite accounts" },
        { label: "Open Tickets", value: openZd.toLocaleString(), icon: "ticket", tone: openZd ? "info" : "success" },
        { label: "Pending RD", value: rd.toLocaleString(), icon: "banknote", tone: rd ? "warning" : "success" },
        { label: "Locked", value: locked.toLocaleString(), icon: "lock", tone: locked ? "warning" : "success" },
        { label: "Top 20 Decline", value: decline.toLocaleString(), icon: "trend-down", tone: decline ? "warning" : "success" },
        { label: "Birthdays (3d)", value: birthdays.toLocaleString(), icon: "gift", tone: "brand" },
      ];

      /* Goals leaderboard. Ranked on share of whatever maximum applies, not on
         raw points: a scored AM is out of 100 and an unscored one out of 80, so
         comparing point totals would rank the unscored last by default. */
      const scored = AGENTS
        .filter(a => a.goals && a.goals.available)
        .map(a => {
          const kpis = a.goals.kpis || [];
          const sc = a.goals.score || {};
          return {
            name: a.agentName,
            score: sc,
            pct: Number(sc.totalPctOfMax ?? a.goals.weightedTrackedPct),
            kpiPct: Number(a.goals.weightedTrackedPct),
            onTrack: kpis.filter(k => k.statusTone === "success").length,
            behind: kpis.filter(k => k.statusTone === "danger" || k.statusTone === "warning").length,
            total: kpis.length,
          };
        })
        .sort((a, b) => (b.pct || 0) - (a.pct || 0));

      const leaderRows = scored.map((s, i) => {
        const tone = s.kpiPct >= 90 ? "success" : s.kpiPct >= 70 ? "warning" : "danger";
        return [
          `<span class="badge ${i === 0 ? "brand" : ""}">${i + 1}</span>`,
          `<button type="button" class="chip" data-agent="${esc(s.name)}">${esc(s.name)}</button>`,
          `<span class="w-semibold t-${tone}">${esc(s.score.totalDisplay || "—")}</span>`,
          `<div style="min-width:150px">${scoreMeterHtml(s.score, tone)}</div>`,
          s.score.managerScored
            ? `<span class="t-manager w-semibold">${esc(s.score.managerPointsDisplay)}</span>`
            : `<span class="t-quaternary">Pending</span>`,
          `<span class="t-success w-semibold">${s.onTrack}</span>`,
          `<span class="${s.behind ? "t-danger w-semibold" : "t-quaternary"}">${s.behind}</span>`,
        ];
      });

      const shareRows = AM_SHARES.map(r => [
        `<button type="button" class="chip" data-agent="${esc(r.agentName)}">${esc(r.agentName)}</button>`,
        `<span class="t-success w-semibold">${esc(r.purchase)}</span>`,
        esc(r.purchaseShare),
        esc(r.purchasedOfBook || r.purchasedPlayers),
      ]);

      const ovRows = OVERVIEW.map(r => [
        `<button type="button" class="chip" data-agent="${esc(r.agentName)}">${esc(r.agentName)}</button>`,
        `<span class="t-success w-semibold">${esc(r.purchase)}</span>`,
        esc(r.purchasedOfBook || r.purchasedPlayers),
        esc(r.openZd), esc(r.takeABreak), esc(r.locked), esc(r.rdOver5k),
        `<span class="t-success">${esc(r.birthdays)}</span>`, esc(r.declineCount),
      ]);

      const greet = (REPORT.overviewGreetingLines || []).map((line, i) => richText(line, i === 0)).join("");

      return `<div class="stack">
        ${greet ? `<div class="hero"><div class="stack-6">${greet}</div></div>` : ""}
        <div class="stats">${cards.map(statCard).join("")}</div>

        ${teamGoalsCard()}

        ${scored.length ? `<div class="card">
          <div class="card-head">
            <span class="card-icon">${icon("target", "ic-sm")}</span>
            <div><div class="card-title">Goals Leaderboard</div>
            <div class="card-sub">80 KPI points + your 20 of appreciation · ranked on share of the applicable maximum</div></div>
          </div>
          ${tableHtml(["#", "AM", "Score", "", "Manager", "On track", "Needs attention"], leaderRows,
            ["center", "left", "right", "left", "right", "right", "right"],
            scored.map(s => s.kpiPct >= 90 ? "success" : s.kpiPct >= 70 ? "warning" : "danger"),
            { markerCol: 1 })}
        </div>` : ""}

        <div class="grid-2">
          <div class="card">
            <div class="card-head">
              <span class="card-icon success">${icon("pie", "ic-sm")}</span>
              <div class="card-title">AM Share Of Elite</div>
            </div>
            ${tableHtml(["AM", "Purchase $", "Share", "Purchased Of Portfolio"], shareRows,
              ["left", "right", "right", "right"], AM_SHARES.map(() => "success"), { markerCol: 1 })}
          </div>
          ${segmentCard()}
        </div>

        <div class="card">
          <div class="card-head">
            <span class="card-icon info">${icon("list", "ic-sm")}</span>
            <div><div class="card-title">AM Overview</div>
            <div class="card-sub">Click an AM to open their board</div></div>
          </div>
          ${tableHtml(
            ["AM", "Purchase $", "Purchased Of Portfolio", "Open Tickets", "Take A Break",
             "Locked", "Pending RD", "Birthdays", "Top 20 Decline"],
            ovRows, ["left", "right", "right", "right", "right", "right", "right", "right", "right"],
            OVERVIEW.map(() => "success"), { markerCol: 1 })}
        </div>
      </div>`;
    }

    function gateHtml() {
      return `<div class="gate">
        <div class="gate-mark">${icon("key", "ic-xl")}</div>
        <h2>Manager Dashboard</h2>
        <p>Cross-AM revenue, goals and risk roll-up. Enter the passcode to view.</p>
        <input type="password" id="gateInput" placeholder="••••••" autocomplete="off" spellcheck="false">
        <div class="err">${esc(app.gateError)}</div>
        <button type="button" class="btn primary" id="gateSubmit" style="width:100%;justify-content:center">
          ${icon("unlock", "ic-sm")} Unlock
        </button>
      </div>`;
    }

    /* ---------------- chrome ---------------- */
    function navCount(viewId) {
      const v = VIEWS[viewId];
      if (!v || !v.key) return null;
      return rowsFor(v.key).length;
    }
    function countTone(viewId, n) {
      if (!n) return "";
      if (["top20", "rd", "locks", "rdfirst"].includes(viewId)) return "warm";
      if (["top10", "birthdays"].includes(viewId)) return "good";
      return "";
    }
    function sidebar() {
      const visible = NAV_ORDER.filter(id => !(VIEWS[id].managerOnly && SINGLE_AM));
      let nav = "";
      for (const group of GROUP_ORDER) {
        const items = visible.filter(id => VIEWS[id].group === group);
        if (!items.length) continue;
        nav += `<div class="side-group-title">${esc(group)}</div>`;
        nav += items.map(id => {
          const v = VIEWS[id];
          const n = navCount(id);
          return `<button type="button" class="nav-item ${app.view === id ? "active" : ""}" data-go="${esc(id)}">
            ${icon(v.icon)}
            <span class="side-label">${esc(v.short || v.label)}</span>
            ${v.gated && !app.unlocked ? icon("lock", "ic-xs")
              : (n !== null ? `<span class="nav-count ${countTone(id, n)}">${n}</span>` : "")}
          </button>`;
        }).join("");
      }
      const amSwitch = (!SINGLE_AM && AM_ORDER.length > 1) ? `<div class="am-switch">
        <div class="am-switch-title">Account Manager</div>
        <div class="am-chips">${AM_ORDER.map(name =>
          `<button type="button" class="am-chip ${app.agent === name ? "active" : ""}" data-agent="${esc(name)}">${esc(name)}</button>`
        ).join("")}</div>
      </div>` : "";

      return `<aside class="sidebar">
        <div class="brand">
          <span class="brand-mark">${icon("spark", "ic-lg")}</span>
          <div class="brand-text">
            <div class="brand-title">${esc(REPORT.title || "Elite AM Brief")}</div>
            <div class="brand-sub">${esc(REPORT.subtitle || "")}</div>
          </div>
        </div>
        ${amSwitch}
        <nav class="side-nav">${nav}</nav>
        <div class="side-foot">
          ${SINGLE_AM ? esc(app.agent) + " · personal board" : "Manager view · all AMs"}<br>
          Report date ${esc(REPORT.date || "")}
        </div>
      </aside>`;
    }

    /* ---------- archive calendar ----------
       ARCHIVE is written by the generator from the files actually on disk, so a
       day only becomes clickable once its report exists. Nothing is computed
       from date arithmetic here: a skipped Friday must not produce a dead link. */
    const ARCHIVE = REPORT.archive || [];
    const ARCHIVE_BY_DATE = new Map(ARCHIVE.map(a => [a.d, a.f]));
    const ARCHIVE_MONTHS = [...new Set(ARCHIVE.map(a => a.d.slice(0, 7)))].sort();
    const MONTH_NAMES = ["January","February","March","April","May","June",
      "July","August","September","October","November","December"];

    function shiftMonth(ym, delta) {
      const y = Number(ym.slice(0, 4));
      const m = Number(ym.slice(5, 7)) + delta;
      const d = new Date(Date.UTC(y, m - 1, 1));
      return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}`;
    }

    function calendarPopHtml() {
      const ym = app.calMonth || (REPORT.date || "").slice(0, 7);
      const year = Number(ym.slice(0, 4));
      const month = Number(ym.slice(5, 7));
      const firstDow = new Date(Date.UTC(year, month - 1, 1)).getUTCDay();
      const daysInMonth = new Date(Date.UTC(year, month, 0)).getUTCDate();
      const canPrev = ARCHIVE_MONTHS.some(m => m < ym);
      const canNext = ARCHIVE_MONTHS.some(m => m > ym);

      let cells = "";
      for (let i = 0; i < firstDow; i++) cells += `<span class="cal-day empty"></span>`;
      for (let d = 1; d <= daysInMonth; d++) {
        const iso = `${ym}-${String(d).padStart(2, "0")}`;
        const file = ARCHIVE_BY_DATE.get(iso);
        const isCurrent = iso === REPORT.date;
        if (file) {
          cells += `<button type="button" class="cal-day has${isCurrent ? " today" : ""}"
            data-cal-open="${esc(file)}" title="Open the brief for ${esc(iso)}">${d}</button>`;
        } else {
          cells += `<span class="cal-day" title="No brief for ${esc(iso)}">${d}</span>`;
        }
      }

      return `<div class="cal-pop" id="calPop">
        <div class="cal-head">
          <button type="button" class="cal-nav" data-cal-month="${esc(shiftMonth(ym, -1))}"
            ${canPrev ? "" : "disabled"} title="Previous month">${icon("chev-left", "ic-xs")}</button>
          <div class="cal-title">${esc(MONTH_NAMES[month - 1])} ${year}</div>
          <button type="button" class="cal-nav" data-cal-month="${esc(shiftMonth(ym, 1))}"
            ${canNext ? "" : "disabled"} title="Next month">${icon("chev-right", "ic-xs")}</button>
        </div>
        <div class="cal-grid">
          ${["S","M","T","W","T","F","S"].map(d => `<div class="cal-dow">${d}</div>`).join("")}
          ${cells}
        </div>
        <div class="cal-foot">${ARCHIVE.length
          ? `${ARCHIVE.length} brief${ARCHIVE.length === 1 ? "" : "s"} saved. Highlighted days have a report; the rest were not generated.`
          : "No other briefs saved yet — history starts from this one."}</div>
      </div>`;
    }

    function topbar() {
      const v = VIEWS[app.view] || VIEWS.home;
      const isManager = !!v.managerOnly;
      const who = isManager ? "All AMs" : app.agent;
      return `<header class="topbar">
        <button type="button" class="icon-btn" id="toggleSidebar" title="Toggle menu">${icon("panel", "ic-sm")}</button>
        <div class="crumb">
          <div class="crumb-top">${esc(v.group)}</div>
          <div class="crumb-title">${icon(v.icon, "ic-lg")}${esc(v.label)}</div>
        </div>
        <div class="spacer"></div>
        <div class="cal-wrap">
          <button type="button" class="cal-btn" id="calBtn" title="Open another day's brief">
            ${icon("calendar", "ic-sm")}${esc(REPORT.subtitle || REPORT.date || "")}
          </button>
          ${app.calOpen ? calendarPopHtml() : ""}
        </div>
        <button type="button" class="icon-btn" id="printBtn" title="Print / save as PDF">${icon("printer", "ic-sm")}</button>
        <div class="who">
          <span class="who-dot">${esc(isManager ? "ALL" : initials(who))}</span>
          <div><div class="who-name">${esc(who)}</div>
          <div class="who-role">${esc(v.sub || "")}</div></div>
        </div>
      </header>`;
    }

    const VIEW_FN = {
      dashboard: viewDashboard, team: viewTeamGoals, home: viewHome, goals: viewGoals,
      top10: viewTop10, top20: viewTop20, rd: viewPendingRd, rdfirst: viewFirstRd,
      tickets: viewTickets, locks: viewLocks, birthdays: viewBirthdays,
    };

    /* ---------------- ticket modal ---------------- */
    function renderModal() {
      const root = document.getElementById("modalRoot");
      const p = app.ticket;
      if (!p) { root.innerHTML = ""; return; }
      root.innerHTML = `<div class="modal-backdrop" id="backdrop">
        <div class="modal-card" id="card">
          <div class="modal-head">
            <span class="card-icon">${icon("ticket", "ic-sm")}</span>
            <div>
              <div class="card-title">Zendesk draft · ${esc(p.name)}</div>
              <div class="card-sub">AID ${esc(p.aid)} · review only, nothing is auto-sent</div>
            </div>
            <div class="spacer"></div>
            <button type="button" class="icon-btn" id="closeX">${icon("x", "ic-sm")}</button>
          </div>
          <div class="modal-body">
            <div class="field-label">Subject</div>
            <input type="text" id="tSubject" value="${esc(p.ticketSubject || "")}">
            <div class="field-label">Message</div>
            <textarea id="tBody" rows="11">${esc(p.ticketBody || "")}</textarea>
          </div>
          <div class="modal-foot">
            <button type="button" class="btn" id="copySubject">${icon("copy", "ic-xs")} Subject</button>
            <button type="button" class="btn" id="copyBody">${icon("copy", "ic-xs")} Message</button>
            <button type="button" class="btn" id="copyBoth">${icon("copy", "ic-xs")} Both</button>
            <div class="spacer"></div>
            <button type="button" class="btn primary" id="openZd">${icon("external", "ic-xs")} Open Zendesk</button>
          </div>
        </div>
      </div>`;
      const close = () => { app.ticket = null; render(); };
      const val = id => document.getElementById(id).value;
      const copy = (text, what) => { navigator.clipboard.writeText(text); toast(what + " copied"); };
      document.getElementById("backdrop").onclick = e => { if (e.target.id === "backdrop") close(); };
      document.getElementById("closeX").onclick = close;
      document.getElementById("copySubject").onclick = () => copy(val("tSubject"), "Subject");
      document.getElementById("copyBody").onclick = () => copy(val("tBody"), "Message");
      document.getElementById("copyBoth").onclick = () =>
        copy(`Subject: ${val("tSubject")}\n\n${val("tBody")}`, "Subject + message");
      document.getElementById("openZd").onclick = () => {
        if (p.zendeskUrl) window.open(p.zendeskUrl, "_blank", "noopener,noreferrer");
      };
    }

    /* ---------------- binding ---------------- */
    function bind() {
      const calBtn = document.getElementById("calBtn");
      if (calBtn) calBtn.onclick = e => {
        e.stopPropagation();
        app.calOpen = !app.calOpen;
        if (app.calOpen) app.calMonth = (REPORT.date || "").slice(0, 7);
        render();
      };
      document.querySelectorAll("[data-cal-month]").forEach(el => {
        el.onclick = e => {
          e.stopPropagation();
          app.calMonth = el.getAttribute("data-cal-month");
          render();
        };
      });
      /* Sibling file in the same folder, so the archive works from a network
         share or a copied folder with no server involved. */
      document.querySelectorAll("[data-cal-open]").forEach(el => {
        el.onclick = () => { window.location.href = el.getAttribute("data-cal-open"); };
      });
      const calPop = document.getElementById("calPop");
      if (calPop) calPop.onclick = e => e.stopPropagation();
      document.querySelectorAll("[data-go]").forEach(el => {
        el.onclick = () => go(el.getAttribute("data-go"));
      });
      document.querySelectorAll("[data-agent]").forEach(el => {
        el.onclick = () => {
          app.agent = el.getAttribute("data-agent");
          if (app.view === "dashboard") app.view = "home";
          render();
          window.scrollTo({ top: 0, behavior: "auto" });
        };
      });
      document.querySelectorAll("input[data-state]").forEach(el => {
        el.oninput = () => setState(el.getAttribute("data-state"), el.value);
      });
      document.querySelectorAll("select[data-state]").forEach(el => {
        el.onchange = () => setState(el.getAttribute("data-state"), el.value);
      });
      document.querySelectorAll("[data-reason-state]").forEach(el => {
        el.onclick = () => setState(el.getAttribute("data-reason-state"), el.getAttribute("data-reason"));
      });
      document.querySelectorAll("[data-page-key]").forEach(el => {
        el.onclick = () => {
          setPage(el.getAttribute("data-page-key"), Number(el.getAttribute("data-page")));
        };
      });
      document.querySelectorAll("[data-ticket-aid]").forEach(el => {
        el.onclick = () => {
          const aid = el.getAttribute("data-ticket-aid");
          const b = agentBlock();
          const pool = [...(b.decline || []), ...(b.rdFirstTime || []), ...(b.birthdays || [])];
          const p = pool.find(x => String(x.aid) === aid);
          if (p) { app.ticket = p; render(); }
        };
      });

      const toggle = document.getElementById("toggleSidebar");
      if (toggle) toggle.onclick = () => {
        if (window.matchMedia("(max-width: 900px)").matches) app.mobileOpen = !app.mobileOpen;
        else app.collapsed = !app.collapsed;
        render();
      };
      const printBtn = document.getElementById("printBtn");
      if (printBtn) printBtn.onclick = () => window.print();

      const gateInput = document.getElementById("gateInput");
      if (gateInput) {
        const submit = () => {
          if (gateToken(gateInput.value) === GATE_TOKEN) {
            app.unlocked = true;
            app.gateError = "";
            rememberGate();
          } else {
            app.gateError = "That passcode does not match.";
          }
          render();
        };
        gateInput.onkeydown = e => { if (e.key === "Enter") submit(); };
        document.getElementById("gateSubmit").onclick = submit;
        if (!app.gateError) gateInput.focus();
      }

      /* Full re-render on every keystroke would otherwise drop the caret. */
      const focusKey = takeFocusKey();
      if (focusKey) {
        const el = document.querySelector(`[data-state="${CSS.escape(focusKey)}"]`);
        if (el && el.tagName === "INPUT") {
          el.focus();
          const end = el.value.length;
          try { el.setSelectionRange(end, end); } catch (e) { /* type doesn't support it */ }
        }
      }
    }

    function render() {
      /* An AM with no goals (Alon) must not sit on a Goals view. */
      if (app.view === "goals" && !(agentBlock().goals)) app.view = "home";
      if (VIEWS[app.view] && VIEWS[app.view].managerOnly && SINGLE_AM) app.view = "home";

      const body = (VIEW_FN[app.view] || viewHome)();
      document.getElementById("root").innerHTML = `<div class="app${app.collapsed ? " collapsed" : ""}${app.mobileOpen ? " mobile-open" : ""}">
        ${sidebar()}
        <div class="main">
          ${topbar()}
          <div class="content">${body}</div>
        </div>
      </div>`;
      document.title = `${REPORT.title || "Elite AM Brief"} · ${REPORT.date || ""}`;
      bind();
      renderModal();
    }

    /* Bound once on document, not re-bound per render: clicking anywhere off the
       calendar closes it, as does Escape. */
    document.addEventListener("click", () => {
      if (app.calOpen) { app.calOpen = false; render(); }
    });
    document.addEventListener("keydown", e => {
      if (e.key === "Escape" && app.calOpen) { app.calOpen = false; render(); }
    });

    setRenderHook(render);
    render();
  