import gi
gi.require_version('Gtk', '3.0')
gi.require_version('WebKit2', '4.1')
from gi.repository import Gtk, WebKit2, GObject, GLib

THEMES = {
    'light': {
        'bg': '#ffffff',
        'fg': '#1a1a1a',
        'link': '#2563eb',
        'body_bg': '#f5f4f0',
    },
    'sepia': {
        'bg': '#f4ecd8',
        'fg': '#5c4a1e',
        'link': '#7a5c2e',
        'body_bg': '#ede3c8',
    },
    'dark': {
        'bg': '#1e1e1e',
        'fg': '#e8e4dc',
        'link': '#c8a96e',
        'body_bg': '#161616',
    },
}


def _theme_css(theme, font_size):
    t = THEMES.get(theme, THEMES['light'])
    return f"""
    html {{
        background-color: {t['bg']} !important;
        margin: 0 !important;
        padding: 0 !important;
    }}
    body {{
        background-color: {t['bg']} !important;
        color: {t['fg']} !important;
        font-size: {font_size}px !important;
        width: 100% !important;
        max-width: 100% !important;
        margin: 0 !important;
        padding: 24px 80px !important;
        line-height: 1.75 !important;
        font-family: "Liberation Serif", Georgia, serif !important;
        box-sizing: border-box !important;
    }}
    a {{ color: {t['link']} !important; }}
    img {{ max-width: 100% !important; height: auto !important; }}
    h1, h2, h3, h4 {{ color: {t['fg']} !important; }}
    """


class EpubReaderView(Gtk.Box):
    __gsignals__ = {
        'progress-changed': (GObject.SignalFlags.RUN_FIRST, None, (int,)),
    }

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._current_index = 0
        self._total = 0
        self._theme = 'light'
        self._font_size = 16
        self._book = None
        self._user_content = WebKit2.UserContentManager()
        self._webview = WebKit2.WebView.new_with_user_content_manager(self._user_content)
        settings = self._webview.get_settings()
        settings.set_enable_javascript(False)
        settings.set_allow_file_access_from_file_urls(True)
        settings.set_allow_universal_access_from_file_urls(True)
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.add(self._webview)
        self.pack_start(scroll, True, True, 0)
        self._apply_theme()

    def load_book(self, book):
        self._book = book
        self._total = len(book)

    def go_to(self, index, scroll_pos=0.0):
        if not self._book or not (0 <= index < self._total):
            return
        self._current_index = index
        uri = self._book.get_item_uri(index)
        if uri:
            self._webview.load_uri(uri)
            self.emit('progress-changed', index)

    def _apply_theme(self):
        css = _theme_css(self._theme, self._font_size)
        self._user_content.remove_all_style_sheets()
        sheet = WebKit2.UserStyleSheet(
            css,
            WebKit2.UserContentInjectedFrames.ALL_FRAMES,
            WebKit2.UserStyleLevel.USER,
            None, None
        )
        self._user_content.add_style_sheet(sheet)
        if self._book:
            self._webview.reload()

    def set_theme(self, theme):
        self._theme = theme
        self._apply_theme()

    def set_font_size(self, size):
        self._font_size = int(size)
        self._apply_theme()

    @property
    def current_index(self):
        return self._current_index

    @property
    def total(self):
        return self._total


class PdfReaderView(Gtk.Box):
    __gsignals__ = {
        'progress-changed': (GObject.SignalFlags.RUN_FIRST, None, (int,)),
    }

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._book = None
        self._current_page = 0
        self._zoom = 1.0
        self._theme = 'light'
        self._resize_pending = False

        self._scroll = Gtk.ScrolledWindow()
        self._scroll.set_vexpand(True)
        self._scroll.set_hexpand(True)
        self._scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self._scroll.connect('size-allocate', self._on_size_allocate)

        self._image = Gtk.Image()
        self._image.set_halign(Gtk.Align.CENTER)
        self._image.set_margin_top(16)
        self._image.set_margin_bottom(16)
        self._scroll.add(self._image)
        self.pack_start(self._scroll, True, True, 0)

        # Navigation bar — full width so the background covers the whole row
        nav = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        nav.get_style_context().add_class('status-bar')

        nav_inner = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        nav_inner.set_halign(Gtk.Align.CENTER)
        nav_inner.set_hexpand(True)
        nav_inner.set_border_width(6)

        self._prev_btn = Gtk.Button(label='← Previous')
        self._prev_btn.connect('clicked', lambda _: self.go_to(self._current_page - 1))
        nav_inner.pack_start(self._prev_btn, False, False, 0)

        self._page_label = Gtk.Label(label='')
        nav_inner.pack_start(self._page_label, False, False, 0)

        self._next_btn = Gtk.Button(label='Next →')
        self._next_btn.connect('clicked', lambda _: self.go_to(self._current_page + 1))
        nav_inner.pack_start(self._next_btn, False, False, 0)

        nav.pack_start(nav_inner, True, True, 0)
        self.pack_start(nav, False, False, 0)

    def load_book(self, book):
        self._book = book
        # Defer first render until widget is fully laid out
        GLib.idle_add(self._render)

    def go_to(self, index, scroll_pos=0.0):
        if not self._book:
            return
        index = max(0, min(index, len(self._book) - 1))
        self._current_page = index
        self._render()
        self.emit('progress-changed', index)

    def _on_size_allocate(self, widget, allocation):
        if self._resize_pending or not self._book:
            return
        self._resize_pending = True
        GLib.timeout_add(150, self._on_resize_done)

    def _on_resize_done(self):
        self._resize_pending = False
        self._render()
        return False

    def _fit_scale(self):
        """Calculate scale so the page fills the available width."""
        alloc_w = self._scroll.get_allocated_width()
        if not self._book or alloc_w < 50:
            return 1.0
        page = self._book._doc.get_page(self._current_page)
        pw, _ = page.get_size()
        return (alloc_w - 32) / pw

    def _render(self):
        if not self._book:
            return False
        scale = self._fit_scale() * self._zoom
        pixbuf = self._book.render_page(self._current_page, scale=scale, theme=self._theme)
        if pixbuf:
            self._image.set_from_pixbuf(pixbuf)
        total = len(self._book)
        self._page_label.set_text(f'Page {self._current_page + 1} of {total}')
        self._prev_btn.set_sensitive(self._current_page > 0)
        self._next_btn.set_sensitive(self._current_page < total - 1)
        return False

    def set_theme(self, theme):
        self._theme = theme
        ctx = self._scroll.get_style_context()
        for t in ('light', 'sepia', 'dark'):
            ctx.remove_class(f'pdf-bg-{t}')
        ctx.add_class(f'pdf-bg-{theme}')
        self._render()

    def set_font_size(self, size):
        self._zoom = size / 16.0
        self._render()

    @property
    def current_index(self):
        return self._current_page

    @property
    def total(self):
        return len(self._book) if self._book else 0
