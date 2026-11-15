import sys, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from generate import build_rules, vscode_bindings
from install import portable_alttab_preferences, scope_captured_rules


class TestRules(unittest.TestCase):
    def test_captured_rules_are_scoped_and_retargeted(self):
        rules = [
            {
                "description": "custom",
                "manipulators": [
                    {
                        "conditions": [
                            {
                                "type": "device_if",
                                "identifiers": [{"vendor_id": 1, "product_id": 2}],
                            }
                        ]
                    },
                    {"type": "basic"},
                ],
            }
        ]
        scoped = scope_captured_rules(rules, (1, 2), (3, 4))
        self.assertEqual(
            scoped[0]["manipulators"][0]["conditions"][0]["identifiers"][0],
            {"vendor_id": 3, "product_id": 4},
        )
        self.assertEqual(
            scoped[0]["manipulators"][1]["conditions"][0],
            {"type": "device_if", "identifiers": [{"vendor_id": 3, "product_id": 4}]},
        )
        self.assertEqual(
            rules[0]["manipulators"][0]["conditions"][0]["identifiers"][0]["vendor_id"],
            1,
        )

    def test_alt_tab_preferences_exclude_machine_state(self):
        prefs = {
            "appearanceTheme": 1,
            "previewFocusedWindow": False,
            "shortcutHold": "option",
            "MSAppCenterInstallId": "private",
            "NSWindow Frame SettingsWindow": "screen",
            "SULastCheckTime": "today",
            "onboardingShortcutUsed": True,
        }
        self.assertEqual(
            portable_alttab_preferences(prefs),
            {
                "appearanceTheme": 1,
                "previewFocusedWindow": False,
                "shortcutHold": "option",
            },
        )

    def test_device_conditions(self):
        rules = build_rules((123, 456))
        self.assertTrue(
            all(
                any(c["type"] == "device_if" for c in m.get("conditions", []))
                for r in rules
                for m in r["manipulators"]
            )
        )

    def test_vscode_home_not_captured(self):
        for r in build_rules():
            if "Home, End" in r["description"]:
                self.assertTrue(
                    all(
                        any(
                            c["type"] == "frontmost_application_unless"
                            for c in m.get("conditions", [])
                        )
                        for m in r["manipulators"]
                    )
                )

    def test_vscode_bindings(self):
        binds = vscode_bindings()
        self.assertTrue(any(x["key"] == "insert" for x in binds))
        self.assertTrue(
            any(x["key"] == "home" and x.get("when") == "terminalFocus" for x in binds)
        )


if __name__ == "__main__":
    unittest.main()
