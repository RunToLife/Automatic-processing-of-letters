import os
import secrets
import sys
from pathlib import Path

# Корень репозитория (для запуска из исходников) - нужен, чтобы найти
# модуль paths.py, лежащий рядом с manage.py. В собранном приложении
# запускающий скрипт (launcher.py) находится там же, где и paths.py,
# и Python сам добавляет его каталог в sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import paths  # noqa: E402  (см. комментарий выше про sys.path)

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = paths.user_data_dir()
INSTANCE_DIR = DATA_DIR / "instance"
INSTANCE_DIR.mkdir(parents=True, exist_ok=True)


def _get_secret_key() -> str:
    """Хранит секретный ключ Django в instance/secret_key.txt, создавая его
    при первом запуске (аналогично тому, как в SQLite хранятся пользователи)."""
    key_file = INSTANCE_DIR / "secret_key.txt"
    if key_file.exists():
        key = key_file.read_text(encoding="utf-8").strip()
        if key:
            return key
    key = secrets.token_hex(32)
    key_file.write_text(key, encoding="utf-8")
    return key


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY") or _get_secret_key()

DEBUG = os.environ.get("DJANGO_DEBUG", "false").lower() == "true"

# Приложение разворачивается в локальной сети под разными адресами
# (localhost, IP сервера, доменное имя) - принимаем любой хост.
ALLOWED_HOSTS = ["*"]
CSRF_TRUSTED_ORIGINS = os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if os.environ.get("CSRF_TRUSTED_ORIGINS") else []

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "letters.apps.LettersConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
]

# В собранном приложении рядом нет ни nginx, ни gunicorn - статику
# (css/js) должен отдавать сам процесс. WhiteNoise делает это без
# отдельного шага collectstatic (см. STATIC_ROOT ниже) и не влияет на
# запуск из исходников, где статику по-прежнему отдаёт runserver сам.
if paths.is_frozen():
    MIDDLEWARE.append("whitenoise.middleware.WhiteNoiseMiddleware")

MIDDLEWARE += [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "letters_project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [paths.resource_path("templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "letters_project.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": INSTANCE_DIR / "letters.db",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
if paths.is_frozen():
    # WhiteNoiseMiddleware сам индексирует все файлы под STATIC_ROOT при
    # старте - отдельный collectstatic на машине пользователя не нужен.
    # STATICFILES_DIRS оставляем пустым: Django ругается (staticfiles.E002),
    # если тот же путь одновременно указан и там, и в STATIC_ROOT, а finders
    # (для которых нужен STATICFILES_DIRS) в проде и не используются.
    STATICFILES_DIRS = []
    STATIC_ROOT = paths.resource_path("static")
else:
    STATICFILES_DIRS = [paths.resource_path("static")]
    STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/upload/"
LOGOUT_REDIRECT_URL = "/login/"

# --------------------------------------------------------------- приложение
#
# Изменяемые данные (БД, загрузки, архив, логи) лежат в user_data_dir():
# в dev-режиме это корень репозитория (как и раньше), в собранном
# приложении - папка `data` рядом с exe (или %LOCALAPPDATA%\Гендальф).

UPLOAD_DIR = DATA_DIR / "storage" / "uploads"
ARCHIVE_DIR = os.environ.get("ARCHIVE_DIR", str(DATA_DIR / "storage" / "archive"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
Path(ARCHIVE_DIR).mkdir(parents=True, exist_ok=True)

LOGS_DIR = DATA_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

MAX_PDF_SIZE = 100 * 1024 * 1024  # 100 MB на один PDF
DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_PDF_SIZE
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

OCR_LANGUAGES = os.environ.get("OCR_LANGUAGES", "rus+eng")
OCR_DPI = int(os.environ.get("OCR_DPI", "300"))

# Tesseract: если TESSERACT_CMD задан явно - используем его (и в dev, и в
# сборке). Иначе, если рядом лежит vendor/tesseract (в собранном
# приложении - всегда; при запуске из исходников - только если кто-то
# сам положил туда бинарник для локальной проверки), используем его.
# Иначе (обычный dev-режим) - как раньше, pytesseract сам найдёт
# "tesseract" в системном PATH.
_VENDOR_TESSERACT_DIR = paths.resource_path("vendor/tesseract")
_VENDOR_TESSERACT_EXE = _VENDOR_TESSERACT_DIR / ("tesseract.exe" if os.name == "nt" else "tesseract")
_VENDOR_TESSDATA_DIR = _VENDOR_TESSERACT_DIR / "tessdata"

if os.environ.get("TESSERACT_CMD"):
    TESSERACT_CMD = os.environ["TESSERACT_CMD"]
elif _VENDOR_TESSERACT_EXE.is_file():
    TESSERACT_CMD = str(_VENDOR_TESSERACT_EXE)
else:
    TESSERACT_CMD = None  # напр. C:\Program Files\Tesseract-OCR\tesseract.exe

TESSDATA_PREFIX = str(_VENDOR_TESSDATA_DIR) if _VENDOR_TESSDATA_DIR.is_dir() else None

# ------------------------------------------------------------- логирование
#
# Пишем в файл всегда (а не только в консоль), чтобы ошибки не терялись
# в собранном приложении, запущенном без консоли (console=False).

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{asctime} {levelname} {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOGS_DIR / "gendalf.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "encoding": "utf-8",
            "formatter": "verbose",
            "level": "INFO",
        },
    },
    "root": {
        "handlers": ["file"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
