/** Blocks reused by more than one view. */
import type { Dict } from "./types";
import { REPORT, day, dayShort, TEAM_GOALS } from "./payload";
import { esc, icon, fmtCount, inlineBold, compactMoney } from "./format";
import { wowHtml, wowPillHtml } from "./cells";
import { donutChartHtml } from "./charts";
import { logoImg } from "./logos";
import { tableHtml } from "./table";
import { app } from "./state";

function segmentByLabel(segments: Dict[], label: string): Dict | undefined {
  return segments.find((s) => String(s.label || "").toLowerCase() === label.toLowerCase());
}

function eliteShareFoot(
  elite: Dict,
  jackpota: Dict | undefined,
  metric: "rev" | "ply",
): string {
  if (metric === "rev") {
    const m = String(elite.share || "").match(/([\d.]+)%/);
    return m ? `${m[1]}% of Jackpota purchase` : "";
  }
  const jp = Number(jackpota?.plyThis || 0);
  const el = Number(elite.plyThis || 0);
  return jp > 0 ? `${((el / jp) * 100).toFixed(1)}% of Jackpota purchased players` : "";
}

function segmentPanel(
  seg: Dict | undefined,
  kind: "jackpota" | "elite",
  jackpota?: Dict,
): string {
  if (!seg) {
    return `<div class="segment-panel">
          <div class="segment-panel-head">${logoImg(kind, 24, kind === "jackpota" ? "Jackpota" : "Elite Club")}
            <span class="segment-panel-title">${kind === "jackpota" ? "Jackpota" : "Elite"}</span></div>
          <div class="segment-empty t-tertiary t-small">No segment data.</div>
        </div>`;
  }
  const revFoot = kind === "elite" ? eliteShareFoot(seg, jackpota, "rev") : "";
  const plyFoot = kind === "elite" ? eliteShareFoot(seg, jackpota, "ply") : "";
  return `<div class="segment-panel">
        <div class="segment-panel-head">${logoImg(kind, 24, kind === "jackpota" ? "Jackpota" : "Elite Club")}
          <span class="segment-panel-title">${esc(seg.label)}</span></div>
        <div class="segment-metric">
          <div class="segment-metric-label">Purchase</div>
          <div class="segment-metric-row">
            <span class="segment-metric-value">${esc(seg.revThis)}</span>
            ${wowPillHtml(seg.revWow)}
          </div>
          ${revFoot ? `<div class="segment-metric-foot t-tertiary t-small">${esc(revFoot)}</div>` : ""}
        </div>
        <div class="segment-metric">
          <div class="segment-metric-label">Purchased players</div>
          <div class="segment-metric-row">
            <span class="segment-metric-value sm">${esc(fmtCount(seg.plyThis))}</span>
            ${wowPillHtml(seg.plyWow)}
          </div>
          ${plyFoot ? `<div class="segment-metric-foot t-tertiary t-small">${esc(plyFoot)}</div>` : ""}
        </div>
      </div>`;
}

/** Elite & Jackpota WoW purchase hero — top of Morning Brief and Manager Dashboard. */
export function segmentHero(): string {
  const segments: Dict[] = REPORT.segments || [];
  const title = REPORT.segmentTitle || "WoW Purchase";
  const jackpota = segmentByLabel(segments, "Jackpota") || segments[0];
  const elite = segmentByLabel(segments, "Elite") || segments[1];
  const geo = REPORT.geoChart || null;
  return `<div class="segment-hero card gold-top">
        <div class="segment-hero-head">
          <div class="card-title">${esc(title)}</div>
        </div>
        <div class="segment-hero-body segment-hero-body-3">
          ${segmentPanel(jackpota, "jackpota")}
          ${segmentPanel(elite, "elite", jackpota)}
          ${donutChartHtml(geo)}
        </div>
      </div>`;
}

/** Elite portfolio snapshot — whole managed book from team goals actuals. */
export function eliteSnapshotCards(): Dict[] {
  const g = TEAM_GOALS;
  if (!g?.available) {
    return [
      { label: "Elite Portfolio", value: "—", tone: "neutral" },
    ];
  }
  return [
    { label: "Elite Portfolio", value: (g.portfolioSize || 0).toLocaleString(), icon: "list",
      tone: "neutral" },
    { label: "MTD Purchase", value: compactMoney(g.mtdPurchase || 0), icon: "dollar",
      tone: "success" },
    { label: "MTD Net Purchase", value: compactMoney(g.mtdNetPurchase || 0), icon: "banknote",
      tone: "brand" },
    { label: "MTD Purchasers", value: String((g.kpis || []).find((k: Dict) => k.key === "monthly_purchasers")?.actualDisplay || "—"),
      icon: "users", tone: "brand" },
  ];
}

