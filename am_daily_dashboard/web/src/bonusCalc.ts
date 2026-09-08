/** Mirrors am_daily_dashboard/bonus_calculator.py for runtime Free Bonus. */

import {
  BONUS_CALC_ACTIVE_PCT,
  BONUS_CALC_INACTIVE_PCT,
  BONUS_CALC_MAX_BONUS,
} from "./bonusConfig";

const BONUS_STATUS_TABLE: Array<[number, string, number]> = [
  [0.0, "No/Low Bonus user", 1.0],
  [0.05, "No/Low Bonus user", 0.9],
  [0.10, "No/Low Bonus user", 0.8],
  [0.15, "Regular Bonus user", 0.7],
  [0.17, "Regular Bonus user", 0.6],
  [0.19, "Regular Bonus user", 0.5],
  [0.22, "Regular Bonus user", 0.4],
  [0.25, "Bonus beggar", 0.3],
  [0.30, "Bonus beggar", 0.2],
  [0.45, "Abuser", 0.1],
];

const ACTIVE_POS_NGR_TABLE: Array<[number, number]> = [
  [1, 5], [10, 10], [20, 20], [30, 30], [40, 40], [50, 50], [60, 60], [70, 70],
  [80, 80], [100, 100], [130, 130], [150, 150], [200, 200], [250, 250], [300, 300],
  [350, 350], [400, 400], [450, 450], [500, 500],
];

export type BonusCalcPath = "positive_ngr" | "not_eligible" | "inactive" | "blocked" | "none";

export interface BonusCalcInput {
  active: boolean;
  ggr: number;
  bonus: number;
  purchaseCount: number;
  purchaseAmount: number;
  bonusPctWindow: number;
  bonusPctLifetime: number;
  locked?: boolean;
  lockLabel?: string;
}

export interface BonusCalcResult {
  freeBonus: number | null;
  offerLabel: string;
  bonusStatus: string;
  bonusStatusMult: number;
  recommended: number;
  capNote: string;
  blocked: boolean;
  blockedReason?: string;
  lookupAmount: number;
  cappedByMax: boolean;
  avgPurchaseCapped: boolean;
  ratioUsed: number;
  segmentLabel: string;
  path: BonusCalcPath;
}

function vlookupApprox(key: number, table: Array<[number, ...number[]]>, valueIndex = 1): number {
  if (!table.length) return 0;
  let chosen = table[0][valueIndex] ?? 0;
  for (const row of table) {
    if (key + 1e-9 >= row[0]) chosen = row[valueIndex] ?? 0;
    else break;
  }
  return chosen;
}

function bonusStatusForRatio(ratio: number): [string, number] {
  const r = Math.max(0, ratio);
  let label = BONUS_STATUS_TABLE[0][1];
  let mult = BONUS_STATUS_TABLE[0][2];
  for (const [threshold, tierLabel, tierMult] of BONUS_STATUS_TABLE) {
    if (r + 1e-9 >= threshold) {
      label = tierLabel;
      mult = tierMult;
    } else break;
  }
  return [label, mult];
}

export function applyGwg(baseSc: number | null, gwgPct: number): [number, number] {
  if (baseSc == null || baseSc <= 0 || gwgPct <= 0) return [0, baseSc || 0];
  const gwgSc = Math.round(baseSc * gwgPct * 100) / 100;
  return [gwgSc, Math.round((baseSc + gwgSc) * 100) / 100];
}

