"""Pure-Python re-implementation of web/build.mjs's two hash guards.

Verifies the committed handoffs/elite_am_brief_web.html two ways with no Node
required, so the guard still works on a machine that never installed it - the
built shell is committed for exactly this reason (see the Phase 2 "Stale-build
guard" note in AM_DAILY_DASHBOARD.md):

- **sources hash** catches "you edited web/src/*.ts (or shell.html/build.mjs)
  and did not rebuild" - recomputed over the same file set and order as
  build.mjs's sourceFiles()/sourcesHash().
- **output hash** catches "you hand-edited the generated HTML, your change
  will be lost" - a source hash alone cannot see this, because the file
  would still claim to be built from the current sources.

Both re-derive build.mjs's own algorithm in Python rather than shelling out to
Node, on purpose: the guard must still fire on a machine with no Node
installed, since the built shell itself is what ships without it.
"""

from __future__ import annotations

import hashlib
import os
import re
import unittest
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
WEB_DIR = PACKAGE_DIR / "web"
SRC_DIR = WEB_DIR / "src"
SHELL_OUTPUT = PACKAGE_DIR / "handoffs" / "elite_am_brief_web.html"

STAMP_MARKER = "__BUILD_STAMP__"
STAMP_RE = re.compile(
    r"<!-- am-brief-build sources sha256:[0-9a-f]{64} output sha256:[0-9a-f]{64} -->"
)


def _lf(s: str) -> str:
    """CRLF -> LF. The repo checks out CRLF on Windows (core.autocrlf=true),
    so hashing raw bytes would make a fresh clone disagree with the machine
    that built it - build.mjs normalises the same way."""
    return s.replace("\r\n", "\n")


def _source_files() -> list[tuple[str, Path]]:
    """Same file set, names and sort order as build.mjs's sourceFiles():
    shell.html and build.mjs by their bare names, everything under web/src/
    (recursively, any extension) as "src/<relative/posix/path>", the whole
    list then sorted by name."""
    files: list[tuple[str, Path]] = [
        ("shell.html", WEB_DIR / "shell.html"),
        ("build.mjs", WEB_DIR / "build.mjs"),
    ]

    def walk(dir_path: Path, prefix: str) -> None:
        for name in sorted(os.listdir(dir_path)):
            full = dir_path / name
            if full.is_dir():
                walk(full, f"{prefix}{name}/")
            else:
                files.append((f"src/{prefix}{name}", full))

    walk(SRC_DIR, "")
    files.sort(key=lambda pair: pair[0])
    return files


def compute_sources_hash() -> str:
    h = hashlib.sha256()
    for name, full in _source_files():
        h.update(name.encode("utf-8"))
        h.update(b"\0")
        h.update(_lf(full.read_text(encoding="utf-8")).encode("utf-8"))
        h.update(b"\0")
    return h.hexdigest()


def compute_output_hash(html: str) -> str:
    """Blank the stamp back to the bare marker before hashing - the stamp
    cannot hash itself, and blanking is what makes this independent of
    whether the embedded output field is the real hash or a placeholder."""
    blanked = STAMP_RE.sub(STAMP_MARKER, html)
    return hashlib.sha256(_lf(blanked).encode("utf-8")).hexdigest()


def _committed_html_and_stamp() -> tuple[str, str, str]:
    html = SHELL_OUTPUT.read_text(encoding="utf-8")
    m = STAMP_RE.search(html)
    if not m:
        raise AssertionError(
            f"{SHELL_OUTPUT} has no am-brief-build stamp comment - is it "
            "still the pre-Phase-2 inline-script shell?"
        )
    sources, output = re.findall(r"sha256:([0-9a-f]{64})", m.group(0))
    return html, sources, output


class WebBuildStampTests(unittest.TestCase):
    """Both hash guards must fail loudly: "you edited the TS and did not
    rebuild" and "you hand-edited the generated HTML, your change will be
    lost." Neither test shells out to Node or esbuild."""

    def test_sources_hash_matches_committed_shell(self) -> None:
        _, committed_sources, _ = _committed_html_and_stamp()
        actual = compute_sources_hash()
        self.assertEqual(
            actual, committed_sources,
            "web/src (or shell.html / build.mjs) changed since the committed "
            "shell was built. Run `node am_daily_dashboard/web/build.mjs` "
            "and commit the result.",
        )

    def test_output_hash_matches_committed_shell(self) -> None:
        html, _, committed_output = _committed_html_and_stamp()
        actual = compute_output_hash(html)
        self.assertEqual(
            actual, committed_output,
            f"{SHELL_OUTPUT} was hand-edited after the last build - that "
            "change will be silently lost at the next `node build.mjs`. "
            "Edit web/src/*.ts instead and rebuild.",
        )


if __name__ == "__main__":
    unittest.main()
