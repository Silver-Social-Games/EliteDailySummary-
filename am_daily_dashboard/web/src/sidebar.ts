/** Left navigation rail — groups, nav badges, and the AM switcher. */
import { AM_ORDER, REPORT, SINGLE_AM } from "./payload";
import { esc, icon } from "./format";
import { rowsFor } from "./selectors";
import { app } from "./state";
import { NAV_GROUPS, VIEWS } from "./registry";
import { logoImg } from "./logos";

function navCount(viewId: string): number | null {
  const v = VIEWS[viewId];
  if (!v || !v.key || v.comingSoon) return null;
  return rowsFor(v.key).length;
}

function countTone(viewId: string, n: number): string {
  if (!n) return "";
  if (["top20", "rd", "locks", "rdfirst"].includes(viewId)) return "warm";
  if (["top10", "birthdays"].includes(viewId)) return "good";
  return "";
}

function navItem(id: string): string {
  const v = VIEWS[id];
  const n = navCount(id);
  const soon = v.comingSoon ? `<span class="nav-soon">Soon</span>` : "";
  return `<button type="button" class="nav-item ${app.view === id ? "active" : ""}${v.comingSoon ? " soon" : ""}" data-go="${esc(id)}">
        ${icon(v.icon)}
        <span class="side-label">${esc(v.short || v.label)}</span>
        ${v.gated && !app.unlocked ? icon("lock", "ic-xs")
          : soon || (n !== null ? `<span class="nav-count ${countTone(id, n)}">${n}</span>` : "")}
      </button>`;
}

export function sidebar(): string {
  let nav = "";
  for (const group of NAV_GROUPS) {
    const entries = group.entries.filter(
      (e) => e.kind !== "view" || !(VIEWS[e.id].managerOnly && SINGLE_AM)
    );
    if (!entries.length) continue;
    if (group.label) {
      nav += `<div class="side-group-title g-${group.accent || "neutral"}">${esc(group.label)}</div>`;
    }
    for (const entry of entries) {
      if (entry.kind === "section") {
        nav += `<div class="side-section-title">${esc(entry.label)}</div>`;
      } else {
        nav += navItem(entry.id);
      }
    }
  }
  const amSwitch = (!SINGLE_AM && AM_ORDER.length > 1) ? `<div class="am-switch">
        <div class="am-switch-title">Account Manager</div>
        <div class="am-chips">${AM_ORDER.map((name) =>
          `<button type="button" class="am-chip ${app.agent === name ? "active" : ""}" data-agent="${esc(name)}">${esc(name)}</button>`
        ).join("")}</div>
      </div>` : "";

  return `<aside class="sidebar">
        <div class="brand">
          <span class="brand-mark">${logoImg("elite", 32, "Elite Club")}</span>
          <div class="brand-text">
            <div class="brand-title">${esc(REPORT.title || "Elite Dashboard")}</div>
            <div class="brand-sub">${esc(REPORT.subtitle || "")}</div>
          </div>
        </div>
        <div class="brand-rule"></div>
        ${amSwitch}
        <nav class="side-nav">${nav}</nav>
        <div class="side-foot">
          ${SINGLE_AM ? esc(app.agent) + " · personal board" : "Manager view · all AMs"}<br>
          Report date ${esc(REPORT.date || "")}
        </div>
      </aside>`;
}
