import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from generate import build_rules, vscode_bindings, TERMINALS, VSCODE
from shortcuts import CONTROL_KEYS
from terminal_profiles import iterm_profile, terminal_profile, KITTY_CONFIG


class ShortcutTests(unittest.TestCase):
    def test_control_letters_and_clipboard_priority(self):
        rules = build_rules((12, 34))
        self.assertEqual(rules[0]['manipulators'][0]['from']['modifiers']['mandatory'], ['command', 'shift'])
        controls = rules[1]['manipulators']
        for letter in 'abcdefghijklmnopqrstuvwxyz':
            item = next(m for m in controls if m['from']['key_code'] == letter)
            self.assertEqual(item['to'], [{'key_code': letter, 'modifiers': ['left_control']}])
            self.assertIn({'type': 'frontmost_application_if', 'bundle_identifiers': TERMINALS}, item['conditions'])
            self.assertEqual(item['from']['modifiers']['optional'], ['any'])

    def test_gui_navigation_never_intercepts_terminals(self):
        rules = build_rules()
        for rule in rules:
            if 'Home, End' in rule['description'] or 'word navigation' in rule['description']:
                for item in rule['manipulators']:
                    self.assertIn({'type': 'frontmost_application_unless',
                                   'bundle_identifiers': [VSCODE] + TERMINALS}, item['conditions'])
        # Plain Page keys remain native; terminal profiles decide how to encode them.
        self.assertFalse(any(m['from']['key_code'] in ('page_up', 'page_down')
                             and not m['from'].get('modifiers')
                             for r in rules for m in r['manipulators']))

    def test_vscode_terminal_controls_do_not_depend_on_selection(self):
        bindings = vscode_bindings()
        for chord, sequence in CONTROL_KEYS.items():
            item = next(b for b in bindings if b['key'] == chord and b.get('when') == 'terminalFocus')
            self.assertEqual(item['args']['text'], sequence)
        for key, sequence in [('pageup', '\x1b[5~'), ('pagedown', '\x1b[6~'),
                              ('home', '\x1b[H'), ('end', '\x1b[F')]:
            self.assertTrue(any(b['key'] == key and b.get('when') == 'terminalFocus'
                                and b.get('args', {}).get('text') == sequence for b in bindings))
        self.assertTrue(any(b['key'] == 'cmd+shift+c' and b['command'].endswith('copySelection') for b in bindings))
        self.assertTrue(all(b.get('when') == '!terminalFocus' for b in bindings
                            if b['command'] in ('workbench.action.navigateBack', 'workbench.action.previousEditor')))

    def test_finder_scoping_and_portable_helper(self):
        rules = build_rules(helper_path='/tmp/user name/finder.js')
        finder = next(r for r in rules if r['description'].endswith('Finder file operations'))
        for item in finder['manipulators']:
            self.assertIn({'type': 'frontmost_application_if', 'bundle_identifiers': [r'^com\.apple\.finder$']}, item['conditions'])
            self.assertIn("'/tmp/user name/finder.js'", item['to'][0]['shell_command'])
        self.assertIn('$HOME', json.dumps(build_rules()))

    def test_screenshot_and_close_mappings(self):
        items = [m for r in build_rules() for m in r['manipulators']]
        alt_f4 = next(m for m in items if m['from']['key_code'] == 'f4')
        self.assertEqual(alt_f4['to'][0], {'key_code': 'w', 'modifiers': ['left_command']})
        shots = [m for m in items if m['from']['key_code'] == 'print_screen']
        self.assertEqual(len(shots), 3)
        self.assertTrue(any(m['to'][0].get('shell_command') == '/usr/sbin/screencapture -i -w -c' for m in shots))

    def test_terminal_profile_sequences(self):
        terminal = terminal_profile()['keyMapBoundKeys']
        iterm = iterm_profile()['Profiles'][0]['Keyboard Map']
        for code, seq in [('f72c', '[5~'), ('f72d', '[6~')]:
            self.assertEqual(terminal[chr(int(code, 16))], '\x1b' + seq)
            self.assertEqual(iterm[f'0x{code}-0x0'], {'Action': 10, 'Text': seq})
        self.assertIn('map page_up send_key page_up', KITTY_CONFIG)
        self.assertNotIn('\x1b', KITTY_CONFIG)  # kitty reads literal escape notation

    def test_exports_match_generator(self):
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(json.loads((root / 'config/vscode-keybindings.json').read_text()), vscode_bindings())
        self.assertEqual(json.loads((root / 'config/karabiner.example.json').read_text())['rules'], build_rules())
