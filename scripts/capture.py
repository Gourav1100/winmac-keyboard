#!/usr/bin/env python3
"""Capture the current keyboard configuration for installation on another Mac."""

import argparse
import platform

from install import (
    KARABINER,
    SNAPSHOT,
    VSCODE,
    ZSHRC,
    detect_device,
    load,
    portable_alttab_preferences,
    read_alttab_preferences,
    write,
)


def zsh_keyboard_bindings(contents):
    return [
        line.strip()
        for line in contents.splitlines()
        if line.lstrip().startswith(("bindkey ", "bindkey\t"))
    ]


def main():
    parser = argparse.ArgumentParser(
        description="Capture the current keyboard and AltTab configuration"
    )
    parser.add_argument("--vendor-id", type=int)
    parser.add_argument("--product-id", type=int)
    args = parser.parse_args()
    if platform.system() != "Darwin":
        parser.error("Capturing AltTab preferences requires macOS")
    if (args.vendor_id is None) != (args.product_id is None):
        parser.error("Provide both --vendor-id and --product-id")
    config = load(KARABINER)
    if not config or not config.get("profiles"):
        parser.error("Karabiner configuration or profiles not found")
    profile = next(
        (item for item in config["profiles"] if item.get("selected")),
        config["profiles"][0],
    )
    choices = detect_device(profile)
    if args.vendor_id is not None:
        device = (args.vendor_id, args.product_id)
    elif len(choices) == 1:
        device = choices[0]
    else:
        parser.error(
            f"Cannot safely choose a keyboard from {choices}; provide --vendor-id and --product-id"
        )
    source = next(
        (
            item
            for item in profile.get("devices", [])
            if item.get("identifiers", {}).get("is_keyboard")
            and (
                item["identifiers"].get("vendor_id"),
                item["identifiers"].get("product_id"),
            )
            == device
        ),
        None,
    )
    if source is None:
        parser.error("Selected keyboard is not in the active Karabiner profile")
    bindings = load(VSCODE, jsonc=True)
    if not isinstance(bindings, list):
        parser.error("VS Code keybindings.json must exist and contain an array")
    alttab = read_alttab_preferences()
    if not alttab:
        parser.error(
            "AltTab preferences not found; launch AltTab and configure it first"
        )
    snapshot = {
        "source_device": device,
        "simple_modifications": source.get("simple_modifications", []),
        "rules": profile.get("complex_modifications", {}).get("rules", []),
        "vscode_keybindings": bindings,
        "alttab_preferences": portable_alttab_preferences(alttab),
    }
    if ZSHRC.exists():
        snapshot["zsh_bindings"] = zsh_keyboard_bindings(ZSHRC.read_text())
    write(SNAPSHOT, snapshot)
    print(f"Captured keyboard {device} and AltTab preferences in {SNAPSHOT}")
    print("Review the snapshot for private paths or commands before publishing it.")


if __name__ == "__main__":
    main()
