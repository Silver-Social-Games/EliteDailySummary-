# Elite AM Brief

Morning board for Coral, Gabriel, Lee, Rachel, and Alon — complementary to the Elite Daily Decline Top 20.

**Definitions:** [`Elite.MD`](../Elite.MD) · **Decline reasons:** `wow_drop_analysis/wow_drop_reason.py`

---

## Start here

Read this section plus the Skill (`.cursor/skills/elite-am-brief/SKILL.md`) and you
have the current state. Everything below is detail and history.

### Pick up here — next session

**UI pass (Aug 2026) — large uncommitted diff on `am_daily_dashboard/`. Last
verified run: `--date 2026-08-17`, `verify_brief.py --render-check` PASS.
Open from `VIP\Elite_Cursor\AM Brief\2026-08-17_elite_am_brief.html`. User
will paste a fix list in the new chat — start there, do not re-ask defaults.**

Workflow: edit `web/src/*.ts` (+ Python payload/SQL if needed) →
`node am_daily_dashboard/web/build.mjs` →
`python am_daily_dashboard/generate_am_daily_dashboard.py --date YYYY-MM-DD` →
`python am_daily_dashboard/verify_brief.py --date YYYY-MM-DD --render-check`.

Key definitions locked this session:
- **Big Losers** = house GGR ≥ **$5K** (`BIG_LOSER_SECTION_MIN` in `config.py`)
- **Big Winners** = player win ≥ **$20K** (`BIG_WINNER_SECTION_MIN`)
- State chart = bar chart from `data/elite_players_by_state.json`; UNKNOWN → Other
- Manager dashboard = Elite Snapshot + Daily Triggers (not Team snapshot)

**Not updated:** canvas + Streamlit (HTML canonical). Games/Anniversary = coming
soon placeholders. Do not commit unless user asks.

Batch 9 (trending games + dormant favourite game flag) is scoped and parked
— explain plan before building both parts.

Five phases, phase 0 done:

