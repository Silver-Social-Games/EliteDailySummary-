"""Shared helper for injecting a JSON payload into a canvas-matched HTML shell.

Both daily_summary and am_daily_dashboard export a Cursor canvas as a
self-contained HTML file the same way: read a static shell template and
swap in a JSON payload at a placeholder. That "inject + write" logic was
duplicated (with a minor default= difference) across
daily_summary/canvas_to_html.py and am_daily_dashboard/canvas_to_html.py.
Each module keeps its own canvas/payload parsing - only this shared tail
end moved.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

PAYLOAD_PLACEHOLDER = "__PAYLOAD_JSON__"


def render_html_shell(
    shell_path: Path,
    payload: dict,
    *,
    json_default: Callable[[object], object] | None = None,
    ensure_ascii: bool = False,
) -> str:
    """Read an HTML shell template and inject payload as JSON.

    Raises FileNotFoundError if the shell is missing. Raises RuntimeError if
    the placeholder is still present in the output - this only happens if
    the serialized payload itself contains the literal marker text; a shell
    template missing the marker entirely is a silent no-op, same as before.
    """
    if not shell_path.exists():
        raise FileNotFoundError(f"Web shell missing: {shell_path}")
    payload_json = json.dumps(payload, ensure_ascii=ensure_ascii, default=json_default)
    # A "</" anywhere in payload text (an AID note, a ticket subject) would
    # otherwise close the shell's own <script> tag early and corrupt the
    # page. "<\/" is a valid escape inside a JS string/object literal and
    # renders identically, so this is invisible to the app.
    payload_json = payload_json.replace("</", "<\\/")
    html = shell_path.read_text(encoding="utf-8").replace(
        PAYLOAD_PLACEHOLDER, payload_json
    )
    if PAYLOAD_PLACEHOLDER in html:
        raise RuntimeError("Payload placeholder still present after replace")
    return html


def write_html_shell(
    shell_path: Path,
    payload: dict,
    out_path: Path,
    *,
    json_default: Callable[[object], object] | None = None,
    ensure_ascii: bool = False,
) -> Path:
    """render_html_shell(), then write the result to out_path."""
    html = render_html_shell(
        shell_path, payload, json_default=json_default, ensure_ascii=ensure_ascii
    )
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return out
