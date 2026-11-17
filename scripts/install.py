#!/usr/bin/env python3
"""Idempotent-ish, backed-up Windows keyboard setup for macOS."""

import argparse
import copy
import datetime
import json
import re
import os
from pathlib import Path
import platform
import plistlib
import shutil
import subprocess
import sys

from generate import PREFIX, build_rules, vscode_bindings
from shortcuts import ZSH_BINDINGS
from terminal_profiles import iterm_profile, terminal_profile, KITTY_CONFIG

HOME = Path.home()
KARABINER = HOME / ".config/karabiner/karabiner.json"
RULES_FILE = (
    HOME / ".config/karabiner/assets/complex_modifications/winmac-generated.json"
)
VSCODE = HOME / "Library/Application Support/Code/User/keybindings.json"
ZSHRC = HOME / ".zshrc"
STATE = HOME / ".config/winmac-keyboard"
SNAPSHOT = Path(__file__).resolve().parents[1] / "config/system.json"
ALTTAB_DOMAIN = "com.lwouis.alt-tab-macos"
ZSH_BEGIN = "# >>> winmac-keyboard >>>"
ZSH_END = "# <<< winmac-keyboard <<<"
LEGACY_DESCRIPTIONS = {
    "Terminal - restore Windows Ctrl+C interrupt",
    "Terminal - Home End and word navigation",
    "Windows Ctrl Shift C and V clipboard shortcuts",
    "01 - Windows key tap opens Spotlight; held remains Control",
    "02 - Windows key combinations",
    "03 - Ctrl+grave reserved for VS Code terminal and bypasses macOS window cycling",
    "04 - Windows Home End and selections",
    "05 - Windows Ctrl word navigation and delete",
    "06 - Windows Ctrl+Shift+Esc launches Activity Monitor",
    "07 - Windows Alt+F4 quits current application",
    "Windows-style Alt+Tab and Alt+F4",
    "Windows Home and End behavior",
    "Windows Ctrl+Backspace deletes previous word",
    "Windows Navigation and Editing Keys",
    "Windows Ctrl Backspace and Ctrl Delete",
    "Windows Alt Tab and Alt F4",
}


def portable_alttab_preferences(preferences):
    excluded_prefixes = ("MSAppCenter", "NS", "SU", "onboarding", "settingsWindowShown")
    return {
        key: value
        for key, value in preferences.items()
        if not key.startswith(excluded_prefixes)
    }


def merge_zshrc(current, bindings):
    lines = current.splitlines(keepends=True)
    starts = [
        index for index, line in enumerate(lines) if line.rstrip("\r\n") == ZSH_BEGIN
    ]
    ends = [index for index, line in enumerate(lines) if line.rstrip("\r\n") == ZSH_END]
    if len(starts) != len(ends) or len(starts) > 1 or (starts and starts[0] >= ends[0]):
        raise ValueError("Invalid winmac-keyboard block in .zshrc")
    block = (
        ZSH_BEGIN + "\n" + "".join(line + "\n" for line in bindings) + ZSH_END + "\n"
    )
    if starts:
        return "".join(lines[: starts[0]]) + block + "".join(lines[ends[0] + 1 :])
    return current + ("\n" if current and not current.endswith("\n") else "") + block


def read_alttab_preferences():
    result = subprocess.run(
        ["defaults", "export", ALTTAB_DOMAIN, "-"], capture_output=True
    )
    if result.returncode:
        message = result.stderr.decode(errors='replace')
        if 'does not exist' in message:
            return {}  # Fresh AltTab install: no persistent preferences yet.
        raise RuntimeError('Cannot back up AltTab preferences: ' + message)
    return plistlib.loads(result.stdout)


def write_alttab_preferences(preferences):
    subprocess.run(
        ["defaults", "import", ALTTAB_DOMAIN, "-"],
        input=plistlib.dumps(preferences),
        check=True,
    )


def stop_alttab():
    subprocess.run(
        [
            "osascript",
            "-e",
            'if application "AltTab" is running then tell application "AltTab" to quit',
        ],
        check=True,
    )


