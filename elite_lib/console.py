"""Console helpers for Elite report generators."""

from __future__ import annotations

import sys


def use_utf8_stdout() -> None:
    """Reconfigure stdout/stderr for UTF-8 (Windows cp1252/cp1255 safe)."""
    for name in ("stdout", "stderr"):
        stream = getattr(sys, name, None)
        if stream is None:
            continue
        reconfigure = getattr(stream, "reconfigure", None)
        if not callable(reconfigure):
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError, TypeError):
            pass
