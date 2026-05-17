import os
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

from database import Database
from epub_reader import EpubBook
from pdf_reader import PdfBook
from ui.library_view import LibraryView
from ui.reader_view import EpubReaderView, PdfReaderView
from ui.sidebar import Sidebar

STYLE_PATH = os.path.join(os.path.dirname(__file__), 'style.css')


def _load_css():
    provider = Gtk.CssProvider()
    try:
        provider.load_from_path(STYLE_PATH)
    except Exception:
        pass
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(),
        provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title='Pageturner')
        screen = Gdk.Screen.get_default()
        w = int(screen.get_width() * 0.85)
        h = int(screen.get_height() * 0.85)
        self.set_default_size(w, h)
        self.set_position(Gtk.WindowPosition.CENTER)
        _load_css()

        self.db = Database()
        self._book = None
        self._book_id = None
        self._reader = None
        self._theme = self.db.get_setting('theme') or 'light'
        self._font_size = int(self.db.get_setting('font_size') or 16)

        self._build_ui()
        self.connect('delete-event', self._on_close)

    def _build_ui(self):
        # Header bar
        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.set_title('Pageturner')
        self.set_titlebar(header)

        # Left: library home button
        self._home_btn = Gtk.Button()
        self._home_btn.set_image(Gtk.Image.new_from_icon_name('go-home-symbolic', Gtk.IconSize.BUTTON))
        self._home_btn.set_tooltip_text('Library')
        self._home_btn.connect('clicked', self._on_home)
        header.pack_start(self._home_btn)

        # Left: sidebar toggle
        self._sidebar_btn = Gtk.ToggleButton()
        self._sidebar_btn.set_image(Gtk.Image.new_from_icon_name('view-sidebar-symbolic', Gtk.IconSize.BUTTON))
        self._sidebar_btn.set_tooltip_text('Toggle sidebar')
        self._sidebar_btn.set_active(True)
        self._sidebar_btn.connect('toggled', self._on_sidebar_toggle)
        header.pack_start(self._sidebar_btn)

        # Right: open button
        open_btn = Gtk.Button()
        open_btn.set_image(Gtk.Image.new_from_icon_name('document-open-symbolic', Gtk.IconSize.BUTTON))
        open_btn.set_tooltip_text('Open book')
        open_btn.connect('clicked', self._on_open)
        header.pack_end(open_btn)

        # Right: bookmark button
        self._bm_btn = Gtk.Button()
        self._bm_btn.set_image(Gtk.Image.new_from_icon_name('bookmark-new-symbolic', Gtk.IconSize.BUTTON))
        self._bm_btn.set_tooltip_text('Add bookmark')
        self._bm_btn.connect('clicked', self._on_add_bookmark)
        self._bm_btn.set_sensitive(False)
        header.pack_end(self._bm_btn)

        # Right: theme buttons
        theme_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        self._theme_btns = {}
        for name, label in [('light', '☀'), ('sepia', '📜'), ('dark', '🌙')]:
            btn = Gtk.Button(label=label)
            btn.set_tooltip_text(name.capitalize())
            btn.get_style_context().add_class('theme-btn')
            btn.connect('clicked', self._on_theme, name)
            theme_box.pack_start(btn, False, False, 0)
            self._theme_btns[name] = btn
        header.pack_end(theme_box)

        # Right: font size slider
        font_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        font_box.pack_start(Gtk.Label(label='A'), False, False, 2)
        self._font_slider = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 12, 28, 1)
        self._font_slider.set_value(self._font_size)
        self._font_slider.set_draw_value(False)
        self._font_slider.set_size_request(100, -1)
        self._font_slider.connect('value-changed', self._on_font_size)
        font_box.pack_start(self._font_slider, False, False, 0)
        font_box.pack_start(Gtk.Label(label='A'), False, False, 2)
        header.pack_end(font_box)

        # Main layout
        self._main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(self._main_box)

        # Stack: library vs reader
        self._stack = Gtk.Stack()
        self._stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._stack.set_transition_duration(150)
        self._main_box.pack_start(self._stack, True, True, 0)

        # Library view
        self._library = LibraryView(self.db)
        self._library.connect('book-selected', self._on_book_selected)
        self._stack.add_named(self._library, 'library')

        # Reader paned
        self._reader_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self._stack.add_named(self._reader_paned, 'reader')

        # Sidebar
        self._sidebar = Sidebar(self.db)
        self._sidebar.connect('toc-selected', self._on_toc_selected)
        self._sidebar.connect('bookmark-selected', self._on_bookmark_selected)
        self._reader_paned.pack1(self._sidebar, False, False)
        self._reader_paned.set_position(220)

        # Reader area placeholder
        self._reader_area = Gtk.Box()
        self._reader_paned.pack2(self._reader_area, True, True)

        # Status bar
        self._status_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self._status_bar.get_style_context().add_class('status-bar')
        self._progress_label = Gtk.Label(label='', xalign=0)
        self._status_bar.pack_start(self._progress_label, False, False, 0)
        self._main_box.pack_start(self._status_bar, False, False, 0)

        self._stack.set_visible_child_name('library')
        self._update_theme_buttons()

    def _open_book(self, filepath):
        ext = os.path.splitext(filepath)[1].lower()
        try:
            if ext == '.epub':
                if self._book and hasattr(self._book, 'cleanup'):
                    self._book.cleanup()
                self._book = EpubBook(filepath)
                book_row = self.db.add_or_get_book(
                    filepath, self._book.title, self._book.author,
                    'epub', len(self._book)
                )
                self._book_id = book_row['id']
                reader = EpubReaderView()
                reader.load_book(self._book)
                reader.connect('progress-changed', self._on_progress_changed)
                self._set_reader(reader)
                saved_idx, _ = self.db.get_progress(self._book_id)
                reader.go_to(saved_idx)
                self._sidebar.load_toc(self._book.toc)

            elif ext == '.pdf':
                if self._book and hasattr(self._book, 'cleanup'):
                    self._book.cleanup()
                self._book = PdfBook(filepath)
                book_row = self.db.add_or_get_book(
                    filepath, self._book.title, self._book.author,
                    'pdf', len(self._book)
                )
                self._book_id = book_row['id']
                reader = PdfReaderView()
                reader.load_book(self._book)
                reader.connect('progress-changed', self._on_progress_changed)
                self._set_reader(reader)
                saved_idx, _ = self.db.get_progress(self._book_id)
                reader.go_to(saved_idx)
                self._sidebar.load_toc(self._book.toc)

            else:
                self._show_error('Unsupported format', f'Cannot open: {filepath}')
                return

            self._sidebar.load_bookmarks(self._book_id)
            self._reader.set_theme(self._theme)
            self._reader.set_font_size(self._font_size)
            self.set_title(f'Pageturner — {self._book.title}')
            self._bm_btn.set_sensitive(True)
            self._stack.set_visible_child_name('reader')
            self._library.refresh()

        except Exception as e:
            self._show_error('Could not open book', str(e))

    def _set_reader(self, reader):
        if self._reader:
            self._reader_area.remove(self._reader)
        self._reader = reader
        self._reader_area.pack_start(reader, True, True, 0)
        self._reader_area.show_all()

    def _on_book_selected(self, library, filepath):
        self._open_book(filepath)

    def _on_open(self, btn):
        dialog = Gtk.FileChooserDialog(
            title='Open Book',
            transient_for=self,
            action=Gtk.FileChooserAction.OPEN,
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK,
        )
        f = Gtk.FileFilter()
        f.set_name('Books (EPUB, PDF)')
        f.add_mime_type('application/epub+zip')
        f.add_mime_type('application/pdf')
        f.add_pattern('*.epub')
        f.add_pattern('*.pdf')
        dialog.add_filter(f)
        resp = dialog.run()
        path = dialog.get_filename()
        dialog.destroy()
        if resp == Gtk.ResponseType.OK and path:
            self._open_book(path)

    def _on_home(self, btn):
        self._save_progress()
        self._stack.set_visible_child_name('library')
        self.set_title('Pageturner')
        self._bm_btn.set_sensitive(False)
        self._progress_label.set_text('')

    def _on_sidebar_toggle(self, btn):
        self._sidebar.set_visible(btn.get_active())

    def _on_toc_selected(self, sidebar, index):
        if self._reader:
            self._reader.go_to(index)

    def _on_bookmark_selected(self, sidebar, index):
        if self._reader:
            self._reader.go_to(index)

    def _on_add_bookmark(self, btn):
        if not self._reader or not self._book_id:
            return
        idx = self._reader.current_index
        dialog = Gtk.Dialog(title='Add Bookmark', transient_for=self, modal=True)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                           Gtk.STOCK_OK, Gtk.ResponseType.OK)
        dialog.set_default_response(Gtk.ResponseType.OK)
        box = dialog.get_content_area()
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        inner.set_border_width(16)
        box.pack_start(inner, True, True, 0)
        inner.pack_start(Gtk.Label(label='Bookmark label (optional):', xalign=0), False, False, 0)
        entry = Gtk.Entry()
        entry.set_placeholder_text(f'Page {idx + 1}')
        entry.set_activates_default(True)
        inner.pack_start(entry, False, False, 0)
        dialog.show_all()
        resp = dialog.run()
        label = entry.get_text().strip()
        dialog.destroy()
        if resp == Gtk.ResponseType.OK:
            self._sidebar.add_bookmark(idx, label or f'Page {idx + 1}')

    def _on_theme(self, btn, theme):
        self._theme = theme
        self.db.set_setting('theme', theme)
        if self._reader:
            self._reader.set_theme(theme)
        self._update_theme_buttons()

    def _on_font_size(self, slider):
        size = int(slider.get_value())
        self._font_size = size
        self.db.set_setting('font_size', size)
        if self._reader:
            self._reader.set_font_size(size)

    def _on_progress_changed(self, reader, index):
        total = reader.total
        self._progress_label.set_text(
            f'Section {index + 1} of {total}' if total else ''
        )
        self._sidebar.highlight_toc_item(index)
        self._save_progress()

    def _save_progress(self):
        if self._reader and self._book_id:
            self.db.save_progress(self._book_id, self._reader.current_index)

    def _update_theme_buttons(self):
        for name, btn in self._theme_btns.items():
            ctx = btn.get_style_context()
            if name == self._theme:
                ctx.add_class('theme-btn-active')
            else:
                ctx.remove_class('theme-btn-active')

    def _show_error(self, title, msg):
        dialog = Gtk.MessageDialog(
            transient_for=self, modal=True,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK, text=title,
        )
        dialog.format_secondary_text(msg)
        dialog.run()
        dialog.destroy()

    def _on_close(self, win, event):
        self._save_progress()
        if self._book and hasattr(self._book, 'cleanup'):
            self._book.cleanup()
        return False
