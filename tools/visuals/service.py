"""SVG-ассеты для самого веб-сервиса: логотип-печать, фон входа, фон приложения, иконка-заглушка.

Результат пишется в letters/static/letters/img/ (подключается из style.css и шаблонов).
Только тёмная тема: интерфейс сервиса всегда «ночной цитадельный».
"""
import math
import random

from .core import (THEMES, n, esc, head, text, common_defs, envelope_def, doc_def, smil, smil_tf,
                   smil_motion, Curve, rune)
from .parts import seal, ridge, ridge_markup, nearest_peak, beacon
from . import banner

T = THEMES['dark']
SW, SH = 1600, 900
D = banner.D


def _doc(w, h, title, desc, defs, live, still):
    return (head(w, h, T, title, desc).replace('<svg ', '<svg preserveAspectRatio="xMidYMid slice" ', 1) + defs +
            f'<g id="live">{live}</g><g id="still">{still}</g></svg>')


def _gradients():
    # те же градиенты, что в баннере (башня, Око, маяки, туман) + более тёмное небо для интерфейса
    return banner.defs(T) + (
        '<defs><linearGradient id="gSkyD" x1="0" y1="0" x2="0" y2="1"><stop offset="0" style="stop-color:var(--bg)"/>'
        '<stop offset=".72" style="stop-color:var(--muted);stop-opacity:.38"/><stop offset="1" style="stop-color:var(--bg)"/></linearGradient></defs>')


# ----------------------------------------------------------- логотип-печать --
def seal_svg():
    defs = common_defs(T, 128, 128)
    live = seal(64, 64, 52, True, 'lg', 3.2)
    still = seal(64, 64, 52, False, 'sg')
    return (head(128, 128, T, 'Печать Гендальфа', 'Золотая печать-сургуч с рунической монограммой.') + defs +
            f'<g id="live">{live}</g><g id="still">{still}</g></svg>')


def favicon_svg():
    from .core import seal_path
    from .parts import MONO_PATH
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="-48 -48 96 96"><title>Гендальф</title>'
            f'<circle r="46" fill="{T["bg"]}"/>'
            f'<path d="{seal_path(40)}" fill="{T["gold"]}" fill-opacity=".25" stroke="{T["gold"]}" stroke-width="3"/>'
            f'<circle r="29" fill="none" stroke="{T["gold"]}" stroke-width="2"/>'
            f'<path d="{MONO_PATH}" fill="none" stroke="{T["gold"]}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/></svg>')


# ---------------------------------------------------- иконка-заглушка --------
def envelope_svg():
    """конверт с руной, пульсирует и «сканируется» — для пустых панелей."""
    defs = common_defs(T, 120, 90) + f'<defs>{envelope_def()}</defs>'

    def sc(anim):
        pulse = smil('opacity', [(0, .25), (.5, .7), (1, .25)], 3, ease='io') if anim else ''
        scan = smil('y', [(0, -30), (1, 30)], 2.6, ease='io') if anim else ''
        scan_o = smil('opacity', [(0, 0), (.15, .9), (.85, .9), (1, 0)], 2.6, ease='lin') if anim else ''
        return (f'<g transform="translate(60,45)"><g filter="url(#glow)" opacity=".9"><use href="#env" class="sc" stroke-width="1.6" transform="scale(2.4)"/></g>'
                f'<rect x="-34" y="-24" width="68" height="48" rx="6" class="sc nf" stroke-width="7" opacity=".25">{pulse}</rect>'
                + rune(3, -5, -7, .9, 'sg', 2.2) +
                f'<g clip-path="url(#ec)"><rect x="-34" y="-30" width="68" height="3" class="fm" opacity="0">{scan}{scan_o}</rect></g>'
                f'<clipPath id="ec"><rect x="-34" y="-24" width="68" height="48"/></clipPath></g>')

    return (head(120, 90, T, 'Письмо', 'Конверт с руной') + defs +
            f'<g id="live">{sc(True)}</g><g id="still">{sc(False)}</g></svg>')


# ----------------------------------------------- Око для экрана «идёт OCR» ----
def eye_svg():
    """сканирующее Око: оверлей «Идёт распознавание»."""
    defs = banner.defs(T)

    def sc(anim):
        scan = (smil('y', [(0, -2), (.5, 58), (1, -2)], 1.8, ease='io') if anim else '')
        return (f'<g transform="translate(90,48) scale(1.2)">{banner.eye(anim).replace(f"translate({banner.CX},{banner.EYE_Y})", "translate(0,0)")}</g>'
                f'<rect x="20" y="0" width="140" height="2" class="fc" opacity=".0" transform="translate(0,45)">{scan}'
                + (smil('opacity', [(0, 0), (.5, .8), (1, 0)], 1.8, ease='io') if anim else '') + '</rect>')

    return (head(180, 100, T, 'Око сканирует', 'Анимация ожидания') + defs +
            f'<g id="live">{sc(True)}</g><g id="still">{sc(False)}</g></svg>')


