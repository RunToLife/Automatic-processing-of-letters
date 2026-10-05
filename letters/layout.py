"""Восстановление вёрстки страницы: из геометрии текста, таблиц и картинок — в HTML,
который сохраняет расположение текста оригинала (отступы, выравнивание, колонки, интервалы).

Модуль не зависит от PyMuPDF/Tesseract: на входе элементы страницы (Seg/Table/Img) в пунктах (pt),
на выходе HTML с абсолютными размерами в pt. Этот же HTML показывается в редакторе и превращается в DOCX
(letters/docxbuild.py), поэтому всё, что здесь записано в style, должно уметь читать docxbuild.

Идея: рекурсивный XY-cut. Страница делится по самым большим «белым» промежуткам: по вертикали — на
колонки (из них получаются невидимые таблицы-раскладки, например «реквизиты слева / адресат справа»
или «должность слева / ФИО справа»), по горизонтали — на блоки. Блок — это абзацы с точными
отступами, выравниванием и интервалами до предыдущего блока.
"""
import html
import statistics
from dataclasses import dataclass, field

# ------------------------------------------------------------------ модель --


@dataclass
class Word:
    x0: float
    y0: float
    x1: float
    y1: float
    text: str
    bold: bool = False
    italic: bool = False
    size: float = 12.0
    font: str = 'serif'          # serif | sans | mono
    base: float = 0.0            # базовая линия слова (0 — не задана)


@dataclass
class Seg:
    """Фрагмент строки: слова на одной базовой линии без широких разрывов."""
    words: list
    baseline: float
    kind: str = 'text'

    def __post_init__(self):
        self.words.sort(key=lambda w: w.x0)

    @property
    def x0(self):
        return min(w.x0 for w in self.words)

    @property
    def x1(self):
        return max(w.x1 for w in self.words)

    @property
    def y0(self):
        return min(w.y0 for w in self.words)

    @property
    def y1(self):
        return max(w.y1 for w in self.words)

    @property
    def size(self):
        return statistics.median(w.size for w in self.words)

    @property
    def bold(self):
        chars = sum(len(w.text) for w in self.words) or 1
        return sum(len(w.text) for w in self.words if w.bold) / chars > .7

    @property
    def text(self):
        return ' '.join(w.text for w in self.words)


@dataclass
class Cell:
    r0: int
    c0: int
    r1: int            # включительно
    c1: int
    bbox: tuple
    segs: list = field(default_factory=list)
    borders: tuple = None      # (верх, право, низ, лево): есть ли реальная линия; None — по виду таблицы
    bg: str = None             # заливка '#rrggbb'


@dataclass
class Table:
    """Таблица: kind='grid' (все границы), 'custom' (границы по ячейкам: рамка, только горизонтали...) или 'layout' (без линий)."""
    bbox: tuple
    xs: list
    ys: list
    cells: list
    kind: str = 'grid'
    base: float = 12.0

    x0 = property(lambda s: s.bbox[0])
    y0 = property(lambda s: s.bbox[1])
    x1 = property(lambda s: s.bbox[2])
    y1 = property(lambda s: s.bbox[3])


@dataclass
class Img:
    x0: float
    y0: float
    x1: float
    y1: float
    data: str                    # base64
    ext: str = 'png'


@dataclass
class Rule:
    """Горизонтальная линия вне таблиц (подчёркивание реквизитов и т. п.)."""
    x0: float
    x1: float
    y: float


@dataclass
class Page:
    width: float
    height: float
    elems: list                 # Seg | Table | Img
    rules: list = field(default_factory=list)
    fills: list = field(default_factory=list)      # заливки (x0, y0, x1, y1, '#rrggbb')


def apply_fills(table, fills):
    """Заливка ячеек (светло-серая шапка, «зебра») по векторным прямоугольникам страницы."""
    for c in table.cells:
        x0, y0, x1, y1 = c.bbox
        area = max((x1 - x0) * (y1 - y0), 1.0)
        for fx0, fy0, fx1, fy1, col in fills:
            ow = min(x1, fx1) - max(x0, fx0)
            oh = min(y1, fy1) - max(y0, fy0)
            if ow > 0 and oh > 0 and ow * oh >= .6 * area:
                c.bg = col
                break


@dataclass
class Meta:
    w: float = 595.0
    h: float = 842.0
    ml: float = 56.7
    mr: float = 56.7
    mt: float = 56.7
    mb: float = 28.0

    def as_dict(self):
        return {k: round(v, 1) for k, v in self.__dict__.items()}


# ---------------------------------------------------------------- утилиты ---
def pt(v):
    s = f'{v:.1f}'.rstrip('0').rstrip('.')
    return f'{"0" if s in ("-0", "") else s}pt'


def _style(**kw):
    return ';'.join(f'{k.replace("_", "-")}:{v}' for k, v in kw.items() if v not in (None, ''))


FONT_CSS = {'serif': "'Times New Roman',serif", 'sans': 'Arial,sans-serif', 'mono': "'Courier New',monospace"}


