import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject


class Sidebar(Gtk.Box):
    __gsignals__ = {
        'toc-selected': (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        'bookmark-selected': (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        'bookmark-deleted': (GObject.SignalFlags.RUN_FIRST, None, (int,)),
    }

    def __init__(self, db):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.db = db
        self.get_style_context().add_class('sidebar')
        self.set_size_request(220, -1)
        self._book_id = None
        self._build_ui()

    def _build_ui(self):
        notebook = Gtk.Notebook()
        notebook.set_tab_pos(Gtk.PositionType.TOP)
        self.pack_start(notebook, True, True, 0)

        # TOC tab
        toc_scroll = Gtk.ScrolledWindow()
        toc_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.toc_list = Gtk.ListBox()
        self.toc_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.toc_list.connect('row-activated', self._on_toc_activated)
        self.toc_list.get_style_context().add_class('sidebar')
        toc_scroll.add(self.toc_list)
        notebook.append_page(toc_scroll, Gtk.Label(label='Contents'))

        # Bookmarks tab
        bm_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        bm_scroll = Gtk.ScrolledWindow()
        bm_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        bm_scroll.set_vexpand(True)
        self.bm_list = Gtk.ListBox()
        self.bm_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.bm_list.connect('row-activated', self._on_bm_activated)
        self.bm_list.get_style_context().add_class('sidebar')
        bm_scroll.add(self.bm_list)
        bm_box.pack_start(bm_scroll, True, True, 0)
        notebook.append_page(bm_box, Gtk.Label(label='Bookmarks'))

    def load_toc(self, toc_items):
        for child in self.toc_list.get_children():
            self.toc_list.remove(child)

        for item in toc_items:
            row = Gtk.ListBoxRow()
            row.toc_index = item['index']
            row.get_style_context().add_class('toc-row')
            label = Gtk.Label(label=item['title'], xalign=0)
            label.set_ellipsize(3)
            label.set_margin_start(item.get('depth', 0) * 12)
            row.add(label)
            self.toc_list.add(row)

        self.toc_list.show_all()

    def load_bookmarks(self, book_id):
        self._book_id = book_id
        self._refresh_bookmarks()

    def _refresh_bookmarks(self):
        for child in self.bm_list.get_children():
            self.bm_list.remove(child)

        if not self._book_id:
            return

        for bm in self.db.get_bookmarks(self._book_id):
            row = Gtk.ListBoxRow()
            row.bookmark_id = bm['id']
            row.item_index = bm['item_index']
            row.get_style_context().add_class('bookmark-row')

            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            label = Gtk.Label(label=bm['label'] or f'Page {bm["item_index"] + 1}', xalign=0)
            label.set_ellipsize(3)
            label.set_hexpand(True)
            box.pack_start(label, True, True, 0)

            del_btn = Gtk.Button()
            del_btn.set_image(Gtk.Image.new_from_icon_name('edit-delete-symbolic', Gtk.IconSize.MENU))
            del_btn.set_relief(Gtk.ReliefStyle.NONE)
            del_btn.connect('clicked', self._on_delete_bookmark, bm['id'])
            box.pack_end(del_btn, False, False, 0)

            row.add(box)
            self.bm_list.add(row)

        self.bm_list.show_all()

    def add_bookmark(self, item_index, label=''):
        if self._book_id is None:
            return
        self.db.add_bookmark(self._book_id, item_index, label)
        self._refresh_bookmarks()

    def _on_toc_activated(self, listbox, row):
        self.emit('toc-selected', row.toc_index)

    def _on_bm_activated(self, listbox, row):
        self.emit('bookmark-selected', row.item_index)

    def _on_delete_bookmark(self, btn, bookmark_id):
        self.db.delete_bookmark(bookmark_id)
        self._refresh_bookmarks()
        self.emit('bookmark-deleted', bookmark_id)

    def highlight_toc_item(self, index):
        for row in self.toc_list.get_children():
            if row.toc_index == index:
                self.toc_list.select_row(row)
                return
