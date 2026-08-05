"""Safely commit and push allowlisted docs/ files to update GitHub Pages.

Only stages:
  - docs/latest.html
  - docs/index.html
  - docs/reports.json
  - docs/reports/*.html

Never uses --force / --force-with-lease / --amend.
Never runs git add .
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Sequence

PROJECT_ROOT = Path(__file__).resolve().parent.parent
COMMIT_MESSAGE = "Publish Elite daily summary to GitHub Pages"

ALLOWED_ROOT_RELPATHS = frozenset(
    {
        "docs/latest.html",
        "docs/index.html",
        "docs/reports.json",
    }
)
REPORTS_HTML_RE = re.compile(r"^docs/reports/[^/]+\.html$")

FORBIDDEN_GIT_FLAGS = frozenset(
    {
        "--force",
        "-f",
        "--force-with-lease",
        "--amend",
    }
)

GitRunner = Callable[[Sequence[str]], "GitResult"]


@dataclass(frozen=True)
class GitResult:
    code: int
    stdout: str = ""
    stderr: str = ""


@dataclass
class PublishResult:
    ok: bool
    message: str
    staged: list[str] = field(default_factory=list)
    dry_run: bool = False
    pushed: bool = False
    commands: list[list[str]] = field(default_factory=list)


class UnsafeGitError(ValueError):
    """Raised when a git argv includes forbidden flags."""


def normalize_repo_relpath(path: str | Path) -> str:
    """Normalize to forward-slash path relative to repo root (no leading ./)."""
    text = str(path).replace("\\", "/").strip()
    if text.startswith("./"):
        text = text[2:]
    return text.lstrip("/")


def is_allowlisted_docs_path(relpath: str) -> bool:
    rel = normalize_repo_relpath(relpath)
    if ".." in rel.split("/"):
        return False
    if rel in ALLOWED_ROOT_RELPATHS:
        return True
    return bool(REPORTS_HTML_RE.match(rel))


def assert_safe_git_argv(argv: Sequence[str]) -> None:
    """Reject force/amend (and never allow bare `git add .`)."""
    if not argv:
        raise UnsafeGitError("empty git argv")
    if argv[0] != "git":
        raise UnsafeGitError(f"expected git command, got: {argv[0]!r}")
    for arg in argv[1:]:
        if arg in FORBIDDEN_GIT_FLAGS or arg.startswith("--force"):
            raise UnsafeGitError(f"forbidden git flag: {arg}")
    if len(argv) >= 2 and argv[1] == "add":
        paths = [a for a in argv[2:] if not a.startswith("-")]
        if any(p in {".", "-A", "--all"} for p in paths):
            raise UnsafeGitError("refusing broad git add")
        for p in paths:
            if not is_allowlisted_docs_path(p):
                raise UnsafeGitError(f"refusing to stage non-allowlisted path: {p}")


def parse_porcelain_paths(porcelain: str) -> list[str]:
    """Parse `git status --porcelain` paths (supports rename `old -> new`)."""
    paths: list[str] = []
    for raw in porcelain.splitlines():
        if len(raw) < 4:
            continue
        entry = raw[3:]
        if " -> " in entry:
            entry = entry.split(" -> ", 1)[1]
        entry = entry.strip().strip('"')
        if entry:
            paths.append(normalize_repo_relpath(entry))
    return paths


def filter_allowlisted(paths: Sequence[str]) -> list[str]:
    return sorted({p for p in (normalize_repo_relpath(x) for x in paths) if is_allowlisted_docs_path(p)})


def default_git_runner(argv: Sequence[str], *, cwd: Path = PROJECT_ROOT) -> GitResult:
    assert_safe_git_argv(argv)
    completed = subprocess.run(
        list(argv),
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return GitResult(completed.returncode, completed.stdout or "", completed.stderr or "")


def _run(
    runner: GitRunner,
    argv: Sequence[str],
    commands: list[list[str]],
    *,
    record: bool = True,
) -> GitResult:
    assert_safe_git_argv(argv)
    cmd = list(argv)
    if record:
        commands.append(cmd)
    return runner(cmd)


def collect_stageable_docs_paths(runner: GitRunner, commands: list[list[str]]) -> list[str]:
    result = _run(runner, ["git", "status", "--porcelain", "--", "docs"], commands)
    if result.code != 0:
        raise RuntimeError(
            f"git status failed ({result.code}): {result.stderr.strip() or result.stdout.strip()}"
        )
    return filter_allowlisted(parse_porcelain_paths(result.stdout))


def publish_docs_to_git(
    *,
    dry_run: bool = False,
    no_push: bool = False,
    runner: GitRunner | None = None,
    skip_pull: bool = False,
) -> PublishResult:
    """Pull, stage allowlisted docs/, commit, and optionally push.

    Returns PublishResult. ok=False on pull/commit/push failure.
    """
    runner = runner or default_git_runner
    commands: list[list[str]] = []

    try:
        if not skip_pull and not dry_run:
            pull = _run(runner, ["git", "pull", "--rebase", "--no-edit"], commands)
            if pull.code != 0:
                msg = pull.stderr.strip() or pull.stdout.strip() or "git pull failed"
                return PublishResult(False, msg, commands=commands)

        staged = collect_stageable_docs_paths(runner, commands)
        if not staged:
            return PublishResult(
                True,
                "No allowlisted docs/ changes to publish",
                staged=[],
                dry_run=dry_run,
                commands=commands,
            )

        if dry_run:
            return PublishResult(
                True,
                f"Dry-run: would stage {len(staged)} file(s), commit, "
                f"{'skip push' if no_push else 'push'}",
                staged=staged,
                dry_run=True,
                commands=commands,
            )

        add_argv = ["git", "add", "--", *staged]
        add = _run(runner, add_argv, commands)
        if add.code != 0:
            msg = add.stderr.strip() or add.stdout.strip() or "git add failed"
            return PublishResult(False, msg, staged=staged, commands=commands)

        commit = _run(
            runner,
            ["git", "commit", "-m", COMMIT_MESSAGE],
            commands,
        )
        if commit.code != 0:
            combined = (commit.stdout + "\n" + commit.stderr).lower()
            if "nothing to commit" in combined:
                return PublishResult(
                    True,
                    "Nothing to commit after staging",
                    staged=staged,
                    commands=commands,
                )
            msg = commit.stderr.strip() or commit.stdout.strip() or "git commit failed"
            return PublishResult(False, msg, staged=staged, commands=commands)

        if no_push:
            return PublishResult(
                True,
                f"Committed {len(staged)} file(s); push skipped (--no-push)",
                staged=staged,
                pushed=False,
                commands=commands,
            )

        push = _run(runner, ["git", "push"], commands)
        if push.code != 0:
            msg = push.stderr.strip() or push.stdout.strip() or "git push failed"
            return PublishResult(False, msg, staged=staged, commands=commands)

        return PublishResult(
            True,
            f"Published {len(staged)} file(s) to origin",
            staged=staged,
            pushed=True,
            commands=commands,
        )
    except UnsafeGitError as exc:
        return PublishResult(False, str(exc), commands=commands)
    except RuntimeError as exc:
        return PublishResult(False, str(exc), commands=commands)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Commit and push allowlisted docs/ files for GitHub Pages"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show allowlisted changes only; do not mutate git",
    )
    parser.add_argument(
        "--no-push",
        action="store_true",
        help="Commit locally but do not push",
    )
    parser.add_argument(
        "--skip-pull",
        action="store_true",
        help="Skip git pull --rebase (useful for local testing)",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    result = publish_docs_to_git(
        dry_run=args.dry_run,
        no_push=args.no_push,
        skip_pull=args.skip_pull,
    )
    for path in result.staged:
        print(f"  stage: {path}")
    print(result.message)
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
