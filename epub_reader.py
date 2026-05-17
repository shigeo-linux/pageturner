import os
import zipfile
import tempfile
import shutil
import xml.etree.ElementTree as ET


class EpubBook:
    def __init__(self, filepath):
        self.filepath = filepath
        self.title = ''
        self.author = ''
        self.spine = []   # list of dicts: {id, title, path}
        self.toc = []     # list of dicts: {title, index}
        self._tmpdir = None
        self._opf_root = ''
        self._load()

    def _get_opf_root(self):
        """Parse META-INF/container.xml to find the directory containing the OPF file."""
        container = os.path.join(self._tmpdir, 'META-INF', 'container.xml')
        if not os.path.exists(container):
            return ''
        try:
            tree = ET.parse(container)
            root = tree.getroot()
            ns = {'c': 'urn:oasis:names:tc:opendocument:xmlns:container'}
            rootfile = root.find('.//c:rootfile', ns)
            if rootfile is not None:
                opf_path = rootfile.get('full-path', '')
                return os.path.dirname(opf_path)
        except Exception:
            pass
        return ''

    def _resolve(self, file_name):
        """Resolve an item's file_name to an absolute path in the temp dir."""
        # Try direct join first
        direct = os.path.join(self._tmpdir, file_name)
        if os.path.exists(direct):
            return direct
        # Try with OPF root prefix
        if self._opf_root:
            with_root = os.path.join(self._tmpdir, self._opf_root, file_name)
            if os.path.exists(with_root):
                return with_root
        # Fallback: search by basename
        basename = os.path.basename(file_name)
        for dirpath, _, files in os.walk(self._tmpdir):
            if basename in files:
                return os.path.join(dirpath, basename)
        return direct  # return best guess even if missing

    def _load(self):
        try:
            from ebooklib import epub
        except ImportError:
            raise RuntimeError("ebooklib not installed")

        book = epub.read_epub(self.filepath, options={'ignore_ncx': False})

        self.title = book.title or os.path.basename(self.filepath)
        authors = book.get_metadata('DC', 'creator')
        self.author = authors[0][0] if authors else ''

        # Extract to temp dir for WebKit loading
        self._tmpdir = tempfile.mkdtemp(prefix='pageturner_epub_')
        with zipfile.ZipFile(self.filepath, 'r') as z:
            z.extractall(self._tmpdir)

        self._opf_root = self._get_opf_root()

        # Build spine — skip nav/ncx items, only include content documents
        self.spine = []
        for item_id, _ in book.spine:
            item = book.get_item_with_id(item_id)
            if item and item.get_type() == 9:  # ITEM_DOCUMENT
                name = item.file_name or ''
                # Skip navigation documents
                if os.path.basename(name) in ('nav.xhtml', 'nav.html', 'toc.ncx'):
                    continue
                path = self._resolve(name)
                if not os.path.exists(path):
                    continue
                self.spine.append({
                    'id': item_id,
                    'title': item.get_name() or item_id,
                    'path': path,
                    'file_name': name,
                })

        # Build TOC from NCX/nav
        self.toc = self._parse_toc(book)

    def _parse_toc(self, book):
        toc = []
        def _walk(items, depth=0):
            for item in items:
                if isinstance(item, tuple):
                    section, children = item
                    href = section.href.split('#')[0] if section.href else ''
                    idx = self._href_to_index(href)
                    toc.append({'title': section.title or '', 'index': idx, 'depth': depth})
                    _walk(children, depth + 1)
                else:
                    href = item.href.split('#')[0] if item.href else ''
                    idx = self._href_to_index(href)
                    toc.append({'title': item.title or '', 'index': idx, 'depth': depth})
        _walk(book.toc)
        return toc if toc else [{'title': s['title'] or f'Section {i+1}', 'index': i, 'depth': 0}
                                  for i, s in enumerate(self.spine)]

    def _href_to_index(self, href):
        basename = os.path.basename(href)
        for i, s in enumerate(self.spine):
            if os.path.basename(s['file_name']) == basename:
                return i
        return 0

    def get_item_uri(self, index):
        if 0 <= index < len(self.spine):
            return 'file://' + self.spine[index]['path']
        return None

    def __len__(self):
        return len(self.spine)

    def cleanup(self):
        if self._tmpdir and os.path.exists(self._tmpdir):
            shutil.rmtree(self._tmpdir, ignore_errors=True)
            self._tmpdir = None
