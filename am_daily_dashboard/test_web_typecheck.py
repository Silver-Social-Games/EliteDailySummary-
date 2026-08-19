"""Bridge so `python -m unittest discover -s am_daily_dashboard` also runs
`tsc --noEmit` over the AM Brief web/ sources.

Skips gracefully (not a failure) if Node/npm aren't on PATH, or if
SKIP_JS_TESTS is set - same convention as test_render_js.py. The whole point
of finishing the Phase 2 split was that web/src now typechecks cleanly
(strict, noUnusedLocals/noUnusedParameters, no // @ts-nocheck anywhere); this
is what keeps that true instead of drifting the next time someone edits a
view.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import unittest
from pathlib import Path

WEB_DIR = Path(__file__).resolve().parent / "web"


def _node_and_npm_available() -> bool:
    return shutil.which("node") is not None and shutil.which("npm") is not None


class WebTypecheckTests(unittest.TestCase):
    def test_web_sources_typecheck_clean(self) -> None:
        if os.environ.get("SKIP_JS_TESTS"):
            self.skipTest("SKIP_JS_TESTS set")
        if not _node_and_npm_available():
            self.skipTest("node/npm not found on PATH - install Node to run tsc --noEmit")

        npx = shutil.which("npx")
        run_kwargs = dict(
            cwd=WEB_DIR, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        )
        if not (WEB_DIR / "node_modules").exists():
            install = subprocess.run(
                [shutil.which("npm"), "install", "--no-audit", "--no-fund"], **run_kwargs
            )
            if install.returncode != 0:
                self.fail(f"npm install failed:\n{install.stdout}\n{install.stderr}")

        result = subprocess.run([npx, "tsc", "--noEmit"], **run_kwargs)
        if result.returncode != 0:
            self.fail(f"tsc --noEmit failed:\n{result.stdout}\n{result.stderr}")


if __name__ == "__main__":
    unittest.main()
