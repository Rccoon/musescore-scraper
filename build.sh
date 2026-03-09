#!/usr/bin/env bash
set -euo pipefail

VENV_DIR=".venv"
MIN_PYTHON="3.10"

# --- Color helpers ---
red()   { printf '\033[0;31m%s\033[0m\n' "$*"; }
green() { printf '\033[0;32m%s\033[0m\n' "$*"; }
yellow(){ printf '\033[0;33m%s\033[0m\n' "$*"; }

# --- Check Python version ---
check_python() {
    local cmd
    for cmd in python3 python; do
        if command -v "$cmd" &>/dev/null; then
            local ver
            ver=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
            if "$cmd" -c "import sys; exit(0 if sys.version_info >= (3,10) else 1)" 2>/dev/null; then
                PYTHON="$cmd"
                green "Found Python $ver ($cmd)"
                return 0
            else
                yellow "Found $cmd ($ver) but need >= $MIN_PYTHON"
            fi
        fi
    done
    red "Error: Python >= $MIN_PYTHON is required but not found."
    exit 1
}

# --- Main ---
echo "=== MuseScore Scraper - Linux Build ==="
echo ""

check_python

echo ""

# Create venv if needed
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    "$PYTHON" -m venv "$VENV_DIR"
fi

# Activate venv
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

# Install packages
echo "Installing packages..."
pip install -e ".[dev]"

echo ""

# Build standalone binary
echo "Building executable..."
pyinstaller --onefile --name musescore-scraper \
    --collect-all curl_cffi \
    --collect-all playwright \
    --collect-all playwright_stealth \
    src/musescore_scraper/cli.py

echo ""
green "Build complete! Binary at: dist/musescore-scraper"

# --- Install prompt ---
INSTALL_BIN="$HOME/.local/bin"
INSTALL_APPS="$HOME/.local/share/applications"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo "Install musescore-scraper? This will:"
echo "  - Copy binary to $INSTALL_BIN/musescore-scraper"
echo "  - Install desktop entry to $INSTALL_APPS/"
echo ""
read -rp "Install now? [y/N] " answer

if [[ "${answer,,}" == "y" || "${answer,,}" == "yes" ]]; then
    mkdir -p "$INSTALL_BIN"
    cp dist/musescore-scraper "$INSTALL_BIN/musescore-scraper"
    chmod +x "$INSTALL_BIN/musescore-scraper"
    green "Installed binary to $INSTALL_BIN/musescore-scraper"

    mkdir -p "$INSTALL_APPS"
    # Write desktop entry with absolute path so desktop environments find the binary
    sed -e "s|^Exec=musescore-scraper|Exec=$INSTALL_BIN/musescore-scraper|" \
        -e "s|MUSESCORE_OUTPUT_DIR|$HOME/Documents/musescore_scraped|" \
        "$SCRIPT_DIR/musescore-scraper.desktop" > "$INSTALL_APPS/musescore-scraper.desktop"
    green "Installed desktop entry to $INSTALL_APPS/musescore-scraper.desktop"

    # Refresh desktop database if available
    if command -v update-desktop-database &>/dev/null; then
        update-desktop-database "$INSTALL_APPS" 2>/dev/null || true
    fi

    # Check if ~/.local/bin is in PATH
    if [[ ":$PATH:" != *":$INSTALL_BIN:"* ]]; then
        yellow ""
        yellow "Warning: $INSTALL_BIN is not in your PATH."
        yellow "Add the following to your shell profile (~/.bashrc, ~/.zshrc, etc.):"
        yellow "  export PATH=\"\$HOME/.local/bin:\$PATH\""
    fi

    echo ""
    green "Installation complete! You can now:"
    green "  - Run 'musescore-scraper' from a terminal"
    green "  - Launch it from your application menu"
else
    echo ""
    echo "Skipped installation. You can run the binary directly:"
    echo "  ./dist/musescore-scraper"
fi