def runs_html(words, base_size, base_font, bold_all=False):
    """слова -> inline-HTML (b/i/span) с форматом, отличающимся от базового."""
    groups = []
    for w in words:
        key = (w.bold and not bold_all, w.italic, round(w.size * 2) / 2 if abs(w.size - base_size) > 1.2 else None,
               w.font if w.font != base_font else None)
        if groups and groups[-1][0] == key:
            groups[-1][1].append(w.text)
        else:
            groups.append((key, [w.text]))
    out = []
    for i, ((b, it, sz, fn), texts) in enumerate(groups):
        txt = html.escape(' '.join(texts))
        if i < len(groups) - 1:
            txt += ' '
        if sz or fn:
            txt = f'<span style="{_style(font_size=pt(sz) if sz else None, font_family=FONT_CSS.get(fn) if fn else None)}">{txt}</span>'
        if it:
            txt = f'<i>{txt}</i>'
        if b:
            txt = f'<b>{txt}</b>'
        out.append(txt)
    return ''.join(out)


def line_text_html(segs, base_size, base_font, bold_all=False):
    """Несколько сегментов одной строки (редкий случай) соединяем пробелами по ширине зазора."""
    segs = sorted(segs, key=lambda s: s.x0)
    parts = []
    for i, s in enumerate(segs):
        if i:
            gap = s.x0 - segs[i - 1].x1
            parts.append('&nbsp;' * max(2, int(round(gap / (base_size * .25)))))
        parts.append(runs_html(s.words, base_size, base_font, bold_all))
    return ''.join(parts)


# -------------------------------------------------------------- Line / Para --
@dataclass
class Line:
    segs: list
    baseline: float
    x0: float
    x1: float
    top: float
    bottom: float
    size: float
    font: str
    bold: bool

    @property
    def words(self):
        return sorted((w for s in self.segs for w in s.words), key=lambda w: w.x0)


def make_lines(segs, tol=None):
    """Сегменты -> строки (по близости базовых линий)."""
    segs = sorted(segs, key=lambda s: (s.baseline, s.x0))
    lines = []
    for s in segs:
        t = tol if tol is not None else max(1.5, .35 * s.size)
        if lines and abs(lines[-1][0] - s.baseline) <= t:
            lines[-1][1].append(s)
        else:
            lines.append([s.baseline, [s]])
    out = []
    for _, ss in lines:
        ws = [w for s in ss for w in s.words]
        sizes = [w.size for w in ws]
        fonts = [w.font for w in ws]
        chars = sum(len(w.text) for w in ws) or 1
        out.append(Line(
            segs=ss, baseline=statistics.median(s.baseline for s in ss),
            x0=min(s.x0 for s in ss), x1=max(s.x1 for s in ss),
            top=min(s.y0 for s in ss), bottom=max(s.y1 for s in ss),
            size=statistics.median(sizes), font=max(set(fonts), key=fonts.count),
            bold=sum(len(w.text) for w in ws if w.bold) / chars > .7))
    return out


@dataclass
class Para:
    lines: list
    align: str = 'left'
    left: float = 0.0       # отступ слева относительно рамки
    right: float = 0.0
    first: float = 0.0      # красная строка (может быть < 0 — выступ)
    br: bool = False        # строки разделять переносами (иначе — перетекание)
    rule_below: bool = False

    @property
    def size(self):
        return statistics.median(l.size for l in self.lines)


def _first_word_w(line):
    w = line.words[0]
    return w.x1 - w.x0


def _split_paragraphs(lines, bx0, bx1, narrow, page_just):
    """Строки одного блока -> абзацы (по заполненности строк, красной строке, размеру, интервалу)."""
    if not lines:
        return []
    BL = min(l.x0 for l in lines)
    BR = max(l.x1 for l in lines)
    BW = max(BR - BL, 1)
    pitches = [b.baseline - a.baseline for a, b in zip(lines, lines[1:])]
    pitch = statistics.median(pitches) if pitches else lines[0].size * 1.2
    centers_all = [(l.x0 + l.x1) / 2 for l in lines]
    leaf_centered = (len(lines) >= 2 and max(centers_all) - min(centers_all) <= 4
                     and max(l.x0 for l in lines) - min(l.x0 for l in lines) > 3)
    groups = [[lines[0]]]
    for prev, cur in zip(lines, lines[1:]):
        new = False
        if narrow:
            # узкий блок (адрес, шапка, подпись): переносы строк сохраняем, абзац меняется только при смене стиля
            if abs(cur.size - prev.size) > 1.2 or cur.bold != prev.bold:
                new = True
            elif cur.baseline - prev.baseline > 1.7 * pitch:
                new = True
        else:
            sp = prev.size * .27
            fits_next = prev.x1 + sp + _first_word_w(cur) <= BR + 2.0   # следующее слово влезло бы -> строку закончили намеренно
            short_prev = (BR - prev.x1) > .35 * BW
            if fits_next or short_prev:
                new = True
            if abs(cur.size - prev.size) > 1.2 or cur.bold != prev.bold:
                new = True
            if cur.baseline - prev.baseline > 1.3 * pitch:
                new = True
        if new:
            groups.append([cur])
        else:
            groups[-1].append(cur)

    paras = []
    for g in groups:
        p = _make_para(g, bx0, bx1, narrow, page_just, BL, BR)
        if leaf_centered and p.align != 'center':
            pl, pr = min(l.x0 for l in g), max(l.x1 for l in g)
            p.align, p.first, p.br = 'center', 0.0, True
            p.left, p.right = max(0.0, pl - bx0 - 3), max(0.0, bx1 - pr - 3)
        paras.append(p)
    return paras


