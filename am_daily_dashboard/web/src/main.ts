// @ts-nocheck

    "use strict";

    /* Parsed from a <script type="application/json"> block rather than
       inlined as a JS object literal: a raw U+2028 or U+2029 in any payload
       field is a syntax error inside a literal but legal inside JSON text.
       html_export.py still escapes "</" - inside a JSON block a literal
       </script> would end the element early just the same. */
    const DATA = JSON.parse(
      document.getElementById("am-brief-payload").textContent
    );
    const REPORT     = DATA.report || {};
    const OVERVIEW   = DATA.overview || [];
    const AGENTS     = DATA.agents || [];
    const AM_SHARES  = DATA.amShares || [];
    const AM_ORDER   = DATA.amOrder || [];
    const SINGLE_AM  = !!DATA.singleAm;
    /* Manager-only: the four books measured as one against the manager's own
       targets. Absent from every per-AM payload by construction. */
    const TEAM_GOALS = DATA.teamGoals || null;
    /* Fallback matches config.manager_gate_token("elite") so briefs generated
       before the gate existed still open the Dashboard. */
    const GATE_TOKEN = DATA.managerGate || "09dcfdd4";

    const day      = REPORT.weekday || "";
    const dayShort = REPORT.dayShort || day.slice(0, 3);
    const TITLES = {
      thisPurchase:  `This ${day} Purchase`,
      priorPurchase: `Prior ${day} Purchase`,
      purchase7d:    "7D Purchase",
      lifetimePurchase: "LT Purchase",
      lifetimeHold:  "Lifetime Hold",
      favouriteGame7d: "Favourite Game (7D)",
    };
    const URGENCY_RANK = { Today: 0, "48h": 1, Watch: 2, None: 3 };
    const REASON_EMPHASIS = [
      "Redemption Blocked", "Redemption in progress", "Needs ", "Same weekday skip",
      "Spend Softening", "Offline Since", "Pending RD", "RD $", "Redeem Status ",
      "Take a break", "No Purchases", "Played Today", "Account locked", "Red flag",
    ];
    const PAGE_SIZES = [25, 50, 100];
    const PAGINATE_ABOVE = 25;

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

    /* ---------------- state ---------------- */
    /* Storage access throws outright where the origin is opaque — a sandboxed
       preview pane, or a file opened through some OneDrive/Office viewers. An
       unguarded read at state init would blank the whole board, so failing to
       remember the unlock is the worst this may cost. */
    const GATE_KEY = "eliteAmBriefUnlocked";
    function gateRemembered() {
      try { return sessionStorage.getItem(GATE_KEY) === GATE_TOKEN; }
      catch (e) { return false; }
    }
    function rememberGate() {
      try { sessionStorage.setItem(GATE_KEY, GATE_TOKEN); } catch (e) {}
    }
    const firstAgent = (AGENTS[0] && AGENTS[0].agentName) || AM_ORDER[0] || "";
    const app = {
      view: SINGLE_AM ? "home" : "dashboard",
      agent: SINGLE_AM ? (DATA.singleAmName || firstAgent) : firstAgent,
      unlocked: gateRemembered(),
      gateError: "",
      collapsed: false,
      mobileOpen: false,
      ticket: null,
      calOpen: false,
      calMonth: (REPORT.date || "").slice(0, 7),
    };
    const tstate = {};
    let focusKey = null;

    function getState(key, fallback) {
      if (!(key in tstate)) tstate[key] = fallback;
      return tstate[key];
    }
    /* Any control that changes the result set sends the table back to page 1 —
       otherwise a search that narrows 260 rows to 3 lands you on an empty page 7. */
    const RESET_SUFFIXES = ["_q", "_search", "_sort", "_sortBy", "_agent", "_reason", "_size"];
    function setState(key, value) {
      tstate[key] = value;
      for (const suffix of RESET_SUFFIXES) {
        if (key.endsWith(suffix)) { tstate[key.slice(0, -suffix.length) + "_page"] = 1; break; }
      }
      focusKey = key;
      render();
    }
    function go(view) {
      app.view = view;
      app.mobileOpen = false;
      render();
      window.scrollTo({ top: 0, behavior: "auto" });
    }

    /* ---------------- helpers ---------------- */
    function esc(s) {
      return String(s ?? "")
        .replace(/&/g, "&amp;").replace(/</g, "&lt;")
        .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }
    function icon(name, cls) {
      return `<svg class="ic ${cls || ""}" aria-hidden="true"><use href="#i-${name}"></use></svg>`;
    }
    function gateToken(s) {
      let h = 5381;
      for (const ch of String(s)) h = (((h * 33) >>> 0) ^ ch.codePointAt(0)) >>> 0;
      return h.toString(16).padStart(8, "0");
    }
    function toNum(v) {
      const n = parseFloat(String(v ?? "").replace(/[^0-9.\-]/g, ""));
      return Number.isNaN(n) ? 0 : n;
    }
    function money(n) { return "$" + Math.round(n).toLocaleString(); }
    function compactMoney(n) {
      const a = Math.abs(n);
      if (a >= 1e6) return "$" + (n / 1e6).toFixed(a >= 1e7 ? 0 : 1) + "M";
      if (a >= 1e4) return "$" + Math.round(n / 1e3) + "K";
      return money(n);
    }
    function agentBlock() { return AGENTS.find(a => a.agentName === app.agent) || AGENTS[0] || {}; }
    function rowsFor(key) { return (agentBlock()[key]) || []; }
    function initials(name) {
      return String(name || "?").trim().split(/\s+/).map(w => w[0]).join("").slice(0, 2).toUpperCase();
    }
    function toast(msg) {
      const root = document.getElementById("toastRoot");
      root.innerHTML = `<div class="toast">${icon("check", "ic-sm")}${esc(msg)}</div>`;
      clearTimeout(toast._t);
      toast._t = setTimeout(() => { root.innerHTML = ""; }, 1800);
    }

    function marker(tone) { return `<span class="marker marker-${tone || "neutral"}"></span>`; }
    function markerCell(tone, content) {
      return `<span class="cell-marker">${marker(tone)}<span>${content}</span></span>`;
    }
    function wowHtml(value) {
      const v = String(value || "").trim();
      const pct = (v.match(/\(([+-]?\d+(?:\.\d+)?)%\)/) || [])[1];
      const n = pct != null ? Number(pct) : NaN;
      const up = (!Number.isNaN(n) && n > 0) || (v.startsWith("+") && !v.startsWith("+$0") && !v.startsWith("+0"));
      const down = (!Number.isNaN(n) && n < 0) || v.startsWith("-") || v.startsWith("$-");
      if (up) return `<span class="t-success w-semibold">${icon("trend-up", "ic-xs")} ${esc(value)}</span>`;
      if (down) return `<span class="t-danger w-semibold">${icon("trend-down", "ic-xs")} ${esc(value)}</span>`;
      return esc(value);
    }
    function moneyHtml(value, emphasize) {
      return emphasize ? `<span class="t-danger w-semibold">${esc(value)}</span>` : esc(value);
    }
    function holdHtml(value) {
      const pct = parseFloat(value);
      return (!Number.isNaN(pct) && pct >= 70)
        ? `<span class="t-success w-semibold">${esc(value)}</span>` : esc(value);
    }
    function unlockHtml(detail, remainingDays) {
      if (!detail) return '<span class="t-quaternary">—</span>';
      const urgent = typeof remainingDays === "number" && remainingDays <= 0;
      return urgent
        ? `<span class="t-danger w-semibold">${icon("alert", "ic-xs")} ${esc(detail)}</span>`
        : esc(detail);
    }
    function agingHtml(created, daysPending, agingFlag) {
      const suffix = typeof daysPending === "number" ? ` (${daysPending}d ago)` : "";
      return agingFlag
        ? `<span class="t-small t-danger w-semibold">${icon("clock", "ic-xs")} ${esc(created)}${esc(suffix)}</span>`
        : `<span class="t-small">${esc(created)}${esc(suffix)}</span>`;
    }
    /* Two-track score meter. The KPI track fills to kpiPoints/kpiPointsMax; the
       manager track stays dashed and empty until a score exists, because an
       unset appreciation is neither 0 nor 20. */
    function scoreMeterHtml(score, tone) {
      const kpiMax = Number(score.kpiPointsMax) || 0;
      const kpiPct = kpiMax > 0 ? Math.max(0, Math.min(100, Number(score.kpiPoints) / kpiMax * 100)) : 0;
      const scored = !!score.managerScored;
      const mgrMax = Number(score.managerPointsMax) || 0;
      const mgrPct = scored && mgrMax > 0
        ? Math.max(0, Math.min(100, Number(score.managerPoints) / mgrMax * 100)) : 0;
      return `<div class="score-meter">
        <span class="trk kpi"><span class="fill ${tone}" style="width:${kpiPct.toFixed(2)}%"></span></span>
        <span class="trk mgr${scored ? "" : " pending"}">${
          scored ? `<span class="fill mgr" style="width:${mgrPct.toFixed(2)}%"></span>` : ""
        }</span>
      </div>`;
    }
    function scoreLegendHtml(score, tone) {
      const scored = !!score.managerScored;
      return `<div class="score-legend">
        <span><i class="lg-${tone}"></i>KPI ${esc(score.kpiPointsDisplay || "")}</span>
        <span><i class="lg-mgr"></i>Manager ${esc(score.managerPointsDisplay || "Pending")}</span>
        ${scored && score.managerNote ? `<span class="t-tertiary">${esc(score.managerNote)}</span>` : ""}
      </div>`;
    }
    function bigWinHtml(p) {
      const won = p.wonYesterday || "—";
      return p.bigWinner
        ? `<span class="t-small t-danger w-semibold">${icon("trend-up", "ic-xs")} ${esc(won)} · Big Winner</span>`
        : `<span class="t-small t-tertiary">${esc(won)}</span>`;
    }
    /* Blank when nothing is flagged. No missing-document ticket is not proof the
       documents are complete, so this stays silent rather than showing an
       all-clear an AM might repeat to a player awaiting a withdrawal. */
    function docsHtml(status) {
      if (!status) return `<span class="t-quaternary">—</span>`;
      return `<span class="t-small t-warning w-semibold">${esc(status)}</span>`;
    }
    function p7dHtml(value) {
      const none = value === "None In 7D";
      return `<span class="p7d-cell ${none ? "t-warning w-semibold" : ""}">${esc(value)}</span>`;
    }
    function urgencyHtml(u) {
      if (u === "Today") return `<span class="badge danger">${icon("zap", "ic-xs")}Today</span>`;
      if (u === "48h") return `<span class="badge warning">48h</span>`;
      if (u === "Watch") return `<span class="badge info">Watch</span>`;
      return `<span class="t-quaternary">${esc(u || "—")}</span>`;
    }
    function aidHtml(p) {
      const aid = esc(p.aid);
      return p.aidUrl
        ? `<a href="${esc(p.aidUrl)}" target="_blank" rel="noopener noreferrer">${aid}</a>` : aid;
    }
    function richText(text, lead) {
      const parts = String(text || "").split(/(\*\*[^*]+\*\*)/g);
      const inner = parts.map(part =>
        (part.startsWith("**") && part.endsWith("**") && part.length >= 4)
          ? `<em>${esc(part.slice(2, -2))}</em>` : esc(part)
      ).join("");
      return `<div class="hero-line ${lead ? "lead" : ""}">${inner}</div>`;
    }
    function sortBySoonestUnlock(rows) {
      return (rows || []).slice().sort((a, b) => {
        const av = a.unlockRemainingDays, bv = b.unlockRemainingDays;
        if (av == null && bv == null) return 0;
        if (av == null) return 1;
        if (bv == null) return -1;
        return av - bv;
      });
    }
    function sortByNumKey(rows, key, desc) {
      const d = desc !== false;
      return (rows || []).slice().sort((a, b) => {
        const av = Number(a[key]), bv = Number(b[key]);
        if (Number.isNaN(av) && Number.isNaN(bv)) return 0;
        if (Number.isNaN(av)) return 1;
        if (Number.isNaN(bv)) return -1;
        return d ? bv - av : av - bv;
      });
    }
    function sortPlayers(rows, mode) {
      const copy = [...rows];
      if (mode === "priorHigh") return copy.sort((a, b) => (b.priorPriorNum || 0) - (a.priorPriorNum || 0));
      if (mode === "lifetimeHigh") return copy.sort((a, b) => (b.lifetimePurchasedNum || 0) - (a.lifetimePurchasedNum || 0));
      if (mode === "gapHigh") return copy.sort((a, b) => (b.sortGap || 0) - (a.sortGap || 0));
      return copy.sort((a, b) => {
        const ra = URGENCY_RANK[a.urgency] ?? 9, rb = URGENCY_RANK[b.urgency] ?? 9;
        return ra !== rb ? ra - rb : (b.sortGap || 0) - (a.sortGap || 0);
      });
    }
    function matchesDecline(row, q) {
      if (!q.trim()) return true;
      const s = q.trim().toLowerCase();
      return [row.name, row.aid, row.agent, row.agentName, row.reason, row.reasonTable,
              row.purchase7d, row.favouriteGame7d, row.recommendation]
        .some(v => String(v || "").toLowerCase().includes(s));
    }
    function matchesAid(row, q, extraKeys) {
      if (!q.trim()) return true;
      const s = q.trim().toLowerCase();
      if (String(row.name || "").toLowerCase().includes(s) || String(row.aid || "").includes(s)) return true;
      return (extraKeys || []).some(k => String(row[k] ?? "").toLowerCase().includes(s));
    }

    /* ---------------- reason / action icons (SVG, not emoji) ---------------- */
    function reasonPartIcon(part) {
      const pl = part.toLowerCase();
      if (part.startsWith("Red flag")) return "flag";
      if (part.startsWith("Redemption Blocked")) return "ban";
      if (part.startsWith("Redemption in progress")) return "hourglass";
      if (part.startsWith("Account locked") || part.includes("Suspended")) return "lock";
      if (part.startsWith("Needs Recent Acceptable POA") || pl.includes("poa")) return "file";
      if (part.startsWith("Needs KYC") || pl.includes("verification document")) return "clipboard";
      if (part.startsWith("RD $") || part.startsWith("Pending RD")) return "banknote";
      if (part.startsWith("Same weekday skip")) return "calendar";
      if (part.startsWith("Payment failed")) return "x-circle";
      if (part.startsWith("No Purchases")) return "alert";
      if (part.startsWith("Played Today")) return "slots";
      if (part.startsWith("Redeem Status")) return "clipboard";
      if (part.startsWith("Take a break")) return "clock";
      if (part.startsWith("Spend Softening")) return "trend-down";
      return "";
    }
    function actionHeadIcon(head) {
      const hl = head.toLowerCase();
      if (head.startsWith("Escalate Ops")) return "arrow-right";
      if (head.startsWith("Escalate Compliance")) return "scale";
      if (head.startsWith("Push purchase")) return "dollar";
      if (head.startsWith("Fix payment method")) return "card";
      if (head.startsWith("Remove restriction")) return "unlock";
      if (head.startsWith("Send to Ops")) return "wrench";
      if (head.startsWith("Soft check-in")) return "message";
      if (head.startsWith("Agent call") || head.startsWith("Reactivation")) return "phone";
      if (head.startsWith("No action")) return "check-circle";
      if (hl.includes("no outreach") || hl.includes("no purchase push")) return "hand";
      return "";
    }
    function reasonPartClass(part) {
      if (part.startsWith("Red flag")) return "t-danger w-semibold";
      if (part.startsWith("Needs ") || part.includes("Blocked")) return "t-warning w-semibold";
      if (part.startsWith("Escalate") || part.includes("Suspended")) return "t-danger w-semibold";
      if (part.startsWith("Same weekday skip") || part.startsWith("Played Today")) return "t-info";
      return "";
    }
    function renderReason(parts, text) {
      const segments = (parts && parts.length)
        ? parts
        : String(text || "").split("●").map(p => p.trim()).filter(Boolean);
      return segments.map((part, i) => {
        const emphasize = i === 0 || REASON_EMPHASIS.some(pfx => part.startsWith(pfx));
        const name = reasonPartIcon(part);
        const cls = emphasize ? (reasonPartClass(part) || "w-semibold") : "";
        const sep = i > 0 ? '<span class="sep">·</span>' : "";
        return sep + `<span class="${cls}">${name ? icon(name, "ic-xs") + " " : ""}${esc(part)}</span>`;
      }).join("");
    }
    function renderAction(text) {
      const chunks = String(text || "").split(" · ").filter(Boolean);
      const head = chunks[0] || text || "";
      const tail = chunks.slice(1).join(" · ");
      const name = actionHeadIcon(head);
      return `<span class="w-semibold">${name ? icon(name, "ic-xs") + " " : ""}${esc(head)}</span>`
           + (tail ? `<span class="t-tertiary"> · ${esc(tail)}</span>` : "");
    }
    function ticketHtml(p) {
      if (!p.ticketEnabled) {
        return p.ticketDisabledReason
          ? `<span class="badge">${icon("lock", "ic-xs")}${esc(p.ticketDisabledReason)}</span>`
          : '<span class="t-quaternary">—</span>';
      }
      const subj = p.ticketSubject || "";
      const preview = subj.length > 30 ? subj.slice(0, 29) + "…" : (subj || "Draft");
      return `<div><button type="button" class="chip" data-ticket-aid="${esc(p.aid)}">`
           + `${icon("ticket", "ic-xs")} Draft</button>`
           + `<div class="ticket-preview">${esc(preview)}</div></div>`;
    }
    function ticketIdsHtml(p) {
      const list = p.tickets || [];
      if (!list.length) return `<span class="t-quaternary">${esc(p.ticketIds || "—")}</span>`;
      return list.map((t, i) =>
        `${i ? ", " : ""}<a href="${esc(t.url)}" target="_blank" rel="noopener noreferrer">${esc(t.id)}</a>`
      ).join("");
    }

    /* ---------------- table + pagination ---------------- */
    function tableHtml(headers, rows, align, tones, opts) {
      opts = opts || {};
      const th = headers.map((h, i) => {
        const a = (align && align[i]) || "left";
        return `<th class="${a === "right" ? "num" : a === "center" ? "center" : ""}">${esc(h)}</th>`;
      }).join("");
      const body = rows.length
        ? rows.map((cells, ri) => {
            const tone = (tones && tones[ri]) || "neutral";
            const isTotal = opts.totalRowIndex === ri;
            const tds = cells.map((c, i) => {
              const a = (align && align[i]) || "left";
              const cls = a === "right" ? "num" : a === "center" ? "center" : "";
              const content = (opts.markerCol === i && !isTotal) ? markerCell(tone, c) : c;
              return `<td class="${cls}">${content}</td>`;
            }).join("");
            return `<tr class="${isTotal ? "total-row" : ""}">${tds}</tr>`;
          }).join("")
        : `<tr><td colspan="${headers.length}" class="empty">${esc(opts.empty || "Nothing to show here.")}</td></tr>`;
      return `<div class="table-frame ${opts.frameClass || ""}">`
           + `<table class="grid ${opts.tableClass || ""}"><thead><tr>${th}</tr></thead>`
           + `<tbody>${body}</tbody></table></div>`;
    }

    /* Returns the visible slice plus the pager markup for it. */
    function paginate(rows, stateKey, forceOn) {
      const total = rows.length;
      const on = forceOn || total > PAGINATE_ABOVE;
      if (!on) return { slice: rows, pager: "", from: total ? 1 : 0, to: total, total };
      const sizeKey = stateKey + "_size", pageKey = stateKey + "_page";
      const raw = getState(sizeKey, String(PAGE_SIZES[0]));
      const size = raw === "all" ? total : Number(raw) || PAGE_SIZES[0];
      const pages = Math.max(1, Math.ceil(total / size));
      const page = Math.min(Math.max(1, Number(getState(pageKey, 1)) || 1), pages);
      tstate[pageKey] = page;
      const start = (page - 1) * size;
      const slice = rows.slice(start, start + size);
      const from = total ? start + 1 : 0;
      const to = Math.min(start + size, total);

      const btn = (label, target, disabled, extraCls) =>
        `<button type="button" class="pg ${extraCls || ""}" data-page-key="${esc(pageKey)}" `
        + `data-page="${target}"${disabled ? " disabled" : ""}>${label}</button>`;

      let nums = "";
      if (pages > 1) {
        const window_ = new Set([1, pages, page, page - 1, page + 1]);
        if (page <= 3) [2, 3, 4].forEach(n => window_.add(n));
        if (page >= pages - 2) [pages - 1, pages - 2, pages - 3].forEach(n => window_.add(n));
        const list = [...window_].filter(n => n >= 1 && n <= pages).sort((a, b) => a - b);
        let prev = 0;
        for (const n of list) {
          if (prev && n - prev > 1) nums += `<span class="pg-gap">…</span>`;
          nums += btn(String(n), n, false, n === page ? "active" : "");
          prev = n;
        }
      }
      const sizeSel = `<span class="select-wrap"><select data-state="${esc(sizeKey)}">`
        + PAGE_SIZES.map(n => `<option value="${n}" ${raw === String(n) ? "selected" : ""}>${n} per page</option>`).join("")
        + `<option value="all" ${raw === "all" ? "selected" : ""}>Show all (${total})</option>`
        + `</select>${icon("chev-down", "ic-xs")}</span>`;

      const pager = `<div class="pager">
        <div class="pager-info">Showing <strong>${from.toLocaleString()}–${to.toLocaleString()}</strong> of ${total.toLocaleString()}</div>
        <div class="spacer"></div>
        ${sizeSel}
        ${pages > 1 ? btn(icon("chevs-left", "ic-xs"), 1, page === 1) : ""}
        ${pages > 1 ? btn(icon("chev-left", "ic-xs"), page - 1, page === 1) : ""}
        ${nums}
        ${pages > 1 ? btn(icon("chev-right", "ic-xs"), page + 1, page === pages) : ""}
        ${pages > 1 ? btn(icon("chevs-right", "ic-xs"), pages, page === pages) : ""}
      </div>`;
      return { slice, pager, from, to, total };
    }

    /* Generic search + sort + paginate section rendered as a card. */
    function tableCard(opts) {
      const all = opts.rows || [];
      const searchEnabled = opts.showSearch !== false;
      const sortEnabled = !!(opts.sortOptions && opts.sortOptions.length && opts.sortFn);
      const qKey = opts.stateKey + "_q", sortKey = opts.stateKey + "_sort";
      const q = searchEnabled ? getState(qKey, "") : "";
      const sortBy = getState(sortKey, opts.defaultSort
        || (opts.sortOptions && opts.sortOptions[0] ? opts.sortOptions[0].value : ""));

      const searched = searchEnabled ? all.filter(r => matchesAid(r, q, opts.extraKeys || [])) : all;
      const ordered = opts.sortFn ? opts.sortFn(searched, sortBy) : searched;
      const { slice, pager, total } = paginate(ordered, opts.stateKey);

      const filtered = q.trim() !== "";
      const countBadge = filtered
        ? `<span class="badge brand">${ordered.length} of ${all.length}</span>`
        : `<span class="badge">${all.length} ${all.length === 1 ? "player" : "players"}</span>`;

      const toolbar = (searchEnabled || sortEnabled) ? `<div class="toolbar">
        ${searchEnabled ? `<label class="search">${icon("search", "ic-sm")}
          <input type="search" placeholder="Search name, AID…" value="${esc(q)}" data-state="${esc(qKey)}">
        </label>` : ""}
        ${sortEnabled ? `<span class="select-wrap"><select data-state="${esc(sortKey)}">`
          + opts.sortOptions.map(o => `<option value="${esc(o.value)}" ${sortBy === o.value ? "selected" : ""}>${esc(o.label)}</option>`).join("")
          + `</select>${icon("chev-down", "ic-xs")}</span>` : ""}
        <div class="spacer"></div>
        ${countBadge}
      </div>` : "";

      return `<div class="card">
        ${toolbar}
        ${tableHtml(opts.headers, slice.map(opts.renderRow), opts.align,
                    slice.map(r => r.tone || "neutral"),
                    { markerCol: opts.markerCol, empty: opts.empty, tableClass: opts.tableClass,
                      frameClass: opts.compact ? "compact" : "" })}
        ${total ? pager : ""}
      </div>`;
    }

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
          tstate[el.getAttribute("data-page-key")] = Number(el.getAttribute("data-page"));
          focusKey = null;
          render();
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
      if (focusKey) {
        const el = document.querySelector(`[data-state="${CSS.escape(focusKey)}"]`);
        if (el && el.tagName === "INPUT") {
          el.focus();
          const end = el.value.length;
          try { el.setSelectionRange(end, end); } catch (e) { /* type doesn't support it */ }
        }
        focusKey = null;
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

    render();
  