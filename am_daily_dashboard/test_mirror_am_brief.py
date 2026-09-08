"""Tests for per-audience AM Brief mirror routing."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PACKAGE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PACKAGE_DIR))

from mirror_am_brief import (
    am_brief_share_dir,
    audience_folder_for_filename,
    mirror_am_brief_to_cursor,
    organize_flat_am_brief_cursor,
)


class AudienceFolderTests(unittest.TestCase):
    def test_manager_dated_and_latest(self) -> None:
        self.assertEqual(
            audience_folder_for_filename("2026-09-06_elite_am_brief.html"),
            "Manager",
        )
        self.assertEqual(audience_folder_for_filename("elite_am_brief.html"), "Manager")

    def test_per_am_dated_and_latest(self) -> None:
        self.assertEqual(
            audience_folder_for_filename("2026-09-06_elite_am_brief_gabriel.html"),
            "Gabriel",
        )
        self.assertEqual(
            audience_folder_for_filename("elite_am_brief_gabriel.html"),
            "Gabriel",
        )

    def test_unknown_names_return_none(self) -> None:
        self.assertIsNone(audience_folder_for_filename("elite_goals_workbook.xlsx"))


class MirrorRoutingTests(unittest.TestCase):
    def test_mirror_routes_into_subfolders(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            am_brief = root / "AM Brief"
            am_brief.mkdir()
            src = am_brief.parent / "2026-09-06_elite_am_brief.html"
            src.write_text("manager", encoding="utf-8")
            gab_src = am_brief.parent / "2026-09-06_elite_am_brief_gabriel.html"
            gab_src.write_text("gabriel", encoding="utf-8")

            with patch("mirror_am_brief.cursor_export_dir", return_value=am_brief):
                copied = mirror_am_brief_to_cursor(src, gab_src)

            self.assertEqual(len(copied), 2)
            self.assertTrue((am_brief / "Manager" / src.name).is_file())
            self.assertTrue((am_brief / "Gabriel" / gab_src.name).is_file())

    def test_organize_moves_flat_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            am_brief = Path(tmp)
            flat = am_brief / "elite_am_brief_gabriel.html"
            flat.write_text("gabriel", encoding="utf-8")

            with patch("mirror_am_brief.cursor_export_dir", return_value=am_brief):
                moves = organize_flat_am_brief_cursor()

            self.assertEqual(len(moves), 1)
            self.assertFalse(flat.exists())
            self.assertTrue((am_brief / "Gabriel" / flat.name).is_file())

    def test_share_dir_by_agent_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            am_brief = Path(tmp)
            with patch("mirror_am_brief.cursor_export_dir", return_value=am_brief):
                share = am_brief_share_dir(agent_name="Gabriel")
            self.assertEqual(share, am_brief / "Gabriel")


if __name__ == "__main__":
    unittest.main()
