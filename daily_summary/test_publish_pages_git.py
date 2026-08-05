"""Unit tests for docs-only GitHub Pages git publish helper."""

from __future__ import annotations

import unittest
from typing import Sequence

from daily_summary.publish_pages_git import (
    COMMIT_MESSAGE,
    FORBIDDEN_GIT_FLAGS,
    GitResult,
    UnsafeGitError,
    assert_safe_git_argv,
    filter_allowlisted,
    is_allowlisted_docs_path,
    normalize_repo_relpath,
    parse_porcelain_paths,
    publish_docs_to_git,
)


class AllowlistTests(unittest.TestCase):
    def test_allows_root_docs_files(self) -> None:
        for path in (
            "docs/latest.html",
            "docs/index.html",
            "docs/reports.json",
            r"docs\latest.html",
            "./docs/index.html",
        ):
            self.assertTrue(is_allowlisted_docs_path(path), path)

    def test_allows_reports_html(self) -> None:
        self.assertTrue(
            is_allowlisted_docs_path(
                "docs/reports/2026-08-02_elite_daily_summary_canvas.html"
            )
        )

    def test_rejects_outside_docs(self) -> None:
        for path in (
            "daily_summary/generate_morning_elite.py",
            "key.json.json",
            ".env",
            "credentials.json",
            "docs/secret.txt",
            "docs/reports/notes.md",
            "docs/reports/sub/nested.html",
            "../docs/latest.html",
            "docs/../Elite.MD",
        ):
            self.assertFalse(is_allowlisted_docs_path(path), path)

    def test_filter_allowlisted(self) -> None:
        paths = filter_allowlisted(
            [
                "docs/latest.html",
                "daily_summary/run_morning_elite_scheduled.ps1",
                "docs/reports/a.html",
                "docs/reports.json",
            ]
        )
        self.assertEqual(
            paths,
            ["docs/latest.html", "docs/reports.json", "docs/reports/a.html"],
        )


class PorcelainAndSafetyTests(unittest.TestCase):
    def test_parse_porcelain_paths(self) -> None:
        porcelain = "\n".join(
            [
                " M docs/latest.html",
                "?? docs/reports/new.html",
                "R  docs/old.html -> docs/reports/renamed.html",
                " M daily_summary/foo.py",
            ]
        )
        paths = parse_porcelain_paths(porcelain)
        self.assertEqual(
            paths,
            [
                "docs/latest.html",
                "docs/reports/new.html",
                "docs/reports/renamed.html",
                "daily_summary/foo.py",
            ],
        )

    def test_normalize_repo_relpath(self) -> None:
        self.assertEqual(normalize_repo_relpath(r"docs\latest.html"), "docs/latest.html")

    def test_assert_safe_rejects_force_and_broad_add(self) -> None:
        with self.assertRaises(UnsafeGitError):
            assert_safe_git_argv(["git", "push", "--force"])
        with self.assertRaises(UnsafeGitError):
            assert_safe_git_argv(["git", "push", "--force-with-lease"])
        with self.assertRaises(UnsafeGitError):
            assert_safe_git_argv(["git", "commit", "--amend", "-m", "x"])
        with self.assertRaises(UnsafeGitError):
            assert_safe_git_argv(["git", "add", "."])
        with self.assertRaises(UnsafeGitError):
            assert_safe_git_argv(["git", "add", "--", "daily_summary/foo.py"])

    def test_assert_safe_allows_allowlisted_add(self) -> None:
        assert_safe_git_argv(
            ["git", "add", "--", "docs/latest.html", "docs/reports/a.html"]
        )


class FakeGit:
    def __init__(self, responses: dict[tuple[str, ...], GitResult] | None = None) -> None:
        self.calls: list[list[str]] = []
        self.responses = responses or {}
        self.default = GitResult(0, "", "")

    def __call__(self, argv: Sequence[str]) -> GitResult:
        self.calls.append(list(argv))
        key = tuple(argv)
        if key in self.responses:
            return self.responses[key]
        # Match by verb for flexible fixtures
        verb = argv[1] if len(argv) > 1 else ""
        for stored, result in self.responses.items():
            if stored and stored[0] == "git" and len(stored) > 1 and stored[1] == verb:
                return result
        return self.default


