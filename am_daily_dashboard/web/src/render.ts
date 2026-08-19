/** The one function that redraws the page.
 *
 * `bind.ts` and `modal.ts` are imported here, not the other way around: they
 * call `state.rerender()`, and `main.ts` points that hook at this `render()`
 * once, at bootstrap. Importing `render.ts` from either of them would make an
 * import cycle whose evaluation order depends on esbuild.
 */
import { REPORT, SINGLE_AM } from "./payload";
import { agentBlock } from "./selectors";
import { app } from "./state";
import { VIEWS, VIEW_FN } from "./registry";
import { sidebar } from "./sidebar";
import { topbar } from "./topbar";
import { bind } from "./bind";
import { renderModal } from "./modal";

export function render(): void {
  /* An AM with no goals (Alon) must not sit on a Goals view. */
  if (app.view === "goals" && !agentBlock().goals) app.view = "home";
  if (VIEWS[app.view] && VIEWS[app.view].managerOnly && SINGLE_AM) app.view = "home";

  const body = (VIEW_FN[app.view] || VIEW_FN.home)();
  document.getElementById("root")!.innerHTML = `<div class="app${app.collapsed ? " collapsed" : ""}${app.mobileOpen ? " mobile-open" : ""}">
        ${sidebar()}
        <div class="main">
          ${topbar()}
          <div class="content">${body}</div>
        </div>
      </div>`;
  document.title = `${REPORT.title || "Elite AM Brief"} · ${REPORT.date || ""}`;
  bind();
  renderModal();
}
