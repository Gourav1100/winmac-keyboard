#!/usr/bin/env python3
"""Read-only checks; actual key delivery still needs testing on macOS."""
import platform
import plistlib
import subprocess
from pathlib import Path
from install import load, STATE

print('Platform:', platform.platform())
karabiner = Path.home() / '.config/karabiner/karabiner.json'
if karabiner.exists():
    data = load(karabiner)
    profiles = data.get('profiles', [])
    profile = next((p for p in profiles if p.get('selected')), profiles[0] if profiles else {})
    rules = profile.get('complex_modifications', {}).get('rules', [])
    managed = [r for r in rules if r.get('description', '').startswith('[WinMac]')]
    print('Selected Karabiner profile:', profile.get('name', '<unnamed>'))
    for device in profile.get('devices', []):
        print('Configured device:', device.get('identifiers', {}), 'ignore:', device.get('ignore', False))
        print('  Simple modifications:', device.get('simple_modifications', []))
    print('Rule order:', [r.get('description', '') for r in rules])
    print('Managed Karabiner rules:', len(managed))
    descriptions = [r.get('description', '') for r in rules]
    print('Duplicate rule descriptions:', sorted({d for d in descriptions if descriptions.count(d) > 1}))
else:
    print('Karabiner configuration: missing')
try:
    vscode = load(Path.home() / 'Library/Application Support/Code/User/keybindings.json', jsonc=True)
    print('VS Code terminal bindings:', sum(b.get('when') == 'terminalFocus' for b in (vscode or [])))
except (ValueError, OSError) as error:
    print('VS Code configuration unreadable:', error)
for path in [STATE / 'finder_actions.js', STATE / 'WinMac.terminal', STATE / 'kitty.conf',
             Path.home() / 'Library/Application Support/iTerm2/DynamicProfiles/winmac.json']:
    print(path, 'present' if path.exists() else 'missing')
print('Select the WinMac terminal profile/include; existing sessions are unchanged.')
print('Use Karabiner EventViewer to verify Page Up/Down and Print Screen key codes.')
print('Test nano paging and Ctrl+X/O/W; zsh bindkey settings do not configure nano.')
print('Verify Finder helper Accessibility/Automation and AltTab Controls permissions on macOS.')

# App Shortcuts act after Karabiner and can undo the intended Control->Command mapping.
if platform.system() == 'Darwin':
    try:
        result = subprocess.run(['defaults', 'export', 'com.apple.finder', '-'],
                                capture_output=True, check=True)
        shortcuts = plistlib.loads(result.stdout).get('NSUserKeyEquivalents', {})
        conflicts = {name: value for name, value in shortcuts.items()
                     if name in ('Copy', 'Paste', 'Select All', 'Move to Bin', 'Move to Trash')
                     and '^' in value}
        print('Finder Control-based App Shortcut conflicts:', conflicts or 'none')
        if conflicts:
            print('Remove these in System Settings > Keyboard > Keyboard Shortcuts > App Shortcuts.')
            print('Physical Ctrl already becomes Command; Finder should retain native Command shortcuts.')
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print('Finder App Shortcuts could not be inspected:', type(error).__name__)
    log = Path.home() / '.local/share/karabiner/log/console_user_server.log'
    try:
        errors = [line for line in log.read_text().splitlines() if '(-1743)' in line]
        if errors:
            print('Historical Automation denial (-1743) recorded:', errors[-1].split(']')[0] + ']')
            print('Check Privacy & Security > Automation > Karabiner-Console-User-Server > System Events.')
            print('Historical log entries do not establish the current permission state.')
    except OSError:
        pass
