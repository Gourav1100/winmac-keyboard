import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import install
import capture
import uninstall


class TestInstall(unittest.TestCase):
    def test_zsh_keyboard_bindings_are_portable_and_idempotent(self):
        source = 'export PATH="$PATH:/Users/example/bin"\nbindkey -e\nbindkey "^A" beginning-of-line\n'
        bindings = capture.zsh_keyboard_bindings(source)
        self.assertEqual(bindings, ["bindkey -e", 'bindkey "^A" beginning-of-line'])
        original = "export EDITOR=vim\n"
        updated = install.merge_zshrc(original, bindings)
        self.assertTrue(updated.startswith(original))
        self.assertEqual(install.merge_zshrc(updated, bindings), updated)
        changed = install.merge_zshrc(updated, ["bindkey -v"])
        self.assertIn("bindkey -v", changed)
        self.assertNotIn("bindkey -e", changed)
        with self.assertRaises(ValueError):
            install.merge_zshrc(original + install.ZSH_BEGIN + "\n", bindings)

    def test_capture_active_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            karabiner = root / "karabiner.json"
            vscode = root / "keybindings.json"
            snapshot = root / "system.json"
            zshrc = root / ".zshrc"
            zshrc.write_text("export EDITOR=vim\nbindkey -e\n")
            install.write(
                karabiner,
                {
                    "profiles": [
                        {
                            "selected": True,
                            "devices": [
                                {
                                    "identifiers": {
                                        "is_keyboard": True,
                                        "vendor_id": 1,
                                        "product_id": 2,
                                    },
                                    "simple_modifications": [],
                                }
                            ],
                            "complex_modifications": {
                                "rules": [{"description": "custom", "manipulators": []}]
                            },
                        }
                    ]
                },
            )
            install.write(vscode, [{"key": "f2", "command": "custom"}])
            with mock.patch.multiple(
                capture,
                KARABINER=karabiner,
                VSCODE=vscode,
                SNAPSHOT=snapshot,
                ZSHRC=zshrc,
            ), mock.patch.object(
                capture.platform, "system", return_value="Darwin"
            ), mock.patch.object(
                sys, "argv", ["capture.py"]
            ), mock.patch.object(
                capture,
                "read_alttab_preferences",
                return_value={"appearanceTheme": 1, "MSAppCenterInstallId": "private"},
            ):
                capture.main()
            saved = install.load(snapshot)
            self.assertEqual(saved["source_device"], [1, 2])
            self.assertEqual(saved["rules"][0]["description"], "custom")
            self.assertEqual(
                saved["vscode_keybindings"], [{"key": "f2", "command": "custom"}]
            )
            self.assertEqual(saved["alttab_preferences"], {"appearanceTheme": 1})
            self.assertEqual(saved["zsh_bindings"], ["bindkey -e"])

    def test_capture_install_and_restore(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            karabiner = root / "karabiner.json"
            rules_file = root / "rules.json"
            vscode = root / "keybindings.json"
            snapshot = root / "system.json"
            zshrc = root / ".zshrc"
            original_zshrc = "export EDITOR=vim\n"
            zshrc.write_text(original_zshrc)
            state = root / ".config/winmac-keyboard"
            original_profile = {
                "selected": True,
                "devices": [
                    {
                        "identifiers": {
                            "is_keyboard": True,
                            "vendor_id": 3,
                            "product_id": 4,
                        },
                        "simple_modifications": [],
                    }
                ],
                "complex_modifications": {
                    "rules": [{"description": "unrelated", "manipulators": []}]
                },
            }
            original_config = {"profiles": [original_profile]}
            original_bindings = [{"key": "f1", "command": "unrelated"}]
            install.write(karabiner, original_config)
            install.write(vscode, original_bindings)
            install.write(
                snapshot,
                {
                    "source_device": [1, 2],
                    "simple_modifications": [
                        {
                            "from": {"key_code": "left_control"},
                            "to": [{"key_code": "left_command"}],
                        }
                    ],
                    "rules": [
                        {"description": "custom", "manipulators": [{"type": "basic"}]}
                    ],
                    "vscode_keybindings": [{"key": "f2", "command": "custom"}],
                    "alttab_preferences": {"appearanceTheme": 1},
                    "zsh_bindings": ["bindkey -e", "bindkey '^A' beginning-of-line"],
                },
            )
            previous_prefs = {"appearanceTheme": 0, "unrelated": "kept"}
            patches = {
                "KARABINER": karabiner,
                "RULES_FILE": rules_file,
                "VSCODE": vscode,
                "SNAPSHOT": snapshot,
                "STATE": state,
                "ZSHRC": zshrc,
            }
            with mock.patch.multiple(install, **patches), mock.patch.object(
                install.platform, "system", return_value="Darwin"
            ), mock.patch.object(
                sys, "argv", ["install.py", "--skip-brew", "--import-snapshot"]
            ), mock.patch.object(
                install, "stop_alttab"
            ), mock.patch.object(
                install, "read_alttab_preferences", return_value=previous_prefs
            ), mock.patch.object(
                install, "write_alttab_preferences"
            ) as write_prefs, mock.patch.object(
                install.subprocess, "run"
            ):
                install.main()
                profile = install.load(karabiner)["profiles"][0]
                self.assertEqual(
                    [
                        rule["description"]
                        for rule in profile["complex_modifications"]["rules"]
                    ],
                    ["custom", "unrelated"],
                )
                self.assertEqual(
                    profile["complex_modifications"]["rules"][0]["manipulators"][0][
                        "conditions"
                    ][0]["identifiers"][0],
                    {"vendor_id": 3, "product_id": 4},
                )
                self.assertEqual(
                    install.load(vscode),
                    original_bindings + [{"key": "f2", "command": "custom"}],
                )
                write_prefs.assert_called_once_with(
                    {"appearanceTheme": 1, "unrelated": "kept"}
                )
                installed_zshrc = zshrc.read_text()
                self.assertTrue(installed_zshrc.startswith(original_zshrc))
                self.assertIn("bindkey -e", installed_zshrc)
                with mock.patch.object(Path, "home", return_value=root), mock.patch(
                    "builtins.input", return_value="RESTORE"
                ), mock.patch.object(uninstall, "stop_alttab"), mock.patch.object(
                    uninstall, "write_alttab_preferences"
                ) as restore_prefs:
                    uninstall.main()
                    restore_prefs.assert_called_once_with(previous_prefs)
                self.assertEqual(install.load(karabiner), original_config)
                self.assertEqual(install.load(vscode), original_bindings)
                self.assertEqual(zshrc.read_text(), original_zshrc)
                zshrc.unlink()
                install.main()
                self.assertTrue(zshrc.exists())
                with mock.patch.object(Path, "home", return_value=root), mock.patch(
                    "builtins.input", return_value="RESTORE"
                ), mock.patch.object(uninstall, "stop_alttab"), mock.patch.object(
                    uninstall, "write_alttab_preferences"
                ):
                    uninstall.main()
                self.assertFalse(zshrc.exists())
                zshrc.write_text(original_zshrc)
                install.main()
                first_install = install.load(karabiner)
                first_bindings = install.load(vscode)
                first_zshrc = zshrc.read_text()
                install.main()
                self.assertEqual(install.load(karabiner), first_install)
                self.assertEqual(install.load(vscode), first_bindings)
                self.assertEqual(zshrc.read_text(), first_zshrc)


class TestDefaultInstall(unittest.TestCase):
    def test_fresh_alttab_has_no_persistent_domain(self):
        result = mock.Mock(returncode=1, stderr=b'Domain com.lwouis.alt-tab-macos does not exist')
        with mock.patch.object(install.subprocess, 'run', return_value=result):
            self.assertEqual(install.read_alttab_preferences(), {})

    def test_alttab_backup_errors_are_not_silently_ignored(self):
        result = mock.Mock(returncode=1, stderr=b'Permission denied')
        with mock.patch.object(install.subprocess, 'run', return_value=result):
            with self.assertRaisesRegex(RuntimeError, 'Cannot back up'):
                install.read_alttab_preferences()

    def test_defaults_migrate_and_restore_profiles_without_snapshot_override(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / '.config/winmac-keyboard'
            karabiner = root / 'karabiner.json'
            vscode = root / 'keybindings.json'
            zshrc = root / '.zshrc'
            snapshot = root / 'system.json'
            iterm = root / 'Library/Application Support/iTerm2/DynamicProfiles/winmac.json'
            config = {'profiles': [{'selected': True, 'devices': [{'identifiers': {
                'is_keyboard': True, 'vendor_id': 1, 'product_id': 2}}],
                'complex_modifications': {'rules': [{'description': 'Terminal - restore Windows Ctrl+C interrupt', 'manipulators': []},
                                                    {'description': 'my custom rule', 'manipulators': []}]}}]}
            install.write(karabiner, config)
            install.write(snapshot, {'rules': [{'description': 'stale snapshot'}]})
            legacy = {'key': 'cmd+c', 'command': 'workbench.action.terminal.sendSequence',
                      'args': {'text': '\x03'}, 'when': 'terminalFocus && !terminalTextSelected'}
            custom = {'key': 'f9', 'command': 'custom.command'}
            install.write(vscode, [legacy, custom])
            zshrc.write_text('export EDITOR=vim\n')
            iterm.parent.mkdir(parents=True)
            iterm.write_text('{"existing": true}\n')
            original_profile = iterm.read_bytes()
            prefs = {'holdShortcut': 'old', 'other': 'preserved'}
            with mock.patch.multiple(install, HOME=root, STATE=state, KARABINER=karabiner,
                                     VSCODE=vscode, ZSHRC=zshrc, SNAPSHOT=snapshot,
                                     RULES_FILE=root / 'rules.json'), \
                 mock.patch.object(install.platform, 'system', return_value='Darwin'), \
                 mock.patch.object(sys, 'argv', ['install.py', '--skip-brew']), \
                 mock.patch.object(install, 'stop_alttab'), \
                 mock.patch.object(install, 'read_alttab_preferences', return_value=prefs), \
                 mock.patch.object(install, 'write_alttab_preferences') as write_prefs, \
                 mock.patch.object(install.subprocess, 'run'):
                install.main()
                bindings = install.load(vscode)
                self.assertNotIn(legacy, bindings)
                self.assertIn(custom, bindings)
                self.assertTrue((state / 'finder_actions.js').exists())
                self.assertTrue((state / 'WinMac.terminal').exists())
                rules = install.load(karabiner)['profiles'][0]['complex_modifications']['rules']
                self.assertEqual(rules[-1]['description'], 'my custom rule')
                self.assertFalse(any(r['description'] == 'stale snapshot' for r in rules))
                write_prefs.assert_called_once_with({'other': 'preserved'})
                with mock.patch.object(Path, 'home', return_value=root), \
                     mock.patch('builtins.input', return_value='RESTORE'), \
                     mock.patch.object(uninstall, 'stop_alttab'), \
                     mock.patch.object(uninstall, 'write_alttab_preferences'):
                    uninstall.main()
                self.assertEqual(iterm.read_bytes(), original_profile)
                self.assertFalse((state / 'finder_actions.js').exists())
                self.assertEqual(install.load(karabiner), config)
                self.assertEqual(install.load(vscode), [legacy, custom])
                self.assertEqual(zshrc.read_text(), 'export EDITOR=vim\n')


if __name__ == "__main__":
    unittest.main()