def _make_para(g, bx0, bx1, narrow, page_just, BL, BR):
    box_c = (bx0 + bx1) / 2
    pl = min(l.x0 for l in g)
    pr = max(l.x1 for l in g)
    first = g[0]
    if len(g) > 1:
        rest_l = min(l.x0 for l in g[1:])
    else:
        rest_l = first.x0
    p = Para(lines=g)
    centers = [(l.x0 + l.x1) / 2 for l in g]
    c_ok = max(centers) - min(centers) <= 3.5
    l_all = max(l.x0 for l in g) - min(l.x0 for l in g) <= 3
    l_rest = max(l.x0 for l in g[1:] or g) - min(l.x0 for l in g[1:] or g) <= 3
    r_ok = max(l.x1 for l in g) - min(l.x1 for l in g) <= 3
    width = pr - pl
    boxw = bx1 - bx0
    if len(g) == 1:
        c = centers[0]
        if abs(c - box_c) <= 4 and width < .92 * boxw:
            p.align = 'center'
        elif first.x0 > bx0 + .45 * boxw and bx1 - first.x1 <= .1 * boxw and width < .5 * boxw:
            p.align = 'right'
        else:
            p.align = 'left'
    else:
        if c_ok and not l_all and (narrow or width < .85 * boxw):
            p.align = 'center'
        elif r_ok and not l_all and (narrow or width < .6 * boxw):
            p.align = 'right'
        elif r_ok and len(g) >= 3 and l_rest and abs(max(l.x1 for l in g[:-1]) - min(l.x1 for l in g[:-1])) <= 1.6 and not narrow:
            p.align = 'justify'
        elif page_just and not narrow and len(g) >= 2 and abs(g[0].x1 - BR) <= 1.6 and \
                max(l.x1 for l in g[:-1]) - min(l.x1 for l in g[:-1]) <= 1.6:
            p.align = 'justify'
        else:
            p.align = 'left'
    if p.align == 'left' or p.align == 'justify':
        p.left = rest_l - bx0 if len(g) > 1 else first.x0 - bx0
        d = first.x0 - rest_l if len(g) > 1 else 0
        if len(g) == 1 and not narrow:
            body_ind = first.x0 - bx0
            # одиночная строка с отступом ~1–2 см — это красная строка
            if 18 <= body_ind <= 56:
                p.left, d = 0.0, body_ind
        p.first = d if abs(d) > 3 else 0.0
        p.right = 0.0 if narrow else max(0.0, bx1 - max(BR, pr) - 3.0)
        if p.right < 6:
            p.right = 0.0
    elif p.align == 'center':
        # запас ~3 pt с каждой стороны: у Word/LibreOffice ширина текста чуть отличается, строка не должна переноситься
        slack = max(3.0, .05 * (pr - pl))
        p.left, p.right = max(0.0, pl - bx0 - slack), max(0.0, bx1 - pr - slack)
    else:  # right
        p.left = 0.0
        p.right = max(0.0, bx1 - pr)
    if p.left < 1.5:
        p.left = 0.0
    p.br = narrow or p.align in ('center', 'right')
    return p


# ------------------------------------------------------------------ XY-cut ---
@dataclass
class Leaf:
    elems: list


@dataclass
class Seq:
    children: list


@dataclass
class Cols:
    cols: list      # [(x0, x1, node)]
    bounds: list = field(default_factory=list)   # середины полос между колонками


def _overlap(a, b, pad=0.0):
    return (a.x0 - pad < b.x1 and b.x0 - pad < a.x1 and a.y0 - pad < b.y1 and b.y0 - pad < a.y1)


def _v_strips(elems, vmin):
    iv = sorted((e.x0, e.x1) for e in elems)
    merged = []
    for a, b in iv:
        if merged and a <= merged[-1][1] + 0.01:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return [(merged[i][1], merged[i + 1][0]) for i in range(len(merged) - 1)
            if merged[i + 1][0] - merged[i][1] >= vmin]


def _h_gaps(elems, hmin):
    iv = sorted((e.y0, e.y1) for e in elems)
    merged = []
    for a, b in iv:
        if merged and a < merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return [(merged[i + 1][0] - merged[i][1], (merged[i][1] + merged[i + 1][0]) / 2) for i in range(len(merged) - 1)
            if merged[i + 1][0] - merged[i][1] >= hmin]


