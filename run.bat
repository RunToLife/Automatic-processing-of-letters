@echo off
cd /d "%~dp0"
REM Tesseract is auto-detected in the default folder; set TESSERACT_CMD below only if it is installed elsewhere:
REM set TESSERACT_CMD=D:\Tools\Tesseract-OCR\tesseract.exe
if not defined TESSERACT_CMD if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" set "TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe"
".venv\Scripts\python.exe" waitress_run.py
pause
