"""Разделитель, футер, typing-заголовок и полоса бейджей стека."""
import math
import random

from .core import (THEMES, n, esc, head, text, common_defs, envelope_def, doc_def, smil, smil_tf,
                   smil_discrete, ev, rune)
from .parts import seal, ridge, ridge_markup, nearest_peak, beacon

# ================= ТЕКСТЫ (правьте здесь) =================
FOOTER_LEFT = 'ГЕНДАЛЬФ'
FOOTER_RIGHT = 'скан → OCR → Word'
TYPING = [
    'Скан письма → Word-документ. Автоматически.',
    'OCR Tesseract: русский + английский.',
    'Таблицы остаются таблицами — с границами и ячейками.',
    'Реестр «СКАНЫ»: фильтры и поиск по всем столбцам.',
]
STACK = [  # (подпись, цвет c/m/g) — реальный стек из requirements.txt
    ('Python 3.11 / 3.12', 'c'), ('Django 5.1', 'g'), ('PyMuPDF', 'm'), ('Tesseract OCR', 'c'),
    ('python-docx', 'g'), ('Pillow', 'm'), ('NumPy', 'c'), ('SQLite', 'g'), ('Waitress', 'm'),
    ('WhiteNoise', 'c'),
]
# ==========================================================


def _wrap(t, w, h, title, desc, defs, live, still, fx=True):
    from .core import overlays
    return (head(w, h, t, title, desc) + defs +
            f'<g id="live">{live}</g><g id="still">{still}</g>' + (overlays(t, w, h) if fx else '') + '</svg>')


# ================================================================ divider ===
DW, DH = 1280, 44
DD = 9.0
DN = 9
KIND = ['c', 'm', 'g']


def divider(theme):
    t = THEMES[theme]
    defs = common_defs(t, DW, DH) + f"""<defs>{envelope_def()}{doc_def()}
<linearGradient id="gL" x1="0" y1="0" x2="1" y2="0"><stop offset="0" style="stop-color:var(--cyan);stop-opacity:0"/><stop offset=".3" style="stop-color:var(--cyan);stop-opacity:.55"/><stop offset=".5" style="stop-color:var(--red);stop-opacity:.9"/><stop offset=".7" style="stop-color:var(--gold);stop-opacity:.55"/><stop offset="1" style="stop-color:var(--gold);stop-opacity:0"/></linearGradient>
<radialGradient id="gE" cx=".5" cy=".5" r=".5"><stop offset="0" style="stop-color:var(--gold)"/><stop offset=".6" style="stop-color:var(--red)"/><stop offset="1" style="stop-color:var(--red);stop-opacity:.1"/></radialGradient>
</defs>"""

    def scene(anim):
        rnd = random.Random(31)
        out = [f'<rect x="0" y="21" width="{DW}" height="2" fill="url(#gL)" opacity=".9"/>',
               f'<rect x="0" y="20" width="{DW}" height="4" fill="url(#gL)" opacity=".25" filter="url(#glowS)"/>']
        for j in range(15):
            x = 40 + j * 82
            if abs(x - 640) < 50:
                continue
            up = j % 2
            out.append(rune(j * 2 + 3, x, 4 if up else 24, .7, 'sm' if j % 3 else 'sc', 1.1, .55))
        # Око в центре
        pul = smil('ry', [(0, 6), (.5, 8), (1, 6)], 2.2) if anim else ''
        slit = smil('rx', [(0, 1.6), (.5, 2.6), (1, 1.6)], 2.2) if anim else ''
        out.append(f'<g transform="translate(640,22)"><path d="M-26,0Q0,-17 26,0Q0,17 -26,0Z" class="sr nf" stroke-width="1.8" filter="url(#glow)"/>'
                   f'<circle r="8" fill="url(#gE)"/><ellipse rx="1.8" ry="6" class="fb">{pul}{slit}</ellipse></g>')
        out.append(f'<path d="M596,22L604,18L612,22L604,26Z M668,22L676,18L684,22L676,26Z" class="sg nf" stroke-width="1.2" opacity=".9"/>')
        # письма: хаос слева → порядок справа
        for i in range(DN):
            kind = KIND[i % 3]
            r = random.Random(40 + i)
            xs = [(0, -30), (.14, 130), (.28, 290), (.42, 470), (.5, 640)]
            ys = [22 + r.uniform(-17, 17) for _ in range(4)]
            rots = [r.uniform(-70, 70), r.uniform(-45, 45), r.uniform(-30, 30), r.uniform(-15, 15)]
            pos = [(0, (-30, ys[0])), (.14, (130, ys[1])), (.28, (290, ys[2])), (.42, (470, ys[3])), (.5, (640, 22)), (1, (1310, 22))]
            rot_k = [(0, rots[0]), (.14, rots[1]), (.28, rots[2]), (.42, rots[3]), (.5, 0), (1, 0)]
            sc_k = [(0, 1.15), (.5, .85), (1, .85)]
            op_k = [(0, 0), (.04, 1), (.96, 1), (1, 0)]
            if anim:
                beg = -i * DD / DN
                out.append(f'<g opacity="0">{smil("opacity", op_k, DD, beg, "lin")}'
                           f'<g>{smil_tf("translate", pos, DD, beg, "lin")}'
                           f'<g>{smil_tf("rotate", rot_k, DD, beg, "io")}<g>{smil_tf("scale", [(a, (b, b)) for a, b in sc_k], DD, beg, "lin")}'
                           f'<use href="#env" class="s{kind}" stroke-width="1.5"/></g></g></g></g>')
            else:
                u = (i + .5) / DN
                x, y = ev(pos, u, 'lin')
                rr = ev(rot_k, u, 'lin')
                s = ev(sc_k, u, 'lin')
                tag = 'doc' if u > .5 else 'env'
                out.append(f'<use href="#{tag}" class="s{kind}" stroke-width="1.5" transform="translate({n(x)},{n(y)}) rotate({n(rr)}) scale({s:.2f})"/>')
        return ''.join(out)

    return _wrap(t, DW, DH, 'Разделитель', 'Неоновая линия: хаотичные письма слева проходят под Оком и выстраиваются в ровный поток справа.',
                 defs, scene(True), scene(False), fx=False)


