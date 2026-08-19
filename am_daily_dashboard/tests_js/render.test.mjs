// jsdom render tests for the standalone Elite AM Brief HTML
// (handoffs/elite_am_brief_web.html). Fixtures are built by
// ../testing/build_fixtures.py (run via `npm test`'s pretest hook) from pure
// Python payload builders — never from BigQuery, never checked into git.
//
// Two documented jsdom traps this file avoids (see AM_DAILY_DASHBOARD.md):
//  - a file:// document URL is an opaque origin where sessionStorage throws;
//    we load HTML as a string with an explicit https:// url instead.
//  - reaching the gated Manager Dashboard needs sessionStorage seeded BEFORE
//    the inline script runs, so we parse with runScripts:"outside-only",
//    seed storage, then eval the script ourselves.
// Day-click calendar *navigation* is intentionally not exercised — jsdom
// cannot navigate, and a failed attempt leaves the window inert, so every
// later assertion in that test would pass vacuously.

import { test, describe } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { JSDOM, VirtualConsole } from "jsdom";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const FIXTURES = path.join(__dirname, "fixtures");
const BASE_URL = "https://am-brief.render-test.local/";

function readFixture(name) {
  const html = readFileSync(path.join(FIXTURES, `${name}.html`), "utf-8");
  const meta = JSON.parse(
    readFileSync(path.join(FIXTURES, `${name}.meta.json`), "utf-8")
  );
  return { html, meta };
}

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
  // jsdom does not implement window.scrollTo (throws "Not implemented"); the
  // shell calls it on every nav change purely for UX, so stub it rather than
  // letting an unrelated jsdom gap fail every render test.
  dom.window.scrollTo = () => {};
  const scriptEl = [...dom.window.document.querySelectorAll("script")].find(
    (s) => !s.src
  );
  if (!scriptEl) {
    throw new Error(`${name}: no inline <script> found in the shell output`);
  }
  dom.window.eval(scriptEl.textContent);
  return { dom, meta, errors };
}

function content(dom) {
  const el = dom.window.document.querySelector(".content");
  assert.ok(el, "expected a .content element — board did not render at all");
  return el;
}

function clickNav(dom, viewId) {
  const btn = dom.window.document.querySelector(`[data-go="${viewId}"]`);
  if (!btn) return false;
  btn.onclick();
  return true;
}

function visibleNavIds(dom) {
  return [...dom.window.document.querySelectorAll("[data-go]")].map((b) =>
    b.getAttribute("data-go")
  );
}

describe("blank-board guard + nav registry coverage", () => {
  test("manager board renders every visible nav item with no JS errors", () => {
    const { dom, errors } = loadBoard("manager");
    const ids = visibleNavIds(dom);
    assert.ok(ids.length > 5, `expected several nav items, got ${ids.length}`);
    for (const id of ids) {
      assert.ok(clickNav(dom, id), `nav button for "${id}" is missing`);
      const html = content(dom).innerHTML.trim();
      assert.ok(html.length > 0, `view "${id}" rendered blank content`);
    }
    assert.deepEqual(errors, [], "uncaught JS error(s) during render");
  });

  test("single-AM board hides the Command group and still renders every remaining view", () => {
    const { dom, meta, errors } = loadBoard("single_am_coral");
    const ids = visibleNavIds(dom);
    assert.ok(
      !ids.includes("dashboard"),
      "a single-AM file must never expose the Manager Dashboard nav item"
    );
    assert.ok(
      !ids.includes("team"),
      "a single-AM file must never expose the Team Goals nav item"
    );
    for (const id of ids) {
      clickNav(dom, id);
      assert.ok(
        content(dom).innerHTML.trim().length > 0,
        `view "${id}" rendered blank content for a single-AM file`
      );
    }
    assert.deepEqual(errors, []);
    assert.equal(meta.singleAmName, "Coral");
  });

  test("all-empty-sections board (Alon) renders explicit empty states, never a blank page", () => {
    const { dom, errors } = loadBoard("empty_sections_alon");
    for (const id of visibleNavIds(dom)) {
      clickNav(dom, id);
      assert.ok(
        content(dom).innerHTML.trim().length > 0,
        `view "${id}" rendered blank for the all-empty fixture`
      );
    }
    assert.deepEqual(errors, []);
  });
});

describe("per-AM file isolation", () => {
  test("a single-AM export carries no trace of another AM's data or manager-only keys", () => {
    const { html } = readFixture("single_am_coral");
    // Not a bare "Gabriel" check: the shell's static empty-state copy
    // ("Goals are tracked for Coral, Gabriel, Lee and Rachel.") legitimately
    // names every AM regardless of payload — that's template boilerplate,
    // not a data leak. Check actual per-AM fixture data instead.
    assert.ok(
      !html.includes("Gabriel Purchaser One") && !html.includes("gabriel_e"),
      "Coral's file must not carry Gabriel's row data or agent tag"
    );
    assert.ok(
      !html.includes('"managerGate"'),
      "managerGate must never reach a per-AM export"
    );
    assert.ok(
      !html.includes('"teamGoals"'),
      "teamGoals must never reach a per-AM export"
    );
  });
});

