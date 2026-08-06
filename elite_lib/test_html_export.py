"""Unit tests for the shared HTML-shell payload injection helper."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from elite_lib.html_export import render_html_shell, write_html_shell


class RenderHtmlShellTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.shell = self.tmp / "shell.html"

    def test_missing_shell_raises_file_not_found(self) -> None:
        with self.assertRaises(FileNotFoundError):
            render_html_shell(self.tmp / "nope.html", {"a": 1})

    def test_injects_payload_json(self) -> None:
        self.shell.write_text("<script>const DATA = __PAYLOAD_JSON__;</script>", encoding="utf-8")
        html = render_html_shell(self.shell, {"a": 1, "b": "x"})
        self.assertIn(json.dumps({"a": 1, "b": "x"}), html)
        self.assertNotIn("__PAYLOAD_JSON__", html)

    def test_shell_missing_placeholder_is_a_silent_noop(self) -> None:
        # Matches the pre-refactor behavior exactly: .replace() finds nothing
        # to replace, so the shell text passes through unchanged.
        self.shell.write_text("<script>no placeholder here</script>", encoding="utf-8")
        html = render_html_shell(self.shell, {"a": 1})
        self.assertEqual(html, "<script>no placeholder here</script>")

    def test_raises_if_payload_text_itself_contains_the_marker(self) -> None:
        self.shell.write_text("__PAYLOAD_JSON__", encoding="utf-8")
        with self.assertRaises(RuntimeError):
            render_html_shell(self.shell, {"note": "__PAYLOAD_JSON__"})

    def test_default_raises_on_non_serializable_like_before(self) -> None:
        self.shell.write_text("__PAYLOAD_JSON__", encoding="utf-8")
        with self.assertRaises(TypeError):
            render_html_shell(self.shell, {"d": object()})

    def test_json_default_str_matches_am_daily_dashboard_behavior(self) -> None:
        self.shell.write_text("__PAYLOAD_JSON__", encoding="utf-8")
        html = render_html_shell(self.shell, {"d": object()}, json_default=str)
        self.assertIn("object object", html)


class WriteHtmlShellTests(unittest.TestCase):
    def test_writes_file_and_creates_parent_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            shell = tmp / "shell.html"
            shell.write_text("__PAYLOAD_JSON__", encoding="utf-8")
            out = tmp / "nested" / "out.html"
            result = write_html_shell(shell, {"x": 1}, out)
            self.assertEqual(result, out)
            self.assertTrue(out.exists())
            self.assertIn('{"x": 1}', out.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
