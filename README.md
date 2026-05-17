# Pageturner

A clean, fast EPUB and PDF reader for Linux with dark mode, sepia mode, bookmarks, and reading progress tracking. Built with GTK3 and Python.

---

## Features

- **EPUB & PDF support** — open and read both formats in one app
- **Three themes** — Light, Sepia, and Dark mode
- **Font size control** — adjust text size with a slider
- **Sidebar navigation** — jump between chapters via table of contents
- **Bookmarks** — add, label, and jump back to bookmarks
- **Reading progress** — automatically resumes where you left off
- **Library** — recently opened books listed on the home screen
- **Default reader** — can be set as your system default for EPUB and PDF files

---

## Disk space

| Component | Size |
|---|---|
| Pageturner app | < 200 KB |
| python3-gi, gir1.2-gtk-3.0 (usually pre-installed) | ~1.5 MB |
| gir1.2-webkit2-4.1 + libwebkit2gtk-4.1-0 (usually pre-installed) | ~90 MB |
| gir1.2-poppler-0.18 | ~110 KB |
| python3-ebooklib | ~150 KB |

**In practice:** On Ubuntu 24.04 and Linux Mint 22.x, WebKit2GTK and the GTK bindings are almost always already installed as system components, so the additional space needed is typically **under 1 MB**. If starting from a minimal install, allow up to **~100 MB** for all dependencies.

---

## Requirements

- Ubuntu 24.04, Linux Mint 22.x, or any GTK3-capable Linux
- Python 3.10+

---

## Installation

### Option 1 — Installer script (recommended)

```bash
cd pageturner/
chmod +x install.sh
./install.sh
```

Then launch with:
```bash
pageturner
```

Or search for **Pageturner** in your application menu.

### Option 2 — Run directly without installing

Install dependencies:

```bash
sudo apt install \
  python3-gi python3-gi-cairo gir1.2-gtk-3.0 \
  gir1.2-webkit2-4.1 \
  gir1.2-poppler-0.18 \
  python3-ebooklib

pip3 install --user --break-system-packages pypdf
```

Then run:

```bash
cd pageturner/
python3 pageturner.py
```

---

## Set as default reader

To open EPUB and PDF files in Pageturner when double-clicking in your file manager:

```bash
xdg-mime default pageturner.desktop application/epub+zip
xdg-mime default pageturner.desktop application/pdf
```

---

## Data storage

| Data | Location |
|---|---|
| Reading progress & bookmarks | `~/.local/share/pageturner/pageturner.db` |

---

## Troubleshooting

**"No module named gi"**
```bash
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0
```

**PDF files won't open**
```bash
sudo apt install gir1.2-poppler-0.18
```

**EPUB files won't open**
```bash
sudo apt install python3-ebooklib
```

**App won't start**
```bash
python3 /opt/pageturner/pageturner.py
```
Run from terminal to see error messages.

---

## Uninstall

```bash
sudo rm -rf /opt/pageturner
sudo rm -f /usr/local/bin/pageturner
sudo rm -f /usr/share/applications/pageturner.desktop
sudo rm -f /usr/share/icons/hicolor/scalable/apps/pageturner.svg
# To also remove reading progress and bookmarks:
rm -rf ~/.local/share/pageturner
```
