"""Unit tests for elite_lib.export_paths — no OneDrive required."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from elite_lib.export_paths import (
    PROJECTS,
    cursor_export_dir,
    cursor_root,
    mirror_to_cursor,
)


class CursorRootTests(unittest.TestCase):
    def test_env_override(self) -> None:
        with patch.dict("os.environ", {"ELITE_CURSOR_ROOT": r"D:\tmp\Elite_Cursor"}):
            self.assertEqual(cursor_root(), Path(r"D:\tmp\Elite_Cursor"))

    def test_unknown_project_raises(self) -> None:
        with self.assertRaises(KeyError):
            cursor_export_dir("not_a_real_project")


class MirrorTests(unittest.TestCase):
    def test_copies_into_project_folder(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Elite_Cursor"
            src_dir = Path(tmp) / "local"
            src_dir.mkdir()
            src = src_dir / "sample.csv"
            src.write_text("aid,1\n", encoding="utf-8")
            with patch.dict("os.environ", {"ELITE_CURSOR_ROOT": str(root)}):
                copied = mirror_to_cursor("purchase_lookup", src)
            dest = root / PROJECTS["purchase_lookup"] / "sample.csv"
            self.assertEqual(copied, [dest])
            self.assertEqual(dest.read_text(encoding="utf-8"), "aid,1\n")

    def test_skips_missing_files(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Elite_Cursor"
            missing = Path(tmp) / "gone.csv"
            with patch.dict("os.environ", {"ELITE_CURSOR_ROOT": str(root)}):
                copied = mirror_to_cursor("wow_drop", missing, None)
            self.assertEqual(copied, [])


if __name__ == "__main__":
    unittest.main()
