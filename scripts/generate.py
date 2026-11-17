#!/usr/bin/env python3
"""Generate device-scoped Karabiner rules and Windows VS Code keybindings."""
import json
from shortcuts import CONTROL_KEYS, TERMINAL_KEYS

FINDER = [r"^com\.apple\.finder$"]

PREFIX = '[WinMac] '
VSCODE = r'^com\.microsoft\.VSCode(?:Insiders)?$'
TERMINALS = [r'^com\.apple\.Terminal$', r'^com\.googlecode\.iterm2$', r'^net\.kovidgoyal\.kitty$']


def key(code, mods=None):
    return {'key_code': code, **({'modifiers': mods} if mods else {})}


def manip(code, dest=None, *, mandatory=None, optional=None, app=None, not_app=None, device=None, shell=None, alone=None):
    source = {'key_code': code}
    if mandatory or optional:
        source['modifiers'] = {'mandatory': mandatory or [], 'optional': optional or ['caps_lock']}
    out = {'type': 'basic', 'from': source, 'to': [{'shell_command': shell}] if shell else [dest]}
    cond = []
    if app:
        cond.append({'type': 'frontmost_application_if', 'bundle_identifiers': app})
    if not_app:
        cond.append({'type': 'frontmost_application_unless', 'bundle_identifiers': not_app})
    if device:
        cond.append({'type': 'device_if', 'identifiers': [{'vendor_id': device[0], 'product_id': device[1], 'is_keyboard': True}]})
    if cond:
        out['conditions'] = cond
    if alone:
        out['to'] = [dict(dest, lazy=True)]
        out['to_if_alone'] = [alone]
        out['parameters'] = {'basic.to_if_alone_timeout_milliseconds': 400}
    return out


def build_rules(device=None, helper_path=None):
    """Input keys are AFTER simple modifications: physical Ctrl => Command; Win => Control."""
    rules = []
    def add(label, items):
        rules.append({'description': PREFIX + label, 'manipulators': items})
    # Clipboard exceptions first; all remaining physical Control chords stay Control.
    add('Terminal clipboard', [
        manip(code, key(code, ['left_command']), mandatory=['command', 'shift'],
              app=TERMINALS, device=device) for code in ('c', 'v')
    ])
    add('Terminal Control keys', [
        manip(code, key(code, ['left_control']), mandatory=['command'], optional=['any'],
              app=TERMINALS, device=device)
        for code in list('abcdefghijklmnopqrstuvwxyz') + [
            'open_bracket', 'close_bracket', 'backslash', 'spacebar',
            '6', 'hyphen', 'left_arrow', 'right_arrow', 'delete_or_backspace',
            'delete_forward', 'home', 'end', 'page_up', 'page_down', 'tab', 'return_or_enter',
        ]
    ])
    add('Physical Win key opens Spotlight when tapped', [
        manip('left_control', key('left_control'), alone=key('spacebar',['left_command']), device=device)
    ])
    add('Win+E Finder, Win+R Spotlight, Win+L lock', [
        manip('e', shell='open -a Finder', mandatory=['left_control'], device=device),
        manip('r', key('spacebar',['left_command']), mandatory=['left_control'], device=device),
        manip('l', key('q',['left_control','left_command']), mandatory=['left_control'], device=device)
    ])
    # Global remapping; bypass VS Code for its editor vs integrated-terminal focus contexts.
    entries = []
    def nav(frm,to,mandatory=None,outmods=None):
        entries.append(manip(frm, key(to, outmods), mandatory=mandatory, not_app=[VSCODE] + TERMINALS, device=device))
    for shift in (False, True):
        sm=['shift'] if shift else None
        tail=['left_shift'] if shift else []
        nav('home','left_arrow',sm,['left_command']+tail)
        nav('end','right_arrow',sm,['left_command']+tail)
        nav('home','up_arrow',['command'] + (['shift'] if shift else []), ['left_command']+tail)
        nav('end','down_arrow',['command'] + (['shift'] if shift else []), ['left_command']+tail)
    add('Windows Home, End and selections (VS Code handles its own)', entries)
    add('Windows Ctrl word navigation and deletion', [
        *[manip(src,key(src,['left_option']+(['left_shift'] if shift else [])),mandatory=['command']+(['shift'] if shift else []),not_app=[VSCODE] + TERMINALS,device=device)
          for src in ('left_arrow','right_arrow') for shift in (False,True)],
        manip('delete_or_backspace',key('delete_or_backspace',['left_option']),mandatory=['command'],not_app=[VSCODE] + TERMINALS,device=device),
        manip('delete_forward',key('delete_forward',['left_option']),mandatory=['command'],not_app=[VSCODE] + TERMINALS,device=device),
    ])
    add('Ctrl+grave avoids macOS next-window shortcut', [
        manip('grave_accent_and_tilde',key('f12',['left_control','left_option','left_shift']),mandatory=['command'],app=[VSCODE],device=device)
    ])
    add('Windows task manager and Alt+F4', [
        manip('escape',shell='open -a "Activity Monitor"',mandatory=['command','shift'],not_app=TERMINALS + [VSCODE],device=device),
        manip('f4',key('w',['left_command']),mandatory=['option'],device=device)
    ])
    # The helper guards Finder text fields and delegates to native Finder commands.
    import shlex
    helper = shlex.quote(str(helper_path)) if helper_path else '"$HOME/.config/winmac-keyboard/finder_actions.js"'
    def finder(action):
        return '/usr/bin/osascript -l JavaScript ' + helper + ' ' + action
    add('Finder file operations', [
        manip(code, mandatory=mods, app=FINDER, device=device, shell=finder(action))
        for code, mods, action in [
            ('delete_forward', None, 'trash'), ('delete_forward', ['shift'], 'delete'),
            ('f2', None, 'rename'), ('x', ['command'], 'cut'),
            ('v', ['command'], 'paste'), ('escape', None, 'cancel'),
        ]
    ])
    add('Finder navigation and info', [
        manip('return_or_enter', key('i', ['left_command']), mandatory=['option'], app=FINDER, device=device),
        manip('up_arrow', key('up_arrow', ['left_command']), mandatory=['option'], app=FINDER, device=device),
        *[manip(code, key(dest, ['left_command']), mandatory=['option'], app=FINDER, device=device)
          for code, dest in (('left_arrow', 'open_bracket'), ('right_arrow', 'close_bracket'))],
    ])
    add('Windows system shortcuts', [
        manip('s', key('spacebar', ['left_command']), mandatory=['left_control'], device=device),
        manip('d', {'apple_vendor_keyboard_key_code': 'expose_desktop'}, mandatory=['left_control'], device=device),
        manip('tab', key('mission_control'), mandatory=['left_control'], device=device),
        manip('i', shell='open -b com.apple.systempreferences', mandatory=['left_control'], device=device),
    ])
    add('Windows screenshots', [
        manip('s', key('5', ['left_command', 'left_shift']), mandatory=['left_control', 'shift'], device=device),
        manip('print_screen', key('3', ['left_control', 'left_command', 'left_shift']), device=device),
        manip('print_screen', key('3', ['left_command', 'left_shift']), mandatory=['left_control'], device=device),
        manip('print_screen', shell='/usr/sbin/screencapture -i -w -c', mandatory=['option'], device=device),
    ])
    return rules


