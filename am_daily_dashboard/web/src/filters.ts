/** Row sorting and search matching. Pure functions over payload rows. */
import type { Dict } from "./types";

const URGENCY_RANK: Dict = { Today: 0, "48h": 1, Watch: 2, None: 3 };

/** Soonest unlock first; rows with no unlock date sink to the bottom, so an
 *  overdue Take a break is never buried under an open-ended lock. */
export function sortBySoonestUnlock(rows: Dict[]): Dict[] {
  return (rows || []).slice().sort((a, b) => {
    const av = a.unlockRemainingDays;
    const bv = b.unlockRemainingDays;
    if (av == null && bv == null) return 0;
    if (av == null) return 1;
    if (bv == null) return -1;
    return av - bv;
  });
}

export function sortByNumKey(rows: Dict[], key: string, desc?: boolean): Dict[] {
  const d = desc !== false;
  return (rows || []).slice().sort((a, b) => {
    const av = Number(a[key]);
    const bv = Number(b[key]);
    if (Number.isNaN(av) && Number.isNaN(bv)) return 0;
    if (Number.isNaN(av)) return 1;
    if (Number.isNaN(bv)) return -1;
    return d ? bv - av : av - bv;
  });
}

export function sortPlayers(rows: Dict[], mode: string): Dict[] {
  const copy = [...rows];
  if (mode === "priorHigh") return copy.sort((a, b) => (b.priorPriorNum || 0) - (a.priorPriorNum || 0));
  if (mode === "lifetimeHigh")
    return copy.sort((a, b) => (b.lifetimePurchasedNum || 0) - (a.lifetimePurchasedNum || 0));
  if (mode === "gapHigh") return copy.sort((a, b) => (b.sortGap || 0) - (a.sortGap || 0));
  return copy.sort((a, b) => {
    const ra = URGENCY_RANK[a.urgency] ?? 9;
    const rb = URGENCY_RANK[b.urgency] ?? 9;
    return ra !== rb ? ra - rb : (b.sortGap || 0) - (a.sortGap || 0);
  });
}

export function matchesDecline(row: Dict, q: string): boolean {
  if (!q.trim()) return true;
  const s = q.trim().toLowerCase();
  return [
    row.name, row.aid, row.agent, row.agentName, row.reason, row.reasonTable,
    row.purchase7d, row.favouriteGame7d, row.recommendation,
  ].some((v) => String(v || "").toLowerCase().includes(s));
}

export function matchesAid(row: Dict, q: string, extraKeys?: string[]): boolean {
  if (!q.trim()) return true;
  const s = q.trim().toLowerCase();
  if (String(row.name || "").toLowerCase().includes(s) || String(row.aid || "").includes(s))
    return true;
  return (extraKeys || []).some((k) => String(row[k] ?? "").toLowerCase().includes(s));
}
