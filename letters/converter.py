"""Преобразование PDF (текстовых и сканов) в HTML для редактирования и в DOCX.

* Страницы с текстовым слоем разбираются напрямую через PyMuPDF
  (сохраняются абзацы, жирный/курсив, размеры шрифта, выравнивание, картинки).
* Страницы-сканы распознаются Tesseract OCR (rus+eng, 300 dpi, предобработка).
"""
import base64
import html
import io
import os
import statistics
from dataclasses import dataclass, field

import pymupdf as fitz
from bs4 import BeautifulSoup
from django.conf import settings
from docx import Document
from docx.shared import Cm, Pt
from htmldocx import HtmlToDocx
from PIL import Image, ImageOps

MIN_TEXT_CHARS = 25  # меньше символов на странице -> считаем страницу сканом


class ConversionError(Exception):
    pass


@dataclass
class ConversionResult:
    html: str
    pages: int
    ocr_pages: int = 0
    warnings: list = field(default_factory=list)


def _setup_tesseract():
    import pytesseract

    if settings.TESSERACT_CMD:
        pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
    os.environ['TESSDATA_PREFIX'] = str(settings.TESSDATA_DIR)
    return pytesseract


def _align(x0, x1, page_w, left_margin, right_margin):
    width = x1 - x0
    if width > 0.8 * (right_margin - left_margin):
        return ''
    center = (x0 + x1) / 2
    if abs(center - page_w / 2) < page_w * 0.05 and x0 > left_margin + page_w * 0.05:
        return 'center'
    if x1 > right_margin - page_w * 0.03 and x0 > page_w * 0.45:
        return 'right'
    return ''


def _p(text_html, align='', tag='p', extra=''):
    style = f' style="text-align:{align}"' if align else ''
    return f'<{tag}{style}>{text_html}</{tag}>'


def _native_page(page):
    d = page.get_text('dict')
    blocks = [b for b in d['blocks'] if b['type'] == 0]
    page_w = page.rect.width
    xs0 = [b['bbox'][0] for b in blocks] or [0]
    xs1 = [b['bbox'][2] for b in blocks] or [page_w]
    lm, rm = min(xs0), max(xs1)
    sizes = [s['size'] for b in blocks for l in b['lines'] for s in l['spans'] if s['text'].strip()]
    base = statistics.median(sizes) if sizes else 11
    out = []
    for b in d['blocks']:
        if b['type'] == 1 and b.get('image'):
            ext = b.get('ext', 'png')
            w = min(int(b['bbox'][2] - b['bbox'][0]), 600)
            data = base64.b64encode(b['image']).decode()
            out.append(f'<p><img src="data:image/{ext};base64,{data}" width="{w}"></p>')
            continue
        if b['type'] != 0:
            continue
        parts, bsize, bold_all = [], [], True
        for l in b['lines']:
            line = []
            for s in l['spans']:
                t = s['text']
                if not t.strip():
                    line.append(html.escape(t))
                    continue
                bold = bool(s['flags'] & 16) or 'bold' in s['font'].lower()
                ital = bool(s['flags'] & 2) or 'italic' in s['font'].lower()
                bold_all &= bold
                bsize.append(s['size'])
                seg = html.escape(t)
                if bold:
                    seg = f'<b>{seg}</b>'
                if ital:
                    seg = f'<i>{seg}</i>'
                line.append(seg)
            parts.append(''.join(line).strip())
        body = ' '.join(p for p in parts if p).replace('</b> <b>', ' ').replace('</i> <i>', ' ')
        if not body:
            continue
        size = statistics.mean(bsize) if bsize else base
        align = _align(b['bbox'][0], b['bbox'][2], page_w, lm, rm)
        if size >= base * 1.35 and len(body) < 200:
            out.append(_p(body, align, 'h2'))
        elif size >= base * 1.15 and bold_all and len(body) < 200:
            out.append(_p(body, align, 'h3'))
        else:
            out.append(_p(body, align))
    return out


def _prepare_for_ocr(img):
    img = ImageOps.grayscale(img)
    img = ImageOps.autocontrast(img, cutoff=1)
    return img


