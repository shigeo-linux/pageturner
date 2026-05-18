#!/bin/bash
set -e

APP_NAME="pageturner"
INSTALL_DIR="/opt/${APP_NAME}"
DESKTOP_DIR="/usr/share/applications"

echo "=== Installing ${APP_NAME} ==="

if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found."
    exit 1
fi

echo "Installing system dependencies..."
sudo apt-get update -qq
sudo apt-get install -y \
    python3-gi \
    python3-gi-cairo \
    gir1.2-gtk-3.0 \
    gir1.2-webkit2-4.1 \
    gir1.2-poppler-0.18 \
    python3-ebooklib python3-venv librsvg2-bin

echo "Copying application files..."
sudo mkdir -p "${INSTALL_DIR}"
sudo cp -r "$(dirname "$0")"/* "${INSTALL_DIR}/"
sudo chmod +x "${INSTALL_DIR}/pageturner.py"

echo "Creating virtual environment..."
sudo python3 -m venv --system-site-packages "${INSTALL_DIR}/venv"
sudo "${INSTALL_DIR}/venv/bin/pip" install --quiet pypdf

echo "Installing icon..."
sudo mkdir -p /usr/share/icons/hicolor/scalable/apps
sudo mkdir -p /usr/share/icons/hicolor/48x48/apps
sudo mkdir -p /usr/share/icons/hicolor/256x256/apps
sudo cp "${INSTALL_DIR}/pageturner.svg" /usr/share/icons/hicolor/scalable/apps/pageturner.svg
rsvg-convert -w 48 -h 48 "${INSTALL_DIR}/pageturner.svg" | sudo tee /usr/share/icons/hicolor/48x48/apps/pageturner.png > /dev/null
rsvg-convert -w 256 -h 256 "${INSTALL_DIR}/pageturner.svg" | sudo tee /usr/share/icons/hicolor/256x256/apps/pageturner.png > /dev/null
sudo gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true

echo "Installing desktop entry..."
sudo cp "${INSTALL_DIR}/pageturner.desktop" "${DESKTOP_DIR}/"
sudo update-desktop-database "${DESKTOP_DIR}" 2>/dev/null || true

echo "Creating launcher..."
sudo tee /usr/local/bin/pageturner > /dev/null << 'EOF'
#!/bin/bash
exec /opt/pageturner/venv/bin/python3 /opt/pageturner/pageturner.py "$@"
EOF
sudo chmod +x /usr/local/bin/pageturner

echo "Creating config directory..."
mkdir -p "$HOME/.config/${APP_NAME}"

echo ""
echo "=== Installation complete! ==="
echo "Run: pageturner"
echo "Or search for 'Pageturner' in your application menu."
