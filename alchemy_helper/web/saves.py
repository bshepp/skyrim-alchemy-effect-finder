"""Discovery and listing of Skyrim SE save files.

`default_saves_dir` locates the standard Skyrim SE saves folder on this
machine (if any); `list_saves` turns a directory of .ess files into
JSON-friendly summaries for the web layer.
"""
from datetime import datetime, timezone
from pathlib import Path

_SAVE_SUBPATH = Path("Documents") / "My Games" / "Skyrim Special Edition" / "Saves"
_ONEDRIVE_SUBPATH = Path("OneDrive") / "Documents" / "My Games" / "Skyrim Special Edition" / "Saves"


def default_saves_dir() -> Path | None:
    """Locate the standard Skyrim SE saves directory, if it exists.

    Tries ``~/Documents/My Games/Skyrim Special Edition/Saves`` first, then
    the OneDrive-redirected equivalent. Returns the first that exists on
    disk, or None if neither does.
    """
    home = Path.home()
    for candidate in (home / _SAVE_SUBPATH, home / _ONEDRIVE_SUBPATH):
        if candidate.exists():
            return candidate
    return None


def list_saves(directory: Path) -> list[dict]:
    """List .ess save files in `directory`, newest first.

    Args:
        directory: Directory to scan (non-recursive).

    Returns:
        List of {"path", "name", "modified_iso"} dicts, sorted by
        modification time descending.
    """
    directory = Path(directory)
    if not directory.is_dir():
        return []

    entries = []
    for save_path in directory.glob("*.ess"):
        stat = save_path.stat()
        entries.append({
            "path": str(save_path),
            "name": save_path.name,
            "modified_iso": datetime.fromtimestamp(
                stat.st_mtime, tz=timezone.utc).isoformat(),
        })

    entries.sort(key=lambda entry: entry["modified_iso"], reverse=True)
    return entries
