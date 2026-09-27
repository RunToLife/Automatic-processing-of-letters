import os
import secrets

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
DB_PATH = os.path.join(INSTANCE_DIR, "letters.db")

UPLOAD_DIR = os.path.join(BASE_DIR, "storage", "uploads")

# Корневая папка, внутри которой пользователю разрешено выбирать
# место сохранения WORD-документов (защита от обхода каталогов).
# Можно переопределить переменной окружения SAVE_ROOT_DIR, например
# указав путь к сетевой шаре: SAVE_ROOT_DIR=//server/share
SAVE_ROOT_DIR = os.environ.get(
    "SAVE_ROOT_DIR", os.path.join(BASE_DIR, "storage", "shared")
)

SECRET_KEY_FILE = os.path.join(INSTANCE_DIR, "secret_key.txt")

MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100 MB на один PDF

OCR_LANGUAGES = os.environ.get("OCR_LANGUAGES", "rus+eng")
OCR_DPI = int(os.environ.get("OCR_DPI", "300"))

TESSERACT_CMD = os.environ.get("TESSERACT_CMD")  # напр. C:\Program Files\Tesseract-OCR\tesseract.exe


def get_secret_key() -> str:
    os.makedirs(INSTANCE_DIR, exist_ok=True)
    if os.path.exists(SECRET_KEY_FILE):
        with open(SECRET_KEY_FILE, "r", encoding="utf-8") as f:
            key = f.read().strip()
            if key:
                return key
    key = secrets.token_hex(32)
    with open(SECRET_KEY_FILE, "w", encoding="utf-8") as f:
        f.write(key)
    return key


def ensure_dirs():
    os.makedirs(INSTANCE_DIR, exist_ok=True)
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(SAVE_ROOT_DIR, exist_ok=True)
