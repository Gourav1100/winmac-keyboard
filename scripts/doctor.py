#!/usr/bin/env python3
import json,platform,shutil
from pathlib import Path
HOME=Path.home()
print('Platform:',platform.platform())
for app in ('karabiner-elements','alt-tab','visual-studio-code'):
    print('Homebrew cask known:',app,'(brew available)' if shutil.which('brew') else '(brew missing)')
p=HOME/'.config/karabiner/karabiner.json'
if p.exists():
    data=json.loads(p.read_text()); profile=next((x for x in data.get('profiles',[]) if x.get('selected')),None)
    rules=(profile or {}).get('complex_modifications',{}).get('rules',[])
    print('Karabiner config: OK; managed rules:',sum(r.get('description','').startswith('[WinMac]') for r in rules))
else: print('Karabiner config: missing')
v=HOME/'Library/Application Support/Code/User/keybindings.json'
try: print('VS Code keybindings:',len(json.loads(v.read_text())),'entries')
except (OSError,ValueError): print('VS Code keybindings missing or not strict JSON (VS Code also accepts JSONC)')
print('Verify via EventViewer; the keyboard must be enabled in Karabiner Devices.')
