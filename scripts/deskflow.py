#!/usr/bin/env python3
"""Optional Deskflow server passthrough using its enter/exit command hooks."""
import argparse
import copy
import configparser
import fcntl
import json
from pathlib import Path
import shlex
import shutil
import sys

RAW = '[WinMac] Deskflow passthrough'
STATE = Path.home() / '.config/winmac-keyboard'
KARABINER = Path.home() / '.config/karabiner/karabiner.json'
DESKFLOW = Path.home() / 'Library/Deskflow/Deskflow.conf'


def configure(config, text, command):
    config = copy.deepcopy(config)
    normal = next(p for p in config['profiles'] if p.get('selected'))
    if normal['name'] == RAW:
        raise ValueError('Return to your normal Karabiner profile before installing')
    if any(p['name'] == RAW for p in config['profiles']):
        raise ValueError('Passthrough profile already exists; uninstall this integration first')
    raw = copy.deepcopy(normal)
    raw.update(name=RAW, selected=False, simple_modifications=[], fn_function_keys=[],
               complex_modifications={'rules': []})
    for device in raw.get('devices', []):
        device['simple_modifications'] = []
        device['fn_function_keys'] = []
        device['disable_built_in_keyboard_if_exists'] = False
        if device.get('identifiers', {}).get('is_keyboard'):
            device['ignore'] = True
    config['profiles'].append(raw)
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    parser.read_string(text)
    if parser.get('core', 'coreMode', fallback='0') != '2':
        raise ValueError('Deskflow must be configured as server')
    for key in ('enterCommand', 'exitCommand'):
        if parser.get('core', key, fallback='').strip():
            raise ValueError('Existing Deskflow commands must be preserved; refusing to overwrite ' + key)
    parser.set('core', 'enableEnterCommand', 'true')
    parser.set('core', 'enableExitCommand', 'true')
    parser.set('core', 'enterCommand', command + ' --enter')
    parser.set('core', 'exitCommand', command + ' --leave')
    import io
    out = io.StringIO()
    parser.write(out, space_around_delimiters=False)
    return config, out.getvalue()


def transition(leaving):
    with (STATE / 'deskflow.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        saved = STATE / 'deskflow-return-profile.json'
        config = json.loads(KARABINER.read_text())
        current = next(p['name'] for p in config['profiles'] if p.get('selected'))
        if leaving:
            if current == RAW:
                return
            saved.write_text(json.dumps(current))
            target = RAW
        elif current == RAW and saved.exists():
            target = json.loads(saved.read_text())
        else:
            return
        if not any(p['name'] == target for p in config['profiles']):
            raise ValueError('Karabiner target profile is missing: ' + target)
        for profile in config['profiles']:
            profile['selected'] = profile['name'] == target
        # Both paths are in ~/.config on the same filesystem; publish a complete JSON file.
        temp = STATE / 'deskflow-profile.tmp'
        temp.write_text(json.dumps(config, indent=2) + '\n')
        temp.chmod(KARABINER.stat().st_mode & 0o777)
        temp.replace(KARABINER)
        with (STATE / 'deskflow-transitions.log').open('a') as log:
            log.write(('leave' if leaving else 'enter') + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    for flag in ('install', 'uninstall', 'leave', 'enter'):
        group.add_argument('--' + flag, action='store_true')
    args = parser.parse_args()
    STATE.mkdir(parents=True, exist_ok=True)
    backup = STATE / 'deskflow-backup'
    if args.leave or args.enter:
        transition(args.leave)
    elif args.install:
        if backup.exists():
            raise SystemExit('Already installed; uninstall this integration before reinstalling')
        installed = STATE / 'deskflow.py'
        command = shlex.join([sys.executable, str(installed)])
        config, text = configure(json.loads(KARABINER.read_text()), DESKFLOW.read_text(), command)
        backup.mkdir()
        shutil.copy2(KARABINER, backup / 'karabiner.json')
        shutil.copy2(DESKFLOW, backup / 'Deskflow.conf')
        shutil.copy2(__file__, installed)
        KARABINER.write_text(json.dumps(config, indent=2) + '\n')
        DESKFLOW.write_text(text)
        print('Installed. Restart Deskflow to load its hooks. Release all keys before crossing screens.')
    else:
        if not backup.exists():
            raise SystemExit('No Deskflow integration backup found')
        transition(False)
        # Like the main uninstaller, restore the pre-install snapshots, including hooks.
        shutil.copy2(backup / 'karabiner.json', KARABINER)
        shutil.copy2(backup / 'Deskflow.conf', DESKFLOW)
        for name in ('deskflow.py', 'deskflow-return-profile.json', 'deskflow.lock', 'deskflow-transitions.log', 'deskflow-profile.tmp'):
            (STATE / name).unlink(missing_ok=True)
        shutil.rmtree(backup)
        print('Restored pre-integration settings. Restart Deskflow.')


if __name__ == '__main__':
    main()
