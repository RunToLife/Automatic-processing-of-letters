@echo off
chcp 65001 >nul
cd /d "%~dp0"
REM Если Tesseract не в PATH, раскомментируйте:
REM set TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
.venv\Scripts\python waitress_run.py
pause