def vscode_bindings():
    def kb(key_, command, when=None, text=None):
        out={'key':key_, 'command':command}
        if text is not None: out['args']={'text':text}
        if when: out['when']=when
        return out
    editor = 'editorTextFocus'
    terminal = 'terminalFocus'
    entries = [
        kb('ctrl+alt+shift+f12', 'workbench.action.terminal.toggleTerminal'),
        kb('insert', 'editor.action.toggleOvertypeInsertMode', editor),
        kb('alt+left', 'workbench.action.navigateBack', '!terminalFocus'),
        kb('alt+right', 'workbench.action.navigateForward', '!terminalFocus'),
        kb('cmd+pageup', 'workbench.action.previousEditor', '!terminalFocus'),
        kb('cmd+pagedown', 'workbench.action.nextEditor', '!terminalFocus'),
        kb('cmd+alt+up', 'editor.action.insertCursorAbove', editor),
        kb('cmd+alt+down', 'editor.action.insertCursorBelow', editor),
        kb('cmd+shift+c', 'workbench.action.terminal.copySelection', terminal),
        kb('cmd+shift+v', 'workbench.action.terminal.paste', terminal),
    ]
    for letter in 'abdefghijklmnopqrstuwxyz':
        entries.append(kb('cmd+shift+' + letter, 'workbench.action.terminal.sendSequence', terminal, chr(ord(letter) - 96)))
    entries.append(kb('cmd+shift+escape', 'workbench.action.openProcessExplorer', '!terminalFocus'))
    for chord, sequence in {**CONTROL_KEYS, **TERMINAL_KEYS}.items():
        entries.append(kb(chord, 'workbench.action.terminal.sendSequence', terminal, sequence))
    for chord, command in {
        'home': 'cursorHome', 'end': 'cursorEnd',
        'shift+home': 'cursorHomeSelect', 'shift+end': 'cursorEndSelect',
        'cmd+home': 'cursorTop', 'cmd+end': 'cursorBottom',
        'cmd+shift+home': 'cursorTopSelect', 'cmd+shift+end': 'cursorBottomSelect',
        'cmd+left': 'cursorWordLeft', 'cmd+right': 'cursorWordRight',
        'cmd+shift+left': 'cursorWordLeftSelect', 'cmd+shift+right': 'cursorWordRightSelect',
        'cmd+backspace': 'deleteWordLeft', 'cmd+delete': 'deleteWordRight',
    }.items():
        entries.append(kb(chord, command, editor))
    return entries


if __name__ == '__main__':
    print(json.dumps({'title': 'WinMac Windows keyboard', 'rules': build_rules()}, indent=2))
