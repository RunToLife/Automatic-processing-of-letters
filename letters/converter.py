"""Преобразование PDF (текстовых и сканов) в HTML для редактирования и в DOCX.

Главная цель — Word, в котором всё лежит там же, где в оригинале: отступы, выравнивание, колонки
(реквизиты слева / адресат справа), интервалы, таблицы (с линиями, только с горизонтальными линиями и
без линий) и подписи. Геометрию собирают две ветки:

* страницы с текстовым слоем — PyMuPDF (слова с шрифтом и размером, линии таблиц из векторной графики);
* страницы-сканы — связка OCRmyPDF + Tesseract: OCRmyPDF (letters/ocrprep.py) разворачивает и выравнивает
  изображение скана, затем Tesseract OCR (rus+eng, 300 dpi) распознаёт слова; находим линии таблиц и стираем
  их перед распознаванием. Без OCRmyPDF работает встроенное выравнивание наклона.

Дальше обе ветки отдают элементы страницы (letters/layout.py), которые превращаются в HTML с точной
вёрсткой; DOCX собирается из этого HTML (letters/docxbuild.py).
"""
import base64
import os
import statistics
from dataclasses import dataclass, field

import numpy as np
import pymupdf as fitz
from django.conf import settings
from PIL import Image

from . import fontmetrics as fm
from . import layout as L
from . import ocrprep

MIN_TEXT_CHARS = 25  # меньше символов на странице -> считаем страницу сканом
SEG_GAP = 1.5        # разрыв в строке шире 1.5 кегля — новый сегмент (колонка)


class ConversionError(Exception):
    pass


@dataclass
class ConversionResult:
    html: str
    pages: int
    ocr_pages: int = 0
    ocrmypdf: bool = False   # сканы подготовлены OCRmyPDF (поворот, наклон, разрешение)
    warnings: list = field(default_factory=list)
    meta: dict = field(default_factory=dict)


def _setup_tesseract():
    import pytesseract

    if settings.TESSERACT_CMD:
        pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
    os.environ['TESSDATA_PREFIX'] = str(settings.TESSDATA_DIR)
    # Один поток OpenMP на процесс Tesseract: иначе параллельные запуски (ячейки таблиц, несколько
    # пользователей) душат друг друга и работают в десятки раз медленнее.
    os.environ.setdefault('OMP_THREAD_LIMIT', '1')
    return pytesseract


# ---------------------------------------------------------------- общее ------
def _edges(values, tol=3.0):
    """Кластеризует координаты границ ячеек -> отсортированные уникальные значения."""
    out = []
    for v in sorted(values):
        if out and v - out[-1][-1] <= tol:
            out[-1].append(v)
        else:
            out.append([v])
    return [sum(g) / len(g) for g in out]


def _nearest(edges, v):
    return min(range(len(edges)), key=lambda i: abs(edges[i] - v))


def segs_from_words(words):
    """Слова -> сегменты строк: кластер по базовой линии, разрыв по широким пробелам."""
    if not words:
        return []
    words = sorted(words, key=lambda w: (w.base, w.x0))
    lines = []
    for w in words:
        if lines and abs(lines[-1][0] - w.base) <= max(1.5, .4 * w.size):
            lines[-1][1].append(w)
            lines[-1][0] = statistics.mean(x.base for x in lines[-1][1])
        else:
            lines.append([w.base, [w]])
    segs = []
    for _, ws in lines:
        ws.sort(key=lambda w: w.x0)
        cur = [ws[0]]
        for a, b in zip(ws, ws[1:]):
            if b.x0 - a.x1 > SEG_GAP * max(a.size, b.size):
                segs.append(L.Seg(cur, statistics.median(x.base for x in cur)))
                cur = [b]
            else:
                cur.append(b)
        segs.append(L.Seg(cur, statistics.median(x.base for x in cur)))
    return segs


def _harmonize(segs):
    """Внутри одной ячейки кегль и жирность единые (на сканах оценка по коротким словам «плавает»)."""
    ws = [w for s in segs for w in s.words]
    if len(ws) < 2:
        return
    size = statistics.median(w.size for w in ws)
    chars = sum(len(w.text) for w in ws) or 1
    bold = sum(len(w.text) for w in ws if w.bold) / chars >= .5
    for w in ws:
        w.size, w.bold = size, bold


def build_table(cell_rects, kind, words, tol=2.5):
    """Прямоугольники ячеек (pt) + слова -> L.Table с rowspan/colspan и текстом в ячейках."""
    xs = _edges([c[0] for c in cell_rects] + [c[2] for c in cell_rects], tol)
    ys = _edges([c[1] for c in cell_rects] + [c[3] for c in cell_rects], tol)
    cells, occupied = [], set()
    cand = []
    for x0, y0, x1, y1 in cell_rects:
        c0, c1 = _nearest(xs, x0), _nearest(xs, x1)
        r0, r1 = _nearest(ys, y0), _nearest(ys, y1)
        if c1 <= c0 or r1 <= r0:
            continue
        cand.append((r0, c0, r1, c1))
    # перекрывающиеся ячейки (сбои разбора линий) отбрасываем: при конфликте выигрывает меньшая
    for r0, c0, r1, c1 in sorted(cand, key=lambda k: ((k[2] - k[0]) * (k[3] - k[1]), k[0], k[1])):
        spots = {(r, c) for r in range(r0, r1) for c in range(c0, c1)}
        if spots & occupied:
            continue
        occupied |= spots
        cells.append(L.Cell(r0, c0, r1 - 1, c1 - 1, (xs[c0], ys[r0], xs[c1], ys[r1])))
    taken = set()
    for ci, c in enumerate(cells):
        inside = []
        for wi, w in enumerate(words):
            cx, cy = (w.x0 + w.x1) / 2, (w.y0 + w.y1) / 2
            if c.bbox[0] - 1 <= cx <= c.bbox[2] + 1 and c.bbox[1] - 1 <= cy <= c.bbox[3] + 1:
                inside.append(w)
                taken.add(wi)
        c.segs = segs_from_words(inside)
        _harmonize(c.segs)
    sizes = [w.size for w in words] or [12.0]
    return L.Table(bbox=(xs[0], ys[0], xs[-1], ys[-1]), xs=xs, ys=ys, cells=cells, kind=kind,
                   base=statistics.median(sizes)), taken


