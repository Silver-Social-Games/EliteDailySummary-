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
/* Peer coverage board: every AM tab present so an AM can cover a colleague,
   but no manager Dashboard/Overview and Goals only on the home AM. */
export const PEER_MODE: boolean = !!DATA.peerMode;
export const HOME_AM: string = String(DATA.homeAm || "");
/* Any per-AM audience (isolated single-AM or peer coverage) hides the manager
   Dashboard, Team Goals and the gate. Only the true manager file keeps them. */
export const HIDE_MANAGER: boolean = SINGLE_AM || PEER_MODE;
export const AUDIENCE_SLUG: string = String(
  DATA.audienceSlug ||
    (SINGLE_AM ? (DATA.singleAmName || "").trim().toLowerCase() : "") ||
    (PEER_MODE ? HOME_AM.trim().toLowerCase() : "")
);
/* Manager-only: the four books measured as one against the manager's own
   targets. Absent from every per-AM payload by construction. */
export const TEAM_GOALS: Dict | null = DATA.teamGoals || null;
/* Fallback matches config.manager_gate_token("elite") so briefs generated
   before the gate existed still open the Dashboard. */
export const GATE_TOKEN: string = DATA.managerGate || "09dcfdd4";

const WD_SHORT = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MON_SHORT = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** ISO date plus `days`, in UTC so no local timezone can shift the day. */
export function shiftIsoDate(iso: string, days: number): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(iso || ""));
  if (!m) return "";
  const d = new Date(Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3]) + days));
  return d.toISOString().slice(0, 10);
}

/** "Sun 27 Sep 2026" (or "Sun 27 Sep" without the year) from an ISO date. */
export function isoDateLabel(iso: string, withYear = true): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(iso || ""));
  if (!m) return "";
  const wd = WD_SHORT[new Date(Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3]))).getUTCDay()];
  const body = `${wd} ${Number(m[3])} ${MON_SHORT[Number(m[2]) - 1]}`;
  return withYear ? `${body} ${m[1]}` : body;
}

/* The brief is read the morning after its data: REPORT.date stays the data
   date (files, queries, archive keys); the board is labelled with the run date. */
export const BRIEF_DATE: string = shiftIsoDate(REPORT.date || "", 1);
export const briefSubtitle: string = BRIEF_DATE ? isoDateLabel(BRIEF_DATE) : String(REPORT.subtitle || "");

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
