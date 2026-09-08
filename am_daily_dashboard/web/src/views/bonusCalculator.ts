/** Bonus Calculator — AID lookup with Inbound V5 Free Bonus output. */

import { aidHtml, moneyHtml } from "../cells";
import { applyGwg, computeFreeBonus } from "../bonusCalc";
import { BONUS_CALC_MAX_BONUS } from "../bonusConfig";
import { bonusRowForAidAny } from "../bonusLookup";
import { esc, icon, scAmount } from "../format";
import { PEER_MODE } from "../payload";
import { app, getState } from "../state";

function pctLabel(n: number): string {
  return `${(n * 100).toFixed(1)}%`;
}

function pctBonusToGgr(bonus: number, ggr: number): string {
  if (!ggr) return "—";
  return pctLabel(bonus / ggr);
}

function wfRow(label: string, value: string, muted = false): string {
  return `<div class="bonus-wf-row${muted ? " muted" : ""}">
    <div class="bonus-wf-k">${esc(label)}</div>
    <div class="bonus-wf-v">${value}</div>
  </div>`;
}

function sheetRow(label: string, value: string, tone: "" | "emph" | "soft" = ""): string {
  return `<div class="bonus-sheet-row${tone ? ` tone-${tone}` : ""}">
    <div class="bonus-sheet-k">${esc(label)}</div>
    <div class="bonus-sheet-v">${value}</div>
  </div>`;
}

function sheetSection(title: string, rows: string, open = false): string {
  return `<details class="bonus-sheet-section"${open ? " open" : ""}>
    <summary class="bonus-sheet-title">${esc(title)}</summary>
    <div class="bonus-sheet-body">${rows}</div>
  </details>`;
}

function gwgChips(selected: number, disabled: boolean): string {
  const options: Array<[number, string]> = [[0, "None"], [0.03, "3%"], [0.05, "5%"], [0.1, "10%"]];
  return `<div class="bonus-gwg-chips${disabled ? " disabled" : ""}" role="group" aria-label="GWG add-on">
    ${options.map(([pct, label]) => {
      const active = Math.abs(selected - pct) < 1e-9;
      return `<button type="button" class="bonus-gwg-chip${active ? " active" : ""}"
        data-gwg-pct="${pct}"${disabled ? " disabled" : ""}>${esc(label)}</button>`;
    }).join("")}
  </div>`;
}