def _ocr_page(page, pytesseract):
    dpi = settings.OCR_DPI
    pix = page.get_pixmap(dpi=dpi, colorspace=fitz.csGRAY, alpha=False)
    img = Image.frombytes('L', (pix.width, pix.height), pix.samples)
    img = _prepare_for_ocr(img)
    try:
        data = pytesseract.image_to_data(
            img, lang=settings.OCR_LANGS, config='--oem 1 --psm 3',
            output_type=pytesseract.Output.DICT)
    except pytesseract.TesseractNotFoundError as e:
        raise ConversionError(
            'Не найден Tesseract OCR. Установите его (см. README.md) '
            'или задайте переменную TESSERACT_CMD.') from e
    except pytesseract.TesseractError as e:
        raise ConversionError(f'Ошибка распознавания: {e}') from e

    # слово -> строка -> абзац
    paras = {}
    for i, txt in enumerate(data['text']):
        if not txt.strip() or float(data['conf'][i]) < 0:
            continue
        key = (data['block_num'][i], data['par_num'][i])
        line = paras.setdefault(key, {}).setdefault(data['line_num'][i], [])
        line.append((data['left'][i], data['top'][i], data['width'][i], data['height'][i], txt))
    if not paras:
        return []

    heights = [w[3] for p in paras.values() for l in p.values() for w in l]
    base = statistics.median(heights)
    page_w = pix.width
    lm = min(w[0] for p in paras.values() for l in p.values() for w in l)
    rm = max(w[0] + w[2] for p in paras.values() for l in p.values() for w in l)
    out = []
    for key in sorted(paras, key=lambda k: min(w[1] for l in paras[k].values() for w in l)):
        lines = paras[key]
        words = [w for l in lines.values() for w in l]
        text = ' '.join(' '.join(w[4] for w in sorted(l)) for _, l in sorted(lines.items()))
        x0, x1 = min(w[0] for w in words), max(w[0] + w[2] for w in words)
        h = statistics.median(w[3] for w in words)
        align = _align(x0, x1, page_w, lm, rm)
        body = html.escape(text)
        if h >= base * 1.4 and len(text) < 200:
            out.append(_p(f'<b>{body}</b>', align, 'h2'))
        else:
            out.append(_p(body, align))
    return out


def convert_pdf(path) -> ConversionResult:
    try:
        doc = fitz.open(path)
    except Exception as e:  # noqa: BLE001
        raise ConversionError(f'Не удалось открыть PDF: {e}') from e
    if doc.needs_pass:
        raise ConversionError('PDF защищён паролем.')
    result = ConversionResult(html='', pages=doc.page_count)
    chunks = []
    pytesseract = None
    for n, page in enumerate(doc, start=1):
        native = _native_page(page) if len(page.get_text().strip()) >= MIN_TEXT_CHARS else []
        if native:
            items = native
        else:
            if pytesseract is None:
                pytesseract = _setup_tesseract()
            items = _ocr_page(page, pytesseract)
            result.ocr_pages += 1
            if not items:
                result.warnings.append(f'Страница {n}: текст не распознан.')
        if n > 1:
            chunks.append('<hr>')
        chunks.extend(items)
    doc.close()
    result.html = '\n'.join(chunks)
    return result


def html_to_docx(content_html: str) -> bytes:
    """Собирает DOCX из отредактированного пользователем HTML."""
    import re

    from docx.enum.text import WD_BREAK

    soup = BeautifulSoup(content_html, 'html.parser')
    for t in soup(['script', 'style', 'iframe', 'object']):
        t.decompose()
    for div in soup.find_all('div'):
        div.name = 'p'

    document = Document()
    sec = document.sections[0]
    sec.left_margin = sec.right_margin = Cm(2)
    sec.top_margin = sec.bottom_margin = Cm(2)
    style = document.styles['Normal']
    style.font.name = 'Times New Roman'
    style.font.size = Pt(12)

    parser = HtmlToDocx()
    pages = [x for x in re.split(r'<hr[^>]*>', str(soup)) if x.strip()] or ['<p></p>']
    for n, chunk in enumerate(pages):
        if n:
            document.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        parser.add_html_to_document(chunk, document)

    buf = io.BytesIO()
    document.save(buf)
    return buf.getvalue()
