import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

INSTANCE_DIR = BASE_DIR / "instance"
INSTANCE_DIR.mkdir(exist_ok=True)


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
        "DIRS": [BASE_DIR / "templates"],
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
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/upload/"
LOGOUT_REDIRECT_URL = "/login/"

# --------------------------------------------------------------- приложение

UPLOAD_DIR = BASE_DIR / "storage" / "uploads"
ARCHIVE_DIR = os.environ.get("ARCHIVE_DIR", str(BASE_DIR / "storage" / "archive"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
Path(ARCHIVE_DIR).mkdir(parents=True, exist_ok=True)

MAX_PDF_SIZE = 100 * 1024 * 1024  # 100 MB на один PDF
DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_PDF_SIZE
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

OCR_LANGUAGES = os.environ.get("OCR_LANGUAGES", "rus+eng")
OCR_DPI = int(os.environ.get("OCR_DPI", "300"))
TESSERACT_CMD = os.environ.get("TESSERACT_CMD")  # напр. C:\Program Files\Tesseract-OCR\tesseract.exe
