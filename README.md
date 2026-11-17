# WinMac Keyboard

Windows keyboard shortcuts on macOS using Karabiner-Elements, VS Code, zsh,
Terminal/iTerm2/kitty, and AltTab. Physical Ctrl becomes Command in GUI apps;
terminal Control shortcuts are restored before GUI translations run.

## Install or upgrade

Requires macOS, Python 3, Karabiner-Elements and AltTab. The installer can install
the latter two through Homebrew. Launch Karabiner once, grant its permissions,
and enable your external keyboard under Devices. Do not also swap modifiers in
macOS System Settings.

```sh
python3 scripts/install.py --dry-run
python3 scripts/install.py
```

If exactly one external keyboard is not detected, specify its EventViewer IDs:

```sh
python3 scripts/install.py --vendor-id 1234 --product-id 5678
```

Use `--all-keyboards` to explicitly include built-in keyboards, or `--skip-brew`
to manage applications yourself. VS Code must already be installed. Its regular
macOS user settings path is managed; Insiders rules are supported by Karabiner,
but its separate keybindings file must be populated from the generated export.

The maintained defaults come from `scripts/generate.py` and `scripts/shortcuts.py`.
`config/system.json` is a historical snapshot and does **not** override defaults.
`--import-snapshot` explicitly restores that older behavior, including its known
terminal limitations. Upgrades remove known legacy rules and exact old VS Code
bindings while preserving unrelated configuration.

### Finish setup on the Mac

1. Grant Karabiner Input Monitoring/Accessibility and system extension permissions.
2. Grant AltTab Accessibility/Screen Recording. The installer resets its primary
   hold/next/previous shortcut overrides to the app's Option+Tab and Shift defaults;
   verify Controls and enable Start at login if desired. Other preferences remain.
3. Reload VS Code. Its integrated-terminal bindings are installed automatically.
4. Activate navigation settings for your external terminal:
   - **Terminal.app:** open `~/.config/winmac-keyboard/WinMac.terminal` and use the
     imported WinMac profile. Set it as Default if desired. Existing profiles remain.
   - **iTerm2:** choose the **WinMac** dynamic profile for new sessions.
   - **kitty:** add `include ~/.config/winmac-keyboard/kitty.conf` to `kitty.conf`
     and restart kitty. Remove conflicting later key mappings if applicable.
5. Open a new zsh session for the managed shell bindings to take effect.
6. Finder operations use a JXA helper installed at
   `~/.config/winmac-keyboard/finder_actions.js`. Allow its macOS Automation and
   Accessibility requests for System Events/Finder. When invoked by Karabiner,
   the responsible launcher is **Karabiner-Console-User-Server**, not your
   terminal or a standalone osascript process. In System Settings → Privacy &
   Security → Automation, expand that launcher and enable System Events
   (and Finder if requested). Unknown focus or denied access stops file actions.

External terminal profiles are necessary: Karabiner leaves Page Up/Down as real
keyboard events, while a terminal can consume those events for scrollback instead
of forwarding them to nano. The profiles send Page Up/Down to the running program.
They also configure Home/End, Delete, and Control word movement/deletion. Home/End
are no longer forcibly replaced with Ctrl+A/E, which could break full-screen apps.

## Shortcuts

All keys below are **physical Windows keyboard keys**. Left/right Ctrl and
Windows are swapped; Alt stays Option and Shift stays Shift. Launcher combinations
use **left Windows**. App-native shortcuts remain subject to application support.

| Keys | Behavior |
| --- | --- |
| Ctrl+C/V/X/Z/A/S/F in GUI apps | Native copy/paste/cut/undo/select all/save/find |
| Ctrl+Left/Right; Ctrl+Shift+Left/Right | Word movement/selection in GUI editors |
| Ctrl+Backspace/Delete | Delete previous/next word in GUI editors |
| Home/End; Shift+Home/End | Line start/end; select to line boundary |
| Ctrl+Home/End; Ctrl+Shift+Home/End | Document start/end; select to document boundary |
| Left Win tap | Spotlight |
| Win+E; Win+R or Win+S; Win+L | Finder; Spotlight; lock screen |
| Win+D; Win+Tab; Win+I | Show desktop; Mission Control; System Settings |
| Alt+Tab / Alt+Shift+Tab | AltTab next/previous window |
| Alt+F4 | Cmd+W: close current window/tab; does not force quit |
| Ctrl+Shift+Esc | Activity Monitor outside terminals/VS Code; VS Code Process Explorer when its terminal is unfocused |
| Print Screen | Entire screen to clipboard |
| Win+Print Screen | Save entire-screen screenshot using macOS's configured location |
| Win+Shift+S | macOS screenshot controls (Cmd+Shift+5) |
| Alt+Print Screen | Interactive window screenshot to clipboard; click a window, Escape cancels |

Screenshot shortcuts rely on macOS screenshot permissions/settings. Print Screen
must report `print_screen` in Karabiner EventViewer; firmware Fn layers may differ.
GUI applications receive ordinary Page Up/Down events; apps decide their scrolling
behavior. This project does not emulate Windows-only features such as clipboard history.

### Terminal shortcuts, including nano

| Keys | Behavior |
| --- | --- |
| Ctrl+A through Ctrl+Z | Actual Control input, including Ctrl+X/O/W/K/U in nano |
| Ctrl+C | Interrupt/cancel, even with selected terminal text |
| Ctrl+V | Control+V to the program (next page in nano), not clipboard paste |
| Ctrl+Shift+C / Ctrl+Shift+V | Terminal clipboard copy/paste |
| Page Up/Down | Application paging with the WinMac terminal profile |
| Home/End, Insert, Delete | Terminal navigation/editing events |
| Ctrl+Left/Right | Word navigation; application support required |
| Ctrl+Backspace/Delete | Word deletion sequences; application support required |

