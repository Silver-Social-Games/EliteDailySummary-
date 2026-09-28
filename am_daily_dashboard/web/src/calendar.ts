/** Archive month calendar in the topbar.

 *

 * ARCHIVE is written by the generator from the files actually on disk, so a

 * day only becomes clickable once its report exists. Nothing is computed

 * from date arithmetic here: a skipped Friday must not produce a dead link.

 *

 * Stale calendars on older dated files are refreshed by refresh_all_brief_archives

 * in canvas_to_html.py and mirrored to Elite_Cursor on every generate / html-only.

 * The Latest shortcut always opens the dateless bookmark file for this audience.

 */

import { AUDIENCE_SLUG, BRIEF_DATE, REPORT, shiftIsoDate } from "./payload";

import { esc, icon } from "./format";

import { app } from "./state";



const ARCHIVE: { d: string; f: string }[] = REPORT.archive || [];

const ARCHIVE_BY_DATE = new Map(ARCHIVE.map((a) => [a.d, a.f]));

/* Days are shown on the run date (data date + 1); files stay keyed by data date. */
const runDate = (dataIso: string) => shiftIsoDate(dataIso, 1) || dataIso;

const dataDate = (runIso: string) => shiftIsoDate(runIso, -1) || runIso;

const CURRENT_RUN = BRIEF_DATE || REPORT.date || "";

const ARCHIVE_MONTHS = [...new Set(ARCHIVE.map((a) => runDate(a.d).slice(0, 7)))].sort();

const MONTH_NAMES = ["January", "February", "March", "April", "May", "June",

  "July", "August", "September", "October", "November", "December"];



function datelessBriefFile(): string {
  if (AUDIENCE_SLUG) return `elite_am_brief_${AUDIENCE_SLUG}.html`;
  return "elite_am_brief.html";
}

/** Per-AM files must never open the manager's dated HTML from the calendar. */
function archiveFileForDate(iso: string): string | undefined {
  const file = ARCHIVE_BY_DATE.get(iso);
  if (!file) return undefined;
  if (!AUDIENCE_SLUG) return file;
  const suffix = `_${AUDIENCE_SLUG}.html`;
  if (file.endsWith(suffix)) return file;
  return `${iso}_elite_am_brief_${AUDIENCE_SLUG}.html`;
}



function shiftMonth(ym: string, delta: number): string {

  const y = Number(ym.slice(0, 4));

  const m = Number(ym.slice(5, 7)) + delta;

  const d = new Date(Date.UTC(y, m - 1, 1));

  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}`;

}



export function calendarPopHtml(): string {

  const ym = app.calMonth || CURRENT_RUN.slice(0, 7);

  const year = Number(ym.slice(0, 4));

  const month = Number(ym.slice(5, 7));

  const firstDow = new Date(Date.UTC(year, month - 1, 1)).getUTCDay();

  const daysInMonth = new Date(Date.UTC(year, month, 0)).getUTCDate();

  const canPrev = ARCHIVE_MONTHS.some((m) => m < ym);

  const canNext = ARCHIVE_MONTHS.some((m) => m > ym);

  const latestArchive = ARCHIVE.length ? ARCHIVE[ARCHIVE.length - 1] : null;

  const recent = ARCHIVE.filter((a) => a.d !== REPORT.date).slice(-5).reverse();



  let cells = "";

  for (let i = 0; i < firstDow; i++) cells += `<span class="cal-day empty"></span>`;

  for (let d = 1; d <= daysInMonth; d++) {

    const iso = `${ym}-${String(d).padStart(2, "0")}`;

    const file = archiveFileForDate(dataDate(iso));

    const isCurrent = iso === CURRENT_RUN;

    if (file) {

      cells += `<button type="button" class="cal-day has${isCurrent ? " today" : ""}"

            data-cal-open="${esc(file)}" title="Open the brief for ${esc(iso)} (data ${esc(dataDate(iso))})">${d}</button>`;

    } else {

      cells += `<span class="cal-day" title="No brief for ${esc(iso)}">${d}</span>`;

    }

  }



  const latestHtml =

    latestArchive && latestArchive.d !== REPORT.date

      ? `<button type="button" class="cal-recent-btn brand" data-cal-open="${esc(datelessBriefFile())}"

            title="Open latest brief (${esc(runDate(latestArchive.d))})">Latest · ${esc(runDate(latestArchive.d).slice(5))}</button>`

      : "";



  const recentHtml = recent.length || latestHtml

    ? `<div class="cal-recent">

        <div class="cal-recent-label">Recent</div>

        <div class="cal-recent-row">${latestHtml}${recent.map((a) => {
          const f = archiveFileForDate(a.d) || a.f;
          return `<button type="button" class="cal-recent-btn" data-cal-open="${esc(f)}" title="${esc(runDate(a.d))}">${esc(runDate(a.d).slice(5))}</button>`;
        }).join("")}</div>

      </div>`

    : "";



  return `<div class="cal-pop" id="calPop">

        ${recentHtml}

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