export function computeFreeBonus(inp: BonusCalcInput): BonusCalcResult {
  if (inp.locked) {
    return {
      freeBonus: null,
      offerLabel: "No Free Bonus Allowed",
      bonusStatus: "",
      bonusStatusMult: 0,
      recommended: 0,
      capNote: "Locked or self-excluded: no outreach bonus.",
      blocked: true,
      blockedReason: inp.lockLabel || "Locked",
      lookupAmount: 0,
      cappedByMax: false,
      avgPurchaseCapped: false,
      ratioUsed: 0,
      segmentLabel: "",
      path: "blocked",
    };
  }

  const ngr = inp.ggr - inp.bonus;
  const avgPurchase = inp.purchaseCount ? inp.purchaseAmount / inp.purchaseCount : 0;
  const bonusRatio = Math.max(inp.bonusPctWindow, inp.bonusPctLifetime);
  const [statusLabel, statusMult] = bonusStatusForRatio(bonusRatio);
  const segmentPct = inp.active ? BONUS_CALC_ACTIVE_PCT : BONUS_CALC_INACTIVE_PCT;
  const segmentLabel = `${inp.active ? "Active" : "Inactive"} · ${(segmentPct * 100).toFixed(0)}% of NGR`;

  if (inp.active && ngr > 0) {
    let recommended = segmentPct * ngr * statusMult;
    const ratio = avgPurchase > 0 ? recommended / avgPurchase : 0;
    let avgPurchaseCapped = false;
    if (ratio > 4) {
      recommended = avgPurchase * 3;
      avgPurchaseCapped = true;
    } else if (ratio > 2) {
      recommended = avgPurchase * 2;
      avgPurchaseCapped = true;
    }
    const lookupAmount = vlookupApprox(recommended, ACTIVE_POS_NGR_TABLE);
    const cappedByMax = lookupAmount > BONUS_CALC_MAX_BONUS;
    const freeBonus = Math.min(lookupAmount, BONUS_CALC_MAX_BONUS);
    return {
      freeBonus: Math.round(freeBonus * 100) / 100,
      offerLabel: `${Math.round(freeBonus).toLocaleString()} SC`,
      bonusStatus: statusLabel,
      bonusStatusMult: statusMult,
      recommended: Math.round(recommended * 100) / 100,
      capNote: `Flat Elite ${(segmentPct * 100).toFixed(0)}% of NGR × ${statusMult.toFixed(1)} status factor, capped at ${BONUS_CALC_MAX_BONUS.toLocaleString()} SC.`,
      blocked: false,
      lookupAmount,
      cappedByMax,
      avgPurchaseCapped,
      ratioUsed: Math.round(ratio * 100) / 100,
      segmentLabel,
      path: "positive_ngr",
    };
  }

  if (inp.active && ngr <= 0) {
    return {
      freeBonus: null,
      offerLabel: "Not eligible",
      bonusStatus: statusLabel,
      bonusStatusMult: statusMult,
      recommended: 0,
      capNote: "Active player with non-positive 14-day NGR: not eligible for Free Bonus.",
      blocked: false,
      lookupAmount: 0,
      cappedByMax: false,
      avgPurchaseCapped: false,
      ratioUsed: 0,
      segmentLabel,
      path: "not_eligible",
    };
  }

  if (ngr > 0) {
    const recommended = segmentPct * ngr * statusMult;
    const lookupAmount = vlookupApprox(recommended, ACTIVE_POS_NGR_TABLE);
    const cappedByMax = lookupAmount > BONUS_CALC_MAX_BONUS;
    const freeBonus = Math.min(lookupAmount, BONUS_CALC_MAX_BONUS);
    return {
      freeBonus: Math.round(freeBonus * 100) / 100,
      offerLabel: `${Math.round(freeBonus).toLocaleString()} SC`,
      bonusStatus: statusLabel,
      bonusStatusMult: statusMult,
      recommended: Math.round(recommended * 100) / 100,
      capNote: "Inactive player: reactivation bonus from lifetime window.",
      blocked: false,
      lookupAmount,
      cappedByMax,
      avgPurchaseCapped: false,
      ratioUsed: 0,
      segmentLabel,
      path: "inactive",
    };
  }

  return {
    freeBonus: null,
    offerLabel: "No Free Bonus Allowed",
    bonusStatus: statusLabel,
    bonusStatusMult: statusMult,
    recommended: 0,
    capNote: "Non-positive NGR: no free bonus.",
    blocked: false,
    lookupAmount: 0,
    cappedByMax: false,
    avgPurchaseCapped: false,
    ratioUsed: 0,
    segmentLabel,
    path: "none",
  };
}
