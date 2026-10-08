"""python manage.py check_ocr — проверка связки Tesseract + OCRmyPDF на этой машине."""
import glob
import io
import os
import shutil
import subprocess
import sys

import pymupdf
from django.conf import settings
from django.core.management.base import BaseCommand
from PIL import Image

from letters import ocrprep


def _find_tesseract():
    if settings.TESSERACT_CMD:
        return settings.TESSERACT_CMD
    return shutil.which('tesseract') or ''


def _find_ghostscript():
    for name in ('gs', 'gswin64c', 'gswin32c'):
        found = shutil.which(name)
        if found:
            return found
    for root in (os.environ.get('ProgramFiles', r'C:\Program Files'),
                 os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)')):
        hits = sorted(glob.glob(os.path.join(root, 'gs', 'gs*', 'bin', 'gswin*c.exe')))
        if hits:
            return hits[-1]
    return ''


def _first_line(cmd, env=None):
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, errors='replace', timeout=30, env=env)
    except (OSError, subprocess.TimeoutExpired) as e:
        return f'не запускается ({e})'
    return ((out.stdout or out.stderr).strip().splitlines() or [''])[0]


def _sample_scan():
    """Страница-«скан» (картинка без текстового слоя), повёрнутая боком: OCRmyPDF должен её развернуть."""
    src = pymupdf.open()
    page = src.new_page(width=595, height=842)
    for i in range(12):     # OSD нужен связный текст: из одной строки ориентацию он не определяет
        page.insert_text((60, 100 + i * 24), 'The quick brown fox jumps over the lazy dog, letter number %d.' % i,
                         fontname='tiro', fontsize=13)
    pix = page.get_pixmap(dpi=300, colorspace=pymupdf.csGRAY, alpha=False)
    img = Image.frombytes('L', (pix.width, pix.height), pix.samples).rotate(90, expand=True)
    buf = io.BytesIO()
    img.save(buf, 'PNG')
    out = pymupdf.open()
    p = out.new_page(width=842, height=595)
    p.insert_image(p.rect, stream=buf.getvalue())
    return out.tobytes()


class Command(BaseCommand):
    help = 'Проверяет Tesseract, языки, OCRmyPDF и Ghostscript и прогоняет пробный скан.'

    def handle(self, *args, **opts):
        bad = []

        def row(ok, title, detail='', required=True):
            mark = 'OK   ' if ok else ('ОШИБКА' if required else 'нет  ')
            self.stdout.write(f'[{mark}] {title}' + (f' — {detail}' if detail else ''))
            if not ok and required:
                bad.append(title)

        self.stdout.write(f'Python {sys.version.split()[0]}, tessdata: {settings.TESSDATA_DIR}')
        tess = _find_tesseract()
        env = dict(os.environ, TESSDATA_PREFIX=str(settings.TESSDATA_DIR))
        row(bool(tess), 'Tesseract', (_first_line([tess, '--version'], env) if tess else
                                      'не найден: установите (см. README.md) или задайте TESSERACT_CMD'))
        for lang in ('rus', 'eng', 'osd'):
            row((settings.TESSDATA_DIR / f'{lang}.traineddata').is_file(), f'tessdata/{lang}.traineddata',
                required=lang != 'osd')
        have_pkg = ocrprep.available()
        row(have_pkg, 'OCRmyPDF (пакет Python)', '' if have_pkg else 'не установлен: повернутые листы не исправляются',
            required=False)
        gs = _find_ghostscript()
        row(bool(gs), 'Ghostscript', gs or 'не найден: OCRmyPDF не сможет подготовить сканы', required=False)
        unp = shutil.which('unpaper')
        row(bool(unp), 'unpaper (только для GENDALF_OCRMYPDF_CLEAN=1)', unp or '', required=False)
        self.stdout.write(f'Режим OCRmyPDF: {settings.OCRMYPDF_MODE}')

        if have_pkg and gs and tess:
            try:
                out = ocrprep.prepare(_sample_scan(), [1])
                doc = pymupdf.open(stream=out, filetype='pdf')
                r = doc[0].rect
                ok = r.height > r.width     # лист лежал боком — после OCRmyPDF должен стоять вертикально
                row(ok, 'Пробный прогон OCRmyPDF (поворот страницы)',
                    '' if ok else 'страница не развёрнута — проверьте tessdata/osd.traineddata', required=False)
            except Exception as e:  # noqa: BLE001
                row(False, 'Пробный прогон OCRmyPDF', str(e), required=False)
        if bad:
            self.stdout.write(self.style.ERROR('Обязательное не готово: ' + ', '.join(bad)))
            sys.exit(1)
        self.stdout.write(self.style.SUCCESS('Готово: распознавание работает.'
                                             if gs and have_pkg else
                                             'Распознавание работает, но без OCRmyPDF (см. пометки выше).'))