def _cut_horizontal(elems, ycut):
    top = [e for e in elems if (e.y0 + e.y1) / 2 < ycut]
    bot = [e for e in elems if (e.y0 + e.y1) / 2 >= ycut]
    if not (top and bot):
        return None
    kids = []
    for part in (top, bot):
        n = xy_tree(part)
        if isinstance(n, Seq):
            kids.extend(n.children)
        elif n:
            kids.append(n)
    return Seq(_merge_cols_rows(kids))


def _merge_cols_rows(kids):
    """Соседние «строки колонок» с одинаковой сеткой — это одна таблица без линий: склеиваем в один узел."""
    out = []
    for k in kids:
        prev = out[-1] if out else None
        if (isinstance(k, Cols) and isinstance(prev, Cols) and len(k.cols) == len(prev.cols)
                and all(abs(a - b) <= 5 for a, b in zip(k.bounds, prev.bounds))):
            merged = []
            for (px0, px1, pn), (kx0, kx1, kn) in zip(prev.cols, k.cols):
                merged.append((min(px0, kx0), max(px1, kx1), Leaf(_flatten(pn) + _flatten(kn))))
            out[-1] = Cols(merged, prev.bounds)
        else:
            out.append(k)
    return out


def xy_tree(elems):
    if not elems:
        return None
    if len(elems) == 1:
        return Leaf(list(elems))
    sizes = [e.size for e in elems if isinstance(e, Seg)] or [12.0]
    lh = statistics.median(sizes)
    # 1) большие горизонтальные промежутки — границы блоков (заголовок / таблица / абзац / подпись)
    big = _h_gaps(elems, max(8.0, .9 * lh))
    if big:
        node = _cut_horizontal(elems, max(big)[1])
        if node:
            return node
    # 2) вертикальные полосы — колонки (реквизиты | адресат, должность | ФИО, колонки таблицы без линий)
    vmin = max(2.0 * lh, 22.0)
    strips = _v_strips(elems, vmin)
    imgs = [e for e in elems if isinstance(e, Img)]
    if imgs:          # печать/логотип от текста отделяет и узкий зазор
        edges = {round(v, 1) for e in imgs for v in (e.x0, e.x1)}
        for a, b in _v_strips(elems, 5.0):
            if (round(a, 1) in edges or round(b, 1) in edges) and (a, b) not in strips:
                strips.append((a, b))
        strips.sort()
    if strips:
        bounds = [-1e9] + [(a + b) / 2 for a, b in strips] + [1e9]
        cols = []
        for i in range(len(bounds) - 1):
            sub = [e for e in elems if bounds[i] <= (e.x0 + e.x1) / 2 < bounds[i + 1]]
            if sub:
                cols.append(sub)
        if len(cols) >= 2:
            return Cols([(min(e.x0 for e in c), max(e.x1 for e in c), xy_tree(c)) for c in cols],
                        [(a + b) / 2 for a, b in strips])
    # 3) малые промежутки между строками
    gaps = _h_gaps(elems, max(4.0, min(12.0, .5 * lh * 1.15)))
    if gaps:
        node = _cut_horizontal(elems, max(gaps)[1])
        if node:
            return node
    return Leaf(sorted(elems, key=lambda e: (e.y0, e.x0)))


# ------------------------------------------------------------------ рендер ---
class Flow:
    """Состояние вертикального потока: где закончилось предыдущее содержимое."""

    def __init__(self, top, page_just=False, rules=None, content_w=475.0, fills=None):
        self.fills = fills or []
        self.floats = []              # «плавающие» картинки (печати поверх текста), ещё не привязанные к абзацу
        self.bottom = top
        self.page_just = page_just
        self.rules = rules or []
        self.content_w = content_w
        self.first_top = None        # верх первого элемента потока (для расчёта верха строки/страницы)


def _align_css(a):
    return {'left': 'left', 'center': 'center', 'right': 'right', 'justify': 'justify'}[a]