def scope_captured_rules(rules, source_device, device):
    rules = copy.deepcopy(rules)
    for rule in rules:
        for manipulator in rule.get("manipulators", []):
            conditions = manipulator.setdefault("conditions", [])
            for condition in conditions:
                if condition.get("type") not in ("device_if", "device_unless"):
                    continue
                for identifier in condition.get("identifiers", []):
                    if (
                        identifier.get("vendor_id"),
                        identifier.get("product_id"),
                    ) == tuple(source_device):
                        if device is None:
                            raise ValueError(
                                "Captured device-specific conditions require a target keyboard"
                            )
                        identifier.update(vendor_id=device[0], product_id=device[1])
            if device is not None:
                conditions.append(
                    {
                        "type": "device_if",
                        "identifiers": [
                            {"vendor_id": device[0], "product_id": device[1]}
                        ],
                    }
                )
    return rules


def load(path, jsonc=False):
    if not path.exists():
        return None
    raw = path.read_text()
    if jsonc:
        # VS Code keybindings uses JSONC: strip comments and trailing commas
        # without changing string literals (including https:// within a keybinding).
        def clean_comments(match):
            return match.group(1) if match.group(1) is not None else ""

        raw = re.sub(
            r"(\"(?:\\.|[^\"\\])*\")|//[^\n]*|/\*[\s\S]*?\*/", clean_comments, raw
        )
        raw = re.sub(r",(?=\s*[}\]])", "", raw)
    return json.loads(raw)


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".winmac.tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")
    tmp.replace(path)


def backup(path, folder):
    if path.exists():
        dest = folder / (path.name + ".backup")
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
        return str(dest)
    return None


def detect_device(profile):
    options = []
    for d in profile.get("devices", []):
        ident = d.get("identifiers", {})
        if (
            ident.get("is_keyboard")
            and not ident.get("is_built_in_keyboard")
            and ident.get("vendor_id") is not None
            and ident.get("product_id") is not None
        ):
            ident_pair = (int(ident["vendor_id"]), int(ident["product_id"]))
            if ident_pair not in options:
                options.append(ident_pair)
    return options


def ensure_brew_install(app, skip=False):
    if skip:
        return
    if not shutil.which("brew"):
        print("Homebrew not found. Install apps manually: https://brew.sh/")
        return
    installed = (
        subprocess.run(["brew", "list", "--cask", app], capture_output=True).returncode
        == 0
    )
    if installed:
        print(f"Already installed: {app}")
    else:
        print(f"Installing {app} with Homebrew...")
        subprocess.run(["brew", "install", "--cask", app], check=True)


