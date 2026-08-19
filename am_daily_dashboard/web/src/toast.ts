/** One transient confirmation at a time, in #toastRoot. */
import { esc, icon } from "./format";

let timer: ReturnType<typeof setTimeout> | undefined;

export function toast(msg: string): void {
  const root = document.getElementById("toastRoot")!;
  root.innerHTML = `<div class="toast">${icon("check", "ic-sm")}${esc(msg)}</div>`;
  clearTimeout(timer);
  timer = setTimeout(() => {
    root.innerHTML = "";
  }, 1800);
}
