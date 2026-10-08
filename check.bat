@echo off
cd /d "%~dp0"
REM Checks Tesseract, Ghostscript and OCRmyPDF on this machine
if not defined TESSERACT_CMD if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" set "TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe"
".venv\Scripts\python.exe" manage.py check_ocr
pause
