/** Left navigation rail — groups, nav badges, and the AM switcher. */
import { AM_ORDER, REPORT, SINGLE_AM } from "./payload";
import { esc, icon } from "./format";
import { rowsFor } from "./selectors";
import { app } from "./state";
import { GROUP_ORDER, NAV_ORDER, VIEWS } from "./registry";

function navCount(viewId: string): number | null {
  const v = VIEWS[viewId];
  if (!v || !v.key) return null;
  return rowsFor(v.key).length;
}

function countTone(viewId: string, n: number): string {
  if (!n) return "";
  if (["top20", "rd", "locks", "rdfirst"].includes(viewId)) return "warm";
  if (["top10", "birthdays"].includes(viewId)) return "good";
  return "";
}

export function sidebar(): string {
  const visible = NAV_ORDER.filter((id) => !(VIEWS[id].managerOnly && SINGLE_AM));
  let nav = "";
  for (const group of GROUP_ORDER) {
    const items = visible.filter((id) => VIEWS[id].group === group);
    if (!items.length) continue;
    nav += `<div class="side-group-title">${esc(group)}</div>`;
    nav += items.map((id) => {
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
        <div class="am-chips">${AM_ORDER.map((name) =>
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
