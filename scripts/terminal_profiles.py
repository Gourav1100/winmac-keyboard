"""Portable terminal profiles; imported explicitly to avoid changing unrelated profiles."""
import json

# iTerm2 Action 10 sends an escape sequence. Unmodified Page keys must reach TUI apps.
def iterm_profile():
    return {'Profiles': [{
        'Name': 'WinMac', 'Guid': '7AB0D2BE-EB3F-4A61-B1B0-0F2F796D6163',
        'Keyboard Map': {
            '0xf72c-0x0': {'Action': 10, 'Text': '[5~'},
            '0xf72d-0x0': {'Action': 10, 'Text': '[6~'},
            '0xf729-0x0': {'Action': 10, 'Text': '[H'},
            '0xf72b-0x0': {'Action': 10, 'Text': '[F'},
            '0xf728-0x0': {'Action': 10, 'Text': '[3~'},
            '0xf702-0x40000': {'Action': 10, 'Text': 'b'},
            '0xf703-0x40000': {'Action': 10, 'Text': 'f'},
            '0x7f-0x40000': {'Action': 10, 'Text': '\x7f'},
            '0xf728-0x40000': {'Action': 10, 'Text': '[3;5~'},
        },
    }]}

KITTY_CONFIG = r'''# Include this file from kitty.conf to enable WinMac navigation.
map page_up send_key page_up
map page_down send_key page_down
map home send_key home
map end send_key end
map delete send_key delete
map ctrl+left send_text all \x1bb
map ctrl+right send_text all \x1bf
map ctrl+backspace send_text all \x1b\x7f
map ctrl+delete send_text all \x1b[3;5~
map ctrl+shift+c copy_to_clipboard
map ctrl+shift+v paste_from_clipboard
'''

# Terminal.app stores key bindings in the profile, not in .zshrc.
# $ is Shift, ~ is Option, ^ is Control, @ is Command. Unmodified keys have no prefix.
def terminal_profile():
    return {
        'name': 'WinMac', 'type': 'Window Settings', 'ProfileCurrentVersion': 2.07,
        'keyMapBoundKeys': {
            '\uf72c': '\x1b[5~', '\uf72d': '\x1b[6~',
            '\uf729': '\x1b[H', '\uf72b': '\x1b[F', '\uf728': '\x1b[3~',
            '^\uf702': '\x1bb', '^\uf703': '\x1bf',
            '^\x7f': '\x1b\x7f', '^\uf728': '\x1b[3;5~',
        },
    }

if __name__ == '__main__':
    print(json.dumps(iterm_profile(), indent=2))
