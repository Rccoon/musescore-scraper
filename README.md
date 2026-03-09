# MuseScore Scraper

Download MuseScore sheet music as PDFs.

Given a MuseScore URL, this tool fetches all score pages and merges them
into a single PDF file.

## Prerequisites

- Python >= 3.10

## Installation

```bash
pip install .
```

For development (includes PyInstaller):

```bash
pip install -e ".[dev]"
```

## Usage

```bash
musescore-scraper                        # saves to current directory
musescore-scraper -o ~/Music/sheets      # saves to a specific directory
musescore-scraper --version              # print version and exit
```

The tool prompts for a MuseScore URL and a filename, downloads the score,
and saves it as a PDF. After each download it asks whether to continue.

Type `exit`, `quit`, or press Ctrl-C to stop.

## Building a Standalone Executable

### Linux

```bash
chmod +x build.sh
./build.sh
```

This creates a virtual environment, installs dependencies, and produces a
standalone binary at `dist/musescore-scraper` via PyInstaller.

After building, the script offers to install:

- Binary to `~/.local/bin/musescore-scraper`
- Desktop entry to `~/.local/share/applications/`

When launched from the desktop entry, PDFs are saved to
`~/Documents/musescore_scraped` by default.

If `~/.local/bin` is not in your PATH, add this to your shell profile:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

### Windows

```cmd
build.bat
```

This creates a virtual environment, installs dependencies, and produces
`dist/MuseScore-scraper.exe` via PyInstaller.
