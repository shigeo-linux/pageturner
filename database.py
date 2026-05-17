import sqlite3
import os

DB_DIR = os.path.expanduser('~/.local/share/pageturner')
DB_PATH = os.path.join(DB_DIR, 'pageturner.db')

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filepath TEXT NOT NULL UNIQUE,
    title TEXT DEFAULT '',
    author TEXT DEFAULT '',
    format TEXT DEFAULT 'epub',
    total_items INTEGER DEFAULT 0,
    last_opened TEXT DEFAULT (datetime('now')),
    added_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL UNIQUE,
    item_index INTEGER DEFAULT 0,
    scroll_pos REAL DEFAULT 0.0,
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS bookmarks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    item_index INTEGER NOT NULL,
    label TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

DEFAULTS = {
    'theme': 'light',
    'font_size': '16',
}


class Database:
    def __init__(self):
        os.makedirs(DB_DIR, exist_ok=True)
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)
        self.conn.commit()
        self._init_settings()

    def _init_settings(self):
        for key, value in DEFAULTS.items():
            self.conn.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, value)
            )
        self.conn.commit()

    # Settings
    def get_setting(self, key):
        row = self.conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row['value'] if row else DEFAULTS.get(key)

    def set_setting(self, key, value):
        self.conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value))
        )
        self.conn.commit()

    # Books
    def add_or_get_book(self, filepath, title='', author='', fmt='epub', total_items=0):
        self.conn.execute(
            """INSERT INTO books (filepath, title, author, format, total_items)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(filepath) DO UPDATE SET
               last_opened=datetime('now'),
               title=CASE WHEN excluded.title != '' THEN excluded.title ELSE title END,
               author=CASE WHEN excluded.author != '' THEN excluded.author ELSE author END,
               total_items=CASE WHEN excluded.total_items > 0 THEN excluded.total_items ELSE total_items END""",
            (filepath, title, author, fmt, total_items)
        )
        self.conn.commit()
        return self.conn.execute(
            "SELECT * FROM books WHERE filepath = ?", (filepath,)
        ).fetchone()

    def get_recent_books(self, limit=20):
        return self.conn.execute(
            "SELECT * FROM books ORDER BY last_opened DESC LIMIT ?", (limit,)
        ).fetchall()

    def remove_book(self, book_id):
        self.conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        self.conn.commit()

    def clear_all_books(self):
        self.conn.execute("DELETE FROM books")
        self.conn.commit()

    # Progress
    def get_progress(self, book_id):
        row = self.conn.execute(
            "SELECT * FROM progress WHERE book_id = ?", (book_id,)
        ).fetchone()
        return (row['item_index'], row['scroll_pos']) if row else (0, 0.0)

    def save_progress(self, book_id, item_index, scroll_pos=0.0):
        self.conn.execute(
            """INSERT INTO progress (book_id, item_index, scroll_pos)
               VALUES (?, ?, ?)
               ON CONFLICT(book_id) DO UPDATE SET
               item_index=excluded.item_index,
               scroll_pos=excluded.scroll_pos,
               updated_at=datetime('now')""",
            (book_id, item_index, scroll_pos)
        )
        self.conn.commit()

    # Bookmarks
    def get_bookmarks(self, book_id):
        return self.conn.execute(
            "SELECT * FROM bookmarks WHERE book_id = ? ORDER BY item_index, created_at",
            (book_id,)
        ).fetchall()

    def add_bookmark(self, book_id, item_index, label=''):
        cur = self.conn.execute(
            "INSERT INTO bookmarks (book_id, item_index, label) VALUES (?, ?, ?)",
            (book_id, item_index, label)
        )
        self.conn.commit()
        return cur.lastrowid

    def delete_bookmark(self, bookmark_id):
        self.conn.execute("DELETE FROM bookmarks WHERE id = ?", (bookmark_id,))
        self.conn.commit()
