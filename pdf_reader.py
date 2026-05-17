import os
import io


def _get_poppler():
    import gi
    gi.require_version('Poppler', '0.18')
    from gi.repository import Poppler
    return Poppler


class PdfBook:
    def __init__(self, filepath):
        self.filepath = filepath
        self.title = ''
        self.author = ''
        self.toc = []
        self._doc = None
        self._load()

    def _load(self):
        Poppler = _get_poppler()
        uri = 'file://' + os.path.abspath(self.filepath)
        self._doc = Poppler.Document.new_from_file(uri)
        self.title = self._doc.get_title() or os.path.basename(self.filepath)
        self.author = self._doc.get_author() or ''
        self.toc = self._parse_toc()

    def _parse_toc(self):
        # Build a simple page list since this Poppler version lacks outline support
        return [
            {'title': f'Page {i + 1}', 'index': i, 'depth': 0}
            for i in range(self.page_count)
        ]

    @property
    def page_count(self):
        return self._doc.get_n_pages() if self._doc else 0

    _BG = {
        'light': (1.0,  1.0,  1.0),
        'sepia': (0.96, 0.93, 0.86),
        'dark':  (0.15, 0.15, 0.15),
    }

    def render_page(self, page_num, scale=1.0, theme='light'):
        """Render a PDF page and return a GdkPixbuf."""
        if not self._doc or page_num >= self.page_count:
            return None

        import gi
        import cairo
        gi.require_version('GdkPixbuf', '2.0')
        from gi.repository import GdkPixbuf

        page = self._doc.get_page(page_num)
        pw, ph = page.get_size()
        w = max(1, int(pw * scale))
        h = max(1, int(ph * scale))

        surface = cairo.ImageSurface(cairo.FORMAT_RGB24, w, h)
        ctx = cairo.Context(surface)
        bg = self._BG.get(theme, (1.0, 1.0, 1.0))
        ctx.set_source_rgb(*bg)
        ctx.paint()
        ctx.scale(scale, scale)
        page.render(ctx)
        surface.flush()

        # Write to PNG in memory and load as GdkPixbuf — avoids BGR↔RGB conversion
        buf = io.BytesIO()
        surface.write_to_png(buf)
        buf.seek(0)
        data = buf.read()

        loader = GdkPixbuf.PixbufLoader.new_with_type('png')
        loader.write(data)
        loader.close()
        return loader.get_pixbuf()

    def __len__(self):
        return self.page_count
