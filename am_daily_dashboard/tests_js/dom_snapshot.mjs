// DOM equality harness for the standalone Elite AM Brief HTML.
//
// The ten assertions in render.test.mjs prove the board is not blank. They do
// not prove a refactor changed nothing. This does: it renders every
// (fixture x gate state x agent x view) plus a set of interaction states, and
// records #root.innerHTML + #modalRoot.innerHTML + document.title verbatim.
// Fixture payloads are deterministic (testing/payload_fixtures.py pins the
// date and hand-writes the archive), so any difference between two runs is a
// real behaviour change, not noise.
//
// Usage:
//   node dom_snapshot.mjs --out <dir>     write snapshots (baseline)
//   node dom_snapshot.mjs --check <dir>   re-render and require byte equality
//
// Build fixtures first: python ../testing/build_fixtures.py

import { mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { JSDOM, VirtualConsole } from "jsdom";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const FIXTURES = path.join(__dirname, "fixtures");
const BASE_URL = "https://am-brief.snapshot.local/";

const FIXTURE_NAMES = ["manager", "single_am_coral", "empty_sections_alon", "large_tickets"];

// Every id in the shell's NAV_ORDER. Listed rather than discovered so a view
// silently dropping out of the sidebar shows up as a missing snapshot file
// instead of quietly shrinking the comparison set.
const ALL_VIEWS = ["dashboard", "team", "home", "goals", "top10", "top20",
  "rd", "rdfirst", "tickets", "locks", "birthdays"];

function readFixture(name) {
  return {
    html: readFileSync(path.join(FIXTURES, `${name}.html`), "utf-8"),
    meta: JSON.parse(readFileSync(path.join(FIXTURES, `${name}.meta.json`), "utf-8")),
  };
}

// Loads a board the same way render.test.mjs does: outside-only so the gate can
// be seeded before any script runs, then eval the inline scripts ourselves. The
// application/json filter is what keeps this working across Phase 2 — after the
// payload moves into its own <script type="application/json"> block, an
// unfiltered "first inline script" lookup would find the payload and eval
// nothing, leaving every board blank and every snapshot falsely equal.
function loadBoard(name, { seedGate = null } = {}) {
  const { html, meta } = readFixture(name);
  const errors = [];
  const virtualConsole = new VirtualConsole();
  virtualConsole.on("jsdomError", (err) => errors.push(err));
  const dom = new JSDOM(html, {
    url: BASE_URL,
    runScripts: "outside-only",
    pretendToBeVisual: true,
    virtualConsole,
  });
  if (seedGate) {
    dom.window.sessionStorage.setItem("eliteAmBriefUnlocked", seedGate);
  }
  dom.window.scrollTo = () => {};
  // matchMedia is absent in jsdom and the sidebar toggle reads it; report
  // desktop so the collapse interaction is deterministic rather than throwing.
  dom.window.matchMedia = () => ({ matches: false });
  const scripts = [...dom.window.document.querySelectorAll("script")].filter(
    (s) => !s.src && (s.getAttribute("type") || "").toLowerCase() !== "application/json"
  );
  if (!scripts.length) {
    throw new Error(`${name}: no executable inline <script> found in the shell output`);
  }
  for (const s of scripts) dom.window.eval(s.textContent);
  return { dom, meta, errors };
}

const q = (dom, sel) => dom.window.document.querySelector(sel);
const qa = (dom, sel) => [...dom.window.document.querySelectorAll(sel)];

function clickNav(dom, viewId) {
  const btn = q(dom, `[data-go="${viewId}"]`);
  if (!btn) return false;
  btn.onclick();
  return true;
}

function clickAgent(dom, name) {
  const chip = qa(dom, "[data-agent]").find((b) => b.getAttribute("data-agent") === name);
  if (!chip) return false;
  chip.onclick();
  return true;
}

function capture(dom, errors) {
  const doc = dom.window.document;
  const root = doc.getElementById("root");
  const modal = doc.getElementById("modalRoot");
  return [
    `title: ${doc.title}`,
    `jsdom-errors: ${errors.length}`,
    "--- #root ---",
    root ? root.innerHTML : "(missing)",
    "--- #modalRoot ---",
    modal ? modal.innerHTML : "(missing)",
    "",
  ].join("\n");
}

// Interaction states, keyed by the fixture they are meaningful for. These cover
// the parts no static view snapshot reaches: the calendar popup, the pager, the
// search box, the reason chips, the ticket modal, the sidebar collapse and a
// rejected passcode.
const INTERACTIONS = {
  manager: {
    "cal-open": (dom) => {
      q(dom, "#calBtn").onclick({ stopPropagation() {} });
    },
    "cal-prev-month": (dom) => {
      q(dom, "#calBtn").onclick({ stopPropagation() {} });
      const prev = qa(dom, "[data-cal-month]").find((el) => !el.disabled);
      if (prev) prev.onclick({ stopPropagation() {} });
    },
    "sidebar-collapsed": (dom) => {
      q(dom, "#toggleSidebar").onclick();
    },
    "gate-wrong-passcode": (dom) => {
      clickNav(dom, "dashboard");
      const input = q(dom, "#gateInput");
      if (input) {
        input.value = "not-the-passcode";
        q(dom, "#gateSubmit").onclick();
      }
    },
    "top20-reason-chip": (dom) => {
      clickNav(dom, "top20");
      const chip = qa(dom, "[data-reason-state]").find(
        (el) => el.getAttribute("data-reason") !== "all"
      );
      if (chip) chip.onclick();
    },
    "top20-search": (dom) => {
      clickNav(dom, "top20");
      const input = q(dom, 'input[type="search"][data-state]');
      if (input) {
        input.value = "Coral";
        input.oninput();
      }
    },
    "ticket-modal": (dom) => {
      clickNav(dom, "top20");
      const btn = qa(dom, "[data-ticket-aid]")[0];
      if (btn) btn.onclick();
    },
    "top10-sorted": (dom) => {
      clickNav(dom, "rd");
      const sel = qa(dom, "select[data-state]").find((s) =>
        [...s.options].some((o) => o.value === "oldest")
      );
      if (sel) {
        sel.value = "oldest";
        sel.onchange();
      }
    },
  },
  large_tickets: {
    "tickets-page-2": (dom) => {
      clickNav(dom, "tickets");
      const btn = qa(dom, "[data-page-key]").find((b) => b.getAttribute("data-page") === "2");
      if (btn) btn.onclick();
    },
    "tickets-page-size-all": (dom) => {
      clickNav(dom, "tickets");
      const sel = qa(dom, "select[data-state]").find((s) =>
        [...s.options].some((o) => o.value === "all")
      );
      if (sel) {
        sel.value = "all";
        sel.onchange();
      }
    },
    "tickets-search": (dom) => {
      clickNav(dom, "tickets");
      const input = q(dom, 'input[type="search"][data-state]');
      if (input) {
        input.value = "Player 5";
        input.oninput();
      }
    },
    "tickets-sort-open": (dom) => {
      clickNav(dom, "tickets");
      const sel = qa(dom, "select[data-state]").find((s) =>
        [...s.options].some((o) => o.value === "tickets")
      );
      if (sel) {
        sel.value = "tickets";
        sel.onchange();
      }
    },
  },
  single_am_coral: {
    "cal-open": (dom) => {
      q(dom, "#calBtn").onclick({ stopPropagation() {} });
    },
    "ticket-modal": (dom) => {
      clickNav(dom, "birthdays");
      const btn = qa(dom, "[data-ticket-aid]")[0];
      if (btn) btn.onclick();
    },
  },
  empty_sections_alon: {
    "goals-redirects-home": (dom) => {
      clickNav(dom, "goals");
    },
  },
};

// Which agents to snapshot per fixture. A single-AM file has no switcher, so
// its only reachable agent is its own.
function agentsFor(meta) {
  if (meta.singleAm) return [meta.singleAmName || "(only)"];
  const order = meta.amOrder || [];
  return order.length ? order : ["(default)"];
}

function* cases() {
  for (const name of FIXTURE_NAMES) {
    const { meta } = readFixture(name);
    const gates = meta.managerGate && !meta.singleAm
      ? [["locked", null], ["unlocked", meta.managerGate]]
      : [["locked", null]];
    for (const [gateLabel, gateToken] of gates) {
      for (const agent of agentsFor(meta)) {
        for (const view of ALL_VIEWS) {
          yield {
            key: `${name}__${gateLabel}__${agent}__view-${view}`,
            run: () => {
              const { dom, errors } = loadBoard(name, { seedGate: gateToken });
              if (!meta.singleAm) clickAgent(dom, agent);
              const reached = clickNav(dom, view);
              return `reachable: ${reached}\n` + capture(dom, errors);
            },
          };
        }
      }
      for (const [label, fn] of Object.entries(INTERACTIONS[name] || {})) {
        yield {
          key: `${name}__${gateLabel}__interaction-${label}`,
          run: () => {
            const { dom, errors } = loadBoard(name, { seedGate: gateToken });
            fn(dom);
            return capture(dom, errors);
          },
        };
      }
    }
  }
}

function firstDifference(a, b) {
  const al = a.split("\n");
  const bl = b.split("\n");
  for (let i = 0; i < Math.max(al.length, bl.length); i++) {
    if (al[i] !== bl[i]) {
      return `line ${i + 1}\n    baseline: ${String(al[i]).slice(0, 300)}\n    current:  ${String(bl[i]).slice(0, 300)}`;
    }
  }
  return "(identical line-by-line but differing bytes — check trailing whitespace)";
}

function main() {
  const mode = process.argv[2];
  const dir = process.argv[3];
  if (!["--out", "--check"].includes(mode) || !dir) {
    console.error("usage: node dom_snapshot.mjs (--out|--check) <dir>");
    process.exit(2);
  }

  if (mode === "--out") {
    rmSync(dir, { recursive: true, force: true });
    mkdirSync(dir, { recursive: true });
    let n = 0;
    for (const c of cases()) {
      writeFileSync(path.join(dir, `${c.key}.snap`), c.run(), "utf-8");
      n++;
    }
    console.log(`wrote ${n} DOM snapshots to ${dir}`);
    return;
  }

  const expected = new Set(
    readdirSync(dir).filter((f) => f.endsWith(".snap")).map((f) => f.slice(0, -5))
  );
  const diffs = [];
  let checked = 0;
  for (const c of cases()) {
    const file = path.join(dir, `${c.key}.snap`);
    if (!expected.delete(c.key)) {
      diffs.push(`NEW snapshot with no baseline: ${c.key}`);
      continue;
    }
    const baseline = readFileSync(file, "utf-8");
    const current = c.run();
    checked++;
    if (baseline !== current) {
      diffs.push(`CHANGED ${c.key}\n  ${firstDifference(baseline, current)}`);
    }
  }
  for (const missing of expected) {
    diffs.push(`MISSING — baseline has ${missing} but this run produced no such case`);
  }

  if (diffs.length) {
    console.log(`DOM snapshot check FAILED — ${diffs.length} difference(s) across ${checked} compared snapshot(s):\n`);
    for (const d of diffs) console.log(`  ${d}\n`);
    process.exit(1);
  }
  console.log(`DOM snapshot check PASSED — ${checked} snapshots byte-identical to ${dir}`);
}

main();
