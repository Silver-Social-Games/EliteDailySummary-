/** Mutable app state, per-table control state, and the manager gate.
 *
 * Nothing here imports a renderer. Anything that needs the board redrawn calls
 * `rerender()`, which `main.ts` points at `render()` once at bootstrap via
 * `setRenderHook()`. Without that indirection `bind.ts` and `modal.ts` would
 * import `render.ts` while `render.ts` imports them, and the bundle would carry
 * an import cycle whose evaluation order depends on esbuild.
 */
import type { AppState, Dict } from "./types";
import { AGENTS, AM_ORDER, DATA, GATE_TOKEN, HIDE_MANAGER, HOME_AM, PEER_MODE, REPORT } from "./payload";
import { VIEWS } from "./registry";

/* ---------------- manager gate ---------------- */

/* Storage access throws outright where the origin is opaque — a sandboxed
   preview pane, or a file opened through some OneDrive/Office viewers. An
   unguarded read at state init would blank the whole board, so failing to
   remember the unlock is the worst this may cost. */
const GATE_KEY = "eliteAmBriefUnlocked";

function gateRemembered(): boolean {
  try {
    return sessionStorage.getItem(GATE_KEY) === GATE_TOKEN;
  } catch (e) {
    return false;
  }
}

export function rememberGate(): void {
  try {
    sessionStorage.setItem(GATE_KEY, GATE_TOKEN);
  } catch (e) {
    /* opaque origin — the unlock just will not survive a reload */
  }
}

export function gateToken(s: unknown): string {
  let h = 5381;
  for (const ch of String(s)) h = (((h * 33) >>> 0) ^ ch.codePointAt(0)!) >>> 0;
  return h.toString(16).padStart(8, "0");
}

/* ---------------- app state ---------------- */

const firstAgent: string = (AGENTS[0] && AGENTS[0].agentName) || AM_ORDER[0] || "";

export const app: AppState = {
  view: HIDE_MANAGER ? "home" : "dashboard",
  agent: PEER_MODE
    ? HOME_AM || firstAgent
    : DATA.singleAmName || firstAgent,
  unlocked: HIDE_MANAGER || gateRemembered(),
  gateError: "",
  collapsed: false,
  mobileOpen: false,
  ticket: null,
  calOpen: false,
  calMonth: (REPORT.date || "").slice(0, 7),
};

/* ---------------- render hook ---------------- */

let renderHook: () => void = () => {};

export function setRenderHook(fn: () => void): void {
  renderHook = fn;
}

export function rerender(): void {
  renderHook();
}

/* ---------------- per-table control state ---------------- */

const tstate: Dict = {};

export function getState(key: string, fallback: unknown): any {
  if (!(key in tstate)) tstate[key] = fallback;
  return tstate[key];
}

/** Write with no page reset, no focus tracking and no re-render — for a value
 *  computed during rendering, such as a page number clamped to the last page. */
export function putState(key: string, value: unknown): void {
  tstate[key] = value;
}

/* Any control that changes the result set sends the table back to page 1 —
   otherwise a search that narrows 260 rows to 3 lands you on an empty page 7. */
const RESET_SUFFIXES = ["_q", "_search", "_sort", "_sortBy", "_agent", "_reason", "_size"];

let focusKey: string | null = null;

export function setState(key: string, value: unknown): void {
  tstate[key] = value;
  for (const suffix of RESET_SUFFIXES) {
    if (key.endsWith(suffix)) {
      tstate[key.slice(0, -suffix.length) + "_page"] = 1;
      break;
    }
  }
  focusKey = key;
  rerender();
}

/** Page change only. Deliberately does not set `focusKey`: a pager click did
 *  not come from a text field, so nothing should steal focus afterwards. */
export function setPage(key: string, page: number): void {
  tstate[key] = page;
  focusKey = null;
  rerender();
}

/** Read and clear. The caret is restored once, by the render that follows the
 *  keystroke, and must not be yanked back on any later unrelated render. */
export function takeFocusKey(): string | null {
  const key = focusKey;
  focusKey = null;
  return key;
}

export function go(view: string): void {
  if (HIDE_MANAGER && VIEWS[view]?.managerOnly) return;
  app.view = view;
  app.mobileOpen = false;
  rerender();
  window.scrollTo({ top: 0, behavior: "auto" });
}
