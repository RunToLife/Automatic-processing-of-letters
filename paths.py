"""Пути к ресурсам приложения и к пользовательским данным.

Используется и при запуске из исходников (`python manage.py ...`), и в
собранном PyInstaller-приложении (`--onedir`), поэтому не должен зависеть
от Django и не должен сам ничего печатать/логировать (логирование ещё не
настроено на момент первого импорта settings.py).

Правила:
- При запуске из исходников (`sys.frozen` не установлен) поведение
  полностью совпадает с тем, что было раньше: и ресурсы, и пользовательские
  данные лежат внутри репозитория (корень репозитория = папка этого файла).
- В собранном приложении:
  - resource_path() - файлы, поставляемые вместе со сборкой (шаблоны,
    статика, vendor/tesseract). Только для чтения, лежат в _internal/
    (PyInstaller сам резолвит это через sys._MEIPASS).
  - user_data_dir() - папка для изменяемых данных (БД, загрузки, архив,
    логи): `data` рядом с exe, а если туда нельзя писать (например,
    программа стоит в Program Files без прав администратора) -
    %LOCALAPPDATA%\\Гендальф.
"""
import os
import sys
from pathlib import Path

APP_NAME = "Гендальф"

# Корень репозитория при запуске из исходников (этот файл лежит в корне).
_DEV_ROOT = Path(__file__).resolve().parent


def is_frozen() -> bool:
    """True внутри приложения, собранного PyInstaller-ом."""
    return bool(getattr(sys, "frozen", False))


def _bundle_dir() -> Path:
    """Папка с ресурсами внутри собранного приложения. sys._MEIPASS
    всегда указывает туда, куда PyInstaller реально положил datas
    (для --onedir это _internal рядом с exe) - это официальный и
    version-safe способ получить этот путь."""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    # На случай если sys._MEIPASS почему-то недоступен - запасной вариант.
    return Path(sys.executable).resolve().parent


def resource_path(rel: str) -> Path:
    """Путь к ресурсу, поставляемому вместе с приложением (шаблоны,
    статика, vendor/tesseract). Только для чтения - в собранном
    приложении эта папка может быть недоступна для записи."""
    base = _bundle_dir() if is_frozen() else _DEV_ROOT
    return base / rel


def _is_writable(dir_path: Path) -> bool:
    try:
        dir_path.mkdir(parents=True, exist_ok=True)
        probe = dir_path / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def user_data_dir() -> Path:
    """Папка для изменяемых данных приложения: БД, загрузки, архив, логи.

    В dev-режиме - корень репозитория (поведение как до упаковки).
    В собранном приложении - папка `data` рядом с exe-файлом, а если
    писать в неё нельзя - %LOCALAPPDATA%\\Гендальф."""
    if not is_frozen():
        return _DEV_ROOT

    exe_dir = Path(sys.executable).resolve().parent
    candidate = exe_dir / "data"
    if _is_writable(candidate):
        return candidate

    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        fallback = Path(local_appdata) / APP_NAME
    else:
        fallback = Path.home() / f".{APP_NAME}"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback
