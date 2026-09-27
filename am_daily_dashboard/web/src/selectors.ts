/** Reads of the payload that depend on which AM is currently selected. */
import type { Dict } from "./types";
import { AGENTS, HIDE_MANAGER } from "./payload";
import { app } from "./state";

export function agentBlock(): Dict {
  return AGENTS.find((a) => a.agentName === app.agent) || AGENTS[0] || {};
}

export function rowsFor(key: string): Dict[] {
  return agentBlock()[key] || [];
}

/** Non-Elite big winners appear in every AM tab; dedupe by AID for manager roll-ups. */
export function dedupeBigWinnersByAid(rows: Dict[]): Dict[] {
  const byAid = new Map<string, Dict>();
  for (const r of rows) {
    const id = String(r.aid ?? "");
    if (!byAid.has(id)) byAid.set(id, r);
  }
  return [...byAid.values()];
}

/** Manager file: full book (last 3 days, one row per player). Per-AM files: that AM's list. */
export function bigWinnersRows(): Dict[] {
  if (HIDE_MANAGER) return rowsFor("bigWinners");
  const all: Dict[] = [];
  for (const a of AGENTS) all.push(...((a.bigWinners as Dict[]) || []));
  return dedupeBigWinnersByAid(all);
}

export function uniqueBigWinnersCount(): number {
  return bigWinnersRows().length;
}
