/** Zendesk ticket draft modal — review-only, nothing is auto-sent.
 *
 * Calls `rerender()`, never `render()` directly: `render.ts` imports this
 * module to wire the modal into the page, so the reverse import would be a
 * cycle. `state.setRenderHook()` points `rerender()` at the real `render()`
 * once, at bootstrap in `main.ts`.
 */
import { esc, icon } from "./format";
import { toast } from "./toast";
import { app, rerender } from "./state";

export function renderModal(): void {
  const root = document.getElementById("modalRoot")!;
  const p = app.ticket;
  if (!p) { root.innerHTML = ""; return; }
  root.innerHTML = `<div class="modal-backdrop" id="backdrop">
        <div class="modal-card" id="card">
          <div class="modal-head">
            <span class="card-icon">${icon("ticket", "ic-sm")}</span>
            <div>
              <div class="card-title">Zendesk draft · ${esc(p.name)}</div>
              <div class="card-sub">AID ${esc(p.aid)} · review only, nothing is auto-sent</div>
            </div>
            <div class="spacer"></div>
            <button type="button" class="icon-btn" id="closeX">${icon("x", "ic-sm")}</button>
          </div>
          <div class="modal-body">
            <div class="field-label">Subject</div>
            <input type="text" id="tSubject" value="${esc(p.ticketSubject || "")}">
            <div class="field-label">Message</div>
            <textarea id="tBody" rows="11">${esc(p.ticketBody || "")}</textarea>
          </div>
          <div class="modal-foot">
            <button type="button" class="btn" id="copySubject">${icon("copy", "ic-xs")} Subject</button>
            <button type="button" class="btn" id="copyBody">${icon("copy", "ic-xs")} Message</button>
            <button type="button" class="btn" id="copyBoth">${icon("copy", "ic-xs")} Both</button>
            <div class="spacer"></div>
            <button type="button" class="btn primary" id="openZd">${icon("external", "ic-xs")} Open Zendesk</button>
          </div>
        </div>
      </div>`;
  const close = () => { app.ticket = null; rerender(); };
  const val = (id: string) => (document.getElementById(id) as HTMLInputElement | HTMLTextAreaElement).value;
  const copy = (text: string, what: string) => { navigator.clipboard.writeText(text); toast(what + " copied"); };
  document.getElementById("backdrop")!.onclick = (e) => { if ((e.target as HTMLElement).id === "backdrop") close(); };
  document.getElementById("closeX")!.onclick = close;
  document.getElementById("copySubject")!.onclick = () => copy(val("tSubject"), "Subject");
  document.getElementById("copyBody")!.onclick = () => copy(val("tBody"), "Message");
  document.getElementById("copyBoth")!.onclick = () =>
    copy(`Subject: ${val("tSubject")}\n\n${val("tBody")}`, "Subject + message");
  document.getElementById("openZd")!.onclick = () => {
    if (p.zendeskUrl) window.open(p.zendeskUrl, "_blank", "noopener,noreferrer");
  };
}