def _strips(words, x0, x1, vmin):
    """Свободные вертикальные полосы между словами -> границы колонок [x0, ..., x1]."""
    iv = sorted((w.x0, w.x1) for w in words)
    merged = []
    for a, b in iv:
        if merged and a <= merged[-1][1] + 0.01:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    cuts = [(merged[i][1] + merged[i + 1][0]) / 2 for i in range(len(merged) - 1)
            if merged[i + 1][0] - merged[i][1] >= vmin]
    return [x0] + cuts + [x1]


def _merge_segs(segs, tol=1.6, gap=6.0):
    """[(a0, a1, pos)] -> склеенные коллинеарные отрезки (куски одной линии)."""
    out = []
    for a0, a1, pos in sorted(segs, key=lambda s: (s[2], s[0])):
        for m in out:
            if abs(m[2] - pos) <= tol and a0 <= m[1] + gap and a1 >= m[0] - gap:
                m[0], m[1] = min(m[0], a0), max(m[1], a1)
                break
        else:
            out.append([a0, a1, pos])
    return out


def _covers(segs, pos, a0, a1, tol=2.5, frac=.6):
    """Есть ли линия на позиции pos, покрывающая не менее frac отрезка [a0, a1]."""
    length = a1 - a0
    if length <= 0:
        return False
    cov = 0.0
    for s0, s1, sp in segs:
        if abs(sp - pos) <= tol:
            cov += max(0.0, min(s1, a1) - max(s0, a0))
    return cov >= frac * length


def line_support(table, H, V):
    """Доля сторон ячеек, на которых есть настоящая линия (не граница заливки)."""
    tot = ok = 0
    for c in table.cells:
        x0, y0, x1, y1 = c.bbox
        for hit in (_covers(H, y0, x0, x1), _covers(H, y1, x0, x1), _covers(V, x0, y0, y1), _covers(V, x1, y0, y1)):
            tot += 1
            ok += bool(hit)
    return ok / tot if tot else 0.0


def segment_tables(hs, vs, words, taken_boxes, page_w):
    """Таблицы по линиям, которых не хватает на полную сетку: рамка, только горизонтали, частичные линии.

    hs: [(x0, x1, y)], vs: [(y0, y1, x)] в pt. Колонки берутся из вертикальных линий, а если их нет — из пустых
    полос между словами. У каждой ячейки запоминаем, с каких сторон у неё реально есть линия.
    Возвращает ([L.Table], [L.Rule]) — Rule для линий, не ставших частью таблицы.
    """
    def inside(x0, x1, y0, y1, t):
        return t[0] - 3 <= x0 and x1 <= t[2] + 3 and t[1] - 3 <= y0 and y1 <= t[3] + 3

    H = _merge_segs([h for h in hs if not any(inside(h[0], h[1], h[2], h[2], t) for t in taken_boxes)])
    V = _merge_segs([v for v in vs if not any(inside(v[2], v[2], v[0], v[1], t) for t in taken_boxes)])
    H.sort(key=lambda h: h[2])
    groups = []
    for h in H:
        for g in groups:
            last = g[-1]
            ov = min(last[1], h[1]) - max(last[0], h[0])
            if ov >= .7 * min(last[1] - last[0], h[1] - h[0]) and 0 < h[2] - last[2] <= 260:
                g.append(h)
                break
        else:
            groups.append([h])
    tables, used = [], set()
    for g in groups:
        x0, x1 = min(h[0] for h in g), max(h[1] for h in g)
        ys = _edges([h[2] for h in g], 2.0)
        top, bot = ys[0], ys[-1]
        if len(ys) < 2 or bot - top < 14 or x1 - x0 < .25 * page_w:
            continue
        frame = (_covers(V, x0, top, bot, 3.0, .7) and _covers(V, x1, top, bot, 3.0, .7))
        if len(ys) < 3 and not frame:
            continue
        region = [w for w in words if x0 - 2 <= (w.x0 + w.x1) / 2 <= x1 + 2 and top - 1 <= (w.y0 + w.y1) / 2 <= bot + 1]
        if len(region) < 3:
            continue
        vin = [v for v in V if x0 + 4 < v[2] < x1 - 4 and min(v[1], bot) - max(v[0], top) >= .3 * (bot - top)]
        lined = bool(vin)
        if lined:
            cols = [x0] + _edges([v[2] for v in vin], 3.0) + [x1]
        else:
            size = statistics.median(w.size for w in region)
            cols = _strips(region, x0, x1, max(.9 * size, 8))
            if len(cols) < 3 and not frame:
                continue
        if len(cols) < 2:
            continue
        rows = [ys[i] for i in range(len(ys)) if i == 0 or ys[i] - ys[i - 1] >= 5]
        if len(rows) < 2:
            continue
        # ячейки сетки; при реальных вертикальных линиях склеиваем через отсутствующие границы (colspan/rowspan)
        nr, nc = len(rows) - 1, len(cols) - 1
        done = [[False] * nc for _ in range(nr)]
        rects = []
        for i in range(nr):
            for j in range(nc):
                if done[i][j]:
                    continue
                j2, i2 = j, i
                if lined:
                    while j2 + 1 < nc and not _covers(V, cols[j2 + 1], rows[i] + 2, rows[i + 1] - 2, 3.0, .5):
                        j2 += 1
                    while i2 + 1 < nr and not _covers(H, rows[i2 + 1], cols[j] + 2, cols[j2 + 1] - 2, 3.0, .5):
                        i2 += 1
                for a in range(i, i2 + 1):
                    for b in range(j, j2 + 1):
                        done[a][b] = True
                rects.append((cols[j], rows[i], cols[j2 + 1], rows[i2 + 1]))
        if len(rects) < 2:
            continue
        t, _ = build_table(rects, 'custom', region)
        for c in t.cells:
            cx0, cy0, cx1, cy1 = c.bbox
            c.borders = (_covers(H, cy0, cx0, cx1), _covers(V, cx1, cy0, cy1),
                         _covers(H, cy1, cx0, cx1), _covers(V, cx0, cy0, cy1))
        if all(all(c.borders) for c in t.cells):
            t.kind = 'grid'
        tables.append(t)
        used.update(id(h) for h in g)
    rules = [L.Rule(h[0], h[1], h[2]) for h in H if id(h) not in used and h[1] - h[0] >= 40]
    return tables, rules