Ctrl+Shift+C/V are reserved for clipboard operations, so they do not send shifted
Control input. Native Shift+Page Up/Down scrollback behavior varies by terminal.
The shell uses Emacs bindings; full-screen programs and tmux interpret input
independently. Terminal Home/End sequences and modified keys must be verified with
your installed terminal/application versions. No nano-specific Ctrl+Y/V mapping is
applied globally, since that would break other programs.

### VS Code

Ctrl+backtick toggles the terminal. Insert toggles editor overtype. Alt+Left/Right
navigate history, Ctrl+Page Up/Down switch tabs, and Ctrl+Alt+Up/Down add cursors
when editing. Terminal focus overrides editor navigation and Control shortcuts;
Ctrl+C always sends an interrupt, and Ctrl+Shift+C copies. Home/End and Page keys
send terminal sequences. The global Karabiner word rules exclude VS Code so these
bindings can match the original Command events produced by physical Ctrl.

### Finder

| Keys | Behavior |
| --- | --- |
| Delete | Move selected files to Trash |
| Shift+Delete | Native Delete Immediately, retaining Finder's confirmation |
| F2 | Rename selected item |
| Alt+Enter | Get Info |
| Alt+Up; Alt+Left/Right | Parent folder; back/forward |
| Ctrl+C / Ctrl+V | Copy/paste files |
| Ctrl+X then Ctrl+V | Copy a pending move, then native Move Item Here |
| Escape | Cancel pending move |

Delete stays forward deletion in Finder rename/search text fields. Cut/paste also
retain native text editing there. File actions require a recognized file-view
focus and selection. Pending move state records the clipboard change counter in
`~/.config/winmac-keyboard/pending-move`; it contains no file paths. The helper
waits for Copy to settle and leaves Finder’s clipboard representations intact.
Copying something else invalidates the counter, and pasting or Escape clears it. Changing
folder/selection does not cancel the pending move, so navigating to a destination
works. Finder handles file conflicts and permissions; the helper never runs `rm`.

## Diagnose, test, restore

```sh
python3 scripts/doctor.py
python3 -m unittest discover -s tests -v
node tests/test_finder.js  # optional developer-only Node control-flow tests
python3 scripts/uninstall.py
```

Backups are under `~/.config/winmac-keyboard/backups/`. Uninstall restores the most
recent installation's original files and AltTab preferences, including generated
terminal profile files and Finder helper. It can overwrite edits made afterward.
Applications remain installed. Remove any manually imported Terminal.app WinMac
profile and kitty include line yourself; existing terminal sessions must be restarted.
A second installation creates another backup; its uninstall restores the state
immediately before that installation, not the first-ever state.

### Finder troubleshooting

Inspect the selected Karabiner profile, the connected keyboard in Devices, and
that keyboard’s Simple Modifications. The generated Finder rules expect Command
**after** physical Control is swapped; A/C remain native and X/V invoke the helper.
Also inspect System Settings → Keyboard → Keyboard Shortcuts → App Shortcuts.
Finder overrides such as Copy=`^c`, Paste=`^v`, Select All=`^a`, and Move to Bin=`^⌫`
conflict with Karabiner: remove those overrides to restore native Command menu
shortcuts. The doctor reports these conflicts but does not delete preferences.
Do not add a second Control/Command swap in macOS. Confirm the K8 firmware mode
and actual HID events instead of inferring them from keycap labels.

Check `~/.local/share/karabiner/log/console_user_server.log` for helper errors.
Error `-1743` indicates denied Automation; Karabiner Input Monitoring and
Accessibility being enabled does not grant System Events Automation. Test from
the actual Karabiner launcher, because running the helper in a terminal uses a
different permission context. Grant permissions in System Settings, never by
editing the TCC database.

Use disposable files for copy, pending move, Trash and rename/search checks.
Record physical keyboard presses separately from synthesized input: UI automation
can exercise native Finder commands without traversing the device-scoped rules,
and is not proof that physical Ctrl or Delete works.

### macOS acceptance checks

Automated tests validate mappings, migration, rollback, and helper decision logic.
Actual macOS Accessibility, profile imports and UI behavior require these checks:

- In nano: Ctrl+X/O/W/K/U, Ctrl+C/V, Page Up/Down, Home/End and Delete.
- In zsh, Vim and tmux: navigation, Control input and clipboard operations.
- In VS Code: repeat terminal checks, then verify editor shortcuts separately.
- In Finder: test disposable files, rename/search fields, cut/paste, cancellation,
  Trash and the Delete Immediately confirmation.
- Test each screenshot target, clipboard versus saved file, cancel, desktop,
  Mission Control, lock screen and both AltTab directions.

## Capture and generated assets

`python3 scripts/capture.py` captures a source Mac into `config/system.json`.
Specify device IDs if necessary. Review captures for private paths before sharing.
Importing a capture is an explicit `--import-snapshot` operation; it does not include
new default terminal profiles or the Finder helper.

`config/karabiner.example.json` and `config/vscode-keybindings.json` are reviewable
exports. Do not enable the Karabiner asset again after installation: active rules
are already merged into the selected profile. `config/vscode-keybindings.legacy.json`
contains immutable migration fingerprints, not the active configuration.

## References

- [Karabiner event modification order](https://karabiner-elements.pqrs.org/docs/manual/misc/event-modification-chaining/)
- [Karabiner complex rules](https://karabiner-elements.pqrs.org/docs/json/)
- [VS Code terminal shortcuts](https://code.visualstudio.com/docs/terminal/advanced)
- [AltTab](https://alt-tab.app/)
