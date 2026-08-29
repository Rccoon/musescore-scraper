# MuseScore Scraper

Download MuseScore sheet music as PDFs.

Given a MuseScore URL, this tool fetches all score pages and merges them
into a single PDF file.

## Prerequisites

- Python >= 3.10
- A desktop session (the browser window must be visible — see below)

## Installation

```bash
pip install .
patchright install chromium
```

For development (includes PyInstaller):

```bash
pip install -e ".[dev]"
patchright install chromium
```

## How it works

MuseScore sits behind two bot-protection layers: a Cloudflare Managed
Challenge and DataDome. Neither can be cleared by plain HTTP requests —
DataDome validates the TLS fingerprint, so no amount of header spoofing or
cookie copying gets through.

The scraper therefore opens a real Chromium window to clear both walls, then
queries MuseScore's internal image API from inside that page. The sheet music
itself is served from S3 without protection, so pages are downloaded in
parallel with plain HTTP once the URLs are known.

Practical consequences:

- **A browser window will briefly appear.** This is required. Headless mode
  and off-screen windows are both detected and blocked, so the window has to
  render on a real display.
- **On a headless Linux server** you need a virtual display (e.g. `xvfb-run`).
- The first run downloads Chromium (~150 MB). The browser profile is cached in
  `~/.cache/musescore-scraper/browser`, so later runs usually skip the
  challenge and start in a couple of seconds.
- The built binary reuses the Chromium that the build script installed (the
  browser cache under `~/.cache/ms-playwright`, or the platform equivalent).
  You can point it elsewhere with the `PLAYWRIGHT_BROWSERS_PATH` environment
  variable.
- Some scores are limited by MuseScore to a **one-page preview**. The tool says
  so explicitly rather than quietly saving a one-page PDF; the rest of those
  scores requires a paid MuseScore account.

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

This creates a virtual environment, installs dependencies, downloads Chromium,
and produces a standalone binary at `dist/musescore-scraper` via PyInstaller.

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