# --------------------------------------------------------- общие слои ---------
def _stars(anim, rnd, ymax):
    out = []
    for k in range(70):
        x, y = rnd.uniform(5, SW - 5), rnd.uniform(5, ymax)
        r = rnd.choice([.7, .9, 1.1, 1.4])
        tw = smil('opacity', [(0, .2), (.5, 1), (1, .2)], rnd.uniform(2.5, 6), -rnd.uniform(0, 4)) if anim and k % 4 == 0 else ''
        out.append(f'<circle cx="{n(x)}" cy="{n(y)}" r="{r}" class="fc" opacity=".5">{tw}</circle>')
    return ''.join(out)


def _rain(anim, count, op, seed=4, speed=(6, 12)):
    rnd = random.Random(seed)
    cols = []
    for k in range(count):
        x = rnd.uniform(8, SW - 8)
        cnt = rnd.randint(5, 9)
        sp = rnd.choice([16, 17, 18])
        g = ''.join(rune(rnd.randint(0, 13), 0, q * sp, .8, 'sc' if (k + q) % 5 else 'sm', 1.2,
                         round(.2 + .6 * (q / cnt) ** 2, 2)) for q in range(cnt))
        dur = rnd.uniform(*speed)
        if anim:
            cols.append(f'<g opacity="{op}">{smil_tf("translate", [(0, (x, -cnt * sp)), (1, (x, SH + 20))], dur, -rnd.uniform(0, dur), "lin")}{g}</g>')
        else:
            cols.append(f'<g transform="translate({n(x)},{n(rnd.uniform(-20, SH - 150))})" opacity="{op * .9:.2f}">{g}</g>')
    return ''.join(cols)


def _ground(anim, y0):
    out = [f'<rect x="0" y="{y0}" width="{SW}" height="{SH - y0}" fill="url(#gGround)"/>',
           f'<path d="M0,{y0}H{SW}" class="sm" stroke-width="1.4" opacity=".7"/>']
    vx = ''.join(f'M{n(SW / 2 + (xe - SW / 2) * .08)},{y0}L{xe},{SH}' for xe in range(-1400, 3000, 140))
    out.append(f'<path d="{vx}" class="sm" stroke-width=".8" opacity=".25" fill="none"/>')
    K, P = 7, 7.0
    span = SH - y0
    for k in range(K):
        if anim:
            ys = [(i / 8, y0 + span * (i / 8) ** 1.9) for i in range(9)]
            a = smil('y1', ys, P, -k * P / K, 'lin') + smil('y2', ys, P, -k * P / K, 'lin') + \
                smil('opacity', [(0, 0), (.15, .2), (1, .6)], P, -k * P / K, 'lin')
            out.append(f'<line x1="0" x2="{SW}" y1="{y0}" y2="{y0}" class="sm" stroke-width="1" opacity="0">{a}</line>')
        else:
            p = (k + .5) / K
            out.append(f'<line x1="0" x2="{SW}" y1="{n(y0 + span * p ** 1.9)}" y2="{n(y0 + span * p ** 1.9)}" class="sm" stroke-width="1" opacity="{.6 * p:.2f}"/>')
    return ''.join(out)


def _mountains(anim, base_far, base_near, bx, amp=1.0, seed=2):
    far_peaks = [(x, a * amp, w) for x, a, w in
                 [(200, 90, 90), (460, 60, 70), (760, 40, 80), (1060, 100, 90), (1300, 70, 80), (1500, 80, 70), (90, 50, 60)]]
    far = ridge(base_far, far_peaks, step=32, seed=seed, jitter=8, xmax=SW + 40)
    near = ridge(base_near, [(100, 50, 70), (480, 60, 80), (900, 45, 70), (1280, 70, 80), (1560, 55, 60)], step=28, seed=seed + 6, jitter=6, xmax=SW + 40)
    out = [ridge_markup(far, SH, 'sm', 'url(#gMount)', seed=4, op=.75),
           ridge_markup(near, SH, 'sc', 'url(#gMount)', seed=9, op=.6)]
    for j, x in enumerate(bx):
        px, py = nearest_peak(far, x)
        out.append(beacon(px, py + 1, anim, .02 + j * .05, D, scale=1.4))
    return ''.join(out)


def _fog(anim):
    out = []
    for cx, cy, rx, ry, g, dx in [(400, 700, 560, 60, 'gFogM', 80), (1250, 740, 600, 70, 'gFogC', -90), (800, 640, 500, 50, 'gFogM', 50)]:
        mv = smil_tf('translate', [(0, (0, 0)), (.5, (dx, 0)), (1, (0, 0))], D) if anim else ''
        out.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="url(#{g})">{mv}</ellipse>')
    return ''.join(out)