# ------------------------------------------------------- текстовые страницы ---
def _font_class(name):
    n = (name or '').lower()
    if any(k in n for k in ('courier', 'mono', 'consol')):
        return 'mono'
    if any(k in n for k in ('arial', 'helvet', 'sans', 'calibri', 'verdana', 'tahoma', 'segoe', 'roboto', 'open', 'lato')):
        return 'sans'
    return 'serif'


def _native_words(page):
    """Слова страницы с шрифтом/размером/базовой линией (в pt)."""
    words = []
    raw = page.get_text('rawdict')
    for blk in raw['blocks']:
        if blk['type'] != 0:
            continue
        for line in blk['lines']:
            for sp in line['spans']:
                fname = sp['font']
                bold = bool(sp['flags'] & 16) or any(k in fname.lower() for k in ('bold', 'black', 'heavy', 'semibold'))
                ital = bool(sp['flags'] & 2) or any(k in fname.lower() for k in ('italic', 'oblique'))
                size = round(sp['size'] * 2) / 2
                base = sp['origin'][1]
                cur = []

                def flush():
                    if cur:
                        xs0 = min(c['bbox'][0] for c in cur)
                        xs1 = max(c['bbox'][2] for c in cur)
                        words.append(L.Word(xs0, sp['bbox'][1], xs1, sp['bbox'][3], ''.join(c['c'] for c in cur),
                                            bold, ital, size, _font_class(fname), base))
                        cur.clear()

                for ch in sp['chars']:
                    if ch['c'].isspace() or ch['c'] == '\xa0':
                        flush()
                    else:
                        cur.append(ch)
                flush()
    return words


def _hex(c):
    return '#%02x%02x%02x' % tuple(int(round(v * 255)) for v in c[:3])


def _native_drawings(page):
    """Линии и заливки из векторной графики: ([(x0,x1,y)], [(y0,y1,x)], [(x0,y0,x1,y1,'#rrggbb')])."""
    hs, vs, fills = [], [], []
    try:
        drawings = page.get_drawings()
    except Exception:  # noqa: BLE001
        return hs, vs, fills
    for d in drawings:
        fc = d.get('fill')
        if fc and len(fc) >= 3 and min(fc[:3]) < .97:      # не белая заливка
            for it in d['items']:
                if it[0] == 're' and it[1].width > 8 and it[1].height > 6:
                    r = it[1]
                    fills.append((r.x0, r.y0, r.x1, r.y1, _hex(fc)))
        stroked = d.get('color') is not None and (d.get('width') or 0) > 0
        for it in d['items']:
            if it[0] == 'l':
                (ax, ay), (bx, by) = it[1], it[2]
                if abs(ay - by) <= .8 and abs(ax - bx) >= 8 and stroked:
                    hs.append((min(ax, bx), max(ax, bx), (ay + by) / 2))
                elif abs(ax - bx) <= .8 and abs(ay - by) >= 8 and stroked:
                    vs.append((min(ay, by), max(ay, by), (ax + bx) / 2))
            elif it[0] == 're':
                r = it[1]
                if r.height <= 2.5 and r.width >= 15:
                    hs.append((r.x0, r.x1, (r.y0 + r.y1) / 2))
                elif r.width <= 2.5 and r.height >= 15:
                    vs.append((r.y0, r.y1, (r.x0 + r.x1) / 2))
                elif stroked and r.width >= 15 and r.height >= 8:
                    hs += [(r.x0, r.x1, r.y0), (r.x0, r.x1, r.y1)]
                    vs += [(r.y0, r.y1, r.x0), (r.y0, r.y1, r.x1)]
    return hs, vs, fills


