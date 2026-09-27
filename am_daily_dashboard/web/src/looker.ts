/** Looker Account Portal (dashboard 5207) — keep in sync with elite_lib.format. */

const ACCOUNT_PORTAL_BASE =
  "https://lookerpatrianna.cloud.looker.com/dashboards/5207";

/** Looker relative date expression — calibrate via LOOKER_ACCOUNT_PORTAL.md if UI stays 7d. */
export const LOOKER_ACCOUNT_PORTAL_TIMEFRAME = "last+30+days";

export function lookerAccountPortalUrl(aid: unknown): string {
  const id = String(aid ?? "").trim();
  if (!id) return "";
  return (
    `${ACCOUNT_PORTAL_BASE}?Account+ID+=${encodeURIComponent(id)}` +
    `&Timeframe=${LOOKER_ACCOUNT_PORTAL_TIMEFRAME}`
  );
}
