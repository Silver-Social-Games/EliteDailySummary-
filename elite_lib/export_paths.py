"""Canonical user-facing export destination: VIP\\Elite_Cursor\\<project>.

Generators still write a working copy under the initiative folder (exports/,
handoffs/, daily_summaries/) so local tools keep working. After that write,
call ``mirror_to_cursor`` so the file also lands in OneDrive Elite_Cursor.

Override the root with env ``ELITE_CURSOR_ROOT`` (used in tests).
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

DEFAULT_CURSOR_ROOT = Path(
    r"C:\Users\Owner\OneDrive - Silver Social Games\Desktop\VIP\Elite_Cursor"
)

# Stable keys used in code / skills. Folder names match the OneDrive layout.
PROJECTS: dict[str, str] = {
    "am_brief": "AM Brief",
    "automated_offers": "Automated Offers",
    "birthday_gift": "Birthday Gift",
    "campaign_readers": "Campaign Readers",
    "ceo_h1": "CEO H1 Slide",
    "crm_playbook": "CRM Offer Playbook",
    "daily_summary": "Daily Summaries",
    "decline_protocol": "Decline Protocol",
    "declining_fri_sat": "Declining Fri-Sat Promo",
    "feedback_cro": "Feedback CRO",
    "goals_q2": "Goals Q2 2026",
    "last_push_60d": "Last Push 60d",
    "new_elite_players": "New Elite Players",
    "purchase_lookup": "Purchase Lookup",
    "queries": "Queries and Definitions",
    "roster": "Roster and Drop Lists",
    "vip_event": "VIP Event",
    "wow_drop": "WoW Drop Analysis",
}


def cursor_root() -> Path:
    raw = os.environ.get("ELITE_CURSOR_ROOT", "").strip()
    return Path(raw) if raw else DEFAULT_CURSOR_ROOT


def cursor_export_dir(project: str) -> Path | None:
    """Create and return Elite_Cursor/<project>, or None if the drive is unavailable."""
    if project not in PROJECTS:
        known = ", ".join(sorted(PROJECTS))
        raise KeyError(f"Unknown Elite_Cursor project {project!r}. Known: {known}")
    dest = cursor_root() / PROJECTS[project]
    try:
        dest.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"Elite_Cursor unavailable ({exc}); keeping local export only.")
        return None
    return dest


def mirror_to_cursor(project: str, *paths: Path | str | None) -> list[Path]:
    """Copy finished files into Elite_Cursor/<project>. Returns copied dest paths."""
    dest_dir = cursor_export_dir(project)
    if dest_dir is None:
        return []
    copied: list[Path] = []
    for raw in paths:
        if raw is None:
            continue
        src = Path(raw)
        if not src.is_file():
            continue
        dest = dest_dir / src.name
        try:
            if src.resolve() != dest.resolve():
                shutil.copy2(src, dest)
        except OSError as exc:
            print(f"Elite_Cursor copy failed for {src.name}: {exc}")
            continue
        copied.append(dest)
    if copied:
        print(f"Elite_Cursor: {dest_dir}")
        for dest in copied:
            print(f"  {dest.name}")
    return copied
