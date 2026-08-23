/** Topbar — breadcrumb, archive calendar, CSV download, and the "who" badge. */
import { REPORT } from "./payload";
import { esc, icon, initials } from "./format";
import { viewSupportsCsvExport } from "./exportCsv";
import { app } from "./state";
import { VIEWS } from "./registry";
import { calendarPopHtml } from "./calendar";

export function topbar(): string {
  const v = VIEWS[app.view] || VIEWS.home;
  const isManager = !!v.managerOnly;
  const who = isManager ? "All AMs" : app.agent;
  const showHome = app.view !== "home";
  const showExport = viewSupportsCsvExport(app.view);
  return `<header class="topbar">
        <button type="button" class="icon-btn" id="toggleSidebar" title="Toggle menu">${icon("panel", "ic-sm")}</button>
        ${showHome ? `<button type="button" class="btn-ghost" data-go="home">${icon("sunrise", "ic-xs")} Morning Brief</button>` : ""}
        <div class="crumb">
          <div class="crumb-top g-${groupAccent(v.group)}">${esc(v.group)}</div>
          <div class="crumb-title">${icon(v.icon, "ic-lg")}${esc(v.label)}</div>
        </div>
        <div class="spacer"></div>
        <div class="topbar-trail">
          ${showExport ? `<button type="button" class="icon-btn export-btn" id="exportCsv" title="Download CSV">${icon("download", "ic-sm")}</button>` : ""}
          <div class="cal-wrap">
            <button type="button" class="cal-btn" id="calBtn" title="Switch report date">
              ${icon("calendar", "ic-sm")}
              <span class="cal-btn-text">
                <span class="cal-btn-kicker">Report date</span>
                <span class="cal-btn-value">${esc(REPORT.subtitle || REPORT.date || "")}</span>
              </span>
              ${icon("chev-down", "ic-xs cal-chev")}
            </button>
            ${app.calOpen ? calendarPopHtml() : ""}
          </div>
          <div class="who">
            <span class="who-dot">${esc(isManager ? "ALL" : initials(who))}</span>
            <div class="who-copy">
              <div class="who-name">${esc(who)}</div>
              ${v.sub ? `<div class="who-role" title="${esc(v.sub)}">${esc(v.sub)}</div>` : ""}
            </div>
          </div>
        </div>
      </header>`;
}

function groupAccent(group: string): string {
  if (group === "Manager") return "manager";
  if (group === "Performance") return "performance";
  if (group === "Daily Triggers") return "operations";
  if (group === "Declining & Churn") return "gaps";
  if (group === "CRM" || group === "Games") return "brand";
  if (group === "Anniversary") return "outreach";
  return "neutral";
}
