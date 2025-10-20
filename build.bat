@echo off
SET VENV_DIR=.venv

REM Check if venv exists
IF NOT EXIST %VENV_DIR% (
    echo Creating virtual environment...
    python -m venv %VENV_DIR%
)

REM Activate the venv
call %VENV_DIR%\Scripts\activate

REM Install packages
echo Installing packages...
pip install -r requirements.txt

REM Build the exe
echo Building executable...
pyinstaller --onefile --name MuseScore-scraper.exe app.py

REM Deactivate and finish
deactivate
pause
