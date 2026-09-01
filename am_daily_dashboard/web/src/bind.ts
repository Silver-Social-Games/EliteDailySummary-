/** Event wiring for the current render.
 *
 * Calls `rerender()`, never `render()` directly — see the note in `modal.ts`;
 * the same import-cycle reasoning applies here since `render.ts` imports this
 * module to bind the page it just drew.
 */
import { GATE_TOKEN, REPORT } from "./payload";
import { CRM_BANDS, CRM_DAY_ORDER } from "./data/crmOffers";
import { exportCurrentViewCsv } from "./exportCsv";
import { agentBlock } from "./selectors";
import { app, gateToken, getState, go, rememberGate, rerender, setPage, setState,
  takeFocusKey } from "./state";

export function bind(): void {
  const calBtn = document.getElementById("calBtn");
  if (calBtn) calBtn.onclick = (e) => {
    e.stopPropagation();
    app.calOpen = !app.calOpen;
    if (app.calOpen && !app.calMonth) app.calMonth = (REPORT.date || "").slice(0, 7);
    rerender();
  };
  document.querySelectorAll("[data-cal-month]").forEach((el) => {
    (el as HTMLElement).onclick = (e) => {
      e.stopPropagation();
      app.calMonth = el.getAttribute("data-cal-month")!;
      rerender();
    };
  });
  /* Sibling file in the same folder, so the archive works from a network
     share or a copied folder with no server involved. */
  document.querySelectorAll("[data-cal-open]").forEach((el) => {
    (el as HTMLElement).onclick = (e) => {
      e.stopPropagation();
      window.location.href = el.getAttribute("data-cal-open")!;
    };
  });
  const calPop = document.getElementById("calPop");
  if (calPop) calPop.onclick = (e) => e.stopPropagation();
  document.querySelectorAll("[data-go]").forEach((el) => {
    (el as HTMLElement).onclick = () => go(el.getAttribute("data-go")!);
  });
  document.querySelectorAll("[data-agent]").forEach((el) => {
    (el as HTMLElement).onclick = () => {
      app.agent = el.getAttribute("data-agent")!;
      if (app.view === "dashboard") app.view = "home";
      rerender();
      window.scrollTo({ top: 0, behavior: "auto" });
    };
  });
  document.querySelectorAll("input[data-state]").forEach((el) => {
    (el as HTMLInputElement).oninput = () => setState(el.getAttribute("data-state")!, (el as HTMLInputElement).value);
  });
  document.querySelectorAll("select[data-state]").forEach((el) => {
    (el as HTMLSelectElement).onchange = () => setState(el.getAttribute("data-state")!, (el as HTMLSelectElement).value);
  });
  document.querySelectorAll("[data-reason-state]").forEach((el) => {
    (el as HTMLElement).onclick = () => setState(el.getAttribute("data-reason-state")!, el.getAttribute("data-reason"));
  });
  document.querySelectorAll("[data-page-key]").forEach((el) => {
    (el as HTMLElement).onclick = () => {
      setPage(el.getAttribute("data-page-key")!, Number(el.getAttribute("data-page")));
    };
  });
  document.querySelectorAll("[data-ticket-aid]").forEach((el) => {
    (el as HTMLElement).onclick = () => {
      const aid = el.getAttribute("data-ticket-aid");
      const b = agentBlock();
      const pool = [...(b.decline || []), ...(b.rdFirstTime || []), ...(b.birthdays || [])];
      const p = pool.find((x) => String(x.aid) === aid);
      if (p) { app.ticket = p; rerender(); }
    };
  });

  const toggle = document.getElementById("toggleSidebar");
  if (toggle) toggle.onclick = () => {
    if (window.matchMedia("(max-width: 900px)").matches) app.mobileOpen = !app.mobileOpen;
    else app.collapsed = !app.collapsed;
    rerender();
  };
  const exportBtn = document.getElementById("exportCsv");
  if (exportBtn) exportBtn.onclick = () => exportCurrentViewCsv();

  document.querySelectorAll("[data-crm-toggle]").forEach((el) => {
    (el as HTMLElement).onclick = () => {
      const kind = el.getAttribute("data-crm-toggle");
      const value = el.getAttribute("data-crm-value") || "";
      const allDays = [...CRM_DAY_ORDER];
      const allBands = CRM_BANDS.map((b) => b.id);
      if (kind === "day") {
        let days: string[] = getState("crm_days", allDays);
        days = days.includes(value) ? days.filter((d) => d !== value) : days.concat(value);
        if (!days.length) days = allDays.slice();
        setState("crm_days", days);
      } else if (kind === "band") {
        let bands: string[] = getState("crm_bands", allBands);
        bands = bands.includes(value) ? bands.filter((b) => b !== value) : bands.concat(value);
        if (!bands.length) bands = allBands.slice();
        setState("crm_bands", bands);
      }
    };
  });
  document.querySelectorAll("[data-crm-quick]").forEach((el) => {
    (el as HTMLElement).onclick = () => {
      const quick = el.getAttribute("data-crm-quick");
      if (quick === "all") setState("crm_days", [...CRM_DAY_ORDER]);
      else if (quick === "weekend") setState("crm_days", ["Friday", "Saturday"]);
      else if (quick === "all-bands") setState("crm_bands", CRM_BANDS.map((b) => b.id));
    };
  });

  const gateInput = document.getElementById("gateInput") as HTMLInputElement | null;
  if (gateInput) {
    const submit = () => {
      if (gateToken(gateInput.value) === GATE_TOKEN) {
        app.unlocked = true;
        app.gateError = "";
        rememberGate();
      } else {
        app.gateError = "That passcode does not match.";
      }
      rerender();
    };
    gateInput.onkeydown = (e) => { if (e.key === "Enter") submit(); };
    document.getElementById("gateSubmit")!.onclick = submit;
    if (!app.gateError) gateInput.focus();
  }

  /* Full re-render on every keystroke would otherwise drop the caret. */
  const focusKey = takeFocusKey();
  if (focusKey) {
    const el = document.querySelector(`[data-state="${CSS.escape(focusKey)}"]`);
    if (el && el.tagName === "INPUT") {
      (el as HTMLInputElement).focus();
      const end = (el as HTMLInputElement).value.length;
      try { (el as HTMLInputElement).setSelectionRange(end, end); } catch (e) { /* type doesn't support it */ }
    }
  }
}
