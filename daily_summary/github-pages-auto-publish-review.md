# Code Review: GitHub Pages Auto-Publish

**Review date:** 2026-08-03  
**Reviewed branch:** `feature/github-pages-auto-publish`  
**Scope:** Git auto-publish helper, unit tests, scheduled launcher wiring, and related documentation  
**Review mode:** Read-only review; no implementation code was changed

## Overall assessment

**Recommendation: do not enable the scheduled auto-push yet.**

The implementation has a good safety-oriented foundation, but several Git edge
cases can prevent publication or commit unrelated work. The most important
problems concern operation order, the existing Git index, and the destination
branch.

The current 15 unit tests pass, but they do not exercise the highest-risk
repository states described below.

## What is good

- The helper uses argument arrays instead of `shell=True`.
- The intended staging allowlist is narrow.
- Force push and amend are not used by the normal flow.
- Dry-run and no-push modes are available.
- Report failure prevents the launcher from starting the Git helper.
- Git output and exit codes are captured by the scheduled launcher.
- The implementation is separated into a testable Python helper.

## Blocking findings

### 1. Critical: pull runs after report generation has made the worktree dirty

**Evidence**

- The scheduled launcher runs the report first:
  `daily_summary/run_morning_elite_scheduled.ps1:41-49`.
- It invokes the Git publisher afterward:
  `daily_summary/run_morning_elite_scheduled.ps1:62-68`.
- The publisher starts with `git pull --rebase`:
  `daily_summary/publish_pages_git.py:173-180`.

**Impact**

The report is expected to modify files under `docs/`. A normal
`git pull --rebase` commonly refuses to run when tracked worktree changes are
present. This means the expected success path can fail before staging or
committing the newly generated report.

Unrelated local modifications make this even more likely. The repository
currently has many modified and untracked files, including modified `docs/`
files.

**Recommendation**

Update from the remote before report generation, or redesign the flow so remote
synchronization does not require rebasing a dirty worktree. Do not automatically
stash unrelated user work.

### 2. Critical: a plain commit can include unrelated files already staged

**Evidence**

- The helper stages allowlisted report files:
  `daily_summary/publish_pages_git.py:200-204`.
- It then runs a normal repository-wide `git commit`:
  `daily_summary/publish_pages_git.py:206-210`.

**Impact**

`git commit` commits the entire current index, not only files staged by the
helper. If a developer previously staged code, credentials, or another
initiative, the automated commit can include those files despite the `docs/`
allowlist.

This breaks the primary safety promise: “only `docs/` files.”

**Recommendation**

Before mutation, verify that the index contains no paths outside the exact
allowlist and fail safely if it does. A stronger design would isolate the
automation’s index or explicitly commit only validated paths while preserving
the developer’s existing index.

### 3. Critical: push destination depends on whichever branch is checked out

**Evidence**

- The helper runs only `git push`:
  `daily_summary/publish_pages_git.py:232-235`.
- It does not verify the current branch, upstream, remote, or destination.
- At review time, the active branch is
  `feature/github-pages-auto-publish`, while its upstream is `origin/main`.

**Impact**

Possible outcomes include:

- Git refuses the push because the local and upstream branch names differ.
- A report is pushed to a feature branch that GitHub Pages does not publish.
- A scheduled run pushes to an unrelated branch left checked out by a
  developer.
- The script reports success while the public `main/docs` site remains stale.

**Recommendation**

Define and validate one explicit deployment destination. The job should refuse
to run unless repository, branch, remote, and upstream match the approved Pages
configuration. Do not silently push the current branch.

### 4. High: a failed push is not reliably retried

**Evidence**

- Commit occurs before push:
  `daily_summary/publish_pages_git.py:206-235`.
- If push fails, the local commit remains.
- On the next run, the helper exits early when there are no new worktree changes:
  `daily_summary/publish_pages_git.py:180-188`.

**Impact**

An authentication or network failure can leave a valid report commit locally
but unpublished. If the next generated report is identical, the helper sees no
`docs/` changes and never retries the pending push.

The same issue applies after using `--no-push`. Windows Task Scheduler’s retry
can rerun generation but still fail to publish the already-created commit.

