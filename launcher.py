"""Точка входа для собранного приложения "Гендальф" (PyInstaller --onedir).

Поднимает Django-приложение поверх встроенного production-сервера
(waitress, привязан только к 127.0.0.1), автоматически применяет
миграции БД, открывает браузер и показывает небольшое окно с кнопками
"Открыть в браузере" и "Остановить и выйти" - без консоли (см.
console=False в app.spec), поэтому без такого окна процесс было бы
нечем штатно остановить.

Режим отладки: переменная окружения GENDALF_DEBUG=1 включает подробное
логирование (DEBUG вместо INFO) и, на Windows, консольное окно поверх
уже собранного --noconsole exe (через AllocConsole) - пересобирать exe
для отладки не нужно.

Этот же скрипт можно запускать и из исходников (`python launcher.py`) -
удобно для проверки frozen-подобного поведения (миграции, порт, окно)
без сборки exe. Обычный dev-сценарий (`python manage.py runserver`)
при этом не меняется и этим скриптом не затрагивается.
"""
import logging
import os
import socket
import sys
import threading
import traceback
import webbrowser
from logging.handlers import RotatingFileHandler

import paths

APP_NAME = paths.APP_NAME
HOST = "127.0.0.1"
PREFERRED_PORT = 5000
PORT_SCAN_ATTEMPTS = 50

DEBUG_MODE = os.environ.get("GENDALF_DEBUG") == "1"

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def _allocate_debug_console() -> None:
    """Показывает консольное окно поверх --noconsole exe (только для
    отладки, только на Windows, только если консоли ещё нет)."""
    if os.name != "nt":
        return
    try:
        import ctypes

        if ctypes.windll.kernel32.GetConsoleWindow():
            return  # консоль уже есть (например, запущено из cmd.exe)
        if ctypes.windll.kernel32.AllocConsole():
            sys.stdout = open("CONOUT$", "w", encoding="utf-8", buffering=1)
            sys.stderr = open("CONOUT$", "w", encoding="utf-8", buffering=1)
            sys.stdin = open("CONIN$", "r", encoding="utf-8")
    except Exception:
        pass  # не получилось - работаем без консоли, в файл лог всё равно пишется


def _setup_logging() -> logging.Logger:
    """Логирование, работающее ещё до инициализации Django - чтобы не
    потерять ошибки старта в --noconsole сборке."""
    logs_dir = paths.user_data_dir() / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("gendalf.launcher")
    logger.setLevel(logging.DEBUG if DEBUG_MODE else logging.INFO)
    # Без этого сообщения дублируются в лог-файле: после django.setup()
    # применяется наш же LOGGING из settings.py, который вешает свой
    # обработчик на root-логгер, и записи gendalf.launcher (propagate=True
    # по умолчанию) доходили бы туда ВТОРОЙ раз.
    logger.propagate = False

    file_handler = RotatingFileHandler(
        logs_dir / "gendalf.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(file_handler)

    if DEBUG_MODE:
        _allocate_debug_console()
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(console_handler)

    def _log_unhandled(exc_type, exc_value, exc_tb):
        logger.critical(
            "Необработанное исключение:\n%s",
            "".join(traceback.format_exception(exc_type, exc_value, exc_tb)),
        )
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = _log_unhandled
    return logger


def _create_server(application, logger: logging.Logger):
    """Пытается поднять waitress на PREFERRED_PORT, а если он занят -
    на следующих портах подряд. Регистрация порта происходит атомарно
    внутри create_server (см. waitress.server.TcpWSGIServer.bind) -
    отдельная проверка "свободен ли порт" заранее не нужна и была бы
    гонкой (порт может быть занят другим процессом между проверкой и
    реальным bind)."""
    import waitress

    last_error = None
    for port in range(PREFERRED_PORT, PREFERRED_PORT + PORT_SCAN_ATTEMPTS):
        try:
            server = waitress.create_server(application, host=HOST, port=port)
            return server, port
        except OSError as exc:
            last_error = exc
            logger.info("Порт %s занят (%s), пробуем следующий", port, exc)
    raise RuntimeError(
        f"Не удалось найти свободный порт в диапазоне "
        f"{PREFERRED_PORT}-{PREFERRED_PORT + PORT_SCAN_ATTEMPTS - 1}"
    ) from last_error


def _run_control_window(url: str) -> None:
    """Небольшое окно без консоли: статус + кнопки "Открыть в браузере" и
    "Остановить и выйти". Без него собранный exe (console=False) было бы
    нечем штатно завершить."""
    import tkinter as tk
    from tkinter import ttk

    root = tk.Tk()
    root.title(APP_NAME)
    root.geometry("400x170")
    root.resizable(False, False)

    icon_path = paths.resource_path("app.ico")
    try:
        if icon_path.is_file():
            root.iconbitmap(str(icon_path))
    except Exception:
        pass  # иконка не критична для работы приложения

    frame = ttk.Frame(root, padding=16)
    frame.pack(fill="both", expand=True)

    ttk.Label(frame, text=APP_NAME, font=("Segoe UI", 14, "bold")).pack(anchor="w")
    ttk.Label(frame, text="Сервер запущен по адресу:").pack(anchor="w", pady=(8, 0))
    ttk.Label(frame, text=url, font=("Consolas", 10, "bold")).pack(anchor="w")
    ttk.Label(
        frame,
        text="Не закрывайте это окно, пока работаете с приложением.",
        foreground="#666666",
    ).pack(anchor="w", pady=(8, 12))

    def open_browser() -> None:
        webbrowser.open(url)

    def stop_and_exit() -> None:
        root.destroy()

    button_row = ttk.Frame(frame)
    button_row.pack(fill="x")
    ttk.Button(button_row, text="Открыть в браузере", command=open_browser).pack(side="left")
    ttk.Button(button_row, text="Остановить и выйти", command=stop_and_exit).pack(side="right")

    root.protocol("WM_DELETE_WINDOW", stop_and_exit)
    root.mainloop()


def main() -> None:
    logger = _setup_logging()
    logger.info("Запуск %s (frozen=%s, debug=%s)", APP_NAME, paths.is_frozen(), DEBUG_MODE)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "letters_project.settings")
    if DEBUG_MODE:
        os.environ["DJANGO_DEBUG"] = "true"

    try:
        import django

        django.setup()

        from django.core.management import call_command

        logger.info("Применение миграций базы данных...")
        call_command("migrate", interactive=False, verbosity=1 if DEBUG_MODE else 0)
        logger.info("Миграции применены.")

        from letters_project.wsgi import application

        server, port = _create_server(application, logger)
        url = f"http://{HOST}:{port}/"
        logger.info("Сервер слушает %s", url)
    except Exception:
        logger.critical("Не удалось запустить %s", APP_NAME, exc_info=True)
        raise

    server_thread = threading.Thread(target=server.run, name="gendalf-server", daemon=True)
    server_thread.start()

    webbrowser.open(url)

    try:
        _run_control_window(url)
    finally:
        logger.info("Остановка сервера...")
        server.close()
        server_thread.join(timeout=5)
        logger.info("%s остановлен.", APP_NAME)


if __name__ == "__main__":
    main()
