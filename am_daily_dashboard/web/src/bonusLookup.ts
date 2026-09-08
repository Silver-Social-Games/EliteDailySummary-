/** Daily Bonus Calculator lookup sidecar (#am-brief-lookup). */

import type { Dict } from "./types";
import { PEER_MODE } from "./payload";

const el = document.getElementById("am-brief-lookup");
export const BONUS_LOOKUP: Dict = el
  ? JSON.parse(el.textContent || '{"rows":[]}')
  : { rows: [] };

export const BONUS_LOOKUP_ROWS: Dict[] = BONUS_LOOKUP.rows || [];

export function bonusRowsForAgent(agent: string): Dict[] {
  return BONUS_LOOKUP_ROWS.filter((r) => String(r.agent || "") === agent);
}

export function bonusRowForAid(agent: string, aid: string): Dict | undefined {
  const needle = String(aid || "").trim();
  if (!needle) return undefined;
  return bonusRowsForAgent(agent).find((r) => String(r.aid || "") === needle);
}

/** Peer coverage board: search the full scoped lookup across all AM tabs. */
export function bonusRowForAidPeer(aid: string): Dict | undefined {
  const needle = String(aid || "").trim();
  if (!needle) return undefined;
  return BONUS_LOOKUP_ROWS.find((r) => String(r.aid || "") === needle);
}

export function bonusRowForAidAny(agent: string, aid: string): Dict | undefined {
  return PEER_MODE ? bonusRowForAidPeer(aid) : bonusRowForAid(agent, aid);
}
