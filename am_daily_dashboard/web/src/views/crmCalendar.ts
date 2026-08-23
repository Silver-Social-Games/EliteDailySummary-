/** CRM Calendar — weekday offer playbook (book-wide, all AM files). */
import type { CrmOfferCell, CrmOfferCycle } from "../data/crmOffers";
import {
  CRM_BANDS, CRM_DAY_ORDER, CRM_OFFERS,
} from "../data/crmOffers";
import { REPORT, day } from "../payload";
import { esc, icon } from "../format";
import { getState } from "../state";

function bandFor(leadLow: number) {
  return CRM_BANDS.find((b) => leadLow >= b.min) || CRM_BANDS[CRM_BANDS.length - 1];
}

function cellFor(cycle: CrmOfferCycle, weekday: string): CrmOfferCell | undefined {
  return cycle.cells.find((c) => c.day === weekday);
}

function crmBoxHtml(cell: CrmOfferCell, opts: {
  muted?: boolean;
  today?: boolean;
}): string {
  const band = bandFor(cell.lead_low);
  const muted = !!opts.muted;
  const today = !!opts.today;
  const tint = muted ? "" :
    `background:rgba(${band.rgb},.07);border-color:rgba(${band.rgb},.55);border-left-color:${band.hue};`;
  const headTint = muted ? "" : `background:rgba(${band.rgb},.16);`;
  const follow = cell.follow_label
    ? `<div class="crm-box-follow">${esc(cell.follow_label)} <strong>${esc(cell.follow_value || "")}</strong></div>`
    : "";
  const name = esc(cell.campaign);
  const heading = cell.link
    ? `<a href="${esc(cell.link)}" target="_blank" rel="noopener noreferrer" class="crm-box-link"
          title="Open ${name}">${name}</a>`
    : `<span>${name}</span>`;
  return `<div class="crm-box${muted ? " muted" : ""}${today ? " today" : ""}" style="${tint}">
        <div class="crm-box-head" style="${headTint}">${heading}</div>
        <div class="crm-box-body">
          <div class="crm-box-cap">First offer</div>
          <div class="crm-box-lead">${esc(cell.lead)}</div>
          ${follow}
        </div>
      </div>`;
}

function filterChip(label: string, pressed: boolean, attrs: string): string {
  return `<button type="button" class="chip crm-chip${pressed ? " active" : ""}" aria-pressed="${pressed ? "true" : "false"}" ${attrs}>
        ${label}</button>`;
}

function desktopGrid(days: string[], activeBands: string[], reportDay: string): string {
  let html = `<span class="crm-cycle-spacer"></span>` +
    days.map((d) =>
      `<div class="crm-day-head${d === reportDay ? " today" : ""}">${esc(d.slice(0, 3))}</div>`
    ).join("");

  for (const cycle of CRM_OFFERS.cycles) {
    html += `<div class="crm-cycle-label">
          <strong>${esc(cycle.title)}</strong>
          <span>${esc(cycle.note || "")}</span>
        </div>`;
    html += days.map((d) => {
      const cell = cellFor(cycle, d);
      if (!cell) return `<div class="crm-box empty"></div>`;
      const muted = !activeBands.includes(bandFor(cell.lead_low).id);
      return crmBoxHtml(cell, { muted, today: d === reportDay });
    }).join("");
  }
  return html;
}

function mobileBlocks(days: string[], activeBands: string[], reportDay: string): string {
  return days.map((d) => `<section class="crm-day-block">
        <div class="crm-day-block-title${d === reportDay ? " today" : ""}">${esc(d)}</div>
        <div class="crm-pair">
          ${CRM_OFFERS.cycles.map((cycle) => {
            const cell = cellFor(cycle, d);
            if (!cell) return "";
            const muted = !activeBands.includes(bandFor(cell.lead_low).id);
            return `<div>
              <div class="crm-cycle-tag">${esc(cycle.title)}</div>
              ${crmBoxHtml(cell, { muted, today: d === reportDay })}
            </div>`;
          }).join("")}
        </div>
      </section>`).join("");
}

export function viewCrmCalendar(): string {
  const reportDay = REPORT.weekday || day || "Monday";
  const allDays = [...CRM_DAY_ORDER];
  const allBandIds = CRM_BANDS.map((b) => b.id);
  const selectedDays: string[] = getState("crm_days", allDays);
  const selectedBands: string[] = getState("crm_bands", allBandIds);

  const days = allDays.filter((d) => selectedDays.includes(d));
  const showDays = days.length ? days : allDays;
  const activeBands = selectedBands.length ? selectedBands : allBandIds;

  const allDaysSelected = selectedDays.length === allDays.length;
  const allBandsSelected = selectedBands.length === allBandIds.length;

  const dayChips = allDays.map((d) =>
    filterChip(d.slice(0, 3), !allDaysSelected && selectedDays.includes(d), `data-crm-toggle="day" data-crm-value="${esc(d)}"`)
  ).join("");

  const bandChips = CRM_BANDS.map((b) =>
    filterChip(
      `<span class="crm-dot" style="background:${b.hue}"></span>${esc(b.label)}`,
      !allBandsSelected && selectedBands.includes(b.id),
      `data-crm-toggle="band" data-crm-value="${esc(b.id)}"`
    )
  ).join("");

  const stateLine = allDaysSelected && allBandsSelected
    ? `All ${allDays.length} weekdays · both cycles`
    : `Showing ${showDays.length} of ${allDays.length} days` +
      (allBandsSelected
        ? ", all first-offer bands"
        : `, ${activeBands.length} of ${allBandIds.length} first-offer bands highlighted`);

  return `<div class="stack crm-view">
        <div class="card">
          <div class="card-head">
            <span class="card-icon brand">${icon("calendar", "ic-sm")}</span>
            <div>
              <div class="card-title">${esc(CRM_OFFERS.title)}</div>
              <div class="card-sub">${esc(CRM_OFFERS.subtitle)}</div>
            </div>
          </div>
        </div>

        <div class="card">
          <div class="card-body stack-10">
            <div class="crm-filters">
              <div>
                <div class="crm-filter-label">Days</div>
                <div class="chip-row">
                  ${filterChip("All", allDaysSelected, 'data-crm-quick="all"')}
                  ${filterChip("Weekend", !allDaysSelected && selectedDays.length === 2 && selectedDays.includes("Friday") && selectedDays.includes("Saturday"), 'data-crm-quick="weekend"')}
                  ${dayChips}
                </div>
              </div>
              <div>
                <div class="crm-filter-label">First offer %</div>
                <div class="chip-row">
                  ${filterChip("All", allBandsSelected, 'data-crm-quick="all-bands"')}
                  ${bandChips}</div>
              </div>
            </div>
            <p class="crm-state t-tertiary t-small">${esc(stateLine)}</p>
            <div class="crm-board desktop" style="--crm-cols:${showDays.length}">
              ${desktopGrid(showDays, activeBands, reportDay)}
            </div>
            <div class="crm-board mobile">
              ${mobileBlocks(showDays, activeBands, reportDay)}
            </div>
          </div>
        </div>
      </div>`;
}
