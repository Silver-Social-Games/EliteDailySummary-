# AM Brief board sources

The Elite AM Brief board is written here as modular TypeScript and bundled by
`build.mjs` into the single self-contained file
`../handoffs/elite_am_brief_web.html`, which Python then fills with a payload
per report.

**That built file is a build output. Do not edit it.** A hand-edit there is
thrown away by the next build, so the test suite fails loudly if either half
drifts (see *Hash guards* below).

## Change the board

```bash
cd am_daily_dashboard/web
npm install                 # once
node build.mjs              # rebuild ../handoffs/elite_am_brief_web.html
npm run typecheck           # tsc --noEmit
```

Then rebuild the actual briefs from the day's saved JSON — no BigQuery, ~3s:

```bash
python am_daily_dashboard/generate_am_daily_dashboard.py --date YYYY-MM-DD --html-only
```

## Why one file, and why no asset pipeline

The brief is opened from OneDrive and from copied folders with no server and no
network, so a single self-contained HTML file is non-negotiable. `app.css` and
`icons.svg` are therefore concatenated **verbatim** — they were never the part
that was hard to change, and running them through a processor would add
behaviour risk for no benefit. Only `src/*.ts` goes through esbuild, unminified
so that `git diff` on the committed output stays reviewable.

## Layout

| File | Owns |
|---|---|
| `shell.html` | The static frame and the four build markers |
| `src/app.css` | Every style, verbatim |
| `src/icons.svg` | The inline SVG sprite, verbatim |
| `src/main.ts` | Bootstrap: parses the payload, registers the render hook, first render |

## Hash guards

`build.mjs` embeds one comment in the built file:

```html
<!-- am-brief-build sources sha256:… output sha256:… -->
```

- **sources** covers `shell.html`, `build.mjs` and every `src/**` file, so
  "edited the TS and forgot to rebuild" is a test failure, not a board that
  silently ignores the change.
- **output** covers the built file itself with that comment blanked out, so
  hand-editing the generated HTML is also a test failure rather than a change
  that quietly disappears at the next build.

Both hash LF-normalised text. The repo checks out CRLF on Windows
(`core.autocrlf=true`), so hashing raw bytes would make a fresh clone disagree
with the machine that built it.

`node build.mjs --check` compares the committed file against a fresh build and
exits non-zero on any difference. `../test_web_build.py` runs the same guards
with no Node required.

## Verifying a change

`npm test` in `../tests_js/` rebuilds the shell, rebuilds fixtures and runs the
jsdom suite. For a refactor, that is not enough — it proves the board is not
blank, not that nothing changed. Use the DOM equality harness:

```bash
cd am_daily_dashboard/tests_js
node dom_snapshot.mjs --out %TEMP%\ambrief-baseline    # before
# ... make the change, rebuild the shell ...
python ../testing/build_fixtures.py
node dom_snapshot.mjs --check %TEMP%\ambrief-baseline  # after
```

It renders every fixture x gate state x agent x view plus the interaction
states (calendar, pager, search, reason chips, ticket modal, sidebar collapse,
rejected passcode) and requires byte-identical output. Fixture payloads are
deterministic, so any difference is a real behaviour change.
