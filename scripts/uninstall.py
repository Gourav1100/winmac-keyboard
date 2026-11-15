#!/usr/bin/env python3
"""Restore backed-up settings (does not uninstall third-party apps)."""

from pathlib import Path
import json, plistlib, shutil
from install import read_alttab_preferences, stop_alttab, write_alttab_preferences


def main():
    state = Path.home() / ".config/winmac-keyboard/latest.json"
    if not state.exists():
        raise SystemExit("No saved install manifest found")
    folder = Path(json.loads(state.read_text())["backup_dir"])
    manifest = json.loads((folder / "manifest.json").read_text())
    print("Restoring originals from:", folder)
    print(
        "WARNING: Any changes made to these files or AltTab preferences since installation will be overwritten."
    )
    if input("Type RESTORE to continue: ") != "RESTORE":
        raise SystemExit("Canceled")
    for path, bkp in manifest["backups"].items():
        target = Path(path)
        if bkp:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(bkp, target)
        elif target.exists():
            target.unlink()
    if manifest.get("alttab_keys"):
        stop_alttab()
        if manifest.get("alttab_backup"):
            preferences = plistlib.loads(Path(manifest["alttab_backup"]).read_bytes())
        else:
            preferences = read_alttab_preferences() or {}
            for key in manifest["alttab_keys"]:
                preferences.pop(key, None)
        write_alttab_preferences(preferences)
    print(
        "Settings restored. Karabiner-Elements and AltTab remain installed; restart AltTab if needed."
    )


if __name__ == "__main__":
    main()
