#!/usr/bin/env python3

c.InteractiveShellApp.exec_PYTHONSTARTUP = False
c.TerminalIPythonApp.display_banner = False
c.InteractiveShellApp.extensions = ['autoreload']
c.InteractiveShellApp.exec_lines = [
    '%autoreload 2',
    # '%matplotlib inline',
]

