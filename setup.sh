#!/usr/bin/env bash
# Установка «Гендальф» (Linux/macOS): виртуальное окружение + библиотеки из vendor/wheels (без интернета) + БД
set -e
cd "$(dirname "$0")"
python3 -m venv .venv
.venv/bin/pip install --no-index --find-links vendor/wheels -r requirements.txt \
  || .venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py collectstatic --noinput
command -v tesseract >/dev/null || echo "ВНИМАНИЕ: не найден Tesseract OCR. Установите: sudo apt install tesseract-ocr (см. README.md)"
echo "Готово. Запуск: ./run.sh"
