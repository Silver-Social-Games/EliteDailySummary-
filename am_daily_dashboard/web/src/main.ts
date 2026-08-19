// @ts-nocheck
import { AM_ORDER, GATE_TOKEN, REPORT, SINGLE_AM } from "./payload";
import { app, gateToken, go, rememberGate, setPage, setRenderHook, setState,
  takeFocusKey } from "./state";
import { agentBlock, rowsFor } from "./selectors";
import { esc, icon, initials } from "./format";
import { toast } from "./toast";
import { GROUP_ORDER, NAV_ORDER, VIEW_FN, VIEWS } from "./registry";
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

      const body = (VIEW_FN[app.view] || VIEW_FN.home)();
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
  