def _native_page(page):
    pw, ph = page.rect.width, page.rect.height
    words = _native_words(page)
    tables, taken_words, boxes = [], set(), []
    hs_all, vs_all, fills_all = _native_drawings(page)
    hs_all, vs_all = _merge_segs(hs_all), _merge_segs(vs_all)
    try:
        found = page.find_tables().tables
    except Exception:  # noqa: BLE001
        found = []
    for t in found:
        rects = [tuple(c) for c in t.cells if c]
        if len(rects) < 2 or t.col_count < 2:
            continue
        bb = t.bbox
        if (bb[2] - bb[0]) * (bb[3] - bb[1]) > .85 * pw * ph:
            continue
        tb, taken = build_table(rects, 'grid', words)
        # find_tables принимает за границы и края цветных заливок; настоящая таблица обязана быть обведена линиями
        if line_support(tb, hs_all, vs_all) < .6:
            continue
        tables.append(tb)
        boxes.append(tb.bbox)
        taken_words |= {id(words[i]) for i in taken}
    hs, vs, fills = hs_all, vs_all, fills_all
    rtabs, rules = segment_tables(hs, vs, [w for w in words if id(w) not in taken_words], boxes, pw)
    for t in rtabs:
        tables.append(t)
        boxes.append(t.bbox)
        for c in t.cells:
            for s in c.segs:
                taken_words |= {id(w) for w in s.words}
    for t in tables:
        L.apply_fills(t, fills)
    free = [w for w in words if id(w) not in taken_words and
            not any(b[0] - 1 <= (w.x0 + w.x1) / 2 <= b[2] + 1 and b[1] - 1 <= (w.y0 + w.y1) / 2 <= b[3] + 1 for b in boxes)]
    elems = list(tables) + segs_from_words(free)
    d = page.get_text('dict')
    for b in d['blocks']:
        if b['type'] == 1 and b.get('image'):
            x0, y0, x1, y1 = b['bbox']
            if (x1 - x0) * (y1 - y0) > .5 * pw * ph or (x1 - x0) < 6 or (y1 - y0) < 6:
                continue
            elems.append(L.Img(x0, y0, x1, y1, base64.b64encode(b['image']).decode(), b.get('ext', 'png')))
    return L.Page(pw, ph, elems, rules, fills)


def _runs_mask(b, k, axis):
    """Пиксели, входящие в непрерывные отрезки True длиной >= k (axis=1 — по строкам)."""
    if axis == 0:
        return _runs_mask(b.T, k, 1).T
    h, w = b.shape
    if w < k:
        return np.zeros_like(b)
    c = np.zeros((h, w + 1), dtype=np.int32)
    np.cumsum(b, axis=1, out=c[:, 1:])
    start = (c[:, k:] - c[:, :-k]) == k          # окно из k подряд True, начиная с позиции i
    diff = np.zeros((h, w + 1), dtype=np.int8)
    diff[:, :w - k + 1] += start
    diff[:, k:] -= start
    return np.cumsum(diff, axis=1)[:, :w] > 0


def _dilate(b, r):
    out = b.copy()
    for d in range(1, r + 1):
        for ax in (0, 1):
            out |= np.roll(b, d, axis=ax)
            out |= np.roll(b, -d, axis=ax)
    return out


def _cluster_idx(idx):
    groups, cur = [], []
    for i in idx:
        if cur and i - cur[-1] > 2:
            groups.append(cur)
            cur = []
        cur.append(int(i))
    if cur:
        groups.append(cur)
    return [(g[0] + g[-1]) / 2 for g in groups]


def _components(mask_small):
    pts = {tuple(p) for p in np.argwhere(mask_small)}
    seen, comps = set(), []
    for p in pts:
        if p in seen:
            continue
        stack, ys, xs = [p], [], []
        seen.add(p)
        while stack:
            y, x = stack.pop()
            ys.append(y)
            xs.append(x)
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    q = (y + dy, x + dx)
                    if q in pts and q not in seen:
                        seen.add(q)
                        stack.append(q)
        comps.append((min(xs), min(ys), max(xs), max(ys)))
    return comps


