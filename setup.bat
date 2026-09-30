@echo off
chcp 65001 >nul
cd /d "%~dp0"
python -m venv .venv || goto :err
.venv\Scripts\python -m pip install --no-index --find-links vendor\wheels -r requirements.txt || .venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python manage.py migrate || goto :err
.venv\Scripts\python manage.py collectstatic --noinput
where tesseract >nul 2>nul || echo ВНИМАНИЕ: Tesseract OCR не найден в PATH - установите его (см. README.md)
echo Готово. Запуск: run.bat
pause
exit /b 0
:err
echo Ошибка установки. Проверьте, что установлен Python 3.11 или 3.12 (галочка Add to PATH).
pause
