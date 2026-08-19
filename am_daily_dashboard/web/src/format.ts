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

export function compactMoney(n: number): string {
  const a = Math.abs(n);
  if (a >= 1e6) return "$" + (n / 1e6).toFixed(a >= 1e7 ? 0 : 1) + "M";
  if (a >= 1e4) return "$" + Math.round(n / 1e3) + "K";
  return money(n);
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

/** **bold** spans in the greeting copy, rendered as a hero line. */
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
