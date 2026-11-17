import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import deskflow


class DeskflowTests(unittest.TestCase):
    def config(self):
        return {'profiles': [{'name': 'Normal', 'selected': True,
                'simple_modifications': [{'custom': True}],
                'complex_modifications': {'rules': [{'custom': True}]},
                'devices': [{'identifiers': {'is_keyboard': True, 'vendor_id': 1, 'product_id': 2},
                             'simple_modifications': [{'custom': True}]}]}]}

    def test_passthrough_preserves_normal_and_ignores_keyboard(self):
        original = self.config()
        before = copy.deepcopy(original)
        result, text = deskflow.configure(original, '[core]\ncoreMode=2\n', '/helper')
        self.assertEqual(original, before)
        self.assertEqual(result['profiles'][0], before['profiles'][0])
        raw = result['profiles'][-1]
        self.assertFalse(raw['selected'])
        self.assertTrue(raw['devices'][0]['ignore'])
        self.assertEqual(raw['simple_modifications'], [])
        self.assertEqual(raw['complex_modifications']['rules'], [])
        self.assertIn('exitCommand=/helper --leave', text)
        self.assertIn('enterCommand=/helper --enter', text)

    def test_refuses_existing_hooks_and_client(self):
        for text in ('[core]\ncoreMode=1\n', '[core]\ncoreMode=2\nexitCommand=existing\n'):
            with self.assertRaises(ValueError):
                deskflow.configure(self.config(), text, '/helper')

    def test_roundtrip_and_idempotent_transition(self):
        with tempfile.TemporaryDirectory() as root:
            state = Path(root) / 'state'
            karabiner = Path(root) / 'karabiner.json'
            config = Path(root) / 'Deskflow.conf'
            karabiner.write_text(json.dumps(self.config()))
            karabiner.chmod(0o600)
            config.write_text('[core]\ncoreMode=2\n[unrelated]\nkeep=yes\n')
            originals = (karabiner.read_bytes(), config.read_bytes())
            def current():
                return next(p['name'] for p in json.loads(karabiner.read_text())['profiles'] if p.get('selected'))
            with mock.patch.multiple(deskflow, STATE=state, KARABINER=karabiner, DESKFLOW=config):
                with mock.patch.object(sys, 'argv', ['deskflow.py', '--install']):
                    deskflow.main()
                deskflow.transition(True)
                deskflow.transition(True)
                self.assertEqual(current(), deskflow.RAW)
                self.assertEqual(karabiner.stat().st_mode & 0o777, 0o600)
                deskflow.transition(False)
                self.assertEqual(current(), 'Normal')
                self.assertEqual((state / 'deskflow-transitions.log').read_text(), 'leave\nenter\n')
                with mock.patch.object(sys, 'argv', ['deskflow.py', '--uninstall']):
                    deskflow.main()
                self.assertEqual((karabiner.read_bytes(), config.read_bytes()), originals)
                self.assertFalse((state / 'deskflow.py').exists())
