@echo off
cd /d "%~dp0"
echo === Gendalf: setup ===
python --version >nul 2>nul || goto :nopython
python -m venv .venv || goto :err
".venv\Scripts\python.exe" -m pip install --no-index --find-links vendor\wheels -r requirements.txt
if errorlevel 1 (
    echo Offline install failed, trying online install...
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto :err
)
".venv\Scripts\python.exe" manage.py migrate || goto :err
".venv\Scripts\python.exe" manage.py collectstatic --noinput || goto :err
where tesseract >nul 2>nul
if errorlevel 1 (
    if not exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
        echo.
        echo WARNING: Tesseract OCR not found. Install it - see README.md - otherwise scans cannot be recognized.
    )
)
echo.
echo Done. Now run run.bat
pause
exit /b 0

:nopython
echo Python not found. Install Python 3.11 or 3.12 and tick "Add Python to PATH".
pause
exit /b 1

:err
echo Setup failed. See messages above.
pause
exit /b 1
