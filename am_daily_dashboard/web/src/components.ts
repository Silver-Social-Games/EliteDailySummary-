/** Blocks reused by more than one view. */
import type { Dict } from "./types";
import { REPORT, day, dayShort } from "./payload";
import { esc, icon } from "./format";
import { wowHtml } from "./cells";
import { tableHtml } from "./table";
import { app } from "./state";

/** Elite & Jackpota weekday segment strip. Data comes from
 *  daily_summary.build_report, not from a query of our own. */
export function segmentCard(): string {
  const segments: Dict[] = REPORT.segments || [];
  const title = REPORT.segmentTitle || `${day} vs last ${day} · Elite & Jackpota`;
  const rows = segments.map((s) => [
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
          segments.map((s) => s.tone || "neutral"),
          { markerCol: 0, empty: "No segment data." }
        )}
      </div>`;
}

/** A KPI tile. Renders as a button that navigates when `view` is set, and as a
 *  flat div otherwise, so nothing looks clickable that is not. */
export function statCard(o: Dict): string {
  const tag = o.view ? "button" : "div";
  return `<${tag} class="stat t-${o.tone || "neutral"}${o.view ? "" : " flat"}"${o.view ? ` data-go="${esc(o.view)}"` : ""}>
        <div class="stat-top">
          <span class="stat-chip">${icon(o.icon, "ic-sm")}</span>
          <span class="stat-label">${esc(o.label)}</span>
        </div>
        <div class="stat-value ${o.small ? "sm" : ""}">${esc(o.value)}</div>
        ${o.foot ? `<div class="stat-foot">${o.foot}</div>` : ""}
      </${tag}>`;
}

/** Never leave a view blank: an empty section says so explicitly. */
export function emptyState(ico: string, title: string, body: string): string {
  return `<div class="card"><div class="card-body" style="text-align:center;padding:48px 20px">
        <div class="card-icon neutral" style="margin:0 auto 12px;width:44px;height:44px">${icon(ico, "ic-lg")}</div>
        <div class="card-title" style="margin-bottom:5px">${esc(title)}</div>
        <div class="t-tertiary t-small">${esc(body)}</div>
      </div></div>`;
}

/** Passcode wall for the manager-only views. */
export function gateHtml(): string {
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