def main():
    p = argparse.ArgumentParser(
        description="Install Windows keyboard behavior on macOS"
    )
    p.add_argument(
        "--vendor-id",
        type=int,
        help="External keyboard vendor ID from Karabiner EventViewer",
    )
    p.add_argument(
        "--product-id",
        type=int,
        help="External keyboard product ID from Karabiner EventViewer",
    )
    p.add_argument(
        "--all-keyboards",
        action="store_true",
        help="Explicitly apply remapping to all keyboards",
    )
    p.add_argument(
        "--skip-brew", action="store_true", help="Skip installing Karabiner and AltTab"
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print device and planned changes without writing",
    )
    p.add_argument('--import-snapshot', action='store_true',
                   help='Explicitly restore the captured configuration instead of maintained defaults')
    a = p.parse_args()
    if (STATE / 'deskflow-backup').exists():
        p.error('Remove Deskflow integration with scripts/deskflow.py --uninstall before upgrading; then reinstall it.')
    if platform.system() != "Darwin" and not a.dry_run:
        p.error("Installation requires macOS. Use --dry-run for inspection elsewhere.")
    if (a.vendor_id is None) != (a.product_id is None):
        p.error("Provide both --vendor-id and --product-id")
    if a.all_keyboards and a.vendor_id is not None:
        p.error("Use either explicit device IDs or --all-keyboards")
    cfg = load(KARABINER)
    if cfg is None:
        if a.dry_run:
            print(f"Karabiner configuration not yet found at {KARABINER}")
            return
        ensure_brew_install("karabiner-elements", a.skip_brew)
        ensure_brew_install("alt-tab", a.skip_brew)
        print(
            "Launch Karabiner-Elements once, grant permissions, enable keyboard, then rerun."
        )
        return
    profiles = cfg.get("profiles", [])
    if not profiles:
        p.error("Karabiner config has no profiles")
    profile = next((v for v in profiles if v.get("selected")), profiles[0])
    choices = detect_device(profile)
    if a.all_keyboards:
        device = None
    elif a.vendor_id is not None:
        device = (a.vendor_id, a.product_id)
    elif len(choices) == 1:
        device = choices[0]
    else:
        print(f"Detected external keyboard IDs: {choices}")
        p.error(
            "Cannot safely choose one keyboard. Supply --vendor-id N --product-id N, or --all-keyboards"
        )
    print(
        f'Target: {"all keyboards" if device is None else f"external keyboard vendor={device[0]} product={device[1]}"}'
    )
    snapshot = load(SNAPSHOT) if a.import_snapshot else None
    if a.import_snapshot and snapshot is None:
        p.error("Captured snapshot not found")
    if snapshot:
        simple = copy.deepcopy(snapshot["simple_modifications"])
        rules = scope_captured_rules(
            snapshot["rules"], snapshot["source_device"], device
        )
        ours = snapshot["vscode_keybindings"]
        alttab = snapshot["alttab_preferences"]
    else:
        simple = [
            {"from": {"key_code": src}, "to": [{"key_code": dst}]}
            for src, dst in (
                ("left_control", "left_command"),
                ("right_control", "right_command"),
                ("left_command", "left_control"),
                ("right_command", "right_control"),
            )
        ]
        rules = build_rules(device, STATE / 'finder_actions.js')
        ours = vscode_bindings()
        # AltTab 11.x: hold Option, press Tab; Shift reverses the selection.
        # Remove overrides so AltTab uses its native Option+Tab / Shift defaults.
        # Recent versions archive ShortcutRecorder objects; strings are not valid.
        alttab = {'holdShortcut': None, 'nextWindowShortcut': None,
                  'previousWindowShortcut': None}
    current = load(VSCODE, jsonc=True)
    if current is None:
        current = []
    if not isinstance(current, list):
        p.error("VS Code keybindings.json must be an array")
    zsh_bindings = snapshot.get("zsh_bindings") if snapshot else ZSH_BINDINGS
    updated_zshrc = None
    if zsh_bindings is not None:
        if not isinstance(zsh_bindings, list) or not all(
            isinstance(line, str)
            and re.match(r"^bindkey[ \t]", line)
            and "\n" not in line
            and "\r" not in line
            for line in zsh_bindings
        ):
            p.error("Captured zsh bindings must be a list of bindkey commands")
        try:
            updated_zshrc = merge_zshrc(
                ZSHRC.read_text() if ZSHRC.exists() else "", zsh_bindings
            )
        except ValueError as error:
            p.error(str(error))
    if a.dry_run:
        print(
            "Would back up and update Karabiner and VS Code; install AltTab"
            + (" and configure AltTab preferences." if alttab is not None else ".")
        )
        if updated_zshrc is not None:
            print("Would back up and update .zshrc keyboard bindings.")
        if not a.import_snapshot:
            print("Would install Finder helper and navigation profiles for Terminal, iTerm2 and kitty.")
        return
    ensure_brew_install("karabiner-elements", a.skip_brew)
    ensure_brew_install("alt-tab", a.skip_brew)
    date = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    folder = STATE / "backups" / date
    files = [KARABINER, RULES_FILE, VSCODE]
    if updated_zshrc is not None:
        files.append(ZSHRC)
    helper = STATE / 'finder_actions.js'
    terminal_file = STATE / 'WinMac.terminal'
    kitty_file = STATE / 'kitty.conf'
    iterm_file = HOME / 'Library/Application Support/iTerm2/DynamicProfiles/winmac.json'
    if not a.import_snapshot:
        files.extend([helper, terminal_file, kitty_file, iterm_file])
    backups = {str(f): backup(f, folder) for f in files}
    alt_backup = None
    if alttab is not None:
        stop_alttab()
        existing_alttab = read_alttab_preferences()
        if existing_alttab is not None:
            folder.mkdir(parents=True, exist_ok=True)
            alt_backup = folder / "alttab.plist"
            alt_backup.write_bytes(plistlib.dumps(existing_alttab))
    folder.mkdir(parents=True, exist_ok=True)
    write(
        folder / "manifest.json",
        {
            "device": device,
            "backups": backups,
            "alttab_backup": str(alt_backup) if alt_backup else None,
            "alttab_keys": list(alttab) if alttab is not None else [],
        },
    )
    write(STATE / "latest.json", {"backup_dir": str(folder), "device": device})
    if device is not None:
        target = None
        for d in profile.setdefault("devices", []):
            ids = d.get("identifiers", {})
            if (
                ids.get("vendor_id") == device[0]
                and ids.get("product_id") == device[1]
                and ids.get("is_keyboard")
            ):
                target = d
                break
        if target is None:
            target = {
                "identifiers": {
                    "vendor_id": device[0],
                    "product_id": device[1],
                    "is_keyboard": True,
                    "is_pointing_device": False,
                    "is_game_pad": False,
                }
            }
            profile["devices"].append(target)
        previous = target.setdefault("simple_modifications", [])
    else:
        previous = profile.setdefault("simple_modifications", [])
    managed_from = [i["from"] for i in simple]
    previous[:] = [v for v in previous if v.get("from") not in managed_from] + simple
    # Remove known rules from previous assistant version (but no arbitrary user rules).
    cm = profile.setdefault("complex_modifications", {}).setdefault("rules", [])
    captured_descriptions = {rule.get("description") for rule in rules}
    cm[:] = [
        r
        for r in cm
        if not r.get("description", "").startswith(PREFIX)
        and r.get("description") not in LEGACY_DESCRIPTIONS
        and r.get("description") not in captured_descriptions
    ]
    cm[:0] = rules
    if not a.import_snapshot:
        helper.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(Path(__file__).with_name('finder_actions.js'), helper)
        terminal_file.write_bytes(plistlib.dumps(terminal_profile(), fmt=plistlib.FMT_BINARY))
        kitty_file.write_text(KITTY_CONFIG)
        write(iterm_file, iterm_profile())
    write(KARABINER, cfg)
    write(
        RULES_FILE,
        {"title": "WinMac - backed-up Windows keyboard rules", "rules": rules},
    )
    # Override same key+when; preserve all unrelated user bindings.
    ours_ids = {(r["key"], r.get("when")) for r in ours}
    current = [r for r in current if (r.get("key"), r.get("when")) not in ours_ids]
    if not a.import_snapshot:
        # Remove only exact legacy objects, including entries whose context changed.
        legacy_export = load(Path(__file__).resolve().parents[1] / 'config/vscode-keybindings.legacy.json') or []
        current = [entry for entry in current if entry not in legacy_export]
    current.extend(ours)
    write(VSCODE, current)
    if updated_zshrc is not None:
        ZSHRC.write_text(updated_zshrc)
    if alttab is not None:
        write_alttab_preferences({k: v for k, v in {**(existing_alttab or {}), **alttab}.items() if v is not None})
    subprocess.run(["open", "-a", "AltTab"], check=False)
    print(
        "\nDone. You must grant Karabiner Input Monitoring/Accessibility, AltTab Accessibility/Screen Recording."
    )
    print("Verify AltTab shortcuts and enable Start at login if desired.")
    if not a.import_snapshot:
        print(f"Terminal.app: open {terminal_file} and use its WinMac profile.")
        print("iTerm2: select the WinMac dynamic profile. Existing profiles are unchanged.")
        print(f"kitty: include {kitty_file} from kitty.conf, then restart kitty.")
        print("Finder helper: allow osascript Accessibility/Automation when macOS prompts.")
    print(
        "Karabiner -> Devices: enable your Windows keyboard. Standard F1-F12 should be enabled where applicable."
    )
    print("Backup:", folder)
    print("Run scripts/doctor.py to inspect installation.")


if __name__ == "__main__":
    main()
