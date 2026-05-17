#!/usr/bin/env python3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gio

from ui.main_window import MainWindow


class PageturnerApp(Gtk.Application):
    def __init__(self):
        super().__init__(
            application_id='com.pageturner.app',
            flags=Gio.ApplicationFlags.HANDLES_OPEN
        )

    def do_activate(self):
        existing = self.get_windows()
        if existing:
            existing[0].present()
            return
        win = MainWindow(self)
        win.show_all()

    def do_open(self, files, n_files, hint):
        existing = self.get_windows()
        if existing:
            win = existing[0]
            win.present()
        else:
            win = MainWindow(self)
            win.show_all()
        if files:
            path = files[0].get_path()
            if path:
                win._open_book(path)


def main():
    app = PageturnerApp()
    return app.run(sys.argv)


if __name__ == '__main__':
    sys.exit(main())