def render_para(p, bx0, bx1, flow):
    first, last = p.lines[0], p.lines[-1]
    size = round(p.size * 2) / 2
    font = first.font
    pitches = [b.baseline - a.baseline for a, b in zip(p.lines, p.lines[1:])]
    pitch = statistics.median(pitches) if pitches else size * 1.2
    pitch = max(pitch, size * 1.0)
    pitch = round(pitch * 2) / 2
    top = first.baseline - .8 * pitch      # Word/LibreOffice: при точном интервале базовая линия на 80% высоты строки
    if flow.first_top is None:
        flow.first_top = top
    sb = max(0.0, top - flow.bottom)
    outer_top = top - sb                    # Word отсчитывает смещение якоря от верха абзаца вместе с интервалом «перед"
    bold_all = all(l.bold for l in p.lines)
    inner = []
    for i, l in enumerate(p.lines):
        inner.append(line_text_html(l.segs, size, font, bold_all))
    sep = '<br>' if p.br else ' '
    body = sep.join(inner)
    if bold_all:
        body = f'<b>{body}</b>'
    style = _style(margin_top=pt(sb) if sb >= .5 else None, margin_bottom='0pt',
                   margin_left=pt(p.left) if p.left else None, margin_right=pt(p.right) if p.right else None,
                   text_indent=pt(p.first) if p.first else None, text_align=_align_css(p.align),
                   line_height=pt(pitch), font_size=pt(size), font_family=FONT_CSS.get(font, FONT_CSS['serif']))
    flow.bottom = last.baseline + .2 * pitch
    anchored = ''
    while flow.floats and flow.floats[0].y0 < flow.bottom:
        anchored += _float_img(flow.floats.pop(0), outer_top, top, bx0 + p.left)
    border = ''
    for r in flow.rules:
        if last.baseline < r.y <= last.baseline + max(12.0, 1.2 * last.size) and r.x1 - r.x0 >= .6 * (p.lines[0].x1 - p.lines[0].x0):
            gap = max(1.0, min(30.0, r.y - (last.baseline + .2 * pitch)))   # зазор между текстом и линией как в оригинале
            border = f';border-bottom:0.75pt solid #000;padding-bottom:{pt(gap)}'
            flow.bottom = r.y + .4
            r.used = True
            if p.align == 'center' and abs((r.x0 + r.x1) / 2 - (first.x0 + first.x1) / 2) < 6 and bx0 <= r.x0 and r.x1 <= bx1:
                style = _style(margin_top=pt(sb) if sb >= .5 else None, margin_bottom='0pt', margin_left=pt(r.x0 - bx0) if r.x0 - bx0 >= 1 else None,
                               margin_right=pt(bx1 - r.x1) if bx1 - r.x1 >= 1 else None, text_align='center', line_height=pt(pitch),
                               font_size=pt(size), font_family=FONT_CSS.get(font, FONT_CSS['serif']))
    pos = ';position:relative' if anchored else ''
    return f'<p style="{style}{border}{pos}">{body}{anchored}</p>'


def render_table(t, bx0, flow):
    if flow.first_top is None:
        flow.first_top = t.y0
    ml = max(0.0, t.x0 - bx0)
    sb = max(0.0, t.y0 - flow.bottom)
    cls = {'grid': 'gd-grid', 'custom': 'gd-custom', 'layout': 'gd-layout'}[t.kind]
    cols = ''.join(f'<col style="width:{pt(b - a)}">' for a, b in zip(t.xs, t.xs[1:]))
    nrows, ncols = len(t.ys) - 1, len(t.xs) - 1
    start = {(c.r0, c.c0): c for c in t.cells}
    covered = set()
    for c in t.cells:
        for r in range(c.r0, c.r1 + 1):
            for cc in range(c.c0, c.c1 + 1):
                if (r, cc) != (c.r0, c.c0):
                    covered.add((r, cc))
    trs = []
    for r in range(nrows):
        h = t.ys[r + 1] - t.ys[r]
        tds = []
        for c in range(ncols):
            if (r, c) in start:
                tds.append(_render_cell(start[(r, c)], t))
            elif (r, c) not in covered:
                tds.append('<td></td>')
        trs.append(f'<tr style="height:{pt(h)}">{"".join(tds)}</tr>')
    style = _style(width=pt(t.x1 - t.x0), margin_left=pt(ml) if ml >= 1 else None,
                   margin_top=pt(sb) if sb >= 1 else None)
    flow.bottom = t.y1
    return f'<table class="{cls}" style="{style}"><colgroup>{cols}</colgroup>{"".join(trs)}</table>'


def _cell_deco(c, t):
    """Границы по сторонам ячейки (таблицы с частичными линиями) и заливка."""
    out = ''
    if t.kind == 'custom' and c.borders is not None:
        for side, on in zip(('top', 'right', 'bottom', 'left'), c.borders):
            out += f';border-{side}:{"0.5pt solid #000" if on else "none"}'
    if c.bg:
        out += f';background:{c.bg}'
    return out


