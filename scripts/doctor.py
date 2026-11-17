#!/usr/bin/env python3
"""Read-only checks; actual key delivery still needs testing on macOS."""
import platform
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
