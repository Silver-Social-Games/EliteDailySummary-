/** Looker Account Portal (dashboard 5207) — keep in sync with elite_lib.format. */

const ACCOUNT_PORTAL_BASE =
  "https://lookerpatrianna.cloud.looker.com/dashboards/5207";

/** Purchase filter date value — calibrate via LOOKER_ACCOUNT_PORTAL.md */
export const LOOKER_ACCOUNT_PORTAL_PURCHASE_DATE = "30+day";

export function lookerAccountPortalUrl(aid: unknown): string {
  const id = String(aid ?? "").trim();
  if (!id) return "";
  return (
    `${ACCOUNT_PORTAL_BASE}?Account+ID+=${encodeURIComponent(id)}` +
    `&Purchase+filter+date=${LOOKER_ACCOUNT_PORTAL_PURCHASE_DATE}`
  );
}
