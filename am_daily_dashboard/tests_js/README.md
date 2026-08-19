# AM Brief render tests

jsdom tests for the standalone Elite AM Brief HTML
(`handoffs/elite_am_brief_web.html`). This is the **official product** — see
the elite-am-brief Skill. Canvas (`canvas_parts/`) and the Streamlit app are
compatibility-only and are not covered here.

## Run

```bash
cd am_daily_dashboard/tests_js
npm install        # once
npm test            # rebuilds fixtures (pretest), then runs the suite
```

Or from the repo root, everything (Python unit tests + this suite, skipped
gracefully if Node is missing):

```bash
python -m unittest discover -s am_daily_dashboard
```

## Why this exists

Every real defect this board has shipped (a blank board from an unguarded
`sessionStorage` read, a calendar-less standalone refresh, a per-AM refresh
overwriting the manager file) was payload-correct and JS-broken — nothing
that reads only the JSON, including `verify_brief.py`, would have caught any
of them. This suite executes the real inline `<script>` in a DOM and asserts
on the result instead.

## Fixtures — never committed, never from BigQuery

`../testing/payload_fixtures.py` builds payload dicts by calling the same
production section builders (`goals.py`, `generate_am_daily_dashboard.py`)
with small hand-written rows. `../testing/build_fixtures.py` then calls the
real `canvas_to_html.write_am_brief_html()` to write actual HTML into
`fixtures/` (gitignored) plus a tiny `*.meta.json` per fixture with just the
few values a test needs to assert against (gate token, archive dates —
never the full payload). No query, no credentials, no huge JSON in git.

## Four traps (from AM_DAILY_DASHBOARD.md) this harness already avoids

- **`file://` is an opaque origin** where `sessionStorage` throws. We load
  the HTML as a string with an explicit `https://` document URL instead.
- **Seed the gate before the script runs.** Parse with
  `runScripts: "outside-only"`, seed `sessionStorage.eliteAmBriefUnlocked`
  with the fixture's own `managerGate` token, then `window.eval` the inline
  script ourselves — never guess the plaintext passcode.
- **Day-click *navigation* is not asserted.** jsdom cannot navigate, and a
  failed attempt leaves the window inert, so every later check in that test
  would pass vacuously. We only assert which days render as clickable.
- **jsdom does not implement `window.scrollTo`.** The shell calls it on every
  nav change; `loadBoard()` stubs it so that unrelated gap never fails a test.

## Adding a new section later

Add the payload key + one `VIEWS`/`NAV_ORDER`/`VIEW_FN` entry in the shell as
usual. The "blank-board guard + nav registry coverage" tests iterate
`[data-go]` buttons generically, so a new view is covered automatically —
no test file edit required unless the new view needs its own behavior
assertion (gate, isolation, etc.).
