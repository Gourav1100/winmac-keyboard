# WinMac Keyboard

Windows-style keyboard behavior for macOS, with a physical **Windows keyboard**, VS Code, external terminals, and AltTab.

This checkout includes a snapshot of the current Mac's active Karabiner rules, keyboard modifications, VS Code keybindings, AltTab preferences, and zsh keyboard bindings in `config/system.json`.

> This repository is a local GitHub-ready project. It is not an official Karabiner, AltTab or VS Code project.

## Requirements

- macOS with a Windows-layout keyboard
- Python 3 (e.g. `python3` from Xcode tools or Homebrew)
- [Homebrew](https://brew.sh/) (optional; the installer uses it to install apps)
- [Karabiner-Elements](https://karabiner-elements.pqrs.org/), [AltTab](https://alt-tab.app/), [VS Code](https://code.visualstudio.com/)

## One-command setup

First launch **Karabiner-Elements** once and enable the external keyboard under **Devices**. This creates `~/.config/karabiner/karabiner.json` and enumerates the keyboard. If the apps are not installed yet, run the installer once to install Karabiner-Elements and AltTab using Homebrew, then launch Karabiner and rerun it.

```bash
python3 scripts/install.py
```

The installer auto-detects a keyboard only when exactly **one** external keyboard appears in the selected Karabiner profile. Otherwise find **vendor_id** and **product_id** in Karabiner-EventViewer, and use:

```bash
python3 scripts/install.py --vendor-id 1234 --product-id 5678
```

To intentionally modify **all keyboards** (including built-in):

```bash
python3 scripts/install.py --all-keyboards
```

Options: `--dry-run`, `--skip-brew`. Your original configuration is backed up under `~/.config/winmac-keyboard/backups/`.

**Permissions and final AltTab setup:**

1. **Karabiner-Elements**: allow Input Monitoring, Accessibility and system extension prompts; enable your external keyboard in Devices. Do **not** also swap modifier keys in macOS System Settings.
2. **AltTab**: allow Accessibility and Screen Recording; verify the restored shortcuts in **Settings → Controls**. In General, enable **Start at login** if desired. macOS permissions and login items cannot be transferred by this installer.
3. **VS Code**: restart or reload the window and confirm keybindings. The installer merges shortcut entries into `~/Library/Application Support/Code/User/keybindings.json`.
4. Optional: enable standard F1–F12 in macOS Keyboard settings and/or your keyboard firmware.

### What gets installed

- Captured Karabiner simple modifications and complex rules, scoped to the chosen keyboard and merged into the active profile.
- Captured VS Code keybindings, preserving unrelated bindings.
- Captured zsh `bindkey` commands in a managed block in `~/.zshrc`, preserving other shell settings. Open a new shell to apply them.
- AltTab macOS window switcher, installed and launched, with captured preferences restored (manual first-run permissions required).
- Old rules from the prior experimental Windows configuration removed **only** when their descriptions match known legacy names.

### Shortcuts

The table describes the project's generated fallback configuration. The captured snapshot takes precedence and may differ; inspect `config/system.json` for the actual installed rules and bindings.

| Physical PC key                    | Behavior                                                             |
| ---------------------------------- | -------------------------------------------------------------------- |
| Ctrl+C/V/X/Z                       | Native macOS copy/paste/cut/undo in most apps                        |
| Win (tap)                          | Spotlight launcher                                                   |
| Win+E / Win+R / Win+L              | Finder / Spotlight / lock screen                                     |
| Alt+Tab                            | AltTab's Windows-style window switcher                               |
| Alt+F4                             | Command+Q (quit app, not merely close window)                        |
| Home / End                         | Line start / line end in GUI apps; Ctrl+A/E in Terminal/iTerm2/kitty |
| Ctrl+Home/End                      | Document start / document end in GUI apps and VS Code editor         |
| Shift+Home/End                     | Select to start / end of line                                        |
| Ctrl+Backspace/Delete              | Delete previous/next word in GUI apps (some apps override)           |
| Page Up/Down / Forward Delete      | Original hardware events, not swallowed                              |
| Insert in VS Code                  | Toggle overtype when editor focused                                  |
| Ctrl+` in VS Code                  | Toggle integrated terminal without macOS window cycling              |
| Ctrl+Shift+C/V in VS Code terminal | Copy selected text / paste                                           |
| Ctrl+C in VS Code terminal         | Copy if selected, otherwise send interrupt                           |
| F2 in Finder                       | Rename selection; VS Code keeps rename-symbol F2                     |

### Shell note

The shell sequences Ctrl+A/E, Esc+B/F, Ctrl+W assume an Emacs-style shell keymap. The captured zsh bindings include `bindkey -e`. Full-screen apps such as Vim, tmux and nano may interpret keys differently. An external terminal's app-specific keyboard shortcuts may override these mappings.

### Limitations

Karabiner translates events, not application functionality. A global overtype mode is impossible without app support. Windows Explorer, clipboard history, Start menu and OS-specific terminal actions cannot be emulated exactly. Physical Ctrl+C in external terminal apps sends SIGINT; Ctrl+Shift+C copies. macOS app shortcuts like Ctrl+Shift+C may conflict with an app's existing features; the installer intentionally does **not** globally override this combination.

AltTab preferences are imported through macOS `defaults`; preference formats and shortcuts may change between AltTab versions, so verify them after installation. Machine-specific telemetry, window positions, update state, and onboarding state are excluded.

### Refresh the captured configuration

After changing your settings on the source Mac, run:

```bash
python3 scripts/capture.py
```

If more than one keyboard is present, pass `--vendor-id N --product-id N`. This replaces `config/system.json` with the selected keyboard's simple modifications, the active profile's complex rules, VS Code keybindings, portable AltTab preferences, and standalone `bindkey` lines from `~/.zshrc`. Other shell settings, including paths and credentials, are not copied. Review the snapshot for private paths or commands before publishing it. On the destination, rerun `scripts/install.py`; source keyboard conditions are retargeted to the selected destination keyboard. Existing global rules in the snapshot become keyboard-scoped unless `--all-keyboards` is used. Captured rules containing source-device conditions cannot be installed with `--all-keyboards`.

## Diagnose / restore

```bash
python3 scripts/doctor.py
python3 -m unittest discover -s tests -v
python3 scripts/uninstall.py
```

Uninstall restores **the backed-up original files and AltTab preferences** and can overwrite later edits. AltTab and Karabiner apps remain installed. Each installation creates a new backup; uninstall restores the most recent one.

## Publish to GitHub

```bash
git init
git add .
git commit -m "Initial Windows keyboard setup for macOS"
gh repo create winmac-keyboard --public --source=. --remote=origin --push
```

This last command requires [GitHub CLI](https://cli.github.com/) and authentication (`gh auth login`). Nothing is uploaded automatically by the installer.

## References

- [Karabiner event modification order](https://karabiner-elements.pqrs.org/docs/manual/misc/event-modification-chaining/)
- [Karabiner complex modification manual](https://karabiner-elements.pqrs.org/docs/json/)
- [VS Code integrated terminal shortcuts](https://code.visualstudio.com/docs/terminal/advanced)
- [AltTab](https://alt-tab.app/)

## Developer notes

`config/system.json` is the captured source configuration. If it is absent, `scripts/install.py` falls back to the generated examples. The installer merges rules directly into the selected Karabiner profile. **Do not separately enable the generated asset rule from Complex Modifications after installation**; that would duplicate the installed active rules. The asset is a reviewable export for manual use.

VS Code `keybindings.json` may contain `//` comments and trailing commas; the installer reads both and writes standard JSON while preserving unrelated keybinding objects (formatting and comments are not preserved). Backups keep the original file.
