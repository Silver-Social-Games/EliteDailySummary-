// Minimal render check against a REAL generated AM Brief HTML file (not a
// fixture) — closes the loop between "the fixture suite passes" and
// "today's actual export renders". Invoked by verify_brief.py --render-check.
//
// Usage: node real_export_check.mjs <path-to-html>
// Exit code 0 = every visible nav item rendered non-blank with no JS error.
// Prints one PASS/FAIL line per nav item, matching verify_brief.py's style.

import { readFileSync } from "node:fs";
import { JSDOM, VirtualConsole } from "jsdom";

const htmlPath = process.argv[2];
if (!htmlPath) {
  console.error("usage: node real_export_check.mjs <path-to-html>");
  process.exit(2);
}

const html = readFileSync(htmlPath, "utf-8");

const errors = [];
const virtualConsole = new VirtualConsole();
virtualConsole.on("jsdomError", (err) => errors.push(err));
const dom = new JSDOM(html, {
  url: "https://am-brief.render-check.local/",
  runScripts: "outside-only",
  pretendToBeVisual: true,
  virtualConsole,
});
const doc = dom.window.document;

// The payload is its own <script type="application/json"> block, so the gate
// token is read by parsing it — no regex over the file, and no test-only hook
// exposing DATA on window.
let managerGate = null;
const payloadEl = doc.getElementById("am-brief-payload");
if (payloadEl) {
  try {
    managerGate = JSON.parse(payloadEl.textContent).managerGate || null;
  } catch {
    // Non-fatal — the gate just won't be seeded; Command-group views will
    // report as gated below rather than failing outright.
  }
}
if (managerGate) {
  dom.window.sessionStorage.setItem("eliteAmBriefUnlocked", managerGate);
}
dom.window.scrollTo = () => {};

// Skip the JSON payload block: evaluating that instead of the app would leave
// the board blank and every check below would pass vacuously.
const scripts = [...doc.querySelectorAll("script")].filter(
  (s) => !s.src && (s.getAttribute("type") || "").toLowerCase() !== "application/json"
);
if (!scripts.length) {
  console.log("  [FAIL] executable inline <script> not found in export");
  process.exit(1);
}
for (const s of scripts) dom.window.eval(s.textContent);
const navIds = [...doc.querySelectorAll("[data-go]")].map((b) => b.getAttribute("data-go"));
let failures = 0;

if (navIds.length === 0) {
  console.log("  [FAIL] no nav items rendered at all (blank board)");
  failures++;
}

for (const id of navIds) {
  const btn = doc.querySelector(`[data-go="${id}"]`);
  btn.onclick();
  const el = doc.querySelector(".content");
  const ok = !!el && el.innerHTML.trim().length > 0;
  console.log(`  [${ok ? "PASS" : "FAIL"}] view "${id}" renders non-blank content`);
  if (!ok) failures++;
}

if (errors.length) {
  console.log(`  [FAIL] ${errors.length} uncaught JS error(s) during render`);
  for (const e of errors) console.log(`         ${e}`);
  failures++;
} else {
  console.log("  [PASS] no uncaught JS errors during render");
}

process.exit(failures ? 1 : 0);