def _render_cell(c, t):
    x0, y0, x1, y1 = c.bbox
    attrs = ''
    if c.r1 > c.r0:
        attrs += f' rowspan="{c.r1 - c.r0 + 1}"'
    if c.c1 > c.c0:
        attrs += f' colspan="{c.c1 - c.c0 + 1}"'
    if not c.segs:
        deco = _cell_deco(c, t)
        return f'<td{attrs} style="{deco.lstrip(";")}"></td>' if deco else f'<td{attrs}></td>'
    lines = make_lines(c.segs)
    size = round(statistics.median(l.size for l in lines) * 2) / 2
    font = max((l.font for l in lines), key=lambda f: sum(1 for l in lines if l.font == f))
    tx0, tx1 = min(l.x0 for l in lines), max(l.x1 for l in lines)
    ty0, ty1 = min(l.top for l in lines), max(l.bottom for l in lines)
    offL, offR = tx0 - x0, x1 - tx1
    w = x1 - x0
    if offL > 5 and abs(offL - offR) <= max(3.0, .12 * w):
        align = 'center'
    elif offR < offL - 5 and offR < .2 * w:
        align = 'right'
    else:
        align = 'left'
    offT, offB = ty0 - y0, y1 - ty1
    if offT > 2.5 and abs(offT - offB) <= max(3.0, .25 * (y1 - y0)):
        valign = 'middle'
    elif offB < offT - 3 and offB < .2 * (y1 - y0):
        valign = 'bottom'
    else:
        valign = 'top'
    # строки внутри ячейки: перетекание, если строка заполнена, иначе перенос
    paras, cur = [], [lines[0]]
    for prev, nxt in zip(lines, lines[1:]):
        wrapped = prev.x1 + prev.size * .27 + _first_word_w(nxt) > x1 - 3.5
        if wrapped:
            cur.append(nxt)
        else:
            paras.append(cur)
            cur = [nxt]
    paras.append(cur)
    bold_all = all(l.bold for l in lines)
    ps = []
    pitch = None
    ps_pitches = [b.baseline - a.baseline for a, b in zip(lines, lines[1:])]
    pitch = round(max(statistics.median(ps_pitches) if ps_pitches else size * 1.2, size) * 2) / 2
    for g in paras:
        body = ' '.join(line_text_html(l.segs, size, font, bold_all) for l in g)
        ps.append(body)
    body = '<br>'.join(ps)
    if bold_all:
        body = f'<b>{body}</b>'
    # отступы ячейки повторяют положение текста оригинала (точность не зависит от угаданного выравнивания)
    pad_t = None
    if t.kind == 'layout':
        valign = 'top'
        pad_t = max(0.0, lines[0].baseline - .8 * pitch - y0)
    slack = 2.5 if align == 'center' else 0.0     # запас по ширине, чтобы текст не перенёсся из-за округлений
    pad_l = max(offL - slack, 0.0) if align in ('left', 'center') else 0.0
    pad_r = max(offR - slack, 0.0) if align in ('right', 'center') else 0.0
    style = _style(text_align=align, vertical_align=valign, font_size=pt(size), line_height=pt(pitch),
                   font_family=FONT_CSS.get(font, FONT_CSS['serif']),
                   white_space='nowrap' if len(lines) == 1 else None,   # однострочная ячейка не должна переноситься
                   padding_left=pt(pad_l), padding_right=pt(pad_r),
                   padding_top=pt(pad_t) if pad_t is not None else None) + _cell_deco(c, t)
    return f'<td{attrs} style="{style}">{body}</td>'


def _float_img(im, outer_top, top, left0):
    """Картинка поверх текста (печать, подпись): привязана к абзацу.

    data-x / data-dy — для Word (X от края страницы, Y от верха абзаца вместе с интервалом «перед»);
    left/top в style — для редактора (от левого верха самого абзаца).
    """
    w, h = im.x1 - im.x0, im.y1 - im.y0
    style = _style(position='absolute', left=pt(im.x0 - left0), top=pt(im.y0 - top), width=pt(w), height=pt(h))
    return (f'<img data-float="1" data-x="{im.x0:.1f}" data-dy="{im.y0 - outer_top:.1f}" style="{style}" '
            f'src="data:image/{im.ext};base64,{im.data}" width="{round(w)}" height="{round(h)}">')


def render_img(im, bx0, flow):
    if flow.first_top is None:
        flow.first_top = im.y0
    sb = max(0.0, im.y0 - flow.bottom)
    flow.bottom = im.y1
    w = round(im.x1 - im.x0)
    style = _style(margin_top=pt(sb) if sb >= .5 else None, margin_bottom='0pt', margin_left=pt(im.x0 - bx0) if im.x0 - bx0 >= 1 else None,
                   text_align='left')
    return (f'<p style="{style}"><img src="data:image/{im.ext};base64,{im.data}" width="{w}" '
            f'height="{round(im.y1 - im.y0)}"></p>')


def render_node(node, bx0, bx1, flow):
    if node is None:
        return ''
    if isinstance(node, Seq):
        return ''.join(render_node(c, bx0, bx1, flow) for c in node.children)
    if isinstance(node, Cols):
        return render_cols(node, bx0, bx1, flow)
    return render_leaf(node, bx0, bx1, flow)