- [x] **Phase 0 — render test harness (done 2026-08-19).** Committed jsdom
  suite lives in `tests_js/` (`render.test.mjs`, `README.md`,
  `package.json`) with Python fixtures in `testing/` (`payload_fixtures.py`
  builds payloads via the real production section builders — no BigQuery, no
  committed JSON; `build_fixtures.py` writes them through the real
  `write_am_brief_html`, so a payload-contract change breaks a fixture, not a
  silent drift). 10 tests: blank-board + full nav coverage across three
  boards (manager / single-AM / all-empty), per-AM isolation, manager gate
  locked-then-unlocked, scored-vs-unscored score meter, archive calendar
  month-scoping, and Open Tickets pagination/search. `npm test` from
  `tests_js/` runs it standalone; `python -m unittest discover -s
  am_daily_dashboard` also runs it via `test_render_js.py` (skips cleanly, not
  a failure, if Node isn't on PATH). **`verify_brief.py --render-check`** now
  additionally renders *today's real* generated HTML in the same way and
  prints PASS/FAIL per nav item — closes the gap where a payload-correct,
  JS-broken board could still pass every existing check.
- [x] **Phase 1 (partial) — `</script>` escape, done 2026-08-19.**
  `elite_lib/html_export.py` now escapes `</` to `<\/` in the injected JSON so
  a stray `</script>` in any field (an AID note, a ticket subject) cannot
  corrupt the page. Still open from Phase 1: nothing blocking — this was the
  one safety fix worth doing immediately; the rest of Phase 1 is documentation
  (this file already states HTML-canonical above).
- [~] **Phase 2 — de-spaghetti the inline JS. Steps 1 and 2 are done and
  committed; step 3 is half-written. Pick up at *Phase 2 progress* below.** The
  design in this bullet is settled and was built as written, not re-decided.
  `handoffs/elite_am_brief_web.html` carries ~1,350 lines of inline `<script>`
  with global mutable state (`app.*`), ad hoc event binding, and per-view
  render functions in one block. Split into modular TS bundled by esbuild into
  one offline `<script>`. The output must stay a **single self-contained HTML
  file** — non-negotiable, OneDrive/offline use depends on it. Run the Phase 0
  suite after every extraction step, not just at the end.

  **Target layout** (`am_daily_dashboard/web/`, new folder): `shell.html` with
  three build markers (`__APP_CSS__`, `__ICON_SPRITE__`, `__APP_JS__`) plus the
  existing `__PAYLOAD_JSON__` left untouched for Python; `src/app.css` and
  `src/icons.svg` **concatenated verbatim** by the build (no esbuild CSS
  processing — zero behaviour risk, and the CSS is not the spaghetti);
  `src/` modules: `types.ts`, `payload.ts`, `state.ts`, `selectors.ts`,
  `format.ts`, `toast.ts`, `cells.ts`, `reason.ts`, `filters.ts`, `table.ts`,
  `components.ts` (statCard / segmentCard / emptyState), `registry.ts`
  (`VIEWS` / `NAV_ORDER` / `GROUP_ORDER`), `views/<one file per sidebar
  section>`, `sidebar.ts`, `topbar.ts`, `calendar.ts`, `modal.ts`, `bind.ts`,
  `render.ts`, `main.ts`. `build.mjs` bundles `src/main.ts` (esbuild, IIFE,
  es2019, **not minified** so the built shell stays diffable) and injects.
  The built file stays at `handoffs/elite_am_brief_web.html`, which
  `canvas_to_html.SHELL` and the `.gitignore` allowlist already point at.

  **Four decisions already made, with the reasons:**

  - **Payload moves to `<script type="application/json"
    id="am-brief-payload">__PAYLOAD_JSON__</script>`**, parsed by
    `payload.ts`. Safer than the current JS object literal (a raw U+2028 is a
    syntax error in a literal but fine in JSON text) and it lets the test
    harness read the gate token instead of regexing it. Keep the `</` escape
    in `html_export.py` — inside a JSON block a literal `</script>` would
    still end the element early, so that fix is what makes this safe.
  - **Two consumers eval the inline script and both must be updated**, or the
    board will silently test as blank: `tests_js/render.test.mjs` and
    `tests_js/real_export_check.mjs` both do
    `[...querySelectorAll("script")].find(s => !s.src)`, which would now find
    the JSON block. Filter out `type="application/json"`, eval the remaining
    inline scripts in order, and replace `real_export_check.mjs`'s
    `/const DATA\s*=\s*(\{...\});\s*\n\s*const REPORT/` regex with a
    `JSON.parse` of the payload block.
  - **No import cycles: re-renders route through `state.rerender()`**, with
    `main.ts` registering `render` via `setRenderHook()` at bootstrap.
    `bind.ts` and `modal.ts` call `rerender()`, never `render()` directly —
    otherwise `render.ts` and `bind.ts` import each other. `focusKey` becomes
    `takeFocusKey()` (read-and-clear) and the pager's direct `tstate` write
    becomes `setPage(key, n)`.
  - **Stale-build guard, because the built shell is now a build output.**
    `build.mjs` embeds `<!-- ... sources sha256:… -->` over the `web/` sources
    (CRLF normalised to LF in both implementations, or a fresh clone
    mismatches), and a Python test recomputes it and fails if someone edited
    TS without rebuilding. This keeps the guard working on a machine with no
    Node, since the shell itself is committed.

  **Verify by DOM equality, not by the 10 assertions.** Before touching
  anything, snapshot `#root.innerHTML` + `document.title` for every
  (fixture × agent × view), locked and gate-seeded, from the **current**
  committed shell into a temp folder; after each extraction step rebuild the
  shell, rebuild fixtures, re-snapshot and require **byte-identical** output.
  The fixture payloads are deterministic (`testing/payload_fixtures.py` pins
  the date and hand-writes the archive), so any diff is a real behaviour
  change. A `tests_js/dom_snapshot.mjs` doing this is worth committing for the
  next refactor.

  **Extraction order that keeps each step verifiable:** (1) scaffold `web/`
  with the entire existing script moved verbatim into one `main.ts` (only
  change: the payload read) and prove the build pipeline renders identically —
  temporarily `// @ts-nocheck`, since esbuild does not typecheck and the types
  arrive with the split; (2) leaf modules; (3) views + components + registry;
  (4) chrome / modal / bind / render / main; (5) wire `npm test`'s `pretest` to
  build the shell before fixtures, add the hash guard test and `tsc --noEmit`,
  then update the Skill routing table to name files instead of functions.

  Environment is ready: Node v24.15.0, npm 11.12.1, registry reachable, so
  `npm i -D esbuild typescript` in `web/` works. `node_modules/` at any depth
  is already gitignored.
#### Phase 2 — done (2026-08-19)

All five steps are committed. `web/src/` is the source of truth for the board's
JS; `handoffs/elite_am_brief_web.html` is the build output. Next work is
Phase 3 — see the checklist a few paragraphs down.

**Two questions the user answered 2026-08-19; do not re-ask.**

- `handoffs/elite_am_brief_web.html` is now a **build output**. Changing the
  board means editing `web/src/*.ts` and running `node web/build.mjs`. The built
  file **stays committed**, so a machine with no Node can still generate briefs.
- **Both** hash guards must **fail loudly** in the test suite: "you edited the
  TS and did not rebuild" *and* "you hand-edited the generated HTML, your change
  will be lost". The second one is why `build.mjs` embeds an `output sha256`
  as well as a `sources sha256` — a source hash alone cannot detect a hand-edit
  of the output.

**Done and committed.** The board builds from `am_daily_dashboard/web/`:
`shell.html` (four markers: `__BUILD_STAMP__`, `__APP_CSS__`, `__ICON_SPRITE__`,
`__APP_JS__`, plus `__PAYLOAD_JSON__` left for Python), `src/app.css` and
`src/icons.svg` concatenated **verbatim**, `src/*.ts` bundled by esbuild
(IIFE, es2019, unminified, `"use strict"` via banner), output written back to
`handoffs/elite_am_brief_web.html` — the path `canvas_to_html.SHELL` and the
`.gitignore` allowlist already point at.

| Commit | Step |
|---|---|
| `e6b3301` | 1 — scaffold `web/`, whole script verbatim in `main.ts`, payload moved to a `<script type="application/json" id="am-brief-payload">` block, both jsdom harnesses updated, `tests_js/dom_snapshot.mjs` added |
| `ff149b3` | 2 — leaf modules: `types`, `payload`, `state`, `selectors`, `format`, `toast`, `cells`, `reason`, `filters`, `table`. `main.ts` 1,361 → 908 lines |
| `709deec` | 3 — `components.ts`, all eleven `views/*.ts`, `registry.ts` (`GROUP_ORDER`/`VIEWS`/`NAV_ORDER`/`VIEW_FN`) |
| `7521bbb` | 4 — `sidebar.ts`, `topbar.ts`, `calendar.ts`, `modal.ts`, `bind.ts`, `render.ts`; `main.ts` reduced to a bootstrap that wires `state.rerender` and document-level listeners |
| (this write-up) | 5 — `pretest` builds the shell before fixtures (`tests_js/package.json`), hash guards re-implemented in pure Python (`test_web_build.py`), `tsc --noEmit` enforced via `test_web_typecheck.py`, Skill routing table now names `web/src/` files. Also fixed a real bug caught while wiring `pretest`: `build.mjs` did not pin `absWorkingDir`, so esbuild's per-module `// src/foo.ts` comments were relative to the *caller's* cwd — running the build from `tests_js/` (`../web/build.mjs`) stamped `../web/src/foo.ts` instead, a spurious diff on every rebuild from a different directory. Fixed with `absWorkingDir: __dirname` |

Step 3 needed no design decisions — every view/`components.ts` file already
existed and typechecked from the step-3-prep commits below; step 3 itself was
purely wiring the registry and deleting the `main.ts` copies. Step 4 needed
one real decision, already applied: `modal.ts` and `bind.ts` call
`state.rerender()` rather than importing `render()` directly, which is what
keeps `render.ts` (which imports `bind`/`sidebar`/`topbar`/`modal`) from
forming an import cycle with the modules it calls back into.

**Model choice, revised 2026-08-19 once the snapshot harness existed.** The
original "use a thinking model for all of Phase 2" was written before there was
any way to detect a silent behaviour change. There is now: 181 byte-exact DOM
snapshots plus 61 tests, and a wrong extraction fails the check rather than
shipping. So **finishing step 3 and doing step 5 are fine on a faster model** —
both are copy-and-delete against a written recipe. **Keep the stronger model for
step 4** (`sidebar`, `topbar`, `calendar`, `modal`, `bind`, `render`, `main`),
where the modules genuinely depend on each other and the render hook has to stay
cycle-free. And in any step: if a snapshot check fails and the cause is not
obvious in a couple of attempts, switch up rather than pushing on — the check
proves *that* something changed, not *what* changed.

**How to verify — this is the whole method, do not substitute the 10 assertions.**

```bash
cd am_daily_dashboard/tests_js
node dom_snapshot.mjs --out %TEMP%\ambrief-baseline    # from a known-good build
# ... extract ... then:
cd ../web && node build.mjs
cd ../tests_js && python ../testing/build_fixtures.py
node dom_snapshot.mjs --check %TEMP%\ambrief-baseline  # must be byte-identical
npm test --silent
```

181 snapshots: every fixture x gate state x agent x view, plus interaction
states (calendar open, prev month, pager, page size, search, reason chip, ticket
modal, sidebar collapse, rejected passcode). Takes ~60s. **A fresh baseline may
be taken from any committed state**, because every committed step is already
proven byte-identical to the pre-refactor shell — the temp folder being wiped
costs nothing.

**Four traps found the hard way this session:**

- **Never dedent a template literal.** The inner lines of the board's multi-line
  template strings are literal DOM whitespace. Module code was re-indented to
  2 spaces but every template literal keeps its original absolute indentation on
  purpose; dedenting them changes the DOM and the snapshot check will fail.
- **The sources hash covers all of `src/**`, imported or not.** Adding a file
  changes the hash, so `node build.mjs --check` fails until you rebuild and
  commit the HTML. That is correct behaviour, not a bug.
- Both harnesses (`render.test.mjs`, `real_export_check.mjs`) filter out
  `type="application/json"` before evaluating inline scripts. Remove that filter
  and every test passes against a blank board.
- Hash LF-normalised text in both implementations. The repo checks out CRLF
  (`core.autocrlf=true`), so raw-byte hashing makes a fresh clone disagree with
  the machine that built it.

- [x] **Phase 2 — modularize the web board's JS.** Done 2026-08-19, all five
  steps committed (table above). `tsc --noEmit` clean, 64 Python tests pass,
  181 DOM snapshots byte-identical to the pre-refactor shell.
- [x] **Phase 3 — extract payload builders (done 2026-08-19).** All pure
  section builders extracted from `generate_am_daily_dashboard.py` into
  `am_daily_dashboard/payload_builders.py` (no BQ, testable directly).
  `generate_am_daily_dashboard.py` is now a thin orchestration shell.
  98 unit tests in `test_payload_builders.py` pass; 162 Python tests total.
  Also extracted: `build_am_shares_and_overview` (closes the `payload_fixtures.py`
  inline-copy NOTE), and `queries._iso(d: date)` guards all SQL date
  interpolations against non-date arguments. SKILL.md routing table updated.
- [x] **Batch 8 item 3 (Big Winners ≥ $20K) — done 2026-08-19.** See Batch 8 item 3 below.

**Model guidance settled with the user 2026-08-19:** use a stronger/thinking
model for Phase 2 (done) and Phase 3 (payload extraction touching the
god-module — same reasoning: real architectural risk, easy to introduce a
subtle behavior change). Phase 0 and Phase 2 step 5 (mechanical verification
and doc updates) were fine on a faster model.

**Nothing from Batches 10–11 is half-finished** — both were verified end to
end on 2026-08-18 and every question they left open has been answered.

**Batch 11 (manager team-total Goals view) is done and verified** — see *Team
Goals* below for the model and every decision the user made. The generator was
re-run for `--date 2026-08-17` after the final change and the output asserted in a
real DOM; exports and the Elite_Cursor mirror are current as of 19:03.

**One thing is worth raising with the user in the next session, and only that:**
the team's Daily Avg Purchase still reads ~$377/day (0.18%) above their own sheet,
and net ~$118/day (0.12%). This is diagnosed, not open — it decomposes into
Rachel's known stale reference row and a $201/day difference on Alon, and Alon's
net matches their sheet to the dollar. **Do not re-investigate it without a fresh
sheet from them.** Ask for an updated table (theirs and Rachel's) and paste it into
`data/elite_goals_reference.tsv` — which now accepts a **`team`** row, so
`--goals-only` prints `Yours` and `Gap` for the manager's own line and the
decomposition no longer has to be done by hand. That closes it in six seconds.

**Batch 8 items 1–3 and 5 are done. Item 4 parked (design locked). Next session:
UI/design improvement pass — ask what feels off, explain plan before building.**
Batch 9 (trending games + dormant favourite game flag) scoped and parked; explain
plan before building both parts.

**Remember the GGR sign** always: `Elite.MD` defines GGR as
`profit − loss` from the house's side, so a player's big win is a **negative** GGR
day. Read it backwards and the whole section inverts.

**Two small carry-overs**, neither blocking:

- **Rachel's row in `data/elite_goals_reference.tsv` is stale** and will keep
  reporting a ~0.4% gap that no code change can close, because her sheet predates a
  backdated assignment. Ask her for a fresh table and replace the row. Do not
  "investigate" that gap again — it is diagnosed in *A pinned re-run is not perfectly
  reproducible*.
- `exports/2026-07-27_elite_am_focus.html` / `.json` are orphans from the board's
  original "Elite AM Focus" name, superseded by the same day's Brief files. Offered
  for deletion 2026-08-18; the user did not decide, so they were left in place.

**Working state (2026-08-19). Everything below is now committed** — the AM Brief
tree is clean and Phase 2 starts from a clean baseline, which is the point: a
Phase 2 diff mixed with Batch 11 would be impossible to roll back. Two commits,
deliberately split:

| Commit | Contents |
|---|---|
| `fb60e63` *Give the AM Brief manager a team-total Goals view* | The whole 2026-08-18 Batch 11 work — the eight files in the table below |
| `36a6b85` *Prove the AM Brief renders before refactoring its JS* | Phase 0 (`tests_js/`, `testing/`, `test_render_js.py`, `verify_brief.py`), the `</script>` escape in `elite_lib/html_export.py`, the two ignore files, and this write-up |

The repo still carries many unrelated modified files from earlier sessions
(birthday_gift, vip_event, daily_summary…) — those were left alone. Baseline at
that point: **61 tests pass**, including the jsdom suite via `test_render_js.py`.

The eight files in `fb60e63`:

| File | Change |
|---|---|
| `am_daily_dashboard/canvas_to_html.py` | `archive_entries` / `with_archive` / `audience_slug` moved here; the writer attaches the archive; `convert()` keeps a per-AM name |
| `am_daily_dashboard/generate_am_daily_dashboard.py` | its archive copy removed, `--html-only` added; team block built and put on the payload; audit includes Team |
| `am_daily_dashboard/goals.py` | `TEAM_AGENT_TAG`, `build_team_goals_block`, `team_actuals`, `include_score` |
| `am_daily_dashboard/queries.py` | `GROUP BY ROLLUP` on the five Goals aggregates; `GOALS_BOOK_TAGS_SQL` (Alon in) vs `GOALS_SCORED_TAGS_SQL` + `scored_book` (shapes unchanged) |
| `am_daily_dashboard/data/elite_goals.tsv` | three `team` rows (Jul/Aug/Sep 2026) |
| `am_daily_dashboard/handoffs/elite_am_brief_web.html` | `sessionStorage` guarded; Team Goals view + Dashboard card |
| `am_daily_dashboard/goals_reference.py` | accepts a `team` row, so the manager's own sheet self-diffs |
| `am_daily_dashboard/test_goals.py` | +22 tests (60 total) |
| `AM_DAILY_DASHBOARD.md` + `.cursor/skills/elite-am-brief/SKILL.md` | this write-up |

Run `python -m unittest discover -s am_daily_dashboard` (61 tests) to confirm the
tree is sound before building on it. The jsdom harness is no longer a temp-folder
recipe — it is committed in `tests_js/` (Phase 0). The *Verify rendering in a DOM*
section below is still worth reading for the four traps it documents, which the
committed harness already avoids.

**State as of 2026-08-18.** Eleven sections per AM tab, plus Overview for the
manager. Elite Goals is built and reconciled: Daily Avg Purchase, Daily Avg Net
Purchase and Monthly Purchasers match the AMs' own table **exactly** for Coral,
Gabriel and Lee (Rachel now differs by one backdated assignment — see *A pinned
re-run is not perfectly reproducible*), % Active lands within a point, and Upgrade
to Elite is **knowingly wrong** and must not be treated as scored. Batches 1 and
3–4 are done; Batch 5 was built and then reverted at the user's request.

Batch 8 items 1 (Top Purchasers price ladder) and 2 (Pending Redemptions big winner
+ docs) shipped 2026-08-18.

**Batch 10 (score out of 100 + archive calendar) is verified end to end
(2026-08-18).** The generator was run for `--date 2026-08-17`, and the generated
files were then rendered in a real DOM and asserted against, not eyeballed. All
three acceptance checks pass: every AM's Goals card reads `NN.N / 80` with a dashed
empty manager track and a `Manager Pending` legend, the topbar calendar opens with
only existing days clickable and navigates to them, and the dateless
`elite_am_brief_<slug>.html` files exist and mirror to Elite_Cursor. Unit tests are
now **50** (38 + 12 new archive/audience tests, minus consolidation). Three real
defects were found by verifying rather than assuming — all fixed, all described
below: the standalone JSON refresh produced a calendar-less file, a per-AM refresh
could overwrite the manager brief, and one unguarded `sessionStorage` read could
blank the entire board.

**Verify rendering in a DOM, not by grepping the HTML.** The legend, the score
meter and the calendar are all built at runtime from the payload, so the literal
string `Manager Pending` does not appear anywhere in the file — searching for it
returns zero and proves nothing. Set up a scratch harness outside the repo:

```bash
mkdir %TEMP%\ambrief-verify && cd %TEMP%\ambrief-verify
npm init -y && npm install jsdom
```

then load the generated file with `runScripts: "dangerously"`, click through
`[data-go="<view>"]` / `[data-agent="<AM>"]` / `#calBtn`, and assert on elements
(`.goal-pct`, `.trk.mgr.pending`, `.score-legend`, `.cal-day.has`). Four traps, each
of which cost time on 2026-08-18:

- Use a normal `https://` document URL. A `file://` URL is an opaque origin where
  jsdom throws on `sessionStorage`, and the board rendered 0 characters.
- Test the day-click navigation **last**. jsdom cannot navigate, and the failed
  attempt leaves the window inert, so every later assertion passes vacuously.
- To reach the gated Dashboard, seed `sessionStorage` with the payload's own
  `managerGate` value before executing the script (`runScripts: "outside-only"`,
  then `window.eval` the inline script). Do not try to guess the passcode.
- Do not assert on exact CSS percentage strings — jsdom normalises `87.50%` to
  `87.5%`, which reads as a failure when nothing is wrong.

To exercise a state the data does not currently contain — a **scored** AM, since
nobody is scored yet — patch a real payload through `goals.build_score_block` and
write it with `write_am_brief_html` to a **temp path**. Never write a dated file into
`exports/`: the archive is built by listing that folder, so a test file becomes a
fake archive entry.

**Batch 7 is done — close it, do not build it.** All four asks exist in the
standalone HTML: left sidebar nav, manager-only gated dashboard, inline SVG icons,
and table pagination (`paginate()`, wired generically through `tableCard` /
`searchableSection` plus Top 20). An earlier note here wrongly said pagination was
outstanding. The canvas and Streamlit implementations do not have the sidebar, so
they have drifted, but that is the known architecture gap, not Batch 7 work.

**Three long-open questions were closed on 2026-08-18** — see the settled table
below: leaderboard ranking, scheduling, and file retention. Nothing about Batch 10
is outstanding now.

**Blocked:** Zendesk auto-create (waiting on API credentials) and the "one month
since AM assignment" rule (definition never settled).

### Do not re-litigate these

Each cost real time to settle. Reasons and rejected alternatives are documented in
the sections named.

| Settled | Short version |
|---|---|
| Book pinning | `as_of` must filter **both** the tag snapshot **and** `agent_start_managed_date`. One without the other silently mixes rosters. → *Pinning takes two filters* |
| Net Purchase | The **by-requested-redeem** variant. → *Net Purchase* |
| Reactivation | 20-day gap off successful payment orders, not 30. → *Tableau is the source of truth* |
| % Active | Last purchase within 30 days over the **whole tagged book**, locked included on both sides. → *A locked player still contributes* |
| Locked players | A tagged player contributes to every KPI regardless of lock status. Never add a lock filter to a Goals numerator. |
| Pace | Saturating KPIs use empirical month-shape divisors, not a linear run rate. → *Why Pace is not a straight run rate* |
| Churned / Active Decliners / Milestone Alerts | Removed. Do not re-add without asking. → *Removed: Churned…* |
| Upgrade to Elite | Unreconciled; every tried definition is listed. Do not adopt the 60-day fit. |
| Score = 80 + 20 | KPI points out of 80 plus the manager's 20, total 100. An unscored AM reads `/80`, **never** `/100`. → *Score out of 100* |
| Two score tracks | The 80 and the 20 are separate bars with a gap and rounded ends. Do not merge them. → *Score out of 100* |
| Archive dates | Built by listing the folder, never by date arithmetic. Per audience, so an AM is only offered days their own file exists for, and the audience comes from the **payload**, not the filename. → *Archive calendar* |
| Late-recorded assignments | A pinned re-run can gain an account whose assignment was backdated, so a sub-1% gap on one AM is expected, not a regression. Never exclude accounts first tagged after the as-of date. → *A pinned re-run is not perfectly reproducible* |
| Leaderboard ranking | Rank on `totalPctOfMax` including mixed scored/unscored, accepted knowing an unscored AM can outrank a scored one. → *Score out of 100* |
| Scheduling | AM Brief stays **manual** — it does not join the Sun–Thu 10:00 task. Run it on request. |
| File retention | **Keep every dated file, no pruning.** Space is negligible (~27 MB/month) and a deleted day cannot be faithfully recreated, since a re-run can return different numbers. → *Archive calendar* |
| Docs column blank | We can only prove "no ticket names a missing document", never that documents are complete. No green all-clear. → *Pending Redemptions big winner and docs* |
| Team targets | Loaded from their own `team` rows, **never** summed from the four AM rows — they do not match. → *Team Goals* |
| Team book includes Alon | The manager owns his portfolio; excluding him understated Daily Avg Purchase ~$4,000/day. He still gets no targets and no Goals section. → *Team Goals* |
| Shape divisors exclude Alon | Measured on the four scored AMs only, so widening the team book cannot move an AM's own pace. → *Team Goals* |
| Team has no score meter | User's call, 2026-08-18: the team view carries **no** 80 + 20 meter and no `/80`. The KPI table stands alone. → *Team Goals* |
| No per-AM breakdown on the team view | Built, shown, and dropped — "my team goals are not an add up of my employees". → *Team Goals* |
| Team ratios | ARPPU and % Active are rebuilt from book totals, never averaged across the AMs. → *Team Goals* |

### Three habits that caused the worst mistakes here

- **Reconcile with the reference file, not by reading numbers aloud.** Paste the
 AM's figures into `data/elite_goals_reference.tsv` and `--goals-only` prints the
 gaps. A 32-account roster leak survived two days because nothing compared the two
 sets automatically.
- **When an instruction and existing code disagree, ask.** Do not write a doc line
 that entrenches the code — that is exactly how three excluded sections stayed in
 the board for days.
- **Run the generator before writing the doc, not after.** Batch 10 was documented
 as finished while never having been executed once, because the write-up came first
 and the session then ran out of room. Passing unit tests and a JS syntax check do
 not tell you the payload reaches the renderer. Verification is the deliverable;
 documentation is the receipt.

---

## Run

```bash
cd "c:\Users\Owner\Downloads\Elite"
python am_daily_dashboard/generate_am_daily_dashboard.py
python am_daily_dashboard/generate_am_daily_dashboard.py --date 2026-07-27
python am_daily_dashboard/generate_am_daily_dashboard.py --date 2026-07-27 --html-only
```

### Daily catch-up and month backfill

Use `generate_am_brief_range.py` when building or extending the archive calendar
(more than one report date on disk). Each day still runs the same pipeline as a
single `--date` generate; archive refresh runs after each day automatically.

| Use | Command |
|---|---|
| **Daily** (after first single-day run) | `python am_daily_dashboard/generate_am_brief_range.py --catch-up --verify` — **`--verify` only** (~5s); add `--render-check` after UI/shell edits, not every morning (locked 2026-08-24) |
| Backfill August | `python am_daily_dashboard/generate_am_brief_range.py --from 2026-08-01 --to 2026-08-31 --skip-existing` |
| Preview dates | add `--dry-run` |
| Re-skin saved month | `--from … --to … --html-only` |

`--catch-up` generates from the day **after** the newest saved manager JSON through
yesterday, skipping dates that already exist. First run ever still needs one
single-day generate to seed the archive.

Default report date = **yesterday**. The brief is **manual by design** — it is not
part of the Sun–Thu 10:00 scheduled task (settled 2026-08-18).

**`--html-only` rebuilds all ten HTML files from that date's saved JSON with no
BigQuery query** (~3s vs ~90s), then mirrors them. Reach for it after every edit to
`handoffs/elite_am_brief_web.html`; a full run only exists to fetch data. Per-AM
files are re-derived through `strip_payload_for_am` rather than read back from their
own JSONs, so the output cannot drift from a real run. It refuses to guess if the
date's JSON is missing.

AM Brief does **not** publish to GitHub Pages. Open the HTML from
`VIP\Elite_Cursor\AM Brief` (a working copy also stays in
`am_daily_dashboard/exports/`). Use `--publish` only if you intentionally need a docs copy.

---

## Output

| Artifact | Path |
|----------|------|
| Canvas | `~/.cursor/projects/.../canvases/elite-am-brief-YYYY-MM-DD.canvas.tsx` (+ per-AM `…-coral/gabriel/lee/rachel.canvas.tsx`) |
| HTML (manager) | `am_daily_dashboard/exports/YYYY-MM-DD_elite_am_brief.html` — Overview + AM tabs |
| HTML (per-AM) | `…_elite_am_brief_{coral\|gabriel\|lee\|rachel}.html` — that AM only (no Overview / switcher) |
| JSON | matching `.json` next to each HTML |

HTML is built by injecting the JSON payload into `handoffs/elite_am_brief_web.html` via `canvas_to_html.write_am_brief_html` (not a static table dump).

Standalone refresh from existing JSON:

```bash
python am_daily_dashboard/canvas_to_html.py am_daily_dashboard/exports/YYYY-MM-DD_elite_am_brief.json
```

---

## Delivery to AMs (not git, not GitHub Pages)

AM Brief is **private HTML**. Coral and the other AMs do **not** get it from git or
the Elite Daily Summary site. Two paths:

### Planned daily path: Slack DM (Sun–Thu 10:00 IL)

Each morning the scheduled task generates yesterday's brief, then `post_am_brief_slack.py`
builds a **stripped per-AM HTML** and DMs it as a file attachment to each AM's Slack
user id.

Setup (once):

1. Copy `am_daily_dashboard/data/am_slack_recipients.local.json.example` →
   `am_slack_recipients.local.json` and fill real Slack user IDs.
2. Add `SLACK_BOT_TOKEN` to `_local_credentials.py` (gitignored).
3. Register Task Scheduler: `am_daily_dashboard/run_am_brief_scheduled.ps1 -EnableAmBriefSlack`

Dry-run before go-live:

```powershell
$env:AM_BRIEF_SLACK_ENABLED='1'
python am_daily_dashboard/post_am_brief_slack.py --dry-run
```

Go-live send (after catch-up):

```bash
python am_daily_dashboard/generate_am_brief_range.py --catch-up --verify
python am_daily_dashboard/post_am_brief_slack.py --skip-catch-up
```

See `@elite-am-brief` **Slack go-live** for the Sunday 2026-08-31 kickoff schedule.

### Ad hoc / review today: send Coral the file manually

Generate Coral's isolated copy:

```bash
python am_daily_dashboard/generate_am_daily_dashboard.py --date YYYY-MM-DD --html-only --cursor-audience coral
```

That writes **`elite_am_brief.html`** under Elite_Cursor (Coral-only payload, no other
AMs). Attach or share:

| Method | File |
|--------|------|
| Slack DM (one-off) | Run `post_am_brief_slack.py --date YYYY-MM-DD` with only Coral's id filled |
| Email / Teams | Attach `VIP\Elite_Cursor\AM Brief\elite_am_brief.html` after `--cursor-audience coral` |
| OneDrive link | Share the file or folder if Coral has access to `VIP\Elite_Cursor\AM Brief` |

**Preview locally (you):** use `elite_am_brief_coral.html` in the same folder — same
content, slugged filename for your archive.

Coral opens the HTML in a browser (double-click or drag into Chrome/Edge). No server
required; calendar links work as sibling files in the same folder.

---

## Sections

### Overview
1. Greeting (once)
2. **Elite & Jackpota** weekday summary + **AM Share Of Elite** (incl. Purchased Of Portfolio)
3. AM Overview metrics (click AM pill → that AM tab only)

### Manager only (gated, never in a per-AM file)
1. **Manager Dashboard** — roll-up cards, Team Goals card, Goals Leaderboard, AM Share, AM Overview
2. **Team Goals** — the whole managed book (Alon included) against the manager's own
   targets. **No** score meter and **no** per-AM breakdown. See *Team Goals* below

### Per AM tab
1. Empowering intro with AM share of Elite + purchased players out of book
2. **Elite Goals** (Coral / Gabriel / Lee / Rachel only — Alon omitted) — current month targets from versioned TSV, MTD actuals, pace, gap, status, weight %, and weighted tracking over the included **80%** KPI weight (manager 20% out of scope). See Goals section below.
3. **Elite & Jackpota** weekday summary (same as Overview)
4. **Morning Checklist** (metric labels jump to sections)
5. **Top 10 Purchasers** — Purchases (#), Top Offer, **Price** (that offer's cost as paid; suffixed `avg` in warning tone if the same offer was bought at more than one amount), **Usual → Ceiling (30D)** price ladder. No Qty / Offer $. See *Top Purchasers price ladder* below
6. **Top 20 · WoW Purchase Gaps** — Daily Elite selection/classify logic, up to 20 per AM
7. **Pending Redemptions** — locked RD ≥ $5,000 created in last **3 days**. Sort: Amount ↓ (default), Won Yesterday ↓, or Oldest first. Created date shows `(Nd ago)` and turns danger-red once a row is within 1 day of the lookback window edge (aging highlight). Then **Won Yesterday** (`· Big Winner` at ≤ −$5,000 GGR), **Docs**, **LTP**, **Hold**, **7D Purchase** — see *Pending Redemptions big winner and docs* below
8. **First-Time Locked RD** — section always shown (empty when none). Ticket column offers a Zendesk draft (review-only), gated by the account's own locked/self-exclusion status
9. **Birthdays · Last 3 Days** — DOB as D/M/Y + Age. Ticket column offers a Zendesk birthday-message draft (review-only), same lock gate
10. **Open Tickets** — LTP, Hold, 7D Purchase + Ticket TIDs link to Zendesk. Sort: LTP ↓ (default), Open Tickets ↓, or 7D Purchase ↓
11. **Locked And Take A Break** — two ways in (`LOCKS_WINDOW_DAYS` / `LOCKS_REVIEW_WINDOW_DAYS`, config.py): still locked **and** (`DATE(locked_at) = report_date`, any reason — the "just happened" feed) **or** (Take a break only, unlock date within 3 days or already passed — regardless of how long ago it started, so a stale overdue break is never missed just because it's no longer "new"). Rows sort by soonest unlock automatically; today/overdue take-a-break rows render in danger tone. **A take-a-break row stays on the board on every subsequent report while the account is still locked and the unlock date is within 3 days or overdue** (e.g. Kristi Couch, unlock 25 Aug, shows 22–25 Aug with countdown). It drops off only after UAM unlocks the account, not on the unlock calendar date alone.

---

## Elite Goals

**Targets file (versioned):** `am_daily_dashboard/data/elite_goals.tsv` (copied from the Downloads
`Elite Goals.tsv` source — do not edit/delete the original Downloads file for generator
reproducibility). Year/month selected from `report_date`.

**Weights (locked, sum = 80%):** Daily Avg Purchase 15%, Daily Avg Net Purchase 15%,
Monthly Purchasers 15%, ARPPU 15%, Reactivation 8%, Upgrade to Elite 5%,
% Active from portfolio 7%. Remaining 20% (manager eval) is **out of scope** for the
headline score.

**Headline display (locked 2026-08-25):** personal AM, Team Goals, and Goals
Leaderboard show **KPI points ÷ 80 × 100** as `%` only (e.g. 78/80 → `97.5%`).
No raw `NN / 80`, no `/100`. Full spec: [`GOALS_DISPLAY.md`](GOALS_DISPLAY.md).

**AMs with Goals:** Coral (`coral_s`), Gabriel (`gabriel_e`), Lee (`lee_t`),
Rachel (`rachel_a`). **Alon:** no Goals section / no Goals-bearing per-AM export.

**`% Active from portfolio`** is accounts whose last successful purchase falls
within 30 days of the as-of date, over the **whole tagged book, locked included**
on both sides of the ratio. The 96% target is a deliberate stretch goal.
`portfolioLocked` stays in the payload and on the audit line so the locked drag is
visible without being subtracted. Two earlier answers were wrong and are recorded
below so they are not tried again: unlocked-only, and an invented "eligible"
subset. See *A locked player still contributes to every KPI*.

**`Upgrade to Elite` is the one KPI that does not reconcile** and it is not safe
to score. The board credits the first in-month Elite tag snapshot, giving 53/46/48/26
for Aug 1–17 2026 against the AM's 8/6/7/9 — an order of magnitude apart, so this
is a different set of accounts, not a dating rule. Ruled out on 2026-08-18:
`agent_start_managed_date` in month (38/43/46/24), plus a "never under another AM"
filter (unchanged, 38/43/46/24), and first-ever purchase or account creation
inside the month (0 for everyone).

The AM's reading is "a new user has an AM tag per the date change". The closest
fit is managed date in month **and** account created within 60 days before month
start, giving 7/6/8/4 — right magnitude, and exact only for Gabriel. Windows from
30 to 365 days were swept on both an absolute and a per-account relative basis and
none reproduces all four. **Do not adopt the 60-day fit**; it is tuned to the data,
which is exactly the mistake the "eligible" subset made on % Active. This KPI was
also force-scored at 100% in [`goals_q2_2026/METHODOLOGY.md`](../goals_q2_2026/METHODOLOGY.md),
so it has never had a working data definition here. Waiting on the Tableau field.

### Net Purchase: use the by-requested-redeem variant

`Net Purchase` on this board is the **by requested redeem** variant, confirmed
with the user 2026-08-18 as "the most valid one":

```
purchased − (requested redeem − cancelled) − chargeback − refunds
```

Implemented as `purchased − redeemed_amt_confirmed_locked_pre − chargeback −
refunds` in `goals_mtd_actuals_sql`. That column on
`jackpota_agg.daily_player_revenue_kpis` is the daily precomputed
confirmed + locked + pre_authorized withdraw-request amount — i.e. requested
redeems net of cancelled / declined / failed. Verified exactly equal to those
status sums from `transactional_data.payment_withdraw_money_requests` for all
four AMs over 2026-08-01..16.

**Do not rebuild this from request `status` directly.** `status` is
current-state, so a request that was locked on the report date can be cancelled
later and a status rebuild silently rewrites history. The precomputed daily
column is fixed at its snapshot.

Formula provenance: `net_purchases_byreq` in
`dbt_analytics_mart.abuse_score_daily` /
`dbt_aninditac.int_abuse_score__daily_player_facts` matches
`purchased − redeem_req_minus_cancelled − chargeback − refunds` on 3.67M of
3.67M rows. Neither model can serve this board directly — the mart covers only
~499 accounts and the intermediate stops at 2026-06-02 — but they pin the
formula.

Impact vs the previous paid-redeem variant (Aug 1–16): Coral $33,951 → $24,485,
Gabriel $31,162 → $24,743, Lee $38,205 → $25,576, Rachel $33,093 → $24,969. All
four now read Behind on the $30,000 goal where three previously read On track.
`print_goals_audit` prints the paid-redeem figure on a `(net if paid-redeem
instead)` line, and the payload carries `mtdNetPurchasePaidRedeem` /
`dailyNetPaidRedeem`, so any gap against the Goals sheet stays explainable.

Residual against the user's sheet is ~3% (Coral $24,485 vs $23,703), consistent
with withdraw-request statuses having moved since their sheet was computed.

### Activity windows: the two KPIs do not share one

**Superseded, and the correction matters — an earlier version of this section said
both `% Active` and `# Reactivation` were calendar-month-to-date. That is wrong for
`% Active`, and "fixing" it back to a calendar month breaks Tableau parity.** The
settled definitions, in *Tableau is the source of truth*, are:

| KPI | Window | Scoped to the month? |
|---|---|---|
| `% Active from portfolio` | last purchase **within 30 days of the as-of date** | No — rolling, point-in-time |
| `# Reactivation` | purchase after a gap of **≥20 days**, counted once per AID | Yes — crossings inside the month |

`% Active` is deliberately a rolling rate because that is what the AMs are measured
on, and because it is already a month-end figure it is never extrapolated (see
*Why Pace is not a straight run rate*). Only `# Reactivation` accrues within the
month and therefore paces linearly.

**Window sensitivity is still the first thing to check when an external sheet
disagrees.** Measured for Coral before the definitions were settled, varying only
the window — the absolute values are stale (this used a 594 unlocked denominator and
a 30-day gap, both since corrected), but the spread is the point:

| Window | Purchasers | % of 594 unlocked | Reactivations |
|---|---|---|---|
| MTD Aug 1–16 | 472 | 79.5% | 30 |
| MTD Aug 1–18 | 482 | 81.1% | 32 |
| Trailing 30d to Aug 16 | 530 | 89.2% | 51 |
| Trailing 31d to Aug 16 | 533 | 89.7% | 54 |
| July full month | 554 | 93.3% | 62 |

Reactivation is the most window-sensitive KPI on the board: a trailing 31 days
returned 54 against 30 for the calendar month, an 80% swing from the window alone.
That sensitivity is why the 20-day gap had to be read off the Tableau query rather
than guessed, and why a Reactivation mismatch should always be treated as a window
question first.

### A locked player still contributes to every KPI

**Standing rule (user, 2026-08-18): if a player is tagged to an AM and made any
purchase during the calendar month, his activity counts toward every KPI — being
locked does not remove his contribution.** A lock is an account-status event, not
a statement that the revenue never happened, and the AM should get credit for
work that already landed.

This is why the Goals numerators never filter on `uam_accounts.locked`:
Daily Avg Purchase, Daily Avg Net Purchase, Monthly Purchasers, ARPPU,
Reactivation and Upgrade all include locked accounts by design. **Do not add a
lock filter to any of them.**

`% Active from portfolio` was the one exception. **Its denominator is the whole
tagged book, locked included** — settled 2026-08-18 by comparing against the AM's
own table.

Two wrong answers were tried first, so do not revisit them:

1. **Unlocked only** (Coral 594). Came from an early instruction, contradicted by
 the standing rule above.
2. **An "eligible" subset** — unlocked plus locked accounts that bought this
 month. Invented as a compromise; it inflated % Active by 4–5 points.

The full book reproduces the AM's figures for Aug 1–17 2026:

| AM | Board | Their table |
|---|---|---|
| Gabriel | 83.0% | 82.0% |
| Rachel | 85.2% | 85.0% |
| Lee | 85.6% | 83.0% |
| Coral | 85.5% | not supplied |

`portfolioSize` and `portfolioSizeAll` are therefore the same number now.
`portfolioLocked` still reports the locked count so the drag stays visible, but it
is **not** subtracted anywhere.

### The Goals book is pinned to the report date

Tags are re-snapshotted daily and the books move fast — **Rachel went from 557 to
589 tagged accounts between 2026-08-16 and 08-18**. The Goals query used to read
the newest snapshot available, so an Aug 16 report scored Aug 1–16 activity
against the Aug 18 roster, and re-running the same date on a later day returned
different numbers.

`dashboard_elite_ctes(as_of=...)` now pins the tag snapshot to the newest one on
or before the report date, and `goals_mtd_actuals_sql` passes it. Effect on
Monthly Purchasers for Aug 16: Rachel 429 → 456, Gabriel 476 → 478, Coral 472 →
471, Lee unchanged. Coral's Daily Avg Net Purchase also moved to $23,480 against
the $23,703 on the AM's table — 0.9% off, down from 3.3%.

Pass `as_of` for anything **scored or compared across dates**. Leave it off for
genuinely live sections — Locked/Take A Break and Pending Redemptions are about
what an AM must act on right now, so the current roster is correct there.

#### Pinning takes two filters, not one — `agent_start_managed_date`

Pinning the tag snapshot alone was not enough, and the leak was easy to miss. The
agent resolves as `COALESCE(t.tag_agent_1, e.agent_name)`, and `agent_name` on
`dbt_aninditac.elite` is **current state**. Any account with no tag row on the
as-of date therefore entered through the fallback no matter what the pin said.

On 2026-08-17 that pulled **32 accounts into Rachel's book** that were not hers
that day, and because newly assigned players buy but have barely redeemed, it
inflated her Daily Avg Net Purchase by 11% — more than her gross (7%). Coral and
Lee gained nobody that day and matched the AM's table to the dollar, which is
what made the fault look like a Rachel-specific net-purchase problem rather than a
book problem.

`dbt_aninditac.elite.agent_start_managed_date` is a real assignment date, so
`as_of` now also filters `agent_start_managed_date IS NULL OR <= as_of`. NULL is
kept — those are legacy rows with no date recorded, not late arrivals.

This reproduces **all four AMs' own figures exactly** for Aug 1–17 2026:

| AM | Book | Daily Avg Purchase | Daily Avg Net | Purchasers |
|---|---|---|---|---|
| Coral | 621 | $56,387 | $24,122 | 482 |
| Gabriel | 646 | $43,549 | $23,350 | 482 |
| Lee | 623 | $54,970 | $24,929 | 476 |
| Rachel | 561 | $48,537 | $24,177 | 433 |

The managed date is also what separates two cases that no tag-history rule could
tell apart, so **do not replace it with a "first tagged" proxy**: all 34 disputed
accounts were first tagged on Aug 18, but Gabriel's 2 have a managed date of
Aug 17 (he owned them, they stay) while 28 of Rachel's 32 start Aug 18 (they go)
and 4 have much older dates (they stay). That is why her book lands on 561 rather
than 557 or 589.

Two rules were tried and rejected — do not revisit: excluding accounts first
tagged after the as-of date (drops Gabriel's 2 and breaks him by 4%), and
excluding only reassignments from another AM (all 34 were previously untagged, so
it changes nothing).

**Not** an upgrade definition: `agent_start_managed_date` inside the month gives
38/43/46/24 against the AM's 8/6/7/9. Use it to date *membership*, never to score
upgrades — see the Goals definitions section for everything already ruled out.

#### A pinned re-run is not perfectly reproducible, and that is not a bug

Pinning fixed the large drift, but it cannot fix all of it, so **do not treat a
small gap against a reference row as a regression to hunt.** Both fields the pin
relies on — `agent_name` and `agent_start_managed_date` — are current state that
can be written *later* with a date *earlier* than the as-of. When an assignment is
recorded after the fact, a re-run of the same past date legitimately gains an
account it did not have before.

Measured on the 2026-08-18 re-run of `--date 2026-08-17`: Rachel's book read 562
against the 561 recorded above, and her Daily Avg Purchase came out $177/day over
her own table. That is **exactly one account** — AID 476756100, managed date
2026-08-15, first tag snapshot 2026-08-18, $3,009.21 MTD, and `$3,009.21 / 17 =
$177.01`. Her sheet was captured before that assignment record existed, so the
board is now arguably the more correct of the two; the reference row is simply
older than the roster.

**Do not "fix" this by excluding accounts first tagged after the as-of date.** That
rule is already rejected above and this run shows why again: Gabriel has two such
accounts (AIDs 202295060 and 70046940, both managed 2026-08-17, first tagged
2026-08-18) worth $1,823/day, and he reconciles to the dollar **with** them. The
same shape of account is right for him and late for her, and no rule reading tag
history can tell the two apart.

Practical consequence: when the audit shows a sub-1% gap on one AM only, check the
book for a late-recorded assignment before suspecting the KPI. The diagnostic is a
join of the pinned book against `MIN(snapshot_date)` per account, filtered to
`first_snapshot > as_of`. And refresh
[`data/elite_goals_reference.tsv`](data/elite_goals_reference.tsv) when an AM
re-sends their table — a stale row will keep reporting a gap that no code change
can close.

### Tableau is the source of truth for Reactivation and % Active

The AMs are measured on a Tableau report, so the board reproduces **its**
definitions rather than inventing parallel ones. Source of truth:
[`elite_reference/Daily_Agg_Per_Player_Query_v1.sql`](../elite_reference/Daily_Agg_Per_Player_Query_v1.sql).

Three things had to change to match it, all settled 2026-08-18:

| | Board before | Tableau / board now |
|---|---|---|
| Purchase source | `daily_player_revenue_kpis.purchased > 0` | `payment_payment_orders` WHERE `success` |
| Reactivation gap | 30 days | **20 days** (`params.churn_period_days`) |
| % Active numerator | bought at some point this month | last purchase **within 30 days** of as-of |

The gap value is the one that mattered. That query's `params.churn_period_days`
is **20**, and its `is_reactivated_today` is "purchased today AND gap from
previous purchase >= churn_period_days". Its inline comments still say 10 —
**they are stale, trust the param.** 20 reproduces Coral's Tableau figure for
Aug 1–16 2026 exactly (55); 30 returns 30.

`% Active` is point-in-time — the share of the book still inside the inactivity
window — not a count that accumulates through the month. So it is **not paced**:
Pace equals Actual, same as a daily average. Coral reads 85.5% against the sheet's
85%. The denominator is the **whole tagged book, locked included** (see *A locked
player still contributes*); an earlier draft of this line said "unlocked book",
which was the first of two wrong answers on that denominator.

Both live in `config.py` as `GOALS_REACTIVATION_GAP_DAYS` and
`GOALS_ACTIVE_LOOKBACK_DAYS`. If that SQL is re-exported, re-check them against
it before trusting any mismatch report.

**Consequence worth reviewing:** on the 20-day definition Coral is already at 55
reactivations by day 16 against a **53/month** goal, pacing to ~107. The 53 goal
lines up almost exactly with the *30-day* pace (58), which suggests the Goals
TSV was calibrated on a 30-day definition while Tableau reports 20-day. The
board now matches Tableau; the goal may need restating.

**As-of / current month:** MTD through `report_date` inclusive (e.g. `--date 2026-08-16`
uses Aug 1–16 only; does not include the next calendar day). First version is
current month only.

| KPI | MTD Actual | Pace (month-end projection) |
|-----|--------|------|
| Daily Avg Purchase | MTD `SUM(purchased) / d` after account/date agg | = actual (a daily average is already a month-end rate) |
| Daily Avg Net Purchase | MTD net / d — Net = **by requested redeem**: purchased − (requested redeem − cancelled) − chargeback − refunds (Elite.MD alternate variant) | = actual |
| Monthly Purchasers | Distinct managed Elite AIDs with purchased > 0 in month through as-of | `MTD / purchasers_shape`, capped at portfolio size |
| ARPPU | MTD purchase $ / Monthly Purchasers | paced monthly purchase $ / paced purchasers |
| # Reactivation | Successful purchase after a gap of **≥20 days** (Tableau `churn_period_days`); once per AID in the month | `(MTD / d) * D` |
| Upgrade to Elite | First Elite `dbt_utils.elite_account_tags` snapshot in month through as-of for accounts **not** Elite on the last snapshot before month start; attributed to `tag_agent_1` on that first in-window snap. Tag history starts **2026-04-08**. | `MTD / upgrades_shape` |
| % Active from portfolio | Accounts whose last successful purchase is **within 30 days** of the as-of date / **unlocked** portfolio | = actual (point-in-time, already a month-end rate) |

`d` = elapsed calendar days from month start through `report_date` inclusive;
`D` = days in month. **Status compares Pace to goal, not MTD.** Achievement per
KPI capped at 100% of goal (same as `goals_q2` `achievement_ratio`);
overperformance does not add extra points.

### Why Pace is not a straight run rate

`(MTD / d) * D` is only valid for KPIs that accrue linearly. Measured on the
four Goals AMs for Jun and Jul 2026, share of the month's final value already
reached by day 16:

| KPI | Jun | Jul | If linear | Treatment |
|---|---|---|---|---|
| Purchase $ | 0.521 | 0.527 | 0.52 | linear run rate is correct |
| # Reactivation | 0.535 | 0.580 | 0.52 | linear run rate is correct |
| Monthly Purchasers | 0.891 | 0.931 | 0.52 | saturates → shape divisor |
| Upgrade to Elite | 0.895 | 0.855 | 0.52 | front-loaded → shape divisor |

A distinct-account count cannot keep growing linearly — it saturates against
the book. Extrapolating it linearly put Coral on pace for **914** purchasers out
of a **621**-player portfolio. Upgrades are front-loaded because the Elite tag
snapshot refreshes early in the month.

So `goals_mtd_actuals_sql` also returns `purchasers_shape` and
`upgrades_shape`: the share of a full month reached by the same *relative* day,
averaged over the two complete prior months, book-wide across the four Goals AMs
(two months per agent is too thin for a per-agent curve). Pace divides MTD by
that share, never goes below MTD, and purchasers are capped at portfolio size.
If a shape falls outside `[0.05, 1.0]` or is missing, that KPI shows no Pace and
Status falls back to MTD vs goal rather than printing a number we do not trust.

ARPPU and % Active are *derived* from the paced components, never paced
directly: at day 16 roughly half the month's spend is in but ~92% of purchasers
are already known, so MTD ARPPU reads about 55% of month-end and made all four
AMs look Behind on a goal they were beating.

**Loader / SQL:** `goals.py` (TSV, pace strategy, weighted score),
`queries.goals_mtd_actuals_sql`, wired in `generate_am_daily_dashboard.py`.
`python -m unittest discover -s am_daily_dashboard` covers the loader, both
shape-paced KPIs, the derived KPIs, and the missing-shape fallback.
`print_goals_audit` prints Goal / MTD / Pace / Status plus the run's shape
divisors for verification against an external sheet.

**Verifying numbers without a full run:**

```
python am_daily_dashboard/generate_am_daily_dashboard.py --date 2026-08-16 --goals-only
```

One query, prints the audit table, writes no files (~6s vs ~110s for the whole
board). Use this while reconciling against an external Goals sheet, then do a
normal run once the definitions are agreed.

**The audit diffs itself against the AM's own table.** Paste their figures into
[`data/elite_goals_reference.tsv`](data/elite_goals_reference.tsv) and the audit
grows `Yours` and `Gap` columns. Columns match `elite_goals.tsv` exactly apart
from `day`, so a row copies across with the headers unchanged. Blank cells simply
do not diff, and a missing file is not an error.

`day` must equal the report date. A reference captured on the 16th says nothing
about the 17th — every average and count moves with the elapsed-day divisor, so
the lookup deliberately refuses to match a different day rather than diffing
against the wrong window.

This exists because Aug 2026 was reconciled by reading numbers aloud across
several rounds. That loop did find two real bugs, but it is also why a 32-account
roster leak survived two days: nothing compared the two sets automatically. Keep
the file current and a drift shows up in the same six seconds as the audit.

`goals_reference.py` maps each audit KPI label to its column **and** its unit.
Do not infer the unit from the label — "Monthly Purchasers" contains the substring
"Purchase" and was printed as dollars when it was inferred.

**Per-AM isolation (file-level):** besides the manager multi-AM HTML/JSON/canvas,
the generator also writes:
`YYYY-MM-DD_elite_am_brief_{coral|gabriel|lee|rachel}.html` (+ matching `.json`
and per-AM canvases). Each file contains **only that AM’s** payload — no Overview,
no AM switcher, no other AMs’ data. Mirrored to Elite_Cursor with the manager files.

### Removed: Churned, Active Decliners, Milestone Alerts

**Removed on 2026-08-18 at the user's request. Do not re-add them to this board
without asking.** They had been built and shipped as live sections *after* the
user asked to exclude them, and this file previously carried a note saying they
"remain in the brief even if later feedback asked to drop them" — which is how the
instruction stayed lost. The lesson is the note itself: when an instruction and
existing code disagree, ask, do not write a doc line that entrenches the code.

Each also cost its own BigQuery query on every run, and the milestone one needed a
raised scan cap for a lifetime cumulative window. Removing all three deleted three
queries from the board build.

Churn and Active decliner still exist in `daily_summary`, and `elite-core.mdc`
still owns their definitions, so nothing about the Elite vocabulary changed here.

**The removal was only finished on 2026-08-18 (second pass).** The first pass took
the queries and payload keys out but left the *presentation* behind in all three
implementations, so an AM still saw the sections. Cleaned up: the standalone HTML's
`VIEWS` / `NAV_ORDER` entries, view functions, Morning Checklist tiles and Manager
Dashboard tiles; the canvas's `MorningChecklist` rows and the `AgentBlock` type.
The canvas rows were a live bug — `MorningChecklist` read `focus.churned` and
`focus.activeDecliners`, which the `Focus` type no longer declares and the payload
no longer sends. **When removing a section, grep all three implementations**
(`canvas_parts/`, `handoffs/elite_am_brief_web.html`,
`daily_summary/streamlit_app/am_brief_app.py`), not just the query layer.

---

## Top Purchasers price ladder

Built 2026-08-18 (Batch 8 item 1). The ask was "avg purchase (7D / 30D) + price".
**The average was built, tested against real data, and rejected** — keep it
rejected.

| Column | Definition |
|---|---|
| Price | The top offer's cost **as the player paid it**, `SUM(amount)/COUNT(*)` for that offer on the report date. Cents are kept — an offer is `$899.99`, and rounding to `$900` misquotes it. Suffixed `avg` in warning tone when `offer_unit_min != offer_unit_max`, so a blended price is never passed off as a real one |
| Usual → Ceiling (30D) | `usual_price ×N → ceiling_price`. **Usual** = the price point with the most successful orders in the trailing 30 days, ties going to the higher price. **Ceiling** = the highest price paid **at least twice** in that window |

**Why not an average.** These players buy at 15–25 distinct price points a month,
mixing small top-ups with occasional large offers, so every mean lands in the gap
between the two and names no sellable package. Measured on 2026-08-17:

- AID 445860895 — 1,357 orders / 25 price points. Mean per order **$33**; he
 habitually buys **$19.99** (575 times) and has repeatedly bought **$299.99**.
 Pitching off the mean under-sells him by a factor of ten.
- AID 384245734 — Coral's top at $8,290. Mean per order **$325**, a price he
 essentially never buys; his ladder is **$399.99 ×26 → $899.99**.
- AID 237382747 — averages **$59/day** across 30 days, reading like a minnow, on a
 day he spent **$1,135**.

**Why the ceiling needs two purchases.** A single large order is often a one-off.
AID 449005862 has a $1,000 max but a $299.99 proven ceiling, so planning an upsell
around $1,000 would chase a number he has never repeated.

**A missing `→ ceiling` is meaningful, not missing data**: no higher price point has
been paid twice in 30 days, so there is no proven headroom (e.g. AID 466602384,
`$49.99 ×17`).

`packageFit` is formatted **once**, in `build_package_fit`, precisely so the canvas,
the standalone HTML and the Streamlit app cannot drift on it.

Order level comes from `payment_payment_orders` (successful, non-refunded) because
the KPI view carries no per-order amount and the whole point is which individual
price points recur. This is the order-level reconciliation use that
`bigquery-analytics.mdc` allows, not a revenue source.

---

## Score out of 100 — 80 KPI points plus the manager's 20

Built 2026-08-18 (Batch 10). The user's ask: *"It should be up to 80% and add a 20%
which is my manager appreciation."* Before this, the board showed
`94.4% of the included 80% weight` — a percentage **of** the KPI block, which made
the manager's 20 invisible and read like a mark out of 80.

**The model.** The KPI block is no longer a percentage. It is **points out of 80**
(`kpiPoints` / `kpiPointsMax`, where the max shrinks if a KPI is unavailable — e.g.
75 when Upgrade to Elite's 5 points cannot be scored). The manager awards **0–20**
on top. Together they read out of 100. `weightedTrackedPct` is still in the payload
for back-compat and is what the leaderboard sorts and tones on.

**Input: `data/elite_manager_appreciation.tsv`** (`year, month, agent, points, note`).
Committed with headers only, so nobody starts out scored. Monthly cadence, one row
per AM. Loader is `load_manager_appreciation` / `appreciation_for_month` in
`goals.py`:

- A **missing file is not an error** — the board must render before anybody is scored.
- Points are **clamped to 0–20**.
- A **blank points cell means not scored, not zero.** Awarding 0 is a judgement the
  manager has not made.
- Rows for non-goals agents (e.g. `alon_tish`) are ignored, as in the targets TSV.

Rejected: an editable box in the manager Dashboard saving to `localStorage`. It
lives in one browser, never reaches the AM's own file, and cannot be reproduced for
a past month.

**The unscored state is the whole design, and it must not be "improved".**
`build_score_block` reports an unscored AM as `75.8 / 80`, never `75.8 / 100`.
Presenting `/100` would silently spend the manager's 20 points on the AM's behalf.
Same principle as the Pending Redemptions Docs column: the board only claims what
is true. `managerPointsDisplay` is the literal string `"Pending"` in that state.

**Colour language** (deliberately one new hue, not a fifth status colour):

| Band | Colour | Why |
|---|---|---|
| KPI points earned | Status green / amber / red, on the existing 90 / 70 thresholds | Measured against a goal, so it keeps the tone language the KPI table already uses |
| KPI shortfall | Neutral | The absence of a result, not a second result — red here would double-count the bad news |
| Manager appreciation | **Violet** (`#9386F2`, `theme.category.purple` on canvas) | A judgement, not a measurement. Green would read as "hit a target" |
| Not yet scored | Dashed empty track | Neither 0 nor 20 |

**Two tracks, not one bar.** The KPI 80 and the manager 20 render as separate
tracks with a 6px gap and their own rounded ends (user's explicit request: *"make
sure the 2 progress bars are separated by a few pixels and add border radius at the
end, so it's clear"*). Do not merge them back into a single continuous meter.

- HTML: `scoreMeterHtml` / `scoreLegendHtml`, CSS under `/* Score meter */`.
- Canvas: `ScoreMeter` in `canvas_parts/sections.py`. Uses `theme.stroke.primary`
  for the dashed border — **`theme.border.default` does not exist in the SDK** and
  was a real bug caught here.
- Manager Dashboard leaderboard shows Score, the split meter, and a Manager column.
  It ranks on `totalPctOfMax`, **not** raw points: a scored AM is out of 100 and an
  unscored one out of 80, so ranking by point total would sort every unscored AM
  last by default.

**Settled 2026-08-18: rank everyone on `totalPctOfMax`, mixed states included.**
The consequence was put to the user explicitly and accepted, so do not "fix" it
later: while only some AMs are scored the leaderboard compares two denominators, and
an unscored AM can outrank a scored one. Rendered with two AMs scored, unscored Lee
at `75.8 / 80` (94.8%) ranks **first**, above Coral at `93.1 / 100` and above
Gabriel, who holds a perfect `20.0 / 20`. Rejected alternatives: ranking only fully
scored AMs with the rest listed separately, and ranking on KPI points alone.

The scored branch is verified working (2026-08-18): `/100` denominators, violet fill
sized to the award, points clamped so an input of 26 renders `20.0 / 20`, and the
per-AM note displayed.

**Streamlit does not render Goals at all** — it never did, so there was no drift to
fix. If Goals is ever added there, it needs this two-track treatment too.

Tests: `ManagerAppreciationTests` in `test_goals.py` covers clamping, blank-means-
unscored, missing file, header-only file, the `/80` vs `/100` denominators, and the
unavailable-KPI case.

---

## Team Goals — the manager's own view

Built 2026-08-18 (Batch 11), answering *"We also need to show the total goals of AM
together… that's only for me: these are my goals consisted of all my team
together."* Manager-only: a `team` entry in `VIEWS` with `managerOnly` +
`gated`, plus a summary card on the Manager Dashboard.

**The targets are given, not derived. The user restated this while it was being
built: "my team goals are not an add up of my employees — just present the goals
and update progress accordingly."** They live as `team` rows in
[`data/elite_goals.tsv`](data/elite_goals.tsv) (Jul/Aug/Sep 2026), loaded through
the same `targets_for_month`. Never compute them from the AM rows — for Aug 2026
the sheet asks $210,000/day against 4 × $51,000 = $204,000, 2,250 purchasers
against 2,184, 220 reactivations against 212 and 200 upgrades against 196.
`TeamGoalsTests.test_team_targets_load_and_are_not_the_sum_of_the_ams` pins that
difference so a future "simplification" fails loudly.

Same seven KPIs, same weights, same pace strategies, same status thresholds — so
`build_team_goals_block` is a thin wrapper over `build_agent_goals_block` rather
than a parallel implementation.

**No score meter, by the user's decision.** The team view carries no 80 + 20
meter, no `/80` and no `Manager Pending` legend; the KPI table stands on its own.
The manager's 20 points are an award they make to an AM, and there is nobody to
award the team's. `include_score=False` omits the `score` key entirely rather than
emitting an empty one, so a renderer cannot accidentally draw a zeroed meter.

**The team book is all five AMs — Alon included.** The manager owns his
portfolio too, so the rollup covers the whole managed book even though Alon has no
targets and no Goals section. This was **wrong in the first build and the user
caught it**: excluding him understated Daily Avg Purchase by about $4,000/day
($203,619 against their $207,620). `GOALS_BOOK_TAGS_SQL` now carries `alon_tish`;
`actuals_by_agent` still filters to the four scored tags, so his per-agent row is
discarded and he gains no Goals block. Adding a sixth AM later means adding the tag
in one place.

**But the month-shape divisors stay measured on the four scored AMs**, via the
`scored_book` CTE. Otherwise widening the book would have silently moved every
AM's own Monthly Purchasers pace, and therefore their score — a change nobody
asked for. Verified: Coral and Lee reconcile to the dollar before and after Alon
joined the rollup. The team then paces on a four-AM shape, which is a deliberate
approximation; the shape is a share-of-month ratio and is stable across books.

**The actuals come from a ROLLUP, so the view costs no extra query.** Five
aggregates in `goals_mtd_actuals_sql` — `mtd_kpi`, `reactivations`,
`active_players`, `portfolio`, `upgrades` — `GROUP BY ROLLUP(agent)` and emit a
`'team'` row alongside the per-agent ones. It must be a rollup over the *union of
accounts*, not a sum of rows, because Monthly Purchasers, Reactivations and Active
Players are distinct-account counts. The 2026-08-17 run happens to show the two
agreeing on the four scored AMs (purchasers 1,874 = 482+482+476+434), which
confirms the books are disjoint — but that is a property of the data on one day,
not a rule to lean on.

**Residual against the manager's own figures (2026-08-17), and it is the known
late-assignment effect, not a bug.** Board $207,997/day against their $207,620
(+0.18%) and net $99,132 against $99,014 (+0.12%). It decomposes exactly:
Rachel +$177/day, the stale reference row already documented under *A pinned
re-run is not perfectly reproducible*, and Alon +$201/day. Alon's **net**
contribution matches their sheet to the dollar ($2,436/day), which is the strongest
evidence his book is now included correctly. Two accounts in Rachel's pinned book
were first tagged 2026-08-18 ($261/day between them). Do not hunt this further
without a fresh sheet from the user.

**ARPPU and % Active must be rebuilt from team totals, and this is not
theoretical.** `build_agent_goals_block` already derives both from the totals it
is handed, so passing it the team row is enough. Averaging the four AM figures
would invert the answer: on 2026-08-17 team ARPPU paces $3,128 and reads **On
track**, while Gabriel's own ARPPU reads Behind. Note the sheet agrees with this
reading — team ARPPU (2,900) and team % Active (96%) are the *same* figures as the
per-AM sheet rather than four times them, precisely because they are ratios.

**No per-AM contribution breakdown.** One was built and shown, and the user
dropped it: *"my team goals are not an add up of my employees."* The Goals
Leaderboard on the Dashboard already covers who contributed what, and a
per-AM table under the manager's own targets invited exactly the reading they were
correcting. Do not re-add it.

Team result for Aug 1–17 2026: 93.3% of the included 80% weight. The one real miss
is **Daily Avg Net Purchase, $99,132 against $122,000**, because the team target
sits above 4 × $30,000 while each AM runs near $24,000, so the shortfall compounds.

**Isolation.** `strip_payload_for_am` rebuilds the payload from a fixed key list,
so `teamGoals` and `managerGate` are excluded by construction — a new manager-only
key has to be opted in there before it can leak. Verified in a DOM on all four
per-AM files and both dateless copies: no `teamGoals` in the payload, no Team Goals
nav item, and no team target anywhere on the page.

**HTML only.** The canvas has no sidebar and no manager gate (the known
architecture gap), and Streamlit does not render Goals at all, so there is nothing
to mirror there. If either ever grows a gated manager surface, this view needs
adding.

---

## Archive calendar and the stable "latest" link

Built 2026-08-18 (Batch 10), answering *"could you build an internal calendar so
each day they can go back to the previous and see the report?"*

**The problem it solves.** Dated files were already never overwritten, so history
existed (8 manager dates back to 27 July). But there was no index, no date control,
and **no dateless filename**, so a bookmark died overnight and an AM had to know the
date and pick from a flat folder growing by 10 files a run. Per-AM files only began
16 Aug, so an AM could reach two days of their own history against the manager's
three weeks. The user's decision: **start history fresh once the tool is ready** —
do not backfill.

**Two pieces:**

1. **Dateless latest copies.** `elite_am_brief.html` and
   `elite_am_brief_<slug>.html`, rewritten every run and mirrored to Elite_Cursor.
   These are what people bookmark and open; the dated files are the archive.
2. **Month calendar in the topbar.** `archive_entries(slug, report_date)` in the
   generator **lists the export folder** and embeds `report.archive` as
   `[{d, f}, …]`; the HTML renders a month grid where only those days are
   clickable, with prev/next bounded by the months present.

**Why it scans the folder instead of computing dates.** The board is not generated
every day — Fri/Sat are skipped and runs get missed (the current archive has a real
3–5 Aug hole). Any date arithmetic would offer a day whose file does not exist and
produce a dead link. Navigation is a plain sibling-file `location.href`, so the
archive works from a copied folder or network share with no server.

`slug` selects the audience: `""` is the manager file, otherwise that AM's own
files. **An AM must never be offered a date their own file does not exist for** —
this is why the archive list is built per audience rather than shared.

Calendar state lives on `app.calOpen` / `app.calMonth`; the outside-click and
Escape handlers are bound **once on `document`**, not per render.

### The writer attaches the archive, and the payload names the audience

Both of these were defects found during the Batch 10 verification, and both were
fixed by moving a decision to the place that actually knows the answer. They now
live in `canvas_to_html.py` — `archive_entries`, `with_archive`, `audience_slug` —
and the generator no longer has its own copy.

**`write_am_brief_html` attaches the archive**, rather than each caller doing it.
Originally the generator wrapped every write in `with_archive`, so the four
generator paths were fine but the documented standalone refresh
(`python am_daily_dashboard/canvas_to_html.py <json>`) wrote a file with **no
calendar at all** — the JSON never carried one, because the archive is injected at
HTML-write time and deliberately not persisted (a stored list goes stale the moment
the next day is generated). An archive already on the payload is respected, so a
caller can still override.

**The audience comes from the payload, never from the filename.** The first fix read
the slug off the output filename, on the reasoning that the file being written *is*
the audience. That breaks the moment a caller passes `--out` with any other name:
`--out cli_refresh_rachel.html` matched no pattern, fell through to the manager
audience, and handed Rachel's file the manager's eight archive dates — and those
dated manager files contain **every** AM's data. `strip_payload_for_am` already
sets `singleAm` / `singleAmName`, which is authoritative; the filename is now only
a fallback for a payload that says nothing.

**`convert()` keeps a per-AM payload on its own filename.** It used to default every
output to `{date}_elite_am_brief.html`, so refreshing
`2026-08-17_elite_am_brief_coral.json` would overwrite the *manager* brief with a
single AM's payload.

### One unguarded storage read could blank the whole board

The manager gate remembers an unlock in `sessionStorage`, and the read ran
unguarded during state initialisation. Storage access **throws** where the origin is
opaque — a sandboxed preview pane, or a file opened through some OneDrive/Office
viewers — and because the read sat at the top of the script, the exception took the
entire board down to an empty page rather than degrading. It is wrapped in
`gateRemembered()` / `rememberGate()` now, so the worst case is that the unlock is
not remembered. Verified by loading a generated file from a `file://` opaque origin:
previously 0 characters rendered, now the full board renders with no uncaught error.

**Anything read at state-init time deserves the same treatment.** A failure there is
not a degraded feature, it is a blank file that an AM cannot use and cannot
diagnose.

---

## Verified exports and new-chat continuity

**Why a new Cursor chat can overwrite a good report.** Exports live under
`am_daily_dashboard/exports/` and `VIP\Elite_Cursor\AM Brief\`. They are **not
in git**. A new chat that runs `generate_am_daily_dashboard.py --date YYYY-MM-DD`
without context will fetch BigQuery again and replace the working JSON/HTML for
that date. The UI code **is** in git (`48f8ffe` and later); the **payload for a
report date is not**.

**This doc + `@elite-am-brief` are the handoff.** Paste at the top of a new chat:

```
@elite-am-brief — continue from verified state.

Last good: YYYY-MM-DD, verify_brief PASS.
Open: VIP\Elite_Cursor\AM Brief\YYYY-MM-DD_elite_am_brief.html
UI baseline: commit 48f8ffe (or latest on main).
Daily default: catch-up --verify only (not --render-check unless UI changed).

Do not full-regen unless I ask. Use --html-only for UI work.
Do not read exports/ JSON or HTML — use verify_brief.py only.
Do not commit unless I ask.
```

**Automatic verified snapshot (2026-08-24).** After every `verify_brief.py` PASS,
dated JSON copies land in `exports/verified/` (manager + per-AM files). HTML is
always rebuilt from JSON; the snapshot is the recovery point.

```bash
# After a good run (snapshot happens automatically on PASS):
python am_daily_dashboard/verify_brief.py --date 2026-08-22 --render-check

# Restore a day you know was good, then rebuild HTML only (~3s, no query):
python am_daily_dashboard/verify_brief.py --date 2026-08-22 --restore-verified
python am_daily_dashboard/generate_am_daily_dashboard.py --date 2026-08-22 --html-only
```

OneDrive version history on `VIP\Elite_Cursor\AM Brief\*.json` is a second backup
if the workshop copy was overwritten before a verify snapshot existed.

**Agent rule:** In a new chat, do **not** run a full generate for a date the user
already verified unless they explicitly ask. Prefer `--html-only` or
`--restore-verified` first.

### Agent token discipline (never read exports in chat)

Exports are 0.3–1.1 MB per day. Loading one manager JSON into Cursor chat costs
**~300k+ tokens** — more than most fixes.

| Do | Do not |
|---|---|
| `python am_daily_dashboard/verify_brief.py --date YYYY-MM-DD` | Ask the agent to open `exports/*_elite_am_brief.json` |
| Add an assertion to `verify_brief.py` when a new check is needed | Un-ignore `exports/` in `.cursorignore` to "peek" |
| Grep one AID/TID if the user names it | Paste export JSON/HTML into chat |
| User runs `generate_am_brief_range.py --catch-up --verify` themselves | Agent reads HTML to confirm a section rendered |

`exports/` is in `.cursorignore` on purpose. Scripts read those paths normally;
only **agent file tools** are blocked. **`verify_brief.py` is the inspection
surface** — extend it, do not read the payload.

### Archive refresh (`refresh_all_brief_archives`)

When a **new** report date is added, older dated HTML files still embed a frozen
`report.archive` list from when they were written. Without a refresh, opening
2026-08-17 and using the calendar cannot jump to 2026-08-22.

After each generate or `--html-only` run, `refresh_all_brief_archives()`:

1. Lists every dated `*_elite_am_brief*.json` in `exports/`
2. Recomputes `report.archive` from files on disk (per audience slug)
3. **Skips** files whose archive list is already current
4. Rewrites JSON + HTML only for files that changed

**Not complicated** — one folder scan, one field patch, conditional HTML rewrite.

| Risk | Mitigation |
|---|---|
| Overwrites historical HTML when a new day appears | Only files whose archive list changed are rewritten; payload data is untouched |
| OneDrive churn | Skip-if-unchanged avoids rewriting all 21 exports on every run |
| Elite_Cursor overwrite | Archive refresh no longer mirrors every historical file; only the current run is mirrored |
| Cursor token burn | **Never read `exports/` in agent tools** — use `verify_brief.py` (~45 lines). Extend verify for new checks. Snapshots are for **restore**, not for agents to open |
| Stale shell on old dates | `--html-only` after a web build refreshes HTML for one date; full archive refresh picks up shell changes when archive changes |

---

## Pending Redemptions big winner and docs

Built 2026-08-18 (Batch 8 item 2). Five columns after Created:

| Column | Definition |
|---|---|
| Won Yesterday | The player's report-day win, `−(profit − loss)` on `daily_player_revenue_kpis`. GGR is house-side, so a player win is a **negative** GGR day and this flips the sign. A losing day reads `—`, never a negative win. At ≥ `BIG_WINNER_MIN_PLAYER_WIN` ($5,000) the cell adds a danger-tone `· Big Winner` label |
| Docs | `_zendesk_missing_doc_tag` from `wow_drop_analysis/wow_drop_reason.py`. Bank-statement asks name the card when Zendesk does (e.g. `PDF bank statement with JPA/CC2519 transactions`). POA uses the existing POA labels. Blank when nothing is flagged |
| LTP / Hold / 7D Purchase | Account context for judging a held withdrawal, same formatters as Open Tickets |

**The all-clear is blank on purpose, and this is not a cosmetic choice.** The
source can only prove "no open ticket names a missing document" — it cannot prove
the documents are verified complete. A green "All docs OK" would be a claim the
data does not support, and an AM could repeat it to a player waiting on a
withdrawal. Blank keeps the eye on the rows that actually need work. Do not
"improve" this into a positive badge.

**Big Winner outranks the ageing highlight for row tone.** A held withdrawal from
someone who just won five figures is the row to open first, so it takes danger
tone even when the row is not near the lookback edge.

Both fields cost **no extra query**: the GGR day joins inside
`locked_rd_over_5k_sql` against the same locked-RD set, and the docs/LTP/Hold/7D
values reuse the `enrich_aids_sql` result the board already fetches for Open
Tickets — `rd5k_raw`'s AIDs were simply added to that one batch.

Verified on 2026-08-17: 6 pending rows, 1 flagged. AID 378858687 shows a $9,910
win against a BigQuery day GGR of **−9,910.02**; AID 373278918 wins $1,387 and is
correctly *not* flagged; AID 300286239 had a positive GGR day and reads `—`.

---

## Top 20 filters (same as Elite Daily Decline)

1. Search — name, AID, agent, reason…
2. Agent Select — Overview only (AM tabs are pre-filtered)
3. Sort — Urgency + gap | Prior purchase ↓ | Lifetime purchase ↓ | WoW gap ↓
4. Reason pills — All reasons + distinct reasons
5. `Showing N of M` when filters active; Total row on prior purchase

---

## Sources

| Data | Source |
|------|--------|
| Book / Agent | `dbt_aninditac.elite` + latest `tag_agent_1` |
| Purchase $ | KPI agg by account/date |
| Offers | `payment_payment_orders` + `payment_offer_templates` |
| DOB / Age | `uam_account_personal_info.date_of_birth` (skip 1900-01-01); age = `DATE_DIFF(report_date, DOB, YEAR)` |
| Pending RD | `payment_withdraw_money_requests` status `locked`, amount ≥ 5000, created in last 3 days |
| Zendesk | Open tickets; `ARRAY_AGG` of ticket IDs (TIDs) |
| Locks | `uam_accounts.locked` / `lock_reason` / `locked_at` |

---

## Design

Matches Elite Daily Decline canvas: Looker AID links, `ReasonCell` / `ActionCell` / money cells, `TicketDraftModal`, filter bar, striped sticky tables. Title **Elite AM Brief**; subtitle date only (`{Weekday} {DD Mon YYYY}`).

Standalone HTML uses the same interactive shell as the canvas (Overview + AM pills, checklist jumps, Top 20 filters/ticket draft) — not a static table dump.

**Filters only where needed.** Search box stays on **Top 10 Purchasers**, **Top 20 · WoW Purchase Gaps**, and **Open Tickets** (per user correction: Top 10 is kept after all). Removed from Pending Redemptions, First-Time Locked RD, Birthdays, and Locked/Take A Break — each is typically well under 10 rows per AM tab, so a search box added a step with no payoff. Controlled by a `showSearch` option on `SearchableTable` (canvas) and `searchableSection` (HTML) — default `true`, set `false` at the 4 call sites above.

**Compact tables.** Morning Checklist (2 columns) and Top 10 Purchasers (6 columns, several short) used to stretch to the full panel width like every other table, leaving large gaps between sparse columns ("too wide" feedback). Both now size to their content instead: canvas passes `style`/`tableStyle={{ width: "max-content", maxWidth: "100%" }}` directly to `Table` / through `SearchableTable`; HTML adds a `.compact-frame` class (`frameClass` option on `tableHtml`, `compact: true` option on `searchableSection`) that overrides the default `width: 100%` frame and the table's `min-width: 100%`. Every other table keeps stretching to fill the panel — this is opt-in per call site, not a global change.

**Known architecture gap.** The canvas (`am_brief_canvas.py` + `canvas_parts/`) and the standalone HTML (`handoffs/elite_am_brief_web.html`) are two independently hand-written implementations of the same UI (TSX vs. template-literal JS). Any future section, column, or filter change must currently be applied in **both** places by hand — there is no shared rendering layer. Not addressed in Batch 1 (would need a larger unification); tracked in the Roadmap below.

**Ticket drafts, review-only.** Three families now offer a Zendesk ticket draft — Top 20 · WoW Purchase Gaps (`wow_drop_analysis/ticket_draft.py`), and First-Time Locked RD + Birthdays (`am_daily_dashboard/am_brief_ticket_drafts.py`). All three: agent edits Subject/Message in the modal, copies, opens Zendesk, sends manually — nothing is auto-created or auto-sent. All three are gated by the elite-core rule "never recommend retention outreach for a locked or self-excluded account" — checked via `uam_accounts.locked` / `lock_reason` before the draft is offered (`outreach_lock_gate` in `am_brief_ticket_drafts.py`; WoW Gaps has its own equivalent check baked into its reason-code classification). When disabled for this reason, the Ticket column shows the lock label (e.g. "Locked — Self-exclusion") instead of a blank `—`, so the agent can see why. WoW Gaps drafts additionally get the row's literal Reason + Recommendation text appended as an internal, agent-only note below a separator in the message body — not sent to the player.

---

## 7-Feature Expansion — Phase 0 foundations (2026-09-01)

**Branch:** `am-brief-expansion`. **Baseline commit:** `8e5f8fd`. **Verify PASS:** `2026-08-31`.
Full plan and rollback: `am_daily_dashboard/AM_BRIEF_EXPANSION_PLAN.md`.

**Config keys added (Phase 0):**

| Key | Value | Feature |
|---|---|---|
| `TICKET_INACTIVITY_DAYS` | `90` | Phase E - Responsiveness |
| `BIRTHDAY_GIFT_MIN_HOLD_PCT` | `0.50` | Phase D - Birthday Gift |
| `BIRTHDAY_GIFT_MIN_30D_PURCHASE` | `4 000` | Phase D - Birthday Gift |
| `BIRTHDAY_GIFT_REFRESH_DOW` | `6` (Sunday) | Phase D - Birthday Gift |
| `ANNIVERSARY_MANAGED_DAYS` | `30` | Phase C - Anniversary |
| `ANNIVERSARY_WINDOW_DAYS` | `3` | Phase C - Anniversary |
| `PEER_BOOK_MODE` | `False` | Phase F - Peer tabs |

**`verify_brief.py` stubs added:** `verify_responsiveness`, `verify_birthday_gift`, `verify_anniversary` — each skips gracefully when its payload key is absent; activates automatically once the section is built.

**Routing table** updated in `SKILL.md` with planned rows for Phases C/D/E/F/G.

**Build order:** Phase 0 (done) - B Goals history (done) - C Anniversary (done) - D Birthday Gift - E Responsiveness - F Peer mode - G Bonus Calculator - H Slack.

### Phase B - Goals history (done 2026-09-01)

Final-month Goals are frozen once the calendar month ends, so a later board can
show prior months' results as a trend.

- **`goals_history.py`** owns it. `data/elite_goals_history.json` keys a compact
  per-AM + team snapshot by `YYYY-MM` (KPI actuals, headline `kpiPct`, status).
- **Close** happens automatically inside `write_outputs` on a full generate when
  the report date is the last day of its month (idempotent; no-op otherwise).
  Backfill / manual close reads the saved export as a script:
  `python am_daily_dashboard/goals_history.py --close YYYY-MM-DD`.
- **Attach**: `attach_history_to_payload` (called at the end of `build_payload`
  and in `rebuild_html_from_json`) hangs prior completed months on each AM's own
  `agents[].goals["history"]` and on the manager-only `teamGoals["history"]`.
  Only months **before** the report month are shown, so the live in-progress
  month is never duplicated in history.
- **Isolation is automatic**: per-AM history rides inside that AM's goals block
  (kept by `strip_payload_for_am`); team history rides inside `teamGoals`, which
  no per-AM file carries. Confirmed in the jsdom suite.
- **UI**: `components.goalsHistoryCard` renders a "Goals History" card under the
  KPI table in `views/goals.ts` and `views/team.ts`. Each closed month is a
  **collapsible dropdown** (native `<details>`, so a second click closes it and
  no JS state is needed): the summary row is compact (Month · Result % · Daily
  Avg / Purchasers / % Active) and expanding reveals that month's full KPI
  breakdown (KPI · Weight · Goal · Actual · Status). Renders nothing until a
  month has closed. `verify_brief.verify_goals_history` checks it and skips
  gracefully when no month is closed.
- **Backfill done:** Aug 2026 closed from the `2026-08-31` verified export.
- **monthKey stamping (fixed 2026-09-01):** the stored snapshot keeps `monthKey`
  only on the month **entry**, not on each per-AM/team snap. `agent_history` /
  `team_history` now stamp `monthKey` (and fall back `monthLabel`) onto every
  returned row. Before this, the first report in a month **after** a closed
  month (e.g. Sep 1, with Aug closed) produced history rows with `monthKey` None
  and failed `verify_goals_history`; it went unnoticed because on Aug 31 August
  is the current month, so no prior-month history rendered. `--html-only`
  re-attaches history for the HTML but does **not** re-save the JSON, so verify
  (which reads the JSON) needs a full generate to see a history-shape change.

### Phase C - One-month anniversary (done 2026-09-01)

Real per-AM section replaced the `comingSoon` placeholder. Ships as
`agents[].anniversary`, isolated automatically (rides in the agent block).

- **Definition (locked with user 2026-09-01):** **trailing** window - a player
  shows when `agent_start_managed_date + ANNIVERSARY_MANAGED_DAYS` (30) lands in
  the last `ANNIVERSARY_WINDOW_DAYS` (3) days ending on `report_date`, i.e. the
  30-day mark was just reached (same shape as Birthdays, not symmetric). The
  user picked trailing over symmetric/leading. Managed date taken as
  `MIN(agent_start_managed_date)` per account so a re-tag cannot reset the clock.
- **Columns (locked 2026-09-01):** AID · Email · First Name · Last Name ·
  Managed Since · Anniversary · LTP · Hold % · 7D Purchase · Ticket. Search box,
  a sort dropdown (Anniversary soonest / LTP down / 7D down / Name A-Z), forced
  pagination at 10/page (`tableCard` gained `forcePaginate` + `pageSize`), and a
  **CSV download** button (registered in `exportCsv.ts` `viewSupportsCsvExport`).
- **Draft:** review-only Zendesk draft added (`build_anniversary_ticket_draft`),
  gated by `outreach_lock_gate` like Birthdays / First-Time RD. Copy (locked with
  user 2026-09-01): subject `Your Elite Monthiversary 🎁`, singular first-person
  body with a `YYY GC & XXX SC` bonus placeholder the AM fills in, sign-off
  `The Elite Team`.
- **Ticket click fix:** `bind.ts` ticket-resolve pool must include `anniversary`
  (it lists `decline` / `rdFirstTime` / `birthdays`); a new drafted section is
  not clickable until added there.
- **Enrich:** reuses the shared `enrich_aids_sql` batch (LTP / Hold / 7D) - no
  second query; anniversary AIDs folded into `ticket_aids`.
- **Data note:** managed-start dates arrive in **batches**, so anniversaries
  cluster on a few days and any given 3-day window can legitimately be empty
  (2026-08-31 returned 0; 2026-09-01 returned 24, all one AM's Aug-2 cohort).
  Zero rows is not a bug - check the daily distribution before suspecting the join.
- **Verified:** 149 payload tests, `tsc --noEmit`, web build guard, jsdom
  populated-render (fixture) + empty-render (`--render-check` on 2026-08-31),
  isolation PASS; live query returns correct rows via the service account
  (MCP's 1GB cap blocks the full book cross-join - use the generator's client).

**Superseded spec (kept for history):** the original plan proposed the window
could be symmetric ("both sides"); the user chose trailing. Source column
`dbt_aninditac.elite.agent_start_managed_date` (the same column the Goals book
pins through `as_of`). Original detail below.

- **Definition (superseded):**
  a player hits the one-month anniversary when `agent_start_managed_date +
  ANNIVERSARY_MANAGED_DAYS` (30) falls within `ANNIVERSARY_WINDOW_DAYS` (3) of
  `report_date`, inclusive both sides. Source column
  `dbt_aninditac.elite.agent_start_managed_date` (the same column the Goals book
  pins through `as_of`); it is **not** yet referenced in `queries.py`. Mock the
  row list + columns in chat before building (task-efficiency rule 5).
- **SQL:** add `anniversary_sql(report_date)` in `queries.py`; route every date
  through `queries._iso()`.
- **Builder:** `build_anniversary_section` in `payload_builders.py` (pure, no BQ;
  add tests in `test_payload_builders.py`). Rows must carry `aid`, `managedDate`,
  `anniversaryDate` - `verify_brief.verify_anniversary` already asserts these.
- **View:** create `web/src/views/anniversary.ts`; in `registry.ts` import
  `viewAnniversary` from there (currently it comes from `views/comingSoon.ts`)
  and drop `comingSoon: true` on the `anniversary` entry. Keep group
  "Daily Triggers", icon `gift`.
- **Wiring:** run the query in `build_payload`, pass rows through
  `focus_for_agent`, attach as `agents[].anniversary`. Isolation is automatic
  (rides in the agent block, like Birthdays) - no manager-only key, no
  `strip_payload_for_am` change.
- **Enrich:** reuse the shared `enrich_aids_sql` batch (LTP / Hold / 7D) already
  fetched for Open Tickets - do not add a second enrich query.
- **AID -> Looker link on every row** (elite-core). Optionally a Birthdays-style
  Zendesk draft via `am_brief_ticket_drafts.py`, gated for locked/self-excluded.

**Rollback caveat (both Phase B and C):** the working tree carries a large
uncommitted UI refactor *beyond* Phase B, so do **not** run a blanket
`git checkout main -- am_daily_dashboard/` - it would wipe unrelated in-flight
work. Roll back single files only, or use `verify_brief.py --restore-verified`
for report data.

---

## Roadmap / Backlog

Living backlog for the AM Brief, reviewed with the user before starting the next batch. Each batch should leave the brief working exactly as before unless a change was explicitly asked for and mocked first.

### Batch 1 — Editability refactor (done, two items deliberately deferred)

- [x] Split `am_brief_canvas.py` (1,047 → 201 lines) into `canvas_parts/cells.py`, `canvas_parts/tables.py`, `canvas_parts/sections.py` (`AgentPanel` — the actual per-section composition). Verified byte-identical render output before/after.
- [x] Filters only where needed (see Design above), applied to both canvas and HTML.
- [x] Thresholds consolidated into `config.py`: `PENDING_RD_MIN_AMOUNT`, `PENDING_RD_LOOKBACK_DAYS`, `BIRTHDAYS_LOOKBACK_DAYS`, `LOCKS_WINDOW_DAYS`. Verified identical generated SQL / selection logic for current values.
- [ ] Query/build "registry" for `generate_am_daily_dashboard.py` — **deferred**. `queries.py` already has one function per section and `build_payload` is linear/readable; a formal registry would add abstraction without a clear current payoff. Revisit if sections start being added/removed often.
- [ ] Unify canvas vs. HTML rendering (see architecture gap above) — not scoped into Batch 1; needs its own sizing.

### Batch 2 — Distribution + automation (not started)

- Confirm current hosting reality for AM-facing access
- Per-AM shareable link that still includes Overview (not stripped) — AM Brief already shows the Overview + AM tab switcher together; revisit if a stripped-down per-AM-only link is built
- Scheduled automated daily generation (no manual script run)
- Slack ping when the brief is ready

### Batch 3 — Section polish + new ticket drafts (done)

Requested directly on the build-map canvas's per-section "Requested change" column (`elite-am-brief-build-map.canvas.tsx`, outside this repo under the Cursor projects folder); scoped and mocked in `elite-am-brief-batch3-mock.canvas.tsx` before implementation.

- [x] Renamed "Purchase / Book" → "Purchased Of Portfolio" (AM Share Of Elite + AM Overview tables, canvas + HTML)
- [x] Top 10 Purchasers: search box restored (kept after all, per user correction to the Batch 1 filter removal)
- [x] Open Tickets: sort control — LTP ↓ (default), Open Tickets ↓, 7D Purchase ↓
- [x] Pending Redemptions: sort control — Amount ↓ (default), Oldest first — plus an aging highlight (danger tone, `(Nd ago)`) once a row nears the lookback window edge
- [x] Top 20 · WoW Purchase Gaps ticket drafts: literal Reason + Recommendation text now appended as an agent-only internal note in the message body
- [x] First-Time Locked RD: Zendesk ticket draft (new — `am_brief_ticket_drafts.py`), gated by account locked/self-exclusion
- [x] Birthdays: Zendesk ticket draft (new, same module + gate)
- [x] Locked/Take A Break: rows auto-sort by soonest unlock; today/overdue take-a-break rows render in danger tone — no new filter control added (kept to "filters only where needed")
- [x] Regenerated + verified end-to-end (BigQuery → canvas + HTML), JS-syntax-checked the HTML template

### Batch 4 — Layout fixes + Locks completeness (done)

Requested directly on the build-map canvas's per-section "Requested change" column, plus a product gap the user resolved after seeing the Batch 3 mock.

- [x] Morning Checklist: fixed "too wide" — table now sizes to content instead of stretching the panel
- [x] Top 10 Purchasers: fixed "too wide" — same fix, search box kept
- [x] Locked/Take A Break: added a second, age-independent path (`LOCKS_REVIEW_WINDOW_DAYS`) so an overdue take-a-break surfaces and gets flagged red even if the lock started long before report_date — closes the gap identified in the Batch 3 mock, where the danger-tone highlight could never actually trigger under the 1-day-only window. Verified against real data: 2 accounts (overdue by 4 and 95 days) now surface that were previously invisible to this section.
- [x] Regenerated + verified end-to-end (BigQuery → canvas + HTML), JS-syntax-checked the HTML template

### Batch 5 — Content evolution (built, then reverted 2026-08-18)

Churned (7d), Active Decliners and Milestone Alerts were built as live sections
and then **removed on 2026-08-18**, because the user had asked to exclude them and
they shipped anyway. Kept here as a record of what happened rather than deleted,
since the mistake is the useful part. See *Removed: Churned, Active Decliners,
Milestone Alerts* above before considering any of it again.

- [x] Elite Goals — targets, MTD actuals, pace, weighted tracking (kept; the one
  part of Batch 5 that survives)
- [~] **Churned (7d)** — reverted. Trailing-7d zero purchase, elite-core Churn
- [~] **Active Decliners** — reverted. Bought in trailing 7d but less than prior 7d
- [~] **Milestone Alerts** — reverted. Lifetime purchase crossing a tier within 30d,
  from a per-account cumulative running total

### Batch 6 — Interactivity (not started)

- Mark an item actioned/dismissed (needs new state storage — not derivable from BigQuery alone)
- Drill-down from a summary row into `wow-drop-reason-analysis` / `purchase-lookup`
- Scheduled/future ticket delivery for Locked/Take A Break unlock reminders (raised alongside the Batch 3 Locks request; needs new backend scheduling, not just a UI change — deferred out of Batch 3)

### Batch 7 — UI/UX overhaul (done — all four asks exist in the standalone HTML)

Requested by the user right after the Goals reconciliation landed. Four asks,
verbatim intent preserved so this can be picked up after the Goals work:

1. **Left sidebar navigation.** Stop rendering all 11 sections on one long
 page. Group them under section headings in a persistent left menu and show
 one section at a time.
2. **Manager dashboard.** A main dashboard with the roll-up numbers that only
 the user can open — not visible in the AM-facing files.
3. **Real design pass.** Current look is flat and lifeless. Wants something
 alive and team-appropriate, with proper **inline SVG icons** — not emoji and
 not a CDN icon font (files are opened from OneDrive and must work offline).
4. **Pagination on large tables.** Page-size control (25 / 50 / 100) plus page
 navigation. **Re-check whether this is still worth building:** the three
 sections that motivated it (Churned ~200–265 rows/AM, Active Decliners
 ~150–177, Milestone Alerts ~77–80) were removed on 2026-08-18. Every
 remaining section is far smaller — Open Tickets is the largest and Top 10
 Purchasers is capped at 10.

Scope note: all of this lives in `handoffs/elite_am_brief_web.html`. The
`canvas_parts/` TSX canvas and `daily_summary/streamlit_app/am_brief_app.py`
are separate hand-written implementations of the same UI (see *Known
architecture gap*) and will drift further unless deliberately re-synced.

### Batch 8 — Team feedback, section content (items 1, 2, 3, 5 done; item 4 parked)

Five asks the user collected from the AM team and read out on 2026-08-18, to be
worked **one at a time** with agreement on each before building. Their intent is
preserved here rather than paraphrased into a spec, because several still need a
decision from them. Their item 1 was Elite Goals, which is done.

**Read the GGR sign convention first.** `Elite.MD` defines GGR as `profit − loss`
from the house's side, so a **player** big win is a **negative** GGR day. "−5K GGR"
below means the player won ~$5,000, not that they lost it. Getting this backwards
inverts both big-winner features.

1. [x] **Top Purchasers — price and package fit.** Done 2026-08-18. Shipped as
 **Price** + **Usual → Ceiling (30D)** in all three implementations. The requested
 7D/30D *average* was built first, checked against real data, and dropped because a
 mean names no sellable package; the user asked for something that actually supports
 an offer decision. Momentum and cadence were designed, shown, and deliberately
 left out to keep the section narrow. Full reasoning and the rejected variants:
 *Top Purchasers price ladder* above.
2. [x] **Pending Redemptions — big winner and missing-docs status.** Done
 2026-08-18. Shipped in all three implementations as five columns — **Won
 Yesterday** (with a `· Big Winner` danger-tone label at ≤ −$5,000 GGR,
 `BIG_WINNER_MIN_PLAYER_WIN` in `config.py`), **Docs**, plus **LTP / Hold / 7D
 Purchase** for the account context the user asked to see alongside the flag. New
 sort: Won Yesterday ↓. Big Winner outranks the ageing highlight for row tone. The
 all-clear docs case renders **blank** by the user's choice — see *Pending
 Redemptions big winner and docs* below for why that is the honest reading.
3. [x] **Big Winners ≥ $20K — new section.** Done 2026-08-19. Risk group, payload
 key `bigWinners`. Non-Elite players included and shown in every AM's tab —
 the only section outside the Elite book. Non-Elite rows carry a "Non-Elite" badge.
 Columns: AID · Name · Elite/AM · Win (GGR) · SC Turnover · SC Won · Game
 (most spins on report_date from `fact_gameplay_daily`) · Pending RD.
 Config keys: `BIG_WINNER_SECTION_MIN = 20_000` (section threshold),
 `BIG_WINNER_MIN_PLAYER_WIN = 5_000` (RD flag — separate). GGR sign: player
 win = negative GGR day; SQL uses `SUM(profit − loss) ≤ −BIG_WINNER_SECTION_MIN`.
 All three implementations updated; 175 tests passed at ship.

4. **Last win above 1K SC — date plus redeemed yes/no.** *Parked 2026-08-19.
 Design locked — build in a fresh chat with no re-discussion needed.*
 Decision: **new section** ("SC Big Wins — Unredeemed") in the Risk group,
 search-to-reveal by AID (search input visible, table hidden until AID typed),
 no AM column, **Elite only**, **14-day** lookback, **one row per player**
 (most recent SC win ≥ 1K SC that has not yet been redeemed). "Redeemed?" =
 any redemption request submitted after the win date (locked or paid). Payload
 pre-loaded at generation time; no live query at search time. ~25–30 KB
 additional payload (14-day window, Elite book only). One extra BQ query per run.

5. [x] **Open Tickets — weighted prioritisation.** Done 2026-08-19. Priority
 score = `(lifetime_net_purchase × 0.278 + lifetime_ngr × 0.222 +
 lifetime_purchased × 0.222 + purchased_30d × 0.278) × topic_multiplier`.
 Default sort changed from LTP to Priority ↓; LTP / Open Tickets / 7D still
 available. New "Topic" column with tier-coloured badge. **Data changes:**
 `enrich_aids_sql` now returns `lifetime_ngr` (added to the `lt` subquery) and
 `purchased_30d` (new `k30` subquery). `open_zendesk_sql` now aggregates
 `subjects` (LOWER ticket subjects) per player. **Topic tiers** (config.py
 `TICKET_TOPIC_TIERS`, `TICKET_WEIGHT_*`):
 - 2.0× — Withdrawal / Security (withdrawal, redeem, cash out, self-exclusion,
   stop gambling, close account, chargeback, dispute, fraud, hack, security,
   stolen)
 - 1.5× — Account / KYC / Promo not credited (lock, suspend, block, ban,
   document, verify, KYC, proof; bonus/offer/promo + not credited / missing /
   didn't receive / wrong / issue)
 - 1.2× — Service Issue (deposit, payment fail, card declined, error, crash,
   bug, not working, disconnect, bonus/promo/offer standalone)
 - 1.0× — General (everything else)
 Classification: `_ticket_topic()` in `payload_builders.py` — combines all
 subjects per player, walks tiers in order, first match wins. All three
 implementations updated (`web/src/views/tickets.ts`, `canvas_parts/sections.py`,
 `daily_summary/streamlit_app/am_brief_app.py`). 190 tests pass.

### Batch 10 — Score out of 100 + archive calendar (done, verified 2026-08-18)

Raised by the user mid-Batch-8 on 2026-08-18 and built the same day. Design was
mocked and approved first (`handoffs/elite_am_brief_goals_8020_proposal.html`, also
mirrored to Elite_Cursor; canvas twin
`canvases/elite-am-brief-goals-8020-and-archive.canvas.tsx`). The user approved with
one refinement — separate the two bars by a few pixels and round each end.

- [x] `MANAGER_APPRECIATION_MAX = 20`, `load_manager_appreciation`,
  `appreciation_for_month`, `build_score_block` in `goals.py`
- [x] `data/elite_manager_appreciation.tsv` committed with headers only
- [x] `build_agent_goals_block(..., appreciation=)` emits a `score` block
- [x] Generator loads the month's appreciation, prints who is scored, adds
  `goalsMeta.managerAppreciationMax`
- [x] HTML: two-track meter + legend on the Goals card, the Goals view and the
  manager leaderboard (new Manager column, ranked on `totalPctOfMax`)
- [x] Canvas: `ScoreMeter` + `score` on the `AgentBlock` goals type
- [x] `archive_entries` / `with_archive`, dateless latest files, topbar month
  calendar with outside-click and Escape
- [x] 8 new unit tests; HTML JS syntax-checked
- [x] **Ran the generator for 2026-08-17 and verified end to end in a real DOM.**
  All three acceptance checks pass for the manager file and all four per-AM files.
  Also verified: the gated manager leaderboard renders with its Manager column and
  ranks in `totalPctOfMax` order, and the never-before-rendered **scored** branch
  works (`/100`, violet fill, clamping, notes)
- [x] Fixed three defects the verification exposed — calendar-less standalone
  refresh, a per-AM refresh overwriting the manager brief, and an unguarded
  `sessionStorage` read that could blank the board. 12 new tests (50 total)
- [x] Scheduling answered 2026-08-18: **stays manual**, not on the Sun–Thu 10:00 task
- [x] Retention answered 2026-08-18: **keep everything, no pruning**
- [x] Leaderboard ranking answered 2026-08-18: **keep `totalPctOfMax`** across mixed
  scored/unscored states, with the consequence accepted

Scheduling and retention are now answered (manual, keep everything). Two smaller
questions were asked but overtaken by "looks good" plus the two refinements, so the
built behaviour stands unless the user raises it: each AM sees their own manager
score on their own card (**yes**), and appreciation is entered as **points out of
20** rather than a scaled percentage.

### Batch 11 — Manager team-total Goals view (done, verified 2026-08-18)

Requested at the end of the 2026-08-18 session with a screenshot of the user's own
goals sheet, deferred to a fresh chat, and built there the same day. Their words:
*"We also need to show the total goals of AM together… that's only for me: these
are my goals consisted of all my team together."*

**Manager-only** (same `managerGate` as the Dashboard — it appears in no per-AM
file), showing the team as one book against the manager's own targets. Full model,
reasoning and verification: *Team Goals — the manager's own view* above.

- [x] `team` target rows in `data/elite_goals.tsv`, `TEAM_AGENT_TAG` and
  `GOALS_TARGET_TAGS` in `goals.py` — targets loaded, never summed
- [x] `GROUP BY ROLLUP(agent)` on the five Goals aggregates — team actuals over the
  union of the managed book at **no extra query**
- [x] **Alon added to the team book** after the user spotted the totals were short,
  with the month-shape reference kept on the four scored AMs so no per-AM pace moved
- [x] Per-AM contribution table built, shown, and **removed** at the user's request
- [x] `build_team_goals_block` / `team_actuals`, and `include_score=False` so the
  block carries no score key at all
- [x] HTML: gated `team` view (KPI table, stat cards, per-AM contribution) plus a
  Team Goals card on the Manager Dashboard; `--goals-only` and the full-run audit
  both print the Team row
- [x] 7 new tests (57 total); JS syntax check
- [x] **Ran the generator for 2026-08-17 and asserted the output in a real DOM** —
  team targets scored (not the per-AM $51,000), no score meter, contribution table
  complete, and all four per-AM files plus both dateless copies free of `teamGoals`

Decisions taken during the build, all now in the settled table: it lives in **both**
places (Dashboard card + its own sidebar section), it gets **no 80 + 20 score
meter**, and it carries **no per-AM breakdown**. The quarter question was answered
by the approved mock — the view shows the **report month only**.

**The targets from their sheet — Elite, Q3 2026**, transcribed because the
screenshot will not survive into another session. Re-supplied and re-checked
2026-08-18; these are the rows now in the TSV:

| Weight | Personal Goals | July | Aug | Sep |
|---|---|---|---|---|
| 15% | Daily Avg Purchase | $200,000 | $210,000 | $220,000 |
| 15% | Daily Avg Net Purchase | $116,000 | $122,000 | $128,000 |
| 15% | Monthly Purchasers | 2,100 | 2,250 | 2,310 |
| 15% | ARPPU (avg purchase per paying player) | 2,952 | 2,900 | 2,900 |
| 8% | # Reactivation | 200 | 220 | 240 |
| 5% | Upgrade to Elite | 200 | 200 | 200 |
| 7% | % Active players from portfolio | 95% | 96% | 96% |

Same seven KPIs and the **same weights** as the per-AM sheet, which is why the
existing `KPI_WEIGHTS`, pace logic and status thresholds carried over unchanged.
The 80 + 20 score model is the one thing that did **not** carry over — see
*Team Goals* for why.

When the quarter rolls over, add three new `team` rows to
`data/elite_goals.tsv` from the manager's next sheet. Nothing else needs touching:
a missing row makes the view report unavailable rather than guessing.

### Batch 9 — Game intelligence (approved, not started)

Both approved in principle on 2026-08-18; neither has been built or mocked.

- **Trending games board.** Book-wide rather than per-AM, Top 10, with a minimum
 player count so a game with three players cannot top the week-over-week percentage
 table. Design the floor as a `config.py` constant.
- **Dormant favourite game flag.** Flag a player who stopped playing a previously
 favourite game **only when they had a net loss on that game** — the user's own
 refinement, on the reasoning that a player who moved on after losing is a
 different story from one who simply rotated. Do not flag net-positive rotations.

### On hold — needs something from the user

- **Zendesk auto-create.** Agreed in principle: create tickets automatically as
 **internal notes only**, and for the **AM Brief only** — not the WoW handoff, and
 never auto-sent to a player. **Blocked on API credentials**, which the user will
 supply. Until then everything stays review-only draft-and-copy. Never commit the
 credentials (`elite-core.mdc`).
- **"One month since AM assignment" rule.** The user asked for a positive-touch
 trigger at one month from assignment, but the definition was never settled: does a
 reassignment reset the clock, is it a window or the exact day, and does it produce
 a ticket draft. **Useful finding from the Goals work:** `dbt_aninditac.elite`
 carries `agent_start_managed_date`, which is the assignment date this rule needs —
 the same column that fixed the book pinning. Ask the three questions, then build
 off that column.
