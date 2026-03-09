@echo off
SET VENV_DIR=.venv

REM Check if venv exists
IF NOT EXIST %VENV_DIR% (
    echo Creating virtual environment...
    python -m venv %VENV_DIR%
)

REM Activate the venv
call %VENV_DIR%\Scripts\activate

REM Install packages (including dev dependencies for PyInstaller)
echo Installing packages...
pip install -e ".[dev]"

REM Build the exe
echo Building executable...
pyinstaller --onefile --name MuseScore-scraper --collect-all curl_cffi src/musescore_scraper/cli.py

REM Deactivate and finish
deactivate
pause
