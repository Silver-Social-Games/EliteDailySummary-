# SPEC: Auto-publish Elite Daily/Weekend to GitHub Pages

**Status:** Implemented but disabled — do not enable before security and code-review findings are resolved  
**Owner:** Elite analytics  
**Last updated:** 2026-08-03 (scheduled auto-publish explicitly disabled)

## Goal

Stop the daily manual `git push`. After the morning report runs, automatically publish HTML to `docs/` and push only that folder so GitHub Pages updates.

## Problem

Today the report can regenerate locally, and `docs/latest.html` already exists, but GitHub Pages only updates after a manual commit + push of `docs/`. A local render alone does not update the cloud site.

## What already exists

- Windows Task Scheduler runs the morning report at 10:00 (Israel time)
  - Register: `daily_summary/register_daily_summary_task.ps1`
  - Launcher: `daily_summary/run_morning_elite_scheduled.ps1`
  - Router: `daily_summary/generate_morning_elite.py`
- Python generates Daily/Weekend HTML
- `daily_summary/publish_github_pages.py` copies reports into `docs/` and refreshes:
  - `docs/latest.html`
  - `docs/index.html`
  - `docs/reports.json`
  - `docs/reports/*.html`
- GitHub Pages serves from the `docs/` folder on `main`
- Site latest URL pattern: `…/latest.html` (Daily/Weekend only; AM Brief stays local)

## What is missing

~~Automatic commit + push of `docs/` after a successful morning run.~~

**Implemented:** `daily_summary/publish_pages_git.py` + launcher wiring + unit tests.
Remaining: one supervised live push to confirm Git credentials work in the
scheduled-task context.

## Scope — what to do

1. **Extend the scheduled launcher** (`daily_summary/run_morning_elite_scheduled.ps1`)
   - After the morning script exits successfully, ensure publish to `docs/` has run.
   - Then run a small, safe git publish sequence.

2. **Add a safe publish-to-git step** (PowerShell or Python helper)
   - `git pull` (or `git pull --rebase`) so local `main` is up to date
   - `git add` **only** these paths:
     - `docs/latest.html`
     - `docs/index.html`
     - `docs/reports.json`
     - `docs/reports/*.html` (new/updated report files)
   - If there is nothing to commit, exit cleanly (no empty commit)
   - Commit with a fixed message, e.g. `Publish Elite daily summary to GitHub Pages`
   - `git push` to `origin` (no force push, no amend)

3. **Hard safety rules**
   - Never `git add .`
   - Never commit credentials, keys, or anything outside `docs/`
   - On conflict / push failure: log the error and stop; do not force anything
   - Keep existing generation logs in `daily_summary/logs/`

4. **Add tests** (see **Tests** below) before enabling auto-push on the scheduled task

5. **Verify once manually end-to-end**
   - Run the launcher (or morning script + publish helper)
   - Confirm `docs/` changed locally
   - Confirm commit appears on `main`
   - Confirm `…/latest.html` on GitHub Pages shows the new report

6. **Operational checks**
   - Machine is on / awake around 10:00
   - Git credentials work for the same Windows user that runs the scheduled task
   - Network is available for BigQuery + `git push`

## Tests

Tests are required for this change. Prefer a small Python helper for the git publish step so path allowlisting and dry-run behavior can be unit-tested (same pattern as `reward_check/test_decision.py`).

### Automated unit tests

Suggested location: `daily_summary/test_publish_pages_git.py` (or beside the helper module).

| Case | Expectation |
|------|-------------|
| Allowlist only `docs/` paths | Staging set includes only `docs/latest.html`, `docs/index.html`, `docs/reports.json`, and `docs/reports/*.html` |
| Reject paths outside `docs/` | Files under `daily_summary/`, credentials, `.env`, keys, etc. are never staged |
| No empty commit | When `docs/` has no changes, helper exits 0 and does not call `git commit` / `git push` |
| Fixed commit message | Commit uses the agreed message (e.g. `Publish Elite daily summary to GitHub Pages`) |
| No force / no amend | Helper never passes `--force`, `--force-with-lease`, or `--amend` |
| Dry-run mode | With `--dry-run` (or equivalent): computes what would be staged/pushed, writes to log, does **not** mutate git |
| Failure on pull/push conflict | Simulated non-zero `git pull` / `git push` → helper exits non-zero, logs error, does not force |
| Skip when report generation failed | Launcher/helper does not publish when morning script exit code ≠ 0 |

Mock `git` subprocess calls in unit tests — do not hit a real remote in CI/local unit runs.

### Integration / manual test plan

Run in order before turning on scheduled auto-push:

1. **Dry-run on real repo**
   - Generate or touch a `docs/` report locally
   - Run publish helper with dry-run
   - Confirm log lists only allowlisted `docs/` files
   - Confirm `git status` unchanged after dry-run

2. **Publish with push disabled (optional flag)**
   - If supported: stage + commit locally without push, or commit on a throwaway branch
   - Confirm commit content is `docs/` only (`git show --stat`)

3. **Full success path (once, supervised)**
   - Successful morning run (or force daily/weekend) → publish → commit → push to the feature branch or `main` as agreed
   - Confirm GitHub commit appears
   - Confirm Pages `latest.html` matches the new report (allow a few minutes for Pages deploy)

4. **Failure path**
   - Simulate offline push or auth failure
   - Confirm error is logged under `daily_summary/logs/`
   - Confirm no force push and working tree left in a recoverable state

5. **AM Brief regression**
   - Confirm AM Brief HTML is still **not** published to Pages

### Done criteria for tests

- Unit tests pass locally (`python -m pytest daily_summary/test_publish_pages_git.py` or `python daily_summary/test_publish_pages_git.py`)
- Dry-run checklist completed once
- One supervised live push succeeded
- Failure path logged without force/amend

## Out of scope (for now)

- GitHub Actions / cloud BigQuery credentials
- Publishing AM Brief to Pages
- Changing report logic or HTML layout
- Cursor Automations as the primary runner

## Complexity notes

| Dimension | Assessment |
|-----------|------------|
| Effort | Small — roughly half a day to one day including unit tests + one supervised live push |
| Project risk | Low–medium if `docs/`-only staging is enforced and tests cover allowlist / no-force |
| Main failure modes | Machine offline, git auth in scheduled context, remote conflict |

Conservative first version: success path only publishes `docs/`, fixed commit message, clear log on failure, no force/amend. Ship unit tests before enabling scheduled auto-push.

## Done when

- Unit tests for the publish helper pass
- Dry-run + one supervised live push succeeded
- No daily manual push is required
- Opening the fixed Pages URL shows the latest Daily/Weekend report after the scheduled morning run

## Related files

- `daily_summary/run_morning_elite_scheduled.ps1`
- `daily_summary/register_daily_summary_task.ps1`
- `daily_summary/generate_morning_elite.py`
- `daily_summary/publish_github_pages.py`
- `daily_summary/test_publish_pages_git.py` *(to add)*
- `docs/latest.html`
- `README.md` (GitHub Pages section)
- `daily_summary/github-pages-auto-publish-spec.md` (this doc)