# ================================================================= footer ===
FW, FH = 1280, 120
FD = 8.0


def footer(theme):
    t = THEMES[theme]
    defs = common_defs(t, FW, FH) + f"""<defs>
<linearGradient id="gMount" x1="0" y1="0" x2="0" y2="1"><stop offset="0" style="stop-color:var(--muted);stop-opacity:.85"/><stop offset="1" style="stop-color:var(--bg)"/></linearGradient>
<radialGradient id="gBeacon" cx=".5" cy=".5" r=".5"><stop offset="0" style="stop-color:var(--gold);stop-opacity:.75"/><stop offset="1" style="stop-color:var(--gold);stop-opacity:0"/></radialGradient>
<linearGradient id="gShaft" x1="0" y1="1" x2="0" y2="0"><stop offset="0" style="stop-color:var(--gold);stop-opacity:.7"/><stop offset="1" style="stop-color:var(--gold);stop-opacity:0"/></linearGradient>
<radialGradient id="gHorF" cx=".5" cy=".5" r=".5"><stop offset="0" style="stop-color:var(--magenta);stop-opacity:{.4 * t['haze']:.2f}"/><stop offset="1" style="stop-color:var(--magenta);stop-opacity:0"/></radialGradient>
<linearGradient id="gTop" x1="0" y1="0" x2="1" y2="0"><stop offset="0" style="stop-color:var(--cyan);stop-opacity:0"/><stop offset=".5" style="stop-color:var(--cyan);stop-opacity:.7"/><stop offset="1" style="stop-color:var(--cyan);stop-opacity:0"/></linearGradient>
</defs>"""
    peaks = [(320, 22, 45), (470, 14, 40), (860, 24, 50), (1010, 20, 40), (1130, 16, 40), (100, 12, 40), (640, 10, 70), (1230, 14, 30)]
    far = ridge(104, peaks, step=24, seed=12, jitter=3)
    bx = [110, 320, 470, 860, 1010, 1130, 1230]

    def scene(anim):
        rnd = random.Random(2)
        out = [f'<rect x="0" y="0" width="{FW}" height="{FH}" class="fb"/>',
               f'<rect x="0" y="0" width="{FW}" height="1.6" fill="url(#gTop)"/>',
               f'<ellipse cx="640" cy="104" rx="560" ry="40" fill="url(#gHorF)"/>',
               ridge_markup(far, FH, 'sm', 'url(#gMount)', seed=6, op=.75)]
        for j, x in enumerate(bx):
            px, py = nearest_peak(far, x)
            out.append(beacon(px, py + 1, anim, .04 + j * .075, FD, scale=.8, shaft=False))
        # дождь рун — редкий
        for k in range(10):
            x = rnd.uniform(10, FW - 10)
            cnt = 4
            g = ''.join(rune(rnd.randint(0, 13), 0, q * 13, .6, 'sc', 1, round(.2 + .5 * (q / cnt) ** 2, 2)) for q in range(cnt))
            if anim:
                dur = rnd.uniform(5, 9)
                out.append(f'<g opacity=".5">{smil_tf("translate", [(0, (x, -60)), (1, (x, FH + 10))], dur, -rnd.uniform(0, dur), "lin")}{g}</g>')
            else:
                out.append(f'<g transform="translate({n(x)},{n(rnd.uniform(0, 80))})" opacity=".4">{g}</g>')
        out.append(seal(640, 46, 30, anim, 'f' + ('l' if anim else 's'), 3.2))
        out.append(text(48, 54, FOOTER_LEFT, 22, 'fg', 'start', cw=.7, extra='filter="url(#glowS)"'))
        out.append(text(FW - 48, 54, FOOTER_RIGHT, 15, 'fc', 'end', cw=.62))
        return ''.join(out)

    return _wrap(t, FW, FH, 'Гендальф — футер',
                 'Золотая печать с руной пульсирует, на горных вершинах цепочкой вспыхивают маяки.',
                 defs, scene(True), scene(False))


