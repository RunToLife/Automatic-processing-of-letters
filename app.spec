# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec для сборки "Гендальф" в режиме --onedir.

Не запускайте `pyinstaller` с этим файлом напрямую руками - используйте
build.bat, который сначала готовит окружение и статику (collectstatic),
а уже потом вызывает `pyinstaller app.spec`. Подробности - в DOCS_DIST.md.

Отладочная консольная сборка: перед запуском build.bat выставьте
    set GENDALF_BUILD_CONSOLE=1
и exe будет собран с console=True (видно print/traceback сразу, без
чтения log-файла). По умолчанию (переменная не установлена) -
console=False, как и требуется для обычной поставки пользователям.
Независимо от этого, уже собранный --noconsole exe можно временно
"открыть" консолью в рантайме через переменную окружения GENDALF_DEBUG=1
(см. launcher.py) - для этого пересборка не нужна.
"""
import os
import sys

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

APP_NAME = "Гендальф"
BUILD_CONSOLE = os.environ.get("GENDALF_BUILD_CONSOLE") == "1"

# collect_submodules() ниже реально импортирует пакеты (letters,
# letters_project) в процессе, который исполняет этот .spec-файл, чтобы
# перечислить их подмодули. Скрипт "pyinstaller" - это консольный
# entry point внутри venv (например, .venv\Scripts\pyinstaller.exe), а
# не сам app.spec, поэтому корень репозитория НЕ добавляется в sys.path
# автоматически - добавляем его явно, иначе import "letters" падает и
# приложение целиком пропадает из сборки (проверено: без этой строки
# получается "ModuleNotFoundError: No module named 'letters'" при
# первом запуске собранного exe).
sys.path.insert(0, os.path.abspath("."))

# --------------------------------------------------------------------------
# У PyInstaller есть встроенный runtime hook для Django (pyi_rth_django.py)
# и hooks для отдельных СУБД-бэкендов (mysql/oracle) - они подхватываются
# автоматически. Но INSTALLED_APPS, management-команды и наше собственное
# приложение letters всё равно грузятся по строковым путям (importlib) —
# обычный статический анализ импортов PyInstaller этого не видит, поэтому
# добираем нужные пакеты целиком через collect_submodules, с запасом
# (лишние мелкие .py-модули почти не влияют на размер). Проверено сборкой
# и прогоном итогового exe: без этого миграции/приложение не запускаются.
hiddenimports = []
for _pkg in (
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.core.management.commands",
    "django.db.backends.sqlite3",
    "django.template.backends.django",
    "letters",
    "letters_project",
    "PIL",
):
    hiddenimports += collect_submodules(_pkg)

hiddenimports += [
    # Middleware/сервер подключаются по строке в settings.py/launcher.py,
    # обычный анализ импортов такие пути не видит.
    "whitenoise.middleware",
    "waitress",
    # tkinter используется в launcher.py для окна управления сервером.
    "tkinter",
]

datas = [
    # staticfiles/ - результат `manage.py collectstatic` (готовит build.bat
    # ПЕРЕД вызовом pyinstaller), содержит и нашу статику (static/css, js),
    # и статику встроенных приложений Django (например, стили /admin/).
    # Кладём это в бандл под именем "static", т.к. paths.resource_path("static")
    # и STATIC_ROOT в settings.py (frozen-ветка) ожидают именно это имя.
    ("staticfiles", "static"),
    ("templates", "templates"),
    # Портативный Tesseract (см. vendor/tesseract/README.md - сама сборка
    # заполняется вручную перед запуском build.bat).
    ("vendor/tesseract", "vendor/tesseract"),
]

if os.path.isfile("app.ico"):
    datas.append(("app.ico", "."))

a = Analysis(
    ["launcher.py"],
    pathex=[os.path.abspath(".")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Инструменты разработки/упаковки, случайно попавшие в окружение -
        # приложению самому они не нужны.
        "pip",
        "setuptools",
        "wheel",
        "pytest",
        "PyInstaller",
    ],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=BUILD_CONSOLE,
    icon="app.ico" if os.path.isfile("app.ico") else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=APP_NAME,
)