def _flow(anim, left=True):
    """хаос писем слева и ровные документы справа (на экране входа)."""
    rnd = random.Random(12)
    out = []
    if left:
        for k in range(30):
            y0 = rnd.uniform(380, 860)
            y1 = max(380, min(860, y0 + rnd.uniform(-90, 90)))
            xe = rnd.uniform(380, 650)
            cv = Curve([(-40, y0), (xe / 2, (y0 + y1) / 2 + rnd.uniform(-50, 50)), (xe, y1)])
            dur, kind, s = rnd.uniform(8, 15), rnd.choice([0, 1, 1, 2]), rnd.uniform(1.0, 1.8)
            peak, beg, r0 = rnd.uniform(.4, .8), -rnd.uniform(0, 15), rnd.uniform(-60, 60)
            cls = 's' + banner.CLS[kind]
            if anim:
                out.append(f'<g opacity="0">{smil("opacity", [(0, 0), (.1, peak), (.7, peak), (1, 0)], dur, beg, "lin")}'
                           f'{smil_motion(cv.d(), [(0, 0), (1, 1)], dur, beg, "lin")}'
                           f'<g transform="scale({s:.2f})"><g>{smil_tf("rotate", [(0, r0), (1, r0 + rnd.choice([-1, 1]) * rnd.uniform(200, 400))], dur, beg, "lin")}'
                           f'<use href="#env" class="{cls}" stroke-width="1.5"/></g></g></g>')
            else:
                f = rnd.uniform(.05, .85)
                x, y = cv.at(f)
                out.append(f'<g opacity="{peak * min(1, f / .1, (1 - f) / .3):.2f}" transform="translate({n(x)},{n(y)}) scale({s:.2f}) rotate({n(r0 + f * 200)})"><use href="#env" class="{cls}" stroke-width="1.5"/></g>')
    for k, y in enumerate([760, 810, 860]):
        cv = Curve([(1000, y), (1700, y)])
        for j in range(5):
            dur = 11.0
            beg = -j * dur / 5 - k * 1.1
            cls = 's' + banner.CLS[k]
            if anim:
                out.append(f'<g opacity="0">{smil("opacity", [(0, 0), (.1, .85), (.85, .85), (1, 0)], dur, beg, "lin")}'
                           f'{smil_motion(cv.d(), [(0, 0), (1, 1)], dur, beg, "lin")}<use href="#doc" class="{cls}" stroke-width="1.4" transform="scale(1.1)"/></g>')
            else:
                x = 1000 + 700 * (j + .5) / 5
                out.append(f'<use href="#doc" class="{cls}" stroke-width="1.4" opacity=".8" transform="translate({n(x)},{y}) scale(1.1)"/>')
        out.append(f'<path d="M1000,{y}H1700" class="s{banner.CLS[k]} nf" stroke-width="1.4" opacity=".4"/>')
    return ''.join(out)


# ------------------------------------------------------------ фон входа -------
def login_bg():
    def scene(anim):
        rnd = random.Random(5)
        tw = f'translate(800,725) scale(1.9) translate(-{banner.CX},-345)'
        eyepart = banner.eye(anim) + banner.beam(anim)
        return (f'<rect width="{SW}" height="{SH}" fill="url(#gSkyD)"/>'
                f'<ellipse cx="800" cy="700" rx="900" ry="190" fill="url(#gHor)"/>'
                + _stars(anim, rnd, 520) + _mountains(anim, 700, 760, [180, 470, 1120, 1320, 1500]) + _fog(anim) +
                f'<g transform="{tw}">{banner.tower(anim, T)}{eyepart}</g>'
                + _ground(anim, 735) + _rain(anim, 26, .5) + _flow(anim))

    return _doc(SW, SH, 'Гендальф — вход', 'Ночная цитадель: башня с Оком, горы с маяками, письма и руны.',
                _gradients(), f'<g id="world">{scene(True)}</g>', scene(False))


# ---------------------------------------------------- фон приложения ----------
def app_bg():
    def scene(anim):
        rnd = random.Random(8)
        return (f'<rect width="{SW}" height="{SH}" fill="url(#gSkyD)"/>'
                f'<ellipse cx="800" cy="840" rx="1000" ry="170" fill="url(#gHor)" opacity=".8"/>'
                + _stars(anim, rnd, 600) + _mountains(anim, 830, 870, [260, 700, 1180, 1480], amp=.55, seed=3)
                + _fog(anim) + _ground(anim, 880) + _rain(anim, 14, .28, seed=9, speed=(9, 18)))

    return _doc(SW, SH, 'Гендальф — фон', 'Тихий ночной фон приложения: горы, маяки, редкий дождь рун.',
                _gradients(), scene(True), scene(False))


BUILD = [
    ('seal.svg', seal_svg), ('favicon.svg', favicon_svg), ('envelope.svg', envelope_svg),
    ('eye.svg', eye_svg), ('login-bg.svg', login_bg), ('app-bg.svg', app_bg),
]
