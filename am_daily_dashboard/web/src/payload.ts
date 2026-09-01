/** The report payload and everything derived directly from it. */
import type { Dict } from "./types";

/* Parsed from a <script type="application/json"> block rather than inlined as
   a JS object literal: a raw U+2028 or U+2029 in any payload field is a syntax
   error inside a literal but legal inside JSON text. html_export.py still
   escapes "</" - inside a JSON block a literal </script> would end the element
   early just the same. */
export const DATA: Dict = JSON.parse(
  document.getElementById("am-brief-payload")!.textContent || "{}"
);

export const REPORT: Dict = DATA.report || {};
export const OVERVIEW: Dict[] = DATA.overview || [];
export const AGENTS: Dict[] = DATA.agents || [];
export const AM_SHARES: Dict[] = DATA.amShares || [];
export const AM_ORDER: string[] = DATA.amOrder || [];
export const SINGLE_AM: boolean = !!DATA.singleAm;
export const AUDIENCE_SLUG: string = String(
  DATA.audienceSlug || (SINGLE_AM ? (DATA.singleAmName || "").trim().toLowerCase() : "")
);
/* Manager-only: the four books measured as one against the manager's own
   targets. Absent from every per-AM payload by construction. */
export const TEAM_GOALS: Dict | null = DATA.teamGoals || null;
/* Fallback matches config.manager_gate_token("elite") so briefs generated
   before the gate existed still open the Dashboard. */
export const GATE_TOKEN: string = DATA.managerGate || "09dcfdd4";

export const day: string = REPORT.weekday || "";
export const dayShort: string = REPORT.dayShort || day.slice(0, 3);

export const TITLES = {
  thisPurchase: dayShort,
  priorPurchase: `Last ${dayShort}`,
  purchase7d: "7D PURCHASE",
  lifetimePurchase: "LT Purchase",
  lifetimeHold: "Lifetime Hold",
  favouriteGame7d: "Favourite Game (7D)",
};