# ================================================================= typing ===
TW, TH = 860, 48
CW = 12.4  # ширина символа при размере 20


def typing(theme):
    t = THEMES[theme]
    P = 4.2
    T = P * len(TYPING)
    defs = common_defs(t, TW, TH)
    clips = []
    items = []
    for j, phrase in enumerate(TYPING):
        s = '> ' + phrase
        w = len(s) * CW
        x0 = (TW - w) / 2
        a = j * P / T
        ty = 1.5 / T
        hold = 2.0 / T
        er = .5 / T
        steps = len(s)
        # дискретные шаги набора
        kt = [(0, 0), (a, 0)]
        for q in range(1, steps + 1):
            kt.append((a + ty * q / steps, q * CW))
        kt.append((a + ty + hold, steps * CW))
        kt.append((a + ty + hold + er, 0))
        kt.append((1, 0))
        # убрать повторы ключей
        clean = []
        for u, v in kt:
            if clean and u <= clean[-1][0]:
                u = clean[-1][0] + 1e-5
            clean.append((u, v))
        clean[-1] = (1, 0)
        clean[0] = (0, 0)
        wdisc = smil_discrete('width', clean, T)
        xdisc = smil_discrete('x', [(u, round(x0 + v, 1)) for u, v in clean], T)
        # одинаково для курсора (смещён вправо) — мигание отдельно
        clips.append(f'<clipPath id="tc{j}"><rect x="{n(x0)}" y="0" width="0" height="{TH}">{wdisc}</rect></clipPath>')
        items.append(f'<g clip-path="url(#tc{j})">{text(x0, 31, s, 20, "fc", "start", cw=CW / 20)}</g>'
                     f'<rect x="{n(x0)}" y="11" width="9" height="24" class="fg" opacity="0" filter="url(#glowS)">{xdisc}'
                     f'{smil_discrete("opacity", [(0, 0), (max(a - 1e-4, 0), 0), (a, 1), (a + ty + hold + er, 0), (1, 0)], T) if a > 0 else smil_discrete("opacity", [(0, 1), (a + ty + hold + er, 0), (1, 0)], T)}</rect>')
    live = ''.join(clips) + ''.join(items)
    s0 = '> ' + TYPING[0]
    x0 = (TW - len(s0) * CW) / 2
    still = text(x0, 31, s0, 20, 'fc', 'start', cw=CW / 20) + f'<rect x="{n(x0 + len(s0) * CW)}" y="11" width="9" height="24" class="fg"/>'
    # без overlays: текст должен быть чистым
    return (head(TW, TH, t, 'Гендальф — слоган', ' / '.join(TYPING)) + defs +
            f'<g id="live">{live}</g><g id="still">{still}</g></svg>')


# ================================================================== stack ===
SW, SH = 860, 90


def stack(theme):
    t = THEMES[theme]

    def scene(anim):
        out = []
        y = 8
        idx = 0
        for row in (STACK[:5], STACK[5:]):
            widths = [len(lbl) * 8.2 + 38 for lbl, _ in row]
            x = (SW - (sum(widths) + 10 * (len(row) - 1))) / 2
            for (lbl, c), w in zip(row, widths):
                glow = smil('opacity', [(0, .12), (.5, .42), (1, .12)], 3.4, -idx * .37) if anim else ''
                out.append(f'<g transform="translate({n(x)},{y})">'
                           f'<rect width="{n(w)}" height="30" rx="15" class="s{c} nf" stroke-width="5" opacity=".2">{glow}</rect>'
                           f'<rect width="{n(w)}" height="30" rx="15" style="fill:var(--muted)" fill-opacity=".7" class="s{c}" stroke-width="1.5"/>'
                           f'<circle cx="16" cy="15" r="3.2" class="f{c}"/>'
                           + text(28, 20, lbl, 13, 'f' + c, 'start', cw=.63) + '</g>')
                x += w + 10
                idx += 1
            y += 40
        return ''.join(out)

    return (head(SW, SH, t, 'Стек проекта', ', '.join(lbl for lbl, _ in STACK)) + common_defs(t, SW, SH) +
            f'<g id="live">{scene(True)}</g><g id="still">{scene(False)}</g></svg>')