/** Daily trigger tiles — shared by Morning Brief and Manager Dashboard. */
export function dailyTriggerMetrics(f: Dict): Dict[] {
  return [
    { label: "Open Tickets", value: fmtCount(f.openZd ?? 0), view: "tickets",
      tone: f.openZd ? "info" : "success" },
    { label: "Big Winners", value: fmtCount(f.bigWinners ?? 0), view: "bigwinners",
      tone: f.bigWinners ? "brand" : "neutral" },
    { label: "Big Losers", value: fmtCount(f.bigLosers ?? 0), view: "biglosers",
      tone: f.bigLosers ? "warning" : "neutral" },
    { label: "Top 20 Dropping", value: fmtCount(f.declineCount ?? 0), view: "top20",
      tone: f.declineCount ? "warning" : "success" },
    { label: "Pending RD", value: fmtCount(f.rdOver5k ?? 0), view: "rd",
      tone: f.rdOver5k ? "warning" : "success" },
    { label: "Take A Break", value: fmtCount(f.takeABreak ?? 0), view: "locks",
      tone: f.takeABreak ? "warning" : "success" },
    { label: "Other Locked", value: fmtCount(f.otherLocked ?? 0), view: "locks",
      tone: f.otherLocked ? "warning" : "success" },
    { label: "Self-Exclusion", value: fmtCount(f.selfExclusion ?? 0), view: "locks",
      tone: "neutral" },
    { label: "Birthdays (3d)", value: fmtCount(f.birthdays ?? 0), view: "birthdays",
      tone: f.birthdays ? "brand" : "neutral" },
  ];
}

/** Legacy table segment — kept for reference; use segmentHero() in views. */
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
  return `<${tag} class="stat gold-top t-${o.tone || "neutral"}${o.view ? "" : " flat"}"${o.view ? ` data-go="${esc(o.view)}"` : ""}>
        <div class="stat-top">
          <span class="stat-chip">${icon(o.icon, "ic-sm")}</span>
          <span class="stat-label">${esc(o.label)}</span>
        </div>
        <div class="stat-value ${o.small ? "sm" : ""}">${esc(o.value)}</div>
        ${o.foot ? `<div class="stat-foot">${o.foot}</div>` : ""}
      </${tag}>`;
}

/** Reference-style KPI band — one white card, metrics in a single row with dividers. */
export function metricBand(title: string, items: Dict[], opts?: { subtitle?: string; cols?: number }): string {
  const cols = opts?.cols || items.length;
  const cells = items.map((o) => {
    const tag = o.view ? "button" : "div";
    const typeAttr = o.view ? ' type="button"' : "";
    return `<${tag}${typeAttr} class="metric-cell t-${o.tone || "neutral"}"${o.view ? ` data-go="${esc(o.view)}"` : ""}>
          <div class="metric-label">${esc(o.label)}</div>
          <div class="metric-value${o.small ? " sm" : ""}">${esc(o.value)}</div>
          ${o.foot ? `<div class="metric-foot">${o.foot}</div>` : ""}
        </${tag}>`;
  }).join("");
  return `<div class="metric-band card gold-top">
        <div class="metric-band-head">
          <div class="card-title">${esc(title)}</div>
          ${opts?.subtitle ? `<div class="card-sub">${esc(opts.subtitle)}</div>` : ""}
        </div>
        <div class="metric-band-grid" style="--metric-cols:${cols}">${cells}</div>
      </div>`;
}

/** Never leave a view blank: an empty section says so explicitly. */
export function emptyState(ico: string, title: string, body: string): string {
  return `<div class="card"><div class="card-body" style="text-align:center;padding:48px 20px">
        <div class="card-icon neutral" style="margin:0 auto 12px;width:44px;height:44px">${icon(ico, "ic-lg")}</div>
        <div class="card-title" style="margin-bottom:5px">${esc(title)}</div>
        <div class="t-tertiary t-small">${esc(body)}</div>
      </div></div>`;
}

/** Compact AM intro — salute + one-line body at the top of Morning Brief. */
export function amIntro(lines: string[]): string {
  if (!lines.length) return "";
  const salute = esc(lines[0]);
  const body = lines.slice(1).map((line) => inlineBold(line)).join(" ");
  return `<div class="am-intro">
        <div class="intro-salute">${salute}</div>
        ${body ? `<div class="intro-body">${body}</div>` : ""}
      </div>`;
}

/** Passcode wall for the manager-only views. */
export function gateHtml(): string {
  return `<div class="gate gold-top">
        <div class="gate-mark">${logoImg("elite", 48, "Elite Club")}</div>
        <h2>Manager Dashboard</h2>
        <p>Cross-AM revenue, goals and risk roll-up. Enter the passcode to view.</p>
        <input type="password" id="gateInput" placeholder="••••••" autocomplete="off" spellcheck="false">
        <div class="err">${esc(app.gateError)}</div>
        <button type="button" class="btn primary" id="gateSubmit" style="width:100%;justify-content:center">
          ${icon("unlock", "ic-sm")} Unlock
        </button>
      </div>`;
}