def table_from_lines(segs, bx1):
    """Строки текста с общими «пустыми колонками» между словами (таблица без линий) -> таблица Word.

    Сегменты строки разрезаются по пустым вертикальным полосам, общим для всех строк; дальше работает text_table.
    """
    lines = make_lines(segs)
    if len(lines) < 3 or len(lines) > 80:
        return None
    words = [w for l in lines for w in l.words]
    size = statistics.median(w.size for w in words)
    gaps = []
    for l in lines:
        ws = l.words
        gaps += [b.x0 - a.x1 for a, b in zip(ws, ws[1:])]
    small = [g for g in gaps if g < .7 * size]            # обычные межсловные пробелы (без разрывов между колонками)
    typical = statistics.median(small) if small else .25 * size
    vmin = max(6.5, .55 * size, 2.2 * typical)
    strips = _v_strips(words, vmin)
    if not strips:
        return None
    if len(lines) < 5 and max(b - a for a, b in strips) < 9:
        return None            # три-четыре строки с узкой полосой — скорее случайность в обычном тексте
    bounds = [-1e9] + [(a + b) / 2 for a, b in strips] + [1e9]
    cols = [[] for _ in range(len(bounds) - 1)]
    for s_ in segs:
        by = {}
        for w in s_.words:
            c = (w.x0 + w.x1) / 2
            i = next(i for i in range(len(bounds) - 1) if bounds[i] <= c < bounds[i + 1])
            by.setdefault(i, []).append(w)
        for i, ws in by.items():
            cols[i].append(Seg(ws, s_.baseline))
    cols = [c for c in cols if c]
    if len(cols) < 2:
        return None
    node = Cols([(min(e.x0 for e in c), max(e.x1 for e in c), Leaf(c)) for c in cols], [(a + b) / 2 for a, b in strips])
    return text_table(node, bx1)


def render_leaf(leaf, bx0, bx1, flow):
    out = []
    pending = []
    if len(leaf.elems) >= 3 and all(isinstance(e, Seg) for e in leaf.elems):
        tt = table_from_lines(leaf.elems, bx1)
        if tt:
            apply_fills(tt, flow.fills)
            return render_table(tt, bx0, flow)

    def flush():
        if not pending:
            return
        lines = make_lines(pending)
        pending.clear()
        BL = min(l.x0 for l in lines)
        BR = max(l.x1 for l in lines)
        narrow = (BR - BL) < .55 * flow.content_w
        for p in _split_paragraphs(lines, bx0, bx1, narrow, flow.page_just):
            out.append(render_para(p, bx0, bx1, flow))

    for e in sorted(leaf.elems, key=lambda e: (e.y0, e.x0)):
        if isinstance(e, Seg):
            pending.append(e)
        else:
            flush()
            out.append(render_table(e, bx0, flow) if isinstance(e, Table) else render_img(e, bx0, flow))
    flush()
    return ''.join(out)


def _flatten(node):
    if node is None:
        return []
    if isinstance(node, Leaf):
        return list(node.elems)
    if isinstance(node, Seq):
        return [e for c in node.children for e in _flatten(c)]
    return [e for _, _, n in node.cols for e in _flatten(n)]


def text_table(node, bx1):
    """Колонки без линий, выстроенные строками (перечень, «этап | срок | статус») -> таблица без границ."""
    elems = _flatten(node)
    if len(node.cols) < 2 or not elems or any(not isinstance(e, Seg) for e in elems):
        return None
    bounds = [-1e9] + list(node.bounds) + [1e9]

    def col_of(e):
        c = (e.x0 + e.x1) / 2
        return next(i for i in range(len(bounds) - 1) if bounds[i] <= c < bounds[i + 1])

    segs = sorted(elems, key=lambda e: (e.baseline, e.x0))
    rows = []
    for e in segs:
        if rows and abs(rows[-1]['base'] - e.baseline) <= max(2.0, .45 * e.size):
            rows[-1]['segs'].append(e)
        else:
            rows.append({'base': e.baseline, 'segs': [e], 'size': e.size})
    # перенесённый текст ячейки: строка, где заполнена одна колонка и она вплотную под такой же ячейкой выше
    merged = []
    for r in rows:
        cols_here = {col_of(e) for e in r['segs']}
        prev = merged[-1] if merged else None
        if (prev and len(cols_here) == 1 and r['base'] - prev['base'] <= 1.55 * max(r['size'], prev['size'])
                and cols_here <= {col_of(e) for e in prev['segs']}
                and len({col_of(e) for e in prev['segs']}) >= 2):
            prev['segs'] += r['segs']
            prev['last'] = r['base']
        else:
            r['last'] = r['base']
            merged.append(r)
    rows = merged
    if len(rows) < 3:
        return None
    populated = sum(1 for r in rows if len({col_of(e) for e in r['segs']}) >= 2)
    if populated < .7 * len(rows):
        return None
    ncols = len(node.cols)
    left = min(c[0] for c in node.cols)
    xs = [left] + list(node.bounds) + [max(bx1, node.cols[-1][1])]
    tops = [min(e.y0 for e in r['segs']) for r in rows]
    bottoms = [max(e.y1 for e in r['segs']) for r in rows]
    ys = [tops[0]] + [(bottoms[i - 1] + tops[i]) / 2 for i in range(1, len(rows))] + [bottoms[-1]]
    cells = []
    for ri, r in enumerate(rows):
        by_col = {}
        for e in r['segs']:
            by_col.setdefault(col_of(e), []).append(e)
        for ci in range(ncols):
            cells.append(Cell(ri, ci, ri, ci, (xs[ci], ys[ri], xs[ci + 1], ys[ri + 1]), by_col.get(ci, [])))
    return Table((xs[0], ys[0], xs[-1], ys[-1]), xs, ys, cells, 'layout',
                 base=statistics.median(e.size for e in segs))