**Recommendation**

Detect whether the approved deployment branch is ahead of its approved remote
and retry that push even when no new report files changed. Log pending commit
state clearly.

## Additional edge cases

### 5. High: hidden scheduled task can wait for interactive Git authentication

`subprocess.run` has no timeout, and Git is not forced into non-interactive mode
(`daily_summary/publish_pages_git.py:122-133`). If credentials expire, the
hidden scheduled task may wait for a prompt until the Task Scheduler execution
limit is reached.

Use a bounded timeout and non-interactive authentication behavior. Treat
credential failure as an explicit logged error.

### 6. Medium: Friday/Saturday “skip” still executes the publisher

The router returns success when no report is scheduled, and the launcher treats
that as permission to publish
(`daily_summary/run_morning_elite_scheduled.ps1:51-68`).

Therefore, a skipped report day can publish old or manually edited `docs/`
files. The launcher should distinguish “report generated successfully” from
“no report scheduled.”

### 7. Medium: any top-level HTML in `docs/reports/` is publishable

The allowlist regex accepts every `docs/reports/*.html` filename:
`daily_summary/publish_pages_git.py:33,76-82`.

This can publish a mistakenly copied AM Brief or another internal HTML artifact,
despite the product rule that AM Brief stays local. Validate the exact
Daily/Weekend filename patterns rather than only the extension and directory.

### 8. Low: the broad-add guard does not actually reject `-A` or `--all`

At `daily_summary/publish_pages_git.py:94-100`, arguments beginning with `-` are
removed before the code checks for `-A` and `--all`. Consequently,
`assert_safe_git_argv(["git", "add", "-A"])` would pass.

The production helper does not currently construct that command, so this is
defense-in-depth rather than an immediate exploit. The guard and its tests
should still match their stated contract.

### 9. Low: rename parsing can fail to stage the old side of a rename

`parse_porcelain_paths` keeps only the destination of `old -> new`
(`daily_summary/publish_pages_git.py:103-115`). Staging only the destination
does not always stage deletion of the old path. Generated report files are
normally additive, so this is a lower-probability issue.

### 10. Low: unexpected process errors are not converted to structured results

The publisher catches `UnsafeGitError` and `RuntimeError`, but not failures such
as Git being missing or subprocess startup errors
(`daily_summary/publish_pages_git.py:244-247`). The launcher will capture a
traceback and non-zero exit, but the operator message will be less clear.

## Test review

**Result:** all 15 current unit tests pass.

The tests cover:

- intended allowlisted and rejected paths;
- dry-run behavior;
- normal commit message;
- mocked pull and push failures;
- no-change behavior;
- absence of force flags in the generated happy-path commands.

Important missing tests:

- unrelated files already present in the Git index;
- `git pull --rebase` with generated `docs/` changes in the worktree;
- wrong branch, detached HEAD, missing upstream, and branch/upstream mismatch;
- a local unpublished commit after push failure;
- retry behavior when there are no new file changes;
- `git add -A` and `git add --all` safety checks;
- Friday/Saturday no-report behavior in the PowerShell launcher;
- AM Brief or unexpected HTML under `docs/reports/`;
- authentication prompt timeout/non-interactive operation;
- a real temporary Git repository integration test (without a network remote).

The mocked tests currently prove the command sequence under assumed responses;
they do not prove that the sequence works in a realistic dirty repository.

## Recommended implementation order

1. Decide the exact deployment branch and remote.
2. Move or redesign remote synchronization so it works before generated
   worktree changes exist.
3. Protect against any pre-staged non-report content.
4. Add recovery for locally committed but unpushed reports.
5. Make scheduled Git operations non-interactive and time-bounded.
6. Distinguish “generated” from “skipped.”
7. Narrow report filename validation to Daily/Weekend artifacts.
8. Add temporary-repository integration tests for the critical Git states.
9. Perform one supervised live run only after all blockers pass.

## Approval recommendation

**Current status: changes requested.**

The approach is reasonable, but the scheduled auto-push should remain disabled
until findings 1–4 are resolved and covered by tests. The existing helper is
safe from force pushing, but it is not yet safe from committing unrelated staged
content or pushing to the wrong destination.
