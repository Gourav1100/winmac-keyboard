#!/usr/bin/env python3
"""Generate device-scoped Karabiner rules and Windows VS Code keybindings."""
import json

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


def build_rules(device=None):
    """Input keys are AFTER simple modifications: physical Ctrl => Command; Win => Control."""
    rules = []
    def add(label, items):
        rules.append({'description': PREFIX + label, 'manipulators': items})
    # Terminal overrides must precede general mappings.
    add('Terminal shell shortcuts (Terminal, iTerm2, kitty)', [
        manip('c', key('c',['left_control']), mandatory=['command'], app=TERMINALS, device=device),
        manip('c', key('c',['left_command']), mandatory=['command','shift'], app=TERMINALS, device=device),
        manip('v', key('v',['left_command']), mandatory=['command','shift'], app=TERMINALS, device=device),
        manip('home', key('a',['left_control']), app=TERMINALS, device=device),
        manip('end', key('e',['left_control']), app=TERMINALS, device=device),
        manip('left_arrow', key('b',['left_option']), mandatory=['command'], app=TERMINALS, device=device),
        manip('right_arrow', key('f',['left_option']), mandatory=['command'], app=TERMINALS, device=device),
        manip('delete_or_backspace', key('w',['left_control']), mandatory=['command'], app=TERMINALS, device=device),
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
        entries.append(manip(frm, key(to, outmods), mandatory=mandatory, not_app=[VSCODE], device=device))
    for shift in (False, True):
        sm=['shift'] if shift else None
        tail=['left_shift'] if shift else []
        nav('home','left_arrow',sm,['left_command']+tail)
        nav('end','right_arrow',sm,['left_command']+tail)
        nav('home','up_arrow',['command'] + (['shift'] if shift else []), ['left_command']+tail)
        nav('end','down_arrow',['command'] + (['shift'] if shift else []), ['left_command']+tail)
    add('Windows Home, End and selections (VS Code handles its own)', entries)
    add('Windows Ctrl word navigation and deletion', [
        *[manip(src,key(src,['left_option']+(['left_shift'] if shift else [])),mandatory=['command']+(['shift'] if shift else []),not_app=[VSCODE],device=device)
          for src in ('left_arrow','right_arrow') for shift in (False,True)],
        manip('delete_or_backspace',key('delete_or_backspace',['left_option']),mandatory=['command'],not_app=[VSCODE],device=device),
        manip('delete_forward',key('delete_forward',['left_option']),mandatory=['command'],not_app=[VSCODE],device=device),
    ])
    add('Ctrl+grave avoids macOS next-window shortcut', [
        manip('grave_accent_and_tilde',key('f12',['left_control','left_option','left_shift']),mandatory=['command'],app=[VSCODE],device=device)
    ])
    add('Windows task manager and Alt+F4', [
        manip('escape',shell='open -a "Activity Monitor"',mandatory=['command','shift'],device=device),
        manip('f4',key('q',['left_command']),mandatory=['option'],device=device)
    ])
    add('F2 rename selected Finder item', [
        manip('f2',key('return_or_enter'),app=[r'^com\.apple\.finder$'],device=device)
    ])
    return rules


def vscode_bindings():
    def kb(key_, command, when=None, text=None):
        out={'key':key_, 'command':command}
        if text is not None: out['args']={'text':text}
        if when: out['when']=when
        return out
    return [
        kb('ctrl+alt+shift+f12','workbench.action.terminal.toggleTerminal'),
        kb('insert','editor.action.toggleOvertypeInsertMode','editorTextFocus'),
        kb('alt+left','workbench.action.navigateBack'), kb('alt+right','workbench.action.navigateForward'),
        kb('cmd+pageup','workbench.action.previousEditor'), kb('cmd+pagedown','workbench.action.nextEditor'),
        kb('cmd+alt+up','editor.action.insertCursorAbove','editorTextFocus'),
        kb('cmd+alt+down','editor.action.insertCursorBelow','editorTextFocus'),
        kb('cmd+c','workbench.action.terminal.copySelection','terminalFocus && terminalTextSelected'),
        kb('cmd+c','workbench.action.terminal.sendSequence','terminalFocus && !terminalTextSelected','\u0003'),
        kb('cmd+shift+c','workbench.action.terminal.copySelection','terminalFocus && terminalTextSelected'),
        kb('cmd+shift+v','workbench.action.terminal.paste','terminalFocus'),
        kb('home','cursorHome','editorTextFocus'), kb('end','cursorEnd','editorTextFocus'),
        kb('shift+home','cursorHomeSelect','editorTextFocus'),kb('shift+end','cursorEndSelect','editorTextFocus'),
        kb('cmd+home','cursorTop','editorTextFocus'),kb('cmd+end','cursorBottom','editorTextFocus'),
        kb('cmd+shift+home','cursorTopSelect','editorTextFocus'),kb('cmd+shift+end','cursorBottomSelect','editorTextFocus'),
        kb('home','workbench.action.terminal.sendSequence','terminalFocus','\u0001'),
        kb('end','workbench.action.terminal.sendSequence','terminalFocus','\u0005'),
        kb('cmd+left','workbench.action.terminal.sendSequence','terminalFocus','\u001bb'),
        kb('cmd+right','workbench.action.terminal.sendSequence','terminalFocus','\u001bf'),
        kb('cmd+backspace','workbench.action.terminal.sendSequence','terminalFocus','\u0017'),
    ]

if __name__ == '__main__':
    print(json.dumps({'title':'WinMac Windows keyboard','rules':build_rules()},indent=2))