function playerMetricsPanel(
  row: Record<string, unknown>,
  result: ReturnType<typeof computeFreeBonus>,
  statusBadge: string,
  windowDays: number,
): string {
  const ggrWin = Number(row.ggrWindow ?? row.ggr ?? 0);
  const bonusWin = Number(row.bonusWindow ?? row.bonus ?? 0);
  const ngrWin = Number(row.ngrWindow ?? row.ngr ?? 0);
  const ggrLt = Number(row.ggrLifetime ?? 0);
  const bonusLt = Number(row.bonusLifetime ?? 0);
  const winLabel = `Last ${windowDays} days`;

  return `<div class="bonus-metrics-sheet card">
    <div class="bonus-metrics-sheet-head">Player metrics</div>
    <div class="bonus-metrics-sheet-grid">
      ${sheetSection("Profile", [
        sheetRow("FTD date", esc(String(row.firstPurchaseDate || "—"))),
        sheetRow("Last bet date", esc(String(row.lastPlayDate || "—")), "emph"),
        sheetRow("Status", statusBadge, "soft"),
        sheetRow("Player segment", esc(result.segmentLabel || "—"), "emph"),
      ].join(""), true)}
      ${sheetSection(winLabel, [
        sheetRow("GGR", moneyHtml(ggrWin), "emph"),
        sheetRow("Bonus SC", scAmount(bonusWin), "emph"),
        sheetRow("NGR", moneyHtml(ngrWin), "soft"),
      ].join(""), true)}
      ${sheetSection("Purchases & bonus history", [
        sheetRow("Last purchase date", esc(String(row.lastPurchaseDate || "—"))),
        sheetRow(`Purchased $ · ${winLabel.toLowerCase()}`, moneyHtml(row.purchaseAmountWindow), "emph"),
        sheetRow(`Purchases (#) · ${winLabel.toLowerCase()}`, esc(String(row.purchaseCountWindow ?? "—")), "soft"),
        sheetRow(`Avg purchase · ${winLabel.toLowerCase()}`, moneyHtml(row.avgPurchaseWindow)),
        sheetRow(`% Bonus / purchase · ${winLabel.toLowerCase()}`, esc(pctLabel(Number(row.bonusPctWindow || 0))), "emph"),
        sheetRow("% Bonus / purchase · lifetime", esc(pctLabel(Number(row.bonusPctLifetime || 0))), "soft"),
        sheetRow("Bonus status", esc(result.bonusStatus || "—")),
      ].join(""))}
      ${sheetSection("Lifetime", [
        sheetRow("GGR", moneyHtml(ggrLt)),
        sheetRow("Bonus SC", scAmount(bonusLt)),
        sheetRow("Total purchased $ · lifetime", moneyHtml(row.purchaseAmountLifetime), "emph"),
        sheetRow("% Bonus to GGR", esc(pctBonusToGgr(bonusLt, ggrLt)), "emph"),
      ].join(""))}
    </div>
  </div>`;
}

export function viewBonusCalculator(): string {
  const aidRaw = String(getState("bonus_aid", "") || "").trim();
  const gwgPct = Number(getState("bonus_gwg_pct", 0) || 0);
  const row = aidRaw ? bonusRowForAidAny(app.agent, aidRaw) : undefined;
  const rowAgent = row ? String(row.agent || "") : "";
  const crossAm = !!row && PEER_MODE && rowAgent !== app.agent;
  let result = null;
  if (row) {
    result = computeFreeBonus({
      active: !!row.active,
      ggr: Number(row.ggr || 0),
      bonus: Number(row.bonus || 0),
      purchaseCount: Number(row.purchaseCount || 0),
      purchaseAmount: Number(row.purchaseAmount || 0),
      bonusPctWindow: Number(row.bonusPctWindow || 0),
      bonusPctLifetime: Number(row.bonusPctLifetime || 0),
      locked: !!row.locked,
      lockLabel: String(row.lockLabel || ""),
    });
  }

  const eligible = !!result && !result.blocked && result.path !== "not_eligible" && result.path !== "none"
    && result.freeBonus != null && result.freeBonus > 0;
  const [gwgSc, totalSc] = eligible ? applyGwg(result!.freeBonus, gwgPct) : [0, 0];

  const statusBadge = row
    ? `<span class="badge ${row.active ? "success" : "warning"}">${row.active ? "Active" : "Inactive"}</span>`
    : "";

  const windowDays = Number(row?.windowDays || 14);

  const offerBlock = !aidRaw
    ? `<p class="bonus-empty">Enter an AID${PEER_MODE ? " on any AM tab" : ""} to see the Inbound Free Bonus recommendation.</p>`
    : !row
      ? `<p class="bonus-empty">AID ${esc(aidRaw)} is not in this brief's bonus lookup${PEER_MODE ? "" : ` on ${esc(app.agent)}'s book`}.</p>`
      : `<div class="bonus-layout">
          ${crossAm ? `<p class="bonus-peer-note">Book owner: <strong>${esc(rowAgent)}</strong> · viewing as ${esc(app.agent)}</p>` : ""}
          <div class="bonus-offer-col card bonus-output-green">
            <div class="bonus-output-head">
              <div>
                <div class="bonus-output-kicker">Free Bonus</div>
                <div class="bonus-output-offer${eligible ? "" : " dim"}">${esc(result!.offerLabel)}</div>
              </div>
              ${result!.blocked ? `<span class="badge">${esc(result!.blockedReason || "Blocked")}</span>` : ""}
            </div>
            ${eligible ? `<div class="bonus-offer-base">Base ${scAmount(result!.freeBonus)}</div>` : ""}
            <div class="bonus-gwg-block">
              <div class="bonus-gwg-label">GWG add-on</div>
              ${gwgChips(gwgPct, !eligible)}
            </div>
            <div class="bonus-offer-total${eligible ? "" : " dim"}">
              <div class="bonus-offer-total-k">Total offer</div>
              <div class="bonus-offer-total-v">${eligible ? scAmount(totalSc) : "—"}</div>
              ${eligible && gwgSc > 0 ? `<div class="bonus-offer-total-note">Includes +${scAmount(gwgSc)} GWG</div>` : ""}
            </div>
            <p class="bonus-output-note">${esc(result!.capNote)}</p>
          </div>
          <details class="bonus-waterfall card" open>
            <summary class="bonus-waterfall-title">Calculation</summary>
            <div class="bonus-waterfall-body">
            ${wfRow("Status factor", esc(result!.bonusStatusMult ? `×${result!.bonusStatusMult.toFixed(1)}` : "—"))}
            ${result!.path === "positive_ngr" || result!.path === "inactive"
              ? wfRow("NGR factor (pre-lookup)", moneyHtml(result!.recommended))
                + wfRow("Lookup tier", scAmount(result!.lookupAmount))
                + wfRow(`${BONUS_CALC_MAX_BONUS} SC cap`, result!.cappedByMax ? "Applied" : "Not needed")
                + (result!.avgPurchaseCapped
                  ? wfRow("Avg purchase cap", esc(`Ratio ${result!.ratioUsed.toFixed(2)} capped to avg purchase`))
                  : "")
              : ""}
            ${wfRow("Base Free Bonus SC", eligible ? scAmount(result!.freeBonus) : esc(result!.offerLabel))}
            ${eligible
              ? wfRow("GWG", gwgSc > 0 ? `+${scAmount(gwgSc)}` : "None")
                + wfRow("Total SC", scAmount(totalSc))
              : wfRow("GWG", "—", true) + wfRow("Total SC", "—", true)}
            </div>
          </details>
        </div>
        ${playerMetricsPanel(row as Record<string, unknown>, result!, statusBadge, windowDays)}`;

  return `<div class="bonus-calc card">
      <div class="card-head">
        <div class="card-head-main">
          ${icon("calculator", "ic-md")}
          <div>
            <h2 class="card-title">Bonus Calculator</h2>
          </div>
        </div>
      </div>
      <div class="bonus-search">
        <label class="bonus-search-label" for="bonusAidInput">AID</label>
        <div class="bonus-search-row">
          <input id="bonusAidInput" type="search" inputmode="numeric" placeholder="Search AID…"
            value="${esc(aidRaw)}" data-state="bonus_aid" autocomplete="off">
          ${row ? `<span class="bonus-aid-link">${aidHtml({
            aid: String(row.aid),
            aidUrl: `https://lookerpatrianna.cloud.looker.com/dashboards/5207?Account+ID+=${encodeURIComponent(String(row.aid))}`,
          })}${row.name ? ` · ${esc(String(row.name))}` : ""}</span>` : ""}
        </div>
      </div>
      ${offerBlock}
    </div>`;
}
