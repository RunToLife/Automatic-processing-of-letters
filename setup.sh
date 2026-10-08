#!/usr/bin/env bash
# Установка «Гендальф» (Linux/macOS): виртуальное окружение + библиотеки из vendor/wheels (без интернета) + БД
set -e
cd "$(dirname "$0")"
python3 -m venv .venv
.venv/bin/pip install --no-index --find-links vendor/wheels -r requirements.txt \
  || .venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py collectstatic --noinput
.venv/bin/python manage.py check_ocr || true
echo "Готово. Запуск: ./run.sh"
