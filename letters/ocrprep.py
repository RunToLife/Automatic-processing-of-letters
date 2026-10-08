"""Подготовка сканов через OCRmyPDF (часть связки Tesseract + OCRmyPDF).

OCRmyPDF запускается как отдельный процесс и делает с постраничными сканами то, что Tesseract сам не умеет:

* определяет ориентацию страницы (OSD) и разворачивает перевёрнутые / повёрнутые на 90° листы;
* выравнивает наклон скана по всему изображению (а не только в пределах ±4°);
* поднимает разрешение низкокачественных сканов до рабочего (OCR_DPI);
* при желании чистит изображение утилитой unpaper (`GENDALF_OCRMYPDF_CLEAN=1`).

Сам текст на этом шаге не распознаётся (`--tesseract-timeout 0`): геометрию слов, кегль, жирность и ячейки таблиц
по-прежнему собирает Tesseract напрямую в letters/converter.py — ему нужны точные рамки слов и отдельный
проход по ячейкам, которых в текстовом слое OCRmyPDF нет. Результат шага — тот же PDF, где у страниц-сканов
выровнено изображение; текстовые страницы остаются нетронутыми.
"""
import os
import shutil
import subprocess
import sys
import tempfile
from importlib.util import find_spec
from pathlib import Path

from django.conf import settings


class OcrPrepError(Exception):
    """OCRmyPDF не смог обработать файл (причина — в тексте исключения)."""


def available():
    """Установлен ли OCRmyPDF (пакет Python). Ghostscript и Tesseract ищет сам OCRmyPDF."""
    return find_spec('ocrmypdf') is not None


def _env():
    env = dict(os.environ)
    env['TESSDATA_PREFIX'] = str(settings.TESSDATA_DIR)
    env.setdefault('OMP_THREAD_LIMIT', '1')       # как и для прямых вызовов Tesseract
    if settings.TESSERACT_CMD:                    # OCRmyPDF ищет tesseract в PATH
        folder = str(Path(settings.TESSERACT_CMD).parent)
        env['PATH'] = folder + os.pathsep + env.get('PATH', '')
    return env


def _page_spec(pages):
    return ','.join(str(n) for n in sorted(pages))


def prepare(data, pages):
    """PDF (bytes) + номера страниц-сканов (с 1) -> PDF (bytes) с выровненными сканами.

    Остальные страницы OCRmyPDF копирует без изменений. Бросает OcrPrepError при любой неудаче.
    """
    if not pages:
        return data
    if not available():
        raise OcrPrepError('Пакет ocrmypdf не установлен.')
    jobs = max(1, min(4, os.cpu_count() or 1))
    with tempfile.TemporaryDirectory(prefix='gendalf-ocrmypdf-') as tmp:
        src, dst = os.path.join(tmp, 'in.pdf'), os.path.join(tmp, 'out.pdf')
        with open(src, 'wb') as f:
            f.write(data)
        cmd = [
            sys.executable, '-m', 'ocrmypdf', '--quiet',
            '--language', settings.OCR_LANGS,
            '--pages', _page_spec(pages),
            '--rotate-pages',
            '--skip-text',                  # страницы с настоящим текстом не трогаем
            '--tesseract-timeout', '0',     # распознавание — позже, в converter.py (см. docstring модуля)
            '--output-type', 'pdf',         # без конвертации в PDF/A: Ghostscript-проход лишь замедляет
            '--optimize', '0',
            '--jobs', str(jobs),
        ]
        if settings.OCRMYPDF_DESKEW:
            cmd.append('--deskew')
        if settings.OCRMYPDF_CLEAN:
            cmd.append('--clean')
        cmd += [src, dst]
        try:
            proc = subprocess.run(cmd, env=_env(), capture_output=True, text=True, errors='replace',
                                  timeout=settings.OCRMYPDF_TIMEOUT, cwd=tmp)
        except subprocess.TimeoutExpired as e:
            raise OcrPrepError(f'OCRmyPDF не уложился в {settings.OCRMYPDF_TIMEOUT} с.') from e
        except OSError as e:
            raise OcrPrepError(f'Не удалось запустить OCRmyPDF: {e}') from e
        if proc.returncode != 0 or not os.path.exists(dst):
            tail = (proc.stderr or proc.stdout or '').strip().splitlines()[-3:]
            raise OcrPrepError(f'OCRmyPDF завершился с кодом {proc.returncode}: ' + ' '.join(tail))
        with open(dst, 'rb') as f:
            return f.read()


def diagnostics():
    """Что есть в системе для OCRmyPDF: пригодится для сообщений и README."""
    return {
        'ocrmypdf': available(),
        'ghostscript': any(shutil.which(n) for n in ('gs', 'gswin64c', 'gswin32c')),
        'unpaper': bool(shutil.which('unpaper')),
    }
