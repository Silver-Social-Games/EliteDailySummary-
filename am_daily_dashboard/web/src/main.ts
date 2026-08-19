/** Bootstrap. Registers the render hook and does the two document-level
 *  listeners that must bind exactly once, then draws the first frame.
 */
import { app, setRenderHook } from "./state";
import { render } from "./render";

/* Bound once on document, not re-bound per render: clicking anywhere off the
   calendar closes it, as does Escape. */
document.addEventListener("click", () => {
  if (app.calOpen) { app.calOpen = false; render(); }
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && app.calOpen) { app.calOpen = false; render(); }
});

setRenderHook(render);
render();