describe("manager dashboard gate", () => {
  test("Dashboard is locked without the passcode", () => {
    const { dom } = loadBoard("manager");
    clickNav(dom, "dashboard");
    assert.ok(
      content(dom).innerHTML.includes('id="gateInput"'),
      "expected the passcode gate; board rendered unlocked with no token"
    );
  });

  test("seeding the fixture's own managerGate token unlocks Dashboard and Team Goals", () => {
    const { meta } = readFixture("manager");
    const { dom, errors } = loadBoard("manager", { seedGate: meta.managerGate });
    clickNav(dom, "dashboard");
    assert.ok(
      !content(dom).innerHTML.includes('id="gateInput"'),
      "Dashboard should be unlocked once the real token is remembered"
    );
    clickNav(dom, "team");
    assert.ok(
      !content(dom).innerHTML.includes('id="gateInput"'),
      "Team Goals should also be unlocked by the same gate"
    );
    assert.deepEqual(errors, []);
  });
});

describe("score meter", () => {
  test("scored AM (Coral) never reads Manager Pending", () => {
    const { dom } = loadBoard("manager");
    clickNav(dom, "goals"); // default agent is AM_ORDER[0] = Coral
    const html = content(dom).innerHTML;
    assert.ok(
      !html.includes("Manager Pending"),
      "Coral is scored by the fixture and must not read Manager Pending"
    );
    assert.ok(
      !/trk mgr pending/.test(html),
      "Coral's manager track must not carry the dashed pending class"
    );
  });

  test("unscored AM (Gabriel) reads Manager Pending with a dashed empty track", () => {
    const { dom } = loadBoard("manager");
    const chip = [...dom.window.document.querySelectorAll("[data-agent]")].find(
      (b) => b.getAttribute("data-agent") === "Gabriel"
    );
    assert.ok(chip, "expected an AM switch chip for Gabriel");
    chip.onclick();
    clickNav(dom, "goals");
    const html = content(dom).innerHTML;
    assert.ok(
      html.includes("Manager Pending"),
      "Gabriel is unscored by the fixture and must read Manager Pending"
    );
    assert.ok(
      /trk mgr pending/.test(html),
      "Gabriel's manager track must carry the dashed pending class"
    );
  });
});

describe("archive calendar", () => {
  test("only archive days in the open month are clickable, matching the fixture's own archive list", () => {
    const { dom, meta } = loadBoard("manager");
    const calBtn = dom.window.document.querySelector("#calBtn");
    assert.ok(calBtn, "expected the calendar trigger button");
    calBtn.onclick({ stopPropagation() {} });
    const clickableDays = [
      ...dom.window.document.querySelectorAll(".cal-day.has"),
    ];
    // The popup renders one month at a time (defaults to the report's own
    // month), so only archive dates that fall in that month should show as
    // clickable — the rest need month navigation, not a day click.
    const openMonth = meta.reportDate.slice(0, 7);
    const expected = meta.archiveDates.filter((d) => d.startsWith(openMonth));
    assert.equal(
      clickableDays.length,
      expected.length,
      `expected ${expected.length} clickable day(s) in ${openMonth}, got ${clickableDays.length}`
    );
    const isoOf = (el) => {
      const title = el.getAttribute("title") || "";
      const m = title.match(/\d{4}-\d{2}-\d{2}/);
      return m ? m[0] : null;
    };
    const clickableIsos = clickableDays.map(isoOf).filter(Boolean).sort();
    assert.deepEqual(clickableIsos, [...expected].sort());

    // The one archive date outside the open month must not be clickable
    // here — it needs the prev-month control, not a day click.
    const outOfMonth = meta.archiveDates.find((d) => !d.startsWith(openMonth));
    if (outOfMonth) {
      const day = String(Number(outOfMonth.slice(8, 10)));
      const deadCell = [...dom.window.document.querySelectorAll(".cal-day")].find(
        (el) => el.textContent.trim() === day && !el.classList.contains("has")
      );
      assert.ok(deadCell, `expected ${outOfMonth} to render as a non-clickable day cell`);
    }
  });
});

describe("search, sort and pagination (Open Tickets, 30-row fixture)", () => {
  test("a 30-row list paginates at 25, search narrows it, and page 2 shows the remainder", () => {
    const { dom } = loadBoard("large_tickets");
    assert.ok(clickNav(dom, "tickets"));
    const doc = dom.window.document;

    const rowsInitial = doc.querySelectorAll(".content table tbody tr");
    assert.equal(
      rowsInitial.length,
      25,
      "expected the first page to show exactly PAGE_SIZES[0] = 25 rows"
    );

    const pageTwoBtn = [...doc.querySelectorAll("[data-page-key]")].find(
      (b) => b.getAttribute("data-page") === "2"
    );
    assert.ok(pageTwoBtn, "expected a page-2 control for a 30-row table");
    pageTwoBtn.onclick();
    const rowsPageTwo = doc.querySelectorAll(".content table tbody tr");
    assert.equal(rowsPageTwo.length, 5, "page 2 of 30 rows at size 25 should show 5");
    assert.ok(
      content(dom).innerHTML.includes("Coral Ticket Player 30"),
      "page 2 should contain the last row"
    );

    const search = doc.querySelector('input[type="search"][data-state]');
    assert.ok(search, "expected the search box on Open Tickets");
    search.value = "Player 5";
    search.oninput();
    const filteredRows = doc.querySelectorAll(".content table tbody tr");
    assert.ok(
      filteredRows.length >= 1 && filteredRows.length < 25,
      `search should narrow the list (got ${filteredRows.length} rows)`
    );
  });
});
