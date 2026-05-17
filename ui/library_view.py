import os
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject


class LibraryView(Gtk.Box):
    __gsignals__ = {
        'book-selected': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__(self, db):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.db = db
        self._build_ui()

    def _build_ui(self):
        # Header
        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        header.set_border_width(32)
        header.set_halign(Gtk.Align.CENTER)
        header.set_valign(Gtk.Align.CENTER)

        title = Gtk.Label(label='Pageturner')
        title.get_style_context().add_class('welcome-title')
        header.pack_start(title, False, False, 0)

        subtitle = Gtk.Label(label='Your EPUB and PDF reader')
        subtitle.get_style_context().add_class('welcome-subtitle')
        header.pack_start(subtitle, False, False, 0)

        open_btn = Gtk.Button(label='Open Book…')
        open_btn.get_style_context().add_class('action-btn')
        open_btn.set_halign(Gtk.Align.CENTER)
        open_btn.connect('clicked', self._on_open)
        header.pack_start(open_btn, False, False, 0)

        self.pack_start(header, False, False, 0)

        sep = Gtk.Separator()
        self.pack_start(sep, False, False, 0)

        # Recent books header row
        recent_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        recent_header.set_margin_start(24)
        recent_header.set_margin_end(16)
        recent_header.set_margin_top(16)
        recent_header.set_margin_bottom(8)

        recent_label = Gtk.Label(label='Recently Opened', xalign=0)
        recent_label.get_style_context().add_class('welcome-subtitle')
        recent_header.pack_start(recent_label, True, True, 0)

        forget_btn = Gtk.Button(label='Forget All')
        forget_btn.get_style_context().add_class('danger-btn')
        forget_btn.connect('clicked', self._on_forget_all)
        recent_header.pack_end(forget_btn, False, False, 0)

        self.pack_start(recent_header, False, False, 0)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)

        self.book_list = Gtk.ListBox()
        self.book_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.book_list.connect('row-activated', self._on_row_activated)
        self.book_list.set_header_func(self._header_func)
        scroll.add(self.book_list)
        self.pack_start(scroll, True, True, 0)

        self.refresh()

    def _header_func(self, row, before, data=None):
        if before and not row.get_header():
            row.set_header(Gtk.Separator())

    def refresh(self):
        for child in self.book_list.get_children():
            self.book_list.remove(child)

        books = self.db.get_recent_books()
        for book in books:
            row = Gtk.ListBoxRow()
            row.filepath = book['filepath']
            row.get_style_context().add_class('library-row')

            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            box.set_border_width(10)

            # Icon
            fmt = book['format'] or 'epub'
            icon_name = 'application-epub+zip' if fmt == 'epub' else 'application-pdf'
            icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.LARGE_TOOLBAR)
            box.pack_start(icon, False, False, 0)

            # Info
            info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            title_lbl = Gtk.Label(label=book['title'] or os.path.basename(book['filepath']), xalign=0)
            title_lbl.get_style_context().add_class('library-book-title')
            title_lbl.set_ellipsize(3)
            info.pack_start(title_lbl, False, False, 0)

            if book['author']:
                auth_lbl = Gtk.Label(label=book['author'], xalign=0)
                auth_lbl.get_style_context().add_class('library-book-author')
                info.pack_start(auth_lbl, False, False, 0)

            fmt_lbl = Gtk.Label(label=fmt.upper(), xalign=0)
            fmt_lbl.get_style_context().add_class('library-book-author')
            info.pack_start(fmt_lbl, False, False, 0)
            box.pack_start(info, True, True, 0)

            # Remove button
            rem_btn = Gtk.Button()
            rem_btn.set_image(Gtk.Image.new_from_icon_name('edit-delete-symbolic', Gtk.IconSize.MENU))
            rem_btn.set_relief(Gtk.ReliefStyle.NONE)
            rem_btn.connect('clicked', self._on_remove, book['id'])
            box.pack_end(rem_btn, False, False, 0)

            row.add(box)
            self.book_list.add(row)

        self.book_list.show_all()

    def _on_row_activated(self, listbox, row):
        if os.path.exists(row.filepath):
            self.emit('book-selected', row.filepath)
        else:
            dialog = Gtk.MessageDialog(
                transient_for=self.get_toplevel(),
                modal=True,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text='File not found',
            )
            dialog.format_secondary_text(row.filepath)
            dialog.run()
            dialog.destroy()

    def _on_remove(self, btn, book_id):
        self.db.remove_book(book_id)
        self.refresh()

    def _on_forget_all(self, btn):
        dialog = Gtk.MessageDialog(
            transient_for=self.get_toplevel(),
            modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text='Clear recently opened list?',
        )
        dialog.format_secondary_text('This removes all books from the list but does not delete the files.')
        resp = dialog.run()
        dialog.destroy()
        if resp == Gtk.ResponseType.YES:
            self.db.clear_all_books()
            self.refresh()

    def _on_open(self, btn):
        dialog = Gtk.FileChooserDialog(
            title='Open Book',
            transient_for=self.get_toplevel(),
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
            self.emit('book-selected', path)
