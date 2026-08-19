"""Bridge so `python -m unittest discover -s am_daily_dashboard` also runs
the jsdom render suite (tests_js/render.test.mjs).

Skips gracefully (not a failure) if Node/npm aren't on PATH, or if
SKIP_JS_TESTS is set — this keeps the Python-only path working for anyone who
hasn't installed Node. The assertion logic itself lives in JS, where DOM
stack traces are native; see tests_js/README.md.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

TESTS_JS_DIR = Path(__file__).resolve().parent / "tests_js"


def _node_and_npm_available() -> bool:
    return shutil.which("node") is not None and shutil.which("npm") is not None


class RenderJsSuiteTests(unittest.TestCase):
    def test_jsdom_render_suite_passes(self) -> None:
        if os.environ.get("SKIP_JS_TESTS"):
            self.skipTest("SKIP_JS_TESTS set")
        if not _node_and_npm_available():
            self.skipTest("node/npm not found on PATH — install Node to run render tests")

        npm = shutil.which("npm")
        # npm/node print unicode glyphs (checkmarks, arrows) that the default
        # Windows console codepage (e.g. cp1255) cannot decode — always read
        # subprocess output as UTF-8 regardless of the host locale.
        run_kwargs = dict(
            cwd=TESTS_JS_DIR, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        )
        if not (TESTS_JS_DIR / "node_modules").exists():
            install = subprocess.run(
                [npm, "install", "--no-audit", "--no-fund"], **run_kwargs
            )
            if install.returncode != 0:
                self.fail(f"npm install failed:\n{install.stdout}\n{install.stderr}")

        result = subprocess.run([npm, "test", "--silent"], **run_kwargs)
        if result.returncode != 0:
            self.fail(f"AM Brief render suite failed:\n{result.stdout}\n{result.stderr}")


if __name__ == "__main__":
    unittest.main()
