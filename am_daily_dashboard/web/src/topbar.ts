/** Topbar — breadcrumb, archive calendar trigger, print, and the "who" badge. */
import { REPORT } from "./payload";
import { esc, icon, initials } from "./format";
import { app } from "./state";
import { VIEWS } from "./registry";
import { calendarPopHtml } from "./calendar";

export function topbar(): string {
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
