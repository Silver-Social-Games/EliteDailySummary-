/** The table shell, pagination, and the generic search + sort + paginate card.
 *
 * Canvas counterpart: canvas_parts/tables.py.
 */
import type { Dict, PaginateResult, TableCardOpts, TableOpts } from "./types";
import { esc, icon } from "./format";
import { markerCell } from "./cells";
import { matchesAid } from "./filters";
import { getState, putState } from "./state";

const PAGE_SIZES = [25, 50, 100];
const PAGINATE_ABOVE = 25;

export function tableHtml(
  headers: string[],
  rows: string[][],
  align?: string[],
  tones?: string[],
  opts?: TableOpts
): string {
  const o: TableOpts = opts || {};
  const th = headers
    .map((h, i) => {
      const a = (align && align[i]) || "left";
      return `<th class="${a === "right" ? "num" : a === "center" ? "center" : ""}">${esc(h)}</th>`;
    })
    .join("");
  const body = rows.length
    ? rows
        .map((cells, ri) => {
          const tone = (tones && tones[ri]) || "neutral";
          const isTotal = o.totalRowIndex === ri;
          const tds = cells
            .map((c, i) => {
              const a = (align && align[i]) || "left";
              const cls = a === "right" ? "num" : a === "center" ? "center" : "";
              const content = o.markerCol === i && !isTotal ? markerCell(tone, c) : c;
              return `<td class="${cls}">${content}</td>`;
            })
            .join("");
          return `<tr class="${isTotal ? "total-row" : ""}">${tds}</tr>`;
        })
        .join("")
    : `<tr><td colspan="${headers.length}" class="empty">${esc(o.empty || "Nothing to show here.")}</td></tr>`;
  return (
    `<div class="table-frame ${o.frameClass || ""}">` +
    `<table class="grid ${o.tableClass || ""}"><thead><tr>${th}</tr></thead>` +
    `<tbody>${body}</tbody></table></div>`
  );
}

/** Returns the visible slice plus the pager markup for it. */
export function paginate(
  rows: Dict[],
  stateKey: string,
  opts?: { forceOn?: boolean; defaultSize?: number; note?: string }
): PaginateResult {
  const total = rows.length;
  const defaultSize = opts?.defaultSize ?? PAGE_SIZES[0];
  const on = opts?.forceOn || total > PAGINATE_ABOVE;
  if (!on && !opts?.forceOn) return { slice: rows, pager: "", from: total ? 1 : 0, to: total, total };
  const sizeKey = stateKey + "_size";
  const pageKey = stateKey + "_page";
  const raw = getState(sizeKey, String(defaultSize));
  const size = raw === "all" ? total : Number(raw) || PAGE_SIZES[0];
  const pages = Math.max(1, Math.ceil(total / size));
  const page = Math.min(Math.max(1, Number(getState(pageKey, 1)) || 1), pages);
  putState(pageKey, page);
  const start = (page - 1) * size;
  const slice = rows.slice(start, start + size);
  const from = total ? start + 1 : 0;
  const to = Math.min(start + size, total);

  const btn = (label: string, target: number, disabled: boolean, extraCls?: string) =>
    `<button type="button" class="pg ${extraCls || ""}" data-page-key="${esc(pageKey)}" ` +
    `data-page="${target}"${disabled ? " disabled" : ""}>${label}</button>`;

  let nums = "";
  if (pages > 1) {
    const window_ = new Set([1, pages, page, page - 1, page + 1]);
    if (page <= 3) [2, 3, 4].forEach((n) => window_.add(n));
    if (page >= pages - 2) [pages - 1, pages - 2, pages - 3].forEach((n) => window_.add(n));
    const list = [...window_].filter((n) => n >= 1 && n <= pages).sort((a, b) => a - b);
    let prev = 0;
    for (const n of list) {
      if (prev && n - prev > 1) nums += `<span class="pg-gap">…</span>`;
      nums += btn(String(n), n, false, n === page ? "active" : "");
      prev = n;
    }
  }
  const sizeSel =
    `<span class="select-wrap"><select data-state="${esc(sizeKey)}">` +
    PAGE_SIZES.map(
      (n) => `<option value="${n}" ${raw === String(n) ? "selected" : ""}>${n} per page</option>`
    ).join("") +
    `<option value="all" ${raw === "all" ? "selected" : ""}>Show all (${total})</option>` +
    `</select>${icon("chev-down", "ic-xs")}</span>`;

  const pager = `<div class="pager">
        <div class="pager-info">Showing <strong>${from.toLocaleString()}–${to.toLocaleString()}</strong> of ${total.toLocaleString()}</div>
        ${opts?.note ? `<div class="pager-note">${esc(opts.note)}</div>` : ""}
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

/** Generic search + sort + paginate section rendered as a card. */
export function tableCard(opts: TableCardOpts): string {
  const all = opts.rows || [];
  const searchEnabled = opts.showSearch !== false;
  const sortEnabled = !!(opts.sortOptions && opts.sortOptions.length && opts.sortFn);
  const qKey = opts.stateKey + "_q";
  const sortKey = opts.stateKey + "_sort";
  const q: string = searchEnabled ? getState(qKey, "") : "";
  const sortBy: string = getState(
    sortKey,
    opts.defaultSort || (opts.sortOptions && opts.sortOptions[0] ? opts.sortOptions[0].value : "")
  );

  const searched = searchEnabled ? all.filter((r) => matchesAid(r, q, opts.extraKeys || [])) : all;
  const ordered = opts.sortFn ? opts.sortFn(searched, sortBy) : searched;
  const { slice, pager, total } = paginate(ordered, opts.stateKey, {
    forceOn: opts.forcePaginate,
    defaultSize: opts.pageSize,
    note: opts.pagerNote,
  });

  const filtered = q.trim() !== "";
  const countBadge = filtered
    ? `<span class="badge brand">${ordered.length} of ${all.length}</span>`
    : `<span class="badge">${all.length} ${all.length === 1 ? "player" : "players"}</span>`;

  const toolbar =
    searchEnabled || sortEnabled
      ? `<div class="toolbar">
        ${
          searchEnabled
            ? `<label class="search">${icon("search", "ic-sm")}
          <input type="search" placeholder="Search name, AID…" value="${esc(q)}" data-state="${esc(qKey)}">
        </label>`
            : ""
        }
        ${
          sortEnabled
            ? `<span class="select-wrap"><select data-state="${esc(sortKey)}">` +
              opts
                .sortOptions!.map(
                  (o) =>
                    `<option value="${esc(o.value)}" ${sortBy === o.value ? "selected" : ""}>${esc(o.label)}</option>`
                )
                .join("") +
              `</select>${icon("chev-down", "ic-xs")}</span>`
            : ""
        }
        <div class="spacer"></div>
        ${countBadge}
      </div>`
      : "";

  const note = opts.note
    ? `<div class="card-sub" style="margin:2px 0 10px">${esc(opts.note)}</div>`
    : "";

  return `<div class="card${opts.cardClass ? ` ${opts.cardClass}` : ""}${opts.compact ? " fit-content" : ""}">
        ${note}
        ${toolbar}
        ${tableHtml(opts.headers, slice.map(opts.renderRow), opts.align, slice.map((r) => r.tone || "neutral"), {
          markerCol: opts.markerCol,
          empty: opts.empty,
          tableClass: opts.tableClass,
          frameClass: opts.compact ? "compact" : "",
        })}
        ${total ? pager : ""}
      </div>`;
}