def render_cols(node, bx0, bx1, flow):
    """Колонки -> одна строка невидимой таблицы; позиции абзацев внутри ячеек считаются от верха строки."""
    elems0 = _flatten(node)
    tt = None
    if len(elems0) >= 3 and all(isinstance(e, Seg) for e in elems0):
        tt = table_from_lines(elems0, bx1)       # самая тонкая сетка колонок — по пустым полосам между словами
    tt = tt or text_table(node, bx1)
    if tt:
        apply_fills(tt, flow.fills)
        return render_table(tt, bx0, flow)
    elems = _flatten(node)
    row_bottom = max(e.y1 for e in elems)
    left = min(c[0] for c in node.cols)
    # границы ячеек — середины пустых полос между колонками; крайние — по содержимому и правому полю
    edges = [left] + list(node.bounds) + [max(bx1, node.cols[-1][1])]
    widths = [edges[i + 1] - edges[i] for i in range(len(node.cols))]
    # проход 1: верх строки = самый высокий первый абзац среди колонок; проход 2: итоговый HTML
    probe_top = min(e.y0 for e in elems)
    tops = []
    for i, (_, _, sub) in enumerate(node.cols):
        pf = Flow(probe_top, flow.page_just, [Rule(r.x0, r.x1, r.y) for r in flow.rules], flow.content_w, flow.fills)
        render_node(sub, edges[i], edges[i + 1], pf)
        if pf.first_top is not None:
            tops.append(pf.first_top)
    row_top = min(tops) if tops else probe_top
    if flow.first_top is None:
        flow.first_top = row_top
    sb = max(0.0, row_top - flow.bottom)
    tds = []
    for i, (cx0, cx1, sub) in enumerate(node.cols):
        sub_flow = Flow(row_top, flow.page_just, flow.rules, flow.content_w, flow.fills)
        inner = render_node(sub, edges[i], edges[i + 1], sub_flow)
        tds.append(f'<td style="vertical-align:top">{inner}</td>')
    ml = max(0.0, edges[0] - bx0)
    style = _style(width=pt(sum(widths)), margin_left=pt(ml) if ml >= 1 else None, margin_top=pt(sb) if sb >= 1 else None)
    cols = ''.join(f'<col style="width:{pt(w)}">' for w in widths)
    flow.bottom = row_bottom
    return f'<table class="gd-layout" style="{style}"><colgroup>{cols}</colgroup><tr>{"".join(tds)}</tr></table>'


def page_just_flag(elems):
    """Есть ли на странице «выключенный по ширине» текст (≥3 строк с одним правым краем)."""
    segs = [e for e in elems if isinstance(e, Seg)]
    if not segs:
        return False
    lines = make_lines(segs)
    run = []
    for l in lines:
        if run and abs(run[-1].x1 - l.x1) <= 1.6 and abs(run[-1].x0 - l.x0) <= 3.5:
            run.append(l)
        else:
            run = [l]
        if len(run) >= 3:
            return True
    return False


def render_page(page, meta, first_top):
    """-> (html, верх первого элемента); first_top — где начинается поток (верхнее поле Word)."""
    elems = [e for e in page.elems]
    if not elems:
        return '', None
    # картинки, перекрывающие текст или таблицу (печати, подписи), не должны сдвигать текст: их «привязываем» к абзацам
    others = [e for e in elems if not isinstance(e, Img)]
    floats, flowing = [], []
    for e in elems:
        if isinstance(e, Img) and any(_overlap(e, o, 2.0) for o in others):
            floats.append(e)
        else:
            flowing.append(e)
    node = xy_tree(flowing)
    flow = Flow(first_top, page_just_flag(flowing), [Rule(r.x0, r.x1, r.y) for r in page.rules],
                page.width - meta.ml - meta.mr, page.fills)
    flow.floats = sorted(floats, key=lambda f: f.y0)
    html_ = render_node(node, meta.ml, page.width - meta.mr, flow)
    if flow.floats:       # картинки ниже всего текста страницы — в пустой абзац-якорь
        html_ += ('<p style="margin:0;line-height:1pt;font-size:1pt;position:relative">'
                  + ''.join(_float_img(f, flow.bottom, flow.bottom, meta.ml) for f in flow.floats) + '</p>')
    return html_, flow.first_top


def compute_meta(pages):
    """Поля страницы Word по расположению содержимого оригинала (чтобы отступы совпали)."""
    xs0, xs1, tops, bottoms = [], [], [], []
    w = max(p.width for p in pages)
    h = max(p.height for p in pages)
    for p in pages:
        for e in p.elems:
            xs0.append(e.x0)
            xs1.append(e.x1)
            tops.append(e.y0)
            bottoms.append(e.y1)
    if not xs0:
        return Meta(w=w, h=h)
    ml = max(14.0, min(xs0))
    mr = max(14.0, w - max(xs1))
    return Meta(w=w, h=h, ml=ml, mr=mr, mt=max(14.0, min(tops) - 2), mb=20.0)