class PublishFlowTests(unittest.TestCase):
    def test_no_empty_commit_when_no_docs_changes(self) -> None:
        fake = FakeGit(
            {
                ("git", "status", "--porcelain", "--", "docs"): GitResult(
                    0, " M daily_summary/x.py\n", ""
                ),
            }
        )
        result = publish_docs_to_git(runner=fake, skip_pull=True)
        self.assertTrue(result.ok)
        self.assertEqual(result.staged, [])
        verbs = [c[1] for c in fake.calls if len(c) > 1]
        self.assertNotIn("commit", verbs)
        self.assertNotIn("push", verbs)
        self.assertNotIn("add", verbs)

    def test_dry_run_does_not_mutate(self) -> None:
        fake = FakeGit(
            {
                ("git", "status", "--porcelain", "--", "docs"): GitResult(
                    0,
                    " M docs/latest.html\n?? docs/reports/a.html\n",
                    "",
                ),
            }
        )
        result = publish_docs_to_git(dry_run=True, runner=fake)
        self.assertTrue(result.ok)
        self.assertTrue(result.dry_run)
        self.assertEqual(
            result.staged,
            ["docs/latest.html", "docs/reports/a.html"],
        )
        verbs = [c[1] for c in fake.calls if len(c) > 1]
        self.assertEqual(verbs, ["status"])
        self.assertFalse(result.pushed)

    def test_fixed_commit_message_and_no_forbidden_flags(self) -> None:
        fake = FakeGit(
            {
                ("git", "status", "--porcelain", "--", "docs"): GitResult(
                    0, " M docs/index.html\n", ""
                ),
            }
        )
        result = publish_docs_to_git(runner=fake, skip_pull=True)
        self.assertTrue(result.ok)
        self.assertTrue(result.pushed)

        commit_calls = [c for c in fake.calls if len(c) > 1 and c[1] == "commit"]
        self.assertEqual(len(commit_calls), 1)
        self.assertEqual(commit_calls[0], ["git", "commit", "-m", COMMIT_MESSAGE])

        for call in fake.calls:
            for arg in call:
                self.assertNotIn(arg, FORBIDDEN_GIT_FLAGS)
                self.assertFalse(arg.startswith("--force"))

    def test_pull_failure_stops_without_force(self) -> None:
        fake = FakeGit(
            {
                ("git", "pull", "--rebase", "--no-edit"): GitResult(
                    1, "", "conflict: divergent branches"
                ),
            }
        )
        result = publish_docs_to_git(runner=fake)
        self.assertFalse(result.ok)
        self.assertIn("conflict", result.message.lower())
        verbs = [c[1] for c in fake.calls if len(c) > 1]
        self.assertEqual(verbs, ["pull"])
        self.assertNotIn("push", verbs)

    def test_push_failure_stops_without_force(self) -> None:
        fake = FakeGit()
        fake.responses = {
            ("git", "status", "--porcelain", "--", "docs"): GitResult(
                0, " M docs/latest.html\n", ""
            ),
            ("git", "push"): GitResult(1, "", "authentication failed"),
        }
        result = publish_docs_to_git(runner=fake, skip_pull=True)
        self.assertFalse(result.ok)
        self.assertIn("authentication", result.message.lower())
        push_calls = [c for c in fake.calls if len(c) > 1 and c[1] == "push"]
        self.assertEqual(push_calls, [["git", "push"]])

    def test_no_push_flag_commits_without_push(self) -> None:
        fake = FakeGit(
            {
                ("git", "status", "--porcelain", "--", "docs"): GitResult(
                    0, " M docs/reports.json\n", ""
                ),
            }
        )
        result = publish_docs_to_git(runner=fake, skip_pull=True, no_push=True)
        self.assertTrue(result.ok)
        self.assertFalse(result.pushed)
        verbs = [c[1] for c in fake.calls if len(c) > 1]
        self.assertIn("commit", verbs)
        self.assertNotIn("push", verbs)

    def test_rejects_non_allowlisted_via_add_guard(self) -> None:
        # Even if status somehow returned a bad path, filter strips it; empty → no commit
        fake = FakeGit(
            {
                ("git", "status", "--porcelain", "--", "docs"): GitResult(
                    0, " M docs/not-allowed.txt\n", ""
                ),
            }
        )
        result = publish_docs_to_git(runner=fake, skip_pull=True)
        self.assertTrue(result.ok)
        self.assertEqual(result.staged, [])


if __name__ == "__main__":
    unittest.main()
