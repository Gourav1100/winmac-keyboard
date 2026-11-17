"""Shared terminal sequences and portable shell bindings."""
# xterm normal-cursor sequences; full-screen programs can select application mode.
TERMINAL_KEYS = {
    'home': '\x1b[H', 'end': '\x1b[F', 'pageup': '\x1b[5~',
    'pagedown': '\x1b[6~', 'insert': '\x1b[2~', 'delete': '\x1b[3~',
    'cmd+left': '\x1bb', 'cmd+right': '\x1bf',
    'cmd+backspace': '\x1b\x7f', 'cmd+delete': '\x1b[3;5~',
}
CONTROL_KEYS = {f'cmd+{chr(n + 96)}': chr(n) for n in range(1, 27)}
CONTROL_KEYS.update({'cmd+[': '\x1b', 'cmd+\\': '\x1c',
                     'cmd+]': '\x1d', 'cmd+shift+6': '\x1e',
                     'cmd+shift+-': '\x1f', 'cmd+space': '\x00'})
ZSH_BINDINGS = [
    'bindkey -e',
    "bindkey '^A' beginning-of-line", "bindkey '^E' end-of-line",
    "bindkey '^[b' backward-word", "bindkey '^[f' forward-word",
    "bindkey '^[^?' backward-kill-word",
    "bindkey '^[[H' beginning-of-line", "bindkey '^[[F' end-of-line",
    "bindkey '^[OH' beginning-of-line", "bindkey '^[OF' end-of-line",
    "bindkey '^[[3~' delete-char", "bindkey '^[[3;5~' kill-word",
    "bindkey '^[[1;5D' backward-word", "bindkey '^[[1;5C' forward-word",
    "bindkey '^[[5~' up-line-or-history", "bindkey '^[[6~' down-line-or-history",
]
