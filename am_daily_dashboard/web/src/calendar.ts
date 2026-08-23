/** Archive month calendar in the topbar.
 *
 * ARCHIVE is written by the generator from the files actually on disk, so a
 * day only becomes clickable once its report exists. Nothing is computed
 * from date arithmetic here: a skipped Friday must not produce a dead link.
 */
import { REPORT } from "./payload";
import { esc, icon } from "./format";
import { app } from "./state";

const ARCHIVE: { d: string; f: string }[] = REPORT.archive || [];
const ARCHIVE_BY_DATE = new Map(ARCHIVE.map((a) => [a.d, a.f]));
const ARCHIVE_MONTHS = [...new Set(ARCHIVE.map((a) => a.d.slice(0, 7)))].sort();
const MONTH_NAMES = ["January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December"];

function shiftMonth(ym: string, delta: number): string {
  const y = Number(ym.slice(0, 4));
  const m = Number(ym.slice(5, 7)) + delta;
  const d = new Date(Date.UTC(y, m - 1, 1));
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}`;
}

export function calendarPopHtml(): string {
  const ym = app.calMonth || (REPORT.date || "").slice(0, 7);
  const year = Number(ym.slice(0, 4));
  const month = Number(ym.slice(5, 7));
  const firstDow = new Date(Date.UTC(year, month - 1, 1)).getUTCDay();
  const daysInMonth = new Date(Date.UTC(year, month, 0)).getUTCDate();
  const canPrev = ARCHIVE_MONTHS.some((m) => m < ym);
  const canNext = ARCHIVE_MONTHS.some((m) => m > ym);

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
          ${["S", "M", "T", "W", "T", "F", "S"].map((d) => `<div class="cal-dow">${d}</div>`).join("")}
          ${cells}
        </div>
        <div class="cal-foot">${ARCHIVE.length
          ? `${ARCHIVE.length} brief${ARCHIVE.length === 1 ? "" : "s"} saved. Highlighted days have a report; the rest were not generated.`
          : "No other briefs saved yet. History starts from this one."}</div>
      </div>`;
}
