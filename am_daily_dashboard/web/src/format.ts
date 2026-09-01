/** Escaping, icons, number formatting. No payload and no state. */

export function esc(s: unknown): string {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** References a <symbol> in the sprite injected from src/icons.svg. */
export function icon(name: string, cls?: string): string {
  return `<svg class="ic ${cls || ""}" aria-hidden="true"><use href="#i-${name}"></use></svg>`;
}

export function toNum(v: unknown): number {
  const n = parseFloat(String(v ?? "").replace(/[^0-9.\-]/g, ""));
  return Number.isNaN(n) ? 0 : n;
}

export function money(n: number): string {
  return "$" + Math.round(n).toLocaleString();
}

/** Integer counts for KPI tiles — always thousands-separated when ≥ 1,000. */
export function fmtCount(n: unknown): string {
  const v = typeof n === "number" ? n : Number(String(n ?? "").replace(/[^\d.-]/g, ""));
  return Number.isFinite(v) ? Math.round(v).toLocaleString() : String(n ?? "0");
}

export function compactMoney(n: number): string {
  const a = Math.abs(n);
  if (a >= 1e6) {
    const m = n / 1e6;
    const absM = Math.abs(m);
    const rounded =
      absM >= 10
        ? Math.round(m)
        : Math.round(m * 10) / 10;
    const body = Number.isInteger(rounded) ? String(rounded) : String(rounded);
    return "$" + body.replace(/\.0$/, "") + "M";
  }
  if (a >= 1e4) return "$" + Math.round(n / 1e3) + "K";
  return money(n);
}

/** Goals points — one decimal when needed, never a trailing .0 */
export function formatGoalPoints(n: number): string {
  if (!Number.isFinite(n)) return "—";
  const rounded = Math.round(n * 10) / 10;
  return Number.isInteger(rounded)
    ? String(Math.round(rounded))
    : rounded.toFixed(1).replace(/\.0$/, "");
}

/** Goals headline % — one decimal when needed, never a trailing .0 */
export function formatGoalPct(pct: number): string {
  if (!Number.isFinite(pct)) return "—";
  const rounded = Math.round(pct * 10) / 10;
  const body = Number.isInteger(rounded)
    ? String(Math.round(rounded))
    : rounded.toFixed(1).replace(/\.0$/, "");
  return `${body}%`;
}

export function initials(name: unknown): string {
  return String(name || "?")
    .trim()
    .split(/\s+/)
    .map((w) => w[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

/** Render **bold** markers inline (no block wrapper). */
export function inlineBold(text: unknown): string {
  return String(text || "")
    .split(/(\*\*[^*]+\*\*)/g)
    .map((part) =>
      part.startsWith("**") && part.endsWith("**") && part.length >= 4
        ? `<strong>${esc(part.slice(2, -2))}</strong>`
        : esc(part)
    )
    .join("");
}

/** **bold** spans in legacy greeting copy, rendered as a hero line. */
export function richText(text: unknown, lead: boolean): string {
  const parts = String(text || "").split(/(\*\*[^*]+\*\*)/g);
  const inner = parts
    .map((part) =>
      part.startsWith("**") && part.endsWith("**") && part.length >= 4
        ? `<em>${esc(part.slice(2, -2))}</em>`
        : esc(part)
    )
    .join("");
  return `<div class="hero-line ${lead ? "lead" : ""}">${inner}</div>`;
}
