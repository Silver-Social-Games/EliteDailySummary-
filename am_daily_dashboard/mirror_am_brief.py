"""Route AM Brief mirrors into per-audience OneDrive subfolders.

Manager files land in ``AM Brief/Manager/``. Each AM gets only their stripped
HTML/JSON in ``AM Brief/{Coral|Gabriel|Lee|Rachel}/`` so OneDrive folder shares
stay isolated. Workshop ``exports/`` stays flat for generation and verify.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from elite_lib.export_paths import cursor_export_dir

DATED_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2})_elite_am_brief(?:_([a-z]+))?\.(html|json)$"
)
LATEST_RE = re.compile(r"^elite_am_brief(?:_([a-z]+))?\.html$")

SLUG_TO_FOLDER: dict[str, str] = {
    "": "Manager",
    "coral": "Coral",
    "gabriel": "Gabriel",
    "lee": "Lee",
    "rachel": "Rachel",
}

FOLDER_TO_SLUG = {folder: slug for slug, folder in SLUG_TO_FOLDER.items() if slug}


def audience_folder_for_filename(name: str) -> str | None:
    """Return the Elite_Cursor subfolder for a brief artifact name."""
    match = DATED_RE.match(name)
    if match:
        return SLUG_TO_FOLDER.get(match.group(2) or "")
    match = LATEST_RE.match(name)
    if match:
        return SLUG_TO_FOLDER.get(match.group(1) or "")
    return None


def am_brief_share_dir(*, agent_name: str = "", slug: str = "") -> Path | None:
    """Resolved share folder for an audience under Elite_Cursor AM Brief."""
    base = cursor_export_dir("am_brief")
    if base is None:
        return None
    if agent_name:
        folder = agent_name.strip()
        if folder not in SLUG_TO_FOLDER.values():
            return None
        return base / folder
    if slug:
        folder = SLUG_TO_FOLDER.get(slug.strip().lower())
        if not folder:
            return None
        return base / folder
    return base / "Manager"


def mirror_am_brief_to_cursor(*paths: Path | str | None) -> list[Path]:
    """Copy brief artifacts into audience subfolders on Elite_Cursor."""
    base = cursor_export_dir("am_brief")
    if base is None:
        return []
    copied: list[Path] = []
    for raw in paths:
        if raw is None:
            continue
        src = Path(raw)
        if not src.is_file():
            continue
        folder = audience_folder_for_filename(src.name)
        if folder is None:
            continue
        dest_dir = base / folder
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / src.name
        try:
            if src.resolve() != dest.resolve():
                shutil.copy2(src, dest)
        except OSError as exc:
            print(f"Elite_Cursor copy failed for {src.name} -> {folder}/: {exc}")
            continue
        copied.append(dest)
    if copied:
        print(f"Elite_Cursor AM Brief:")
        by_folder: dict[str, list[Path]] = {}
        for dest in copied:
            by_folder.setdefault(dest.parent.name, []).append(dest)
        for folder, files in sorted(by_folder.items()):
            print(f"  {folder}/")
            for dest in files:
                print(f"    {dest.name}")
    return copied


def organize_flat_am_brief_cursor(*, dry_run: bool = False) -> list[tuple[Path, Path]]:
    """Move legacy flat files from AM Brief/ root into audience subfolders."""
    base = cursor_export_dir("am_brief")
    if base is None:
        return []
    moves: list[tuple[Path, Path]] = []
    for path in sorted(base.iterdir()):
        if not path.is_file():
            continue
        folder = audience_folder_for_filename(path.name)
        if not folder:
            continue
        dest = base / folder / path.name
        if dest.resolve() == path.resolve():
            continue
        moves.append((path, dest))
        if dry_run:
            print(f"[DRY RUN] {path.name} -> {folder}/")
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            dest.unlink()
        shutil.move(str(path), str(dest))
        print(f"Moved {path.name} -> {folder}/")
    if dry_run and moves:
        print(f"\n{len(moves)} file(s) would move into audience subfolders.")
    elif moves:
        print(f"\nOrganized {len(moves)} file(s) into audience subfolders.")
    return moves


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Move flat AM Brief files on Elite_Cursor into audience subfolders"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print moves without changing files",
    )
    args = parser.parse_args()
    organize_flat_am_brief_cursor(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