def detect_scan_tables(arr, dpi):
    """Ищет таблицы с линиями на скане. arr — numpy uint8 (оттенки серого).

    Возвращает (tables, line_mask, hmask, vmask), tables = [{'bbox': (x0,y0,x1,y1), 'cells': [(x0,y0,x1,y1)]}].
    """
    dark = arr < 200
    k = max(int(dpi * 0.2), 20)
    # линия может «гулять» на пиксель после выравнивания наклона: утолщаем поперёк линии (но не вдоль —
    # иначе буквы одной строки склеятся в «горизонтальную линию»)
    dh = dark | np.roll(dark, 1, axis=0) | np.roll(dark, -1, axis=0)
    dv = dark | np.roll(dark, 1, axis=1) | np.roll(dark, -1, axis=1)
    hmask = _runs_mask(dh, k, 1)
    vmask = _runs_mask(dv, k, 0)
    lines = hmask | vmask
    if lines.mean() > .05:
        # «линиями» стало больше 5% листа: тень, фон или фото — сетку по пикселям искать бессмысленно (и долго)
        z = np.zeros_like(lines)
        return [], z, z, z
    f = 4
    H, W = lines.shape
    small = lines[:H // f * f, :W // f * f].reshape(H // f, f, W // f, f).any(axis=(1, 3))
    small = _dilate(small, 1)
    tables = []
    for sx0, sy0, sx1, sy1 in _components(small):
        x0, y0, x1, y1 = sx0 * f, sy0 * f, min((sx1 + 1) * f, W), min((sy1 + 1) * f, H)
        w, h = x1 - x0, y1 - y0
        if w < dpi * 1.0 or h < dpi * 0.3:
            continue
        hm, vm = hmask[y0:y1, x0:x1], vmask[y0:y1, x0:x1]
        ys = [y0 + v for v in _cluster_idx(np.where(hm.sum(axis=1) >= 0.3 * w)[0])]
        xs = [x0 + v for v in _cluster_idx(np.where(vm.sum(axis=0) >= 0.3 * h)[0])]
        if len(ys) < 2 or len(xs) < 2 or (len(ys) - 1) * (len(xs) - 1) < 2:
            continue

        def v_present(x, ya, yb):
            xi = int(round(x))
            seg = vmask[int(ya):int(yb), max(xi - 3, 0):xi + 4]
            return seg.size and seg.any(axis=1).mean() > 0.5

        def h_present(y, xa, xb):
            yi = int(round(y))
            seg = hmask[max(yi - 3, 0):yi + 4, int(xa):int(xb)]
            return seg.size and seg.any(axis=0).mean() > 0.5

        nr, nc = len(ys) - 1, len(xs) - 1
        done = [[False] * nc for _ in range(nr)]
        cells = []
        for i in range(nr):
            for j in range(nc):
                if done[i][j]:
                    continue
                j2 = j
                while j2 + 1 < nc and not v_present(xs[j2 + 1], ys[i] + 3, ys[i + 1] - 3):
                    j2 += 1
                i2 = i
                while i2 + 1 < nr and not h_present(ys[i2 + 1], xs[j] + 3, xs[j2 + 1] - 3):
                    i2 += 1
                for a in range(i, i2 + 1):
                    for b in range(j, j2 + 1):
                        done[a][b] = True
                cells.append((xs[j], ys[i], xs[j2 + 1], ys[i2 + 1]))
        tables.append({'bbox': (xs[0], ys[0], xs[-1], ys[-1]), 'cells': cells})
    return tables, lines, hmask, vmask



# ------------------------------------------------------------------ сканы ----


def _normalize(img):
    """Бумага -> белый, чернила -> чёрный. Автоконтраст с отсечкой 1% ломает страницы, где чернил меньше 1%
    (короткое письмо): «чёрной» объявлялась серая точка, и весь лист темнел — OCR ничего не находил."""
    a = np.asarray(img, dtype=np.float32)
    sample = a[::3, ::3]
    hi = float(np.percentile(sample, 90))
    lo = float(np.percentile(sample, .02))
    if hi - lo < 40:
        return img
    return Image.fromarray(np.clip((a - lo) / (hi - lo) * 255.0, 0, 255).astype(np.uint8))


def _deskew(img):
    """Выравнивает наклон скана (до ±4°) по профилю строк текста/линий."""
    small_f = max(1, round(min(img.size) / 700))
    sm = img.resize((img.width // small_f, img.height // small_f), Image.BILINEAR)
    b = sm.point(lambda v: 255 if v < 140 else 0)

    def score(angle):
        r = b.rotate(angle, resample=Image.NEAREST, fillcolor=0)
        prof = np.asarray(r, dtype=np.float32).sum(axis=1)
        return float(np.var(prof))

    best, best_s = 0.0, score(0.0)
    for a in np.arange(-4.0, 4.01, .5):
        sc_ = score(float(a))
        if sc_ > best_s * 1.02:
            best, best_s = float(a), sc_
    for a in np.arange(best - .5, best + .51, .1):
        sc_ = score(float(a))
        if sc_ > best_s:
            best, best_s = float(a), sc_
    if abs(best) < .15:
        return img
    return img.rotate(best, resample=Image.BICUBIC, fillcolor=255)


_ASC = set('бйёdfhklbtij0123456789()[]/|') | set('АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯABCDEFGHIJKLMNOPQRSTUVWXYZ')
_DESC = set('рцдщуфpqgyj,;')


def _glyph_extent(text):
    """Какая доля кегля занята вертикальным размахом слова (по составу букв)."""
    desc = any(c in _DESC for c in text)
    asc = any(c in _ASC for c in text)
    if desc and asc:
        return .90
    if asc:
        return .68
    if desc:
        return .66
    return .46


def _snap_size(v):
    """Кегль чаще всего целый: 12.26 -> 12, 12.55 -> 12.5."""
    if abs(v - round(v)) <= .4:
        v = float(round(v))
    else:
        v = round(v * 2) / 2
    return min(max(v, 6.0), 48.0)


def _erode(b, r):
    for _ in range(r):
        o = b.copy()
        o[1:] &= b[:-1]
        o[:-1] &= b[1:]
        o[:, 1:] &= b[:, :-1]
        o[:, :-1] &= b[:, 1:]
        b = o
    return b


def _ink_survival(dark, box, size_px):
    """Доля чернил, переживших «эрозию» ~ толщины штриха: у жирного шрифта она выше."""
    x0, y0, x1, y1 = box
    crop = dark[max(y0, 0):y1, max(x0, 0):x1]
    if crop.size == 0 or crop.sum() < 20:
        return 0.0
    r = max(2, int(round(.036 * size_px)))       # стержни обычного начертания ~0.085 кегля исчезают, жирные (~0.14) остаются
    return float(_erode(crop, r).sum() / crop.sum())


BOLD_SURVIVAL = .21


def _segs_from_mask(mask, exclude, sc, dpi, vertical=False):
    """Линии скана вне таблиц -> [(a0, a1, pos)] в pt (горизонтальные: x0, x1, y; вертикальные: y0, y1, x)."""
    mm = mask.T if vertical else mask
    hm = mm.copy()
    for (x0, y0, x1, y1) in exclude:
        a0, b0, a1, b1 = (y0, x0, y1, x1) if vertical else (x0, y0, x1, y1)
        hm[max(int(b0) - 3, 0):int(b1) + 4, max(int(a0) - 3, 0):int(a1) + 4] = False
    rows = np.where(hm.sum(axis=1) >= max(int(dpi * .3), 30))[0]
    out = []
    if not len(rows):
        return out
    groups, cur = [], [rows[0]]
    for r in rows[1:]:
        if r - cur[-1] > 2:
            groups.append(cur)
            cur = []
        cur.append(r)
    groups.append(cur)
    for g in groups:
        band = hm[g[0]:g[-1] + 1].any(axis=0)
        xs = np.where(band)[0]
        if not len(xs):
            continue
        start, prev = xs[0], xs[0]
        for x in list(xs[1:]) + [None]:
            if x is None or x - prev > 8:
                if prev - start >= dpi * .3:
                    out.append((start * sc, prev * sc, (g[0] + g[-1]) / 2 * sc))
                if x is not None:
                    start = x
            if x is not None:
                prev = x
    return out


def _scan_fills(arr, sc):
    """Серые заливки на скане (шапка таблицы, «зебра») -> [(x0, y0, x1, y1, '#rrggbb')] в pt.

    Блоки 8×8 px: 70-й процентиль яркости = «цвет фона блока» (текст — меньшинство пикселей, на белой бумаге это 255).
    """
    b = 8
    H, W = arr.shape
    h, w = H // b, W // b
    if h < 10 or w < 10:
        return []
    blocks = arr[:h * b, :w * b].reshape(h, b, w, b).transpose(0, 2, 1, 3).reshape(h, w, b * b)
    p70 = np.percentile(blocks, 70, axis=2)
    mask = (p70 < 240) & (p70 > 150)
    if mask.mean() > .35:
        return []                                  # фон/тень на весь лист — это не заливки ячеек
    fills = []
    for x0, y0, x1, y1 in _components(mask):
        if (x1 - x0 + 1) * (y1 - y0 + 1) < 12 or (y1 - y0 + 1) < 2:
            continue
        sel = p70[y0:y1 + 1, x0:x1 + 1]
        inside = sel[mask[y0:y1 + 1, x0:x1 + 1]]
        if inside.size < .6 * sel.size or inside.std() > 7:
            continue
        v = int(round(float(np.median(inside)) / 8) * 8)
        fills.append((x0 * b * sc, y0 * b * sc, (x1 + 1) * b * sc, (y1 + 1) * b * sc, '#%02x%02x%02x' % (v, v, v)))
    return fills


def _seg_size(seg_words):
    """Размер шрифта сегмента по ширине его текста в Times New Roman (None — мало текста)."""
    ws = [w for w in seg_words if len(w.text) >= 2]
    chars = sum(len(w.text) for w in ws)
    if chars < 6:
        return None
    adv = sum(fm.advance(w.text, w.bold) for w in ws)
    width = sum(w.x1 - w.x0 for w in ws)
    if adv <= 0:
        return None
    return width / adv * 1.015       # ширина чернил чуть меньше суммы продвижений глифов


def _estimate_fonts(words, dark, sc):
    """Размер (по ширине), жирность (по толщине штриха) и базовая линия слов скана. Меняет слова на месте."""
    if not words:
        return
    probe = segs_from_words(words)

    def assign():
        raw = {}
        for sg in probe:
            raw[id(sg)] = _seg_size(sg.words)
        known = [v for v in raw.values() if v]
        page_med = statistics.median(known) if known else 12.0
        vals = {}
        for sg in probe:
            v = raw[id(sg)]
            if v is None:
                near = [raw[id(o)] for o in probe if raw[id(o)] and abs(o.baseline - sg.baseline) <= 3]
                v = statistics.median(near) if near else page_med
            vals[id(sg)] = v
        # близкие размеры на странице — один кегль (оценка по ширине даёт разброс ±3%)
        order = sorted(probe, key=lambda g: vals[id(g)])
        clusters = []
        for sg in order:
            w_ = sum(len(x.text) for x in sg.words) or 1
            if clusters and vals[id(sg)] - clusters[-1]['mean'] <= .6:
                c = clusters[-1]
                c['items'].append((sg, w_))
                c['mean'] = sum(vals[id(g)] * ww for g, ww in c['items']) / sum(ww for _, ww in c['items'])
            else:
                clusters.append({'mean': vals[id(sg)], 'items': [(sg, w_)]})
        for c in clusters:
            size = _snap_size(c['mean'])
            for sg, _ in c['items']:
                for w in sg.words:
                    w.size = size

    assign()
    for sg in probe:                              # жирность: по доле чернил, переживших эрозию
        for w in sg.words:
            if len(w.text) >= 2:
                box = (int(w.x0 / sc), int(w.y0 / sc), int(w.x1 / sc), int(w.y1 / sc))
                w.bold = _ink_survival(dark, box, w.size / sc) > BOLD_SURVIVAL
    assign()                                      # размер ещё раз — с учётом более широкого жирного начертания
    for sg in probe:
        for w in sg.words:
            has_desc = any(c in _DESC for c in w.text)
            w.base = w.y1 - (.2 * w.size if has_desc else 0)


def _cell_ocr(clean, rect, pytesseract, multiline):
    """Распознаёт одну ячейку отдельно (psm 7/6): мелкие «1», «2», «5» в узких колонках страница целиком даёт мусором."""
    x0, y0, x1, y1 = rect
    crop = clean[y0 + 4:y1 - 3, x0 + 4:x1 - 3]
    if crop.size == 0:
        return []
    pad = 12
    crop = np.pad(crop, pad, constant_values=255)
    try:
        d = pytesseract.image_to_data(Image.fromarray(crop), lang=settings.OCR_LANGS,
                                      config='--oem 1 --psm %d' % (6 if multiline else 7),
                                      output_type=pytesseract.Output.DICT)
    except Exception:  # noqa: BLE001  — сбой одной ячейки не должен ронять страницу
        return []
    out = []
    for i, txt in enumerate(d['text']):
        txt = txt.strip()
        if not txt or float(d['conf'][i]) < 0:
            continue
        out.append((x0 + 4 - pad + d['left'][i], y0 + 3 - pad + d['top'][i], d['width'][i], d['height'][i], txt,
                    float(d['conf'][i])))
    return out


def _reocr_cells(clean, dark, tables, raw, pytesseract):
    """Ячейки таблиц с сомнительным результатом (пусто при наличии чернил, ≤4 символов, низкая уверенность)
    распознаются заново по одной."""
    if not tables:
        return raw
    jobs = []
    for t in tables:
        for rect in t['cells']:
            x0, y0, x1, y1 = (int(v) for v in rect)
            inner = [w for w in raw if x0 <= w[0] + w[2] / 2 <= x1 and y0 <= w[1] + w[3] / 2 <= y1]
            chars = sum(len(w[4]) for w in inner)
            conf = statistics.mean(w[5] for w in inner) if inner else 0
            ink = int(dark[y0 + 3:y1 - 2, x0 + 3:x1 - 2].sum())
            if ink >= 25 and (not inner or conf < 80 or (chars <= 4 and conf < 92)):
                line_h = statistics.median(w[3] for w in inner) if inner else 40
                jobs.append(((x0, y0, x1, y1), inner, (y1 - y0) > 2.2 * max(line_h, 20),
                             statistics.mean(w[5] for w in inner) if inner else -1))
    if not jobs:
        return raw
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=max(1, min(4, os.cpu_count() or 1))) as ex:
        results = list(ex.map(lambda j: _cell_ocr(clean, j[0], pytesseract, j[2]), jobs))
    drop = set()
    add = []
    for (rect, inner, _, old_conf), res in zip(jobs, results):
        # заменяем, только если новое чтение не хуже страничного (иначе «шт.» легко превращается в «ШТ.»)
        if res and (not inner or statistics.mean(w[5] for w in res) >= old_conf):
            drop |= {id(w) for w in inner}
            add += res
    return [w for w in raw if id(w) not in drop] + add


def _ocr_page(page, pytesseract):
    dpi = settings.OCR_DPI
    sc = 72.0 / dpi
    pix = page.get_pixmap(dpi=dpi, colorspace=fitz.csGRAY, alpha=False)
    img = Image.frombytes('L', (pix.width, pix.height), pix.samples)
    img = _normalize(img)
    img = _deskew(img)
    arr = np.array(img)
    tables, line_mask, hmask, vmask = detect_scan_tables(arr, dpi)
    # стираем линии (таблицы, подчёркивания), чтобы они не мешали распознаванию текста
    erase = _dilate(line_mask, 2)
    clean = np.where(erase, 255, arr).astype(np.uint8)
    dark = clean < 140
    try:
        data = pytesseract.image_to_data(
            Image.fromarray(clean), lang=settings.OCR_LANGS, config='--oem 1 --psm 3',
            output_type=pytesseract.Output.DICT)
    except pytesseract.TesseractNotFoundError as e:
        raise ConversionError(
            'Не найден Tesseract OCR. Установите его (см. README.md) '
            'или задайте переменную TESSERACT_CMD.') from e
    except pytesseract.TesseractError as e:
        raise ConversionError(f'Ошибка распознавания: {e}') from e

    raw = []
    for i, txt in enumerate(data['text']):
        txt = txt.strip()
        if not txt or float(data['conf'][i]) < 0:
            continue
        if float(data['conf'][i]) < 25 and len(txt) <= 2:
            continue
        x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
        if w > .9 * pix.width:
            continue
        raw.append((x, y, w, h, txt, float(data['conf'][i])))
    raw = _reocr_cells(clean, dark, tables, raw, pytesseract)
    words = []
    for x, y, w, h, txt, _ in raw:
        size = (h * sc) / _glyph_extent(txt)
        has_desc = any(c in _DESC for c in txt)
        words.append(L.Word(x * sc, y * sc, (x + w) * sc, (y + h) * sc, txt, False, False, size, 'serif',
                            (y + h) * sc - (.2 * size if has_desc else 0)))
    _estimate_fonts(words, dark, sc)

    elems, taken_ids, boxes = [], set(), []
    for t in tables:
        rects = [(c[0] * sc, c[1] * sc, c[2] * sc, c[3] * sc) for c in t['cells']]
        tb, taken = build_table(rects, 'grid', words, tol=dpi * .03 * sc)
        elems.append(tb)
        boxes.append(tb.bbox)
        taken_ids |= {id(words[i]) for i in taken}
    excl = [t['bbox'] for t in tables]
    hs = _segs_from_mask(hmask, excl, sc, dpi)
    vs = _segs_from_mask(vmask, excl, sc, dpi, vertical=True)
    free_all = [w for w in words if id(w) not in taken_ids]
    rtabs, rules = segment_tables(hs, vs, free_all, boxes, page.rect.width)
    for t in rtabs:
        elems.append(t)
        boxes.append(t.bbox)
        for c in t.cells:
            for s in c.segs:
                taken_ids |= {id(w) for w in s.words}
    free = [w for w in words if id(w) not in taken_ids and
            not any(b[0] - 1 <= (w.x0 + w.x1) / 2 <= b[2] + 1 and b[1] - 1 <= (w.y0 + w.y1) / 2 <= b[3] + 1 for b in boxes)]
    elems += segs_from_words(free)
    fills = _scan_fills(arr, sc)
    for t in elems:
        if isinstance(t, L.Table):
            L.apply_fills(t, fills)
    return L.Page(page.rect.width, page.rect.height, elems, rules, fills)


def _prepare_scans(data, doc, scan_nums, result):
    """OCRmyPDF как первый шаг для страниц-сканов -> fitz.Document с выровненными сканами или None.

    Режим (settings.OCRMYPDF_MODE): off — пропустить; auto — применить, если установлен, а при сбое продолжить
    со встроенной подготовкой (с предупреждением); on — без OCRmyPDF не работаем.
    """
    mode = settings.OCRMYPDF_MODE
    if not scan_nums or mode == 'off':
        return None
    if not ocrprep.available():
        if mode == 'on':
            raise ConversionError('GENDALF_OCRMYPDF=on, но пакет ocrmypdf не установлен (см. README.md).')
        return None
    try:
        out = ocrprep.prepare(data, scan_nums)
        prepared = fitz.open(stream=out, filetype='pdf')
    except Exception as e:  # noqa: BLE001  — любой сбой подготовки (в т.ч. OcrPrepError) не должен ронять конвертацию
        if mode == 'on':
            raise ConversionError(f'OCRmyPDF: {e}') from e
        result.warnings.append(f'OCRmyPDF не применён ({e}); использована встроенная подготовка скана.')
        return None
    if prepared.page_count != doc.page_count:
        prepared.close()
        if mode == 'on':
            raise ConversionError('OCRmyPDF изменил число страниц документа.')
        result.warnings.append('OCRmyPDF изменил число страниц; использована встроенная подготовка скана.')
        return None
    result.ocrmypdf = True
    return prepared


def convert_pdf(data: bytes) -> ConversionResult:
    """data — содержимое PDF (без временных файлов: на Windows они мешают открытию)."""
    try:
        doc = fitz.open(stream=data, filetype='pdf')
    except Exception as e:  # noqa: BLE001
        raise ConversionError(f'Не удалось открыть PDF: {e}') from e
    if doc.needs_pass:
        raise ConversionError('PDF защищён паролем.')
    result = ConversionResult(html='', pages=doc.page_count)
    scan_nums = [n for n, page in enumerate(doc, start=1) if len(page.get_text().strip()) < MIN_TEXT_CHARS]
    prepared = _prepare_scans(data, doc, scan_nums, result)
    pages = []
    pytesseract = None
    for n, page in enumerate(doc, start=1):
        if n not in scan_nums:
            pg = _native_page(page)
        else:
            if pytesseract is None:
                pytesseract = _setup_tesseract()
            pg = _ocr_page(prepared[n - 1] if prepared else page, pytesseract)
            result.ocr_pages += 1
            if not pg.elems:
                result.warnings.append(f'Страница {n}: текст не распознан.')
        pages.append(pg)
    if prepared:
        prepared.close()
    doc.close()
    meta = L.compute_meta(pages)
    # проход 1: узнаём, где реально начинается содержимое -> верхнее поле Word; проход 2: итоговый HTML
    tops = [t for t in (L.render_page(pg, meta, meta.mt)[1] for pg in pages) if t is not None]
    if tops:
        meta.mt = max(14.0, min(tops))
    chunks = []
    for n, pg in enumerate(pages):
        if n:
            chunks.append('<hr>')
        chunks.append(L.render_page(pg, meta, meta.mt)[0])
    result.html = '\n'.join(chunks)
    result.meta = meta.as_dict()
    return result
