# MuseScore Scraper

Download MuseScore sheet music as PDFs.

Given a MuseScore URL, this tool automates a headless browser to scroll through
the score, capture all SVG page images, and merge them into a single PDF.

## Prerequisites

- Python 3.9+
- **Google Chrome** or **Chromium**

The scraper auto-detects which browser is available at runtime. It checks for
the following binaries in order: `google-chrome-stable`, `google-chrome`,
`chromium`, `chromium-browser`.

### Installing a browser

| Distro | Command |
|---|---|
| Arch Linux | `sudo pacman -S chromium` |
| Debian / Ubuntu | `sudo apt install chromium-browser` |
| Fedora | `sudo dnf install chromium` |
| Windows / macOS | Install [Google Chrome](https://www.google.com/chrome/) |

## Installation

```bash
pip install .
```

For development (includes PyInstaller for building executables):

```bash
pip install -e ".[dev]"
```

## Usage

Run the CLI:

```bash
musescore-scraper
```

You will be prompted to enter a filename and a MuseScore URL. The resulting PDF
is saved to the `output/` directory.

Type `exit`, `quit`, or press `Ctrl-C` to stop.

## Building a Standalone Executable

### Linux

```bash
chmod +x build.sh
./build.sh
```

This creates a `.venv`, installs dependencies, checks for Chrome/Chromium, and
produces a standalone binary at `dist/musescore-scraper` via PyInstaller.

After building, the script will offer to install the binary and a `.desktop`
entry so you can launch it from your application menu:

- Binary is copied to `~/.local/bin/musescore-scraper`
- Desktop entry is copied to `~/.local/share/applications/`

If `~/.local/bin` is not in your `$PATH`, add this to your shell profile
(`~/.bashrc`, `~/.zshrc`, etc.):

```bash
export PATH="$HOME/.local/bin:$PATH"
```

To install manually (without the build script prompt):

```bash
cp dist/musescore-scraper ~/.local/bin/
cp musescore-scraper.desktop ~/.local/share/applications/
```

### Windows

```cmd
build.bat
```

This creates a `.venv`, installs dependencies, and produces a standalone `.exe`
at `dist/MuseScore-scraper.exe` via PyInstaller.
