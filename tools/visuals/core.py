"""Общие кирпичики для генерации SVG: темы, SMIL-хелперы, руны, фильтры, кривые."""
import math
import random

# --------------------------------------------------------------------------
# ТЕМЫ (6 цветов палитры + служебные параметры)
# --------------------------------------------------------------------------
THEMES = {
    'dark': dict(
        bg='#05060f', gold='#ffb800', cyan='#00f0ff', magenta='#ff2bd6',
        red='#ff1a1a', muted='#1a2140',
        blend='screen', stars=1, grain_op=.07, scan_op=.14, vig_op=.78,
        shade='#05060f', haze=1.0,
    ),
    'light': dict(
        bg='#f5efe0', gold='#a56a00', cyan='#006f7a', magenta='#b0108f',
        red='#c40d0d', muted='#d8dcee',
        blend='normal', stars=0, grain_op=.10, scan_op=.05, vig_op=.35,
        shade='#006f7a', haze=.55,
    ),
}

MONO = ("ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',"
        "'DejaVu Sans Mono','Courier New',monospace")

EASE = {
    'io': '.42 0 .58 1',
    'out': '.12 .8 .3 1',
    'in': '.55 0 .9 .55',
    'lin': '0 0 1 1',
    'soft': '.45 .05 .55 .95',
}

KIND_CLS = ['c', 'm', 'g']  # текстовый PDF / скан (OCR) / таблица


def n(v):
    s = f'{v:.1f}'
    if s.endswith('.0'):
        s = s[:-2]
    return '0' if s == '-0' else s


def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def css_vars(t):
    return (f":root{{--bg:{t['bg']};--gold:{t['gold']};--cyan:{t['cyan']};"
            f"--magenta:{t['magenta']};--red:{t['red']};--muted:{t['muted']}}}")


def base_css(t):
    return css_vars(t) + """
.fb{fill:var(--bg)}.fg{fill:var(--gold)}.fc{fill:var(--cyan)}.fm{fill:var(--magenta)}.fr{fill:var(--red)}.fu{fill:var(--muted)}
.sg{stroke:var(--gold)}.sc{stroke:var(--cyan)}.sm{stroke:var(--magenta)}.sr{stroke:var(--red)}.su{stroke:var(--muted)}.sb{stroke:var(--bg)}
.nf{fill:none}
svg{stroke-linecap:round;stroke-linejoin:round}
text{font-family:""" + MONO.replace('"', "'") + """;font-weight:700}
#still{display:none}
@media (prefers-reduced-motion:reduce){#live{display:none}#still{display:inline}}
"""


def head(w, h, t, title, desc, extra_css=''):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" role="img" aria-labelledby="t d">\n'
            f'<title id="t">{esc(title)}</title><desc id="d">{esc(desc)}</desc>\n'
            f'<style>{base_css(t)}{extra_css}</style>\n')


# --------------------------------------------------------------------------
# ТЕКСТ с фиксированной шириной (не зависим от конкретного моноспейса)
# --------------------------------------------------------------------------
def text(x, y, s, size, cls='fc', anchor='start', cw=.62, extra='', inner=''):
    w = len(s) * size * cw
    return (f'<text x="{n(x)}" y="{n(y)}" font-size="{size}" class="{cls}" '
            f'text-anchor="{anchor}" textLength="{n(w)}" lengthAdjust="spacing" {extra}>{esc(s)}{inner}</text>')


# --------------------------------------------------------------------------
# SMIL
# --------------------------------------------------------------------------
def _fmt(v):
    if isinstance(v, str):
        return v
    if isinstance(v, (tuple, list)):
        return ','.join(n(a) for a in v)
    return n(v)


def _t(v):
    s = f'{v:.4f}'.rstrip('0').rstrip('.')
    return s if s else '0'


def _splines(ease, segs):
    if isinstance(ease, str):
        ease = [ease] * segs
    return ';'.join(EASE.get(e, e) for e in ease)


def _timing(dur, begin, repeat, freeze):
    b = f'{begin:g}s' if begin else '0s'
    s = f'dur="{dur:g}s" begin="{b}"'
    if repeat:
        s += ' repeatCount="indefinite"'
    if freeze:
        s += ' fill="freeze"'
    return s


def smil(attr, keys, dur, begin=0, ease='io', repeat=True, freeze=False, tag='animate', extra=''):
    """keys: [(u, value)], u в долях dur."""
    kt = ';'.join(_t(u) for u, _ in keys)
    vals = ';'.join(_fmt(v) for _, v in keys)
    sp = _splines(ease, len(keys) - 1)
    head_ = f'<animate attributeName="{attr}"' if tag == 'animate' else f'<animateTransform attributeName="transform" type="{attr}"'
    return (f'{head_} values="{vals}" keyTimes="{kt}" calcMode="spline" keySplines="{sp}" '
            f'{_timing(dur, begin, repeat, freeze)} {extra}/>')


def smil_tf(typ, keys, dur, begin=0, ease='io', repeat=True, freeze=False):
    return smil(typ, keys, dur, begin, ease, repeat, freeze, tag='tf')


def smil_discrete(attr, keys, dur, begin=0, repeat=True):
    kt = ';'.join(_t(u) for u, _ in keys)
    vals = ';'.join(str(v) for _, v in keys)
    return (f'<animate attributeName="{attr}" values="{vals}" keyTimes="{kt}" calcMode="discrete" '
            f'{_timing(dur, begin, repeat, False)}/>')


def smil_motion(path_d, keys, dur, begin=0, ease='io', rotate=False):
    kt = ';'.join(_t(u) for u, _ in keys)
    kp = ';'.join(_t(p) for _, p in keys)
    sp = _splines(ease, len(keys) - 1)
    rot = ' rotate="auto"' if rotate else ''
    return (f'<animateMotion path="{path_d}"{rot} keyPoints="{kp}" keyTimes="{kt}" calcMode="spline" '
            f'keySplines="{sp}" {_timing(dur, begin, True, False)}/>')


def bez_ease(name, x):
    """значение сглаживающей кривой cubic-bezier при прогрессе x (для статичного кадра)."""
    p = [float(v) for v in EASE.get(name, name).split()]
    x1, y1, x2, y2 = p

    def bx(t):
        return 3 * (1 - t) ** 2 * t * x1 + 3 * (1 - t) * t * t * x2 + t ** 3

    def by(t):
        return 3 * (1 - t) ** 2 * t * y1 + 3 * (1 - t) * t * t * y2 + t ** 3

    lo, hi = 0.0, 1.0
    for _ in range(30):
        mid = (lo + hi) / 2
        if bx(mid) < x:
            lo = mid
        else:
            hi = mid
    return by((lo + hi) / 2)


def ev(keys, u, ease='io'):
    """вычислить трек в момент u (для статичного кадра)."""
    if u <= keys[0][0]:
        return keys[0][1]
    for k in range(len(keys) - 1):
        u0, v0 = keys[k]
        u1, v1 = keys[k + 1]
        if u0 <= u <= u1:
            e = ease if isinstance(ease, str) else ease[k]
            f = 0 if u1 == u0 else bez_ease(e, (u - u0) / (u1 - u0))
            if isinstance(v0, (tuple, list)):
                return tuple(a + (b - a) * f for a, b in zip(v0, v1))
            return v0 + (v1 - v0) * f
    return keys[-1][1]


# --------------------------------------------------------------------------
# Кривые (Catmull-Rom → кубические Безье) + позиция по доле длины
# --------------------------------------------------------------------------
class Curve:
    def __init__(self, pts):
        self.pts = pts
        self.segs = []
        if len(pts) == 2:
            p0, p1 = pts
            self.segs.append((p0, ((2 * p0[0] + p1[0]) / 3, (2 * p0[1] + p1[1]) / 3),
                              ((p0[0] + 2 * p1[0]) / 3, (p0[1] + 2 * p1[1]) / 3), p1))
        else:
            ext = [pts[0]] + list(pts) + [pts[-1]]
            for i in range(1, len(ext) - 2):
                p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
                c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
                c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
                self.segs.append((p1, c1, c2, p2))
        # плоская выборка
        self.samples = [self.segs[0][0]]
        for s in self.segs:
            for k in range(1, 25):
                self.samples.append(self._pt(s, k / 24))
        self.cum = [0.0]
        for a, b in zip(self.samples, self.samples[1:]):
            self.cum.append(self.cum[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
        self.length = self.cum[-1]

    @staticmethod
    def _pt(s, t):
        p0, c1, c2, p1 = s
        mt = 1 - t
        return (mt ** 3 * p0[0] + 3 * mt * mt * t * c1[0] + 3 * mt * t * t * c2[0] + t ** 3 * p1[0],
                mt ** 3 * p0[1] + 3 * mt * mt * t * c1[1] + 3 * mt * t * t * c2[1] + t ** 3 * p1[1])

    def d(self):
        s0 = self.segs[0][0]
        out = [f'M{n(s0[0])},{n(s0[1])}']
        for _, c1, c2, p in self.segs:
            out.append(f'C{n(c1[0])},{n(c1[1])} {n(c2[0])},{n(c2[1])} {n(p[0])},{n(p[1])}')
        return ' '.join(out)

    def at(self, f):
        target = max(0, min(1, f)) * self.length
        for i in range(1, len(self.cum)):
            if self.cum[i] >= target:
                seg = self.cum[i] - self.cum[i - 1] or 1
                k = (target - self.cum[i - 1]) / seg
                a, b = self.samples[i - 1], self.samples[i]
                return (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k)
        return self.samples[-1]


# --------------------------------------------------------------------------
# Руны (вымышленные, не из фильмов): стебель + 2–3 ветви
# --------------------------------------------------------------------------
_RUNE_PARTS = ['M5,0L10,4L5,8', 'M5,3L10,7', 'M5,8L0,4', 'M5,16L10,11', 'M5,6L0,10',
               'M0,0L5,5', 'M5,0L0,5L5,10', 'M2,8H8', 'M5,4L10,0', 'M5,12L0,16',
               'M5,2L9,6L5,10L1,6Z']


def rune_paths(count=14, seed=11):
    rnd = random.Random(seed)
    out = []
    for i in range(count):
        parts = ['M5,0V16'] + rnd.sample(_RUNE_PARTS, rnd.choice([2, 2, 3]))
        out.append(f'<path id="r{i}" fill="none" d="{"".join(parts)}"/>')
    return ''.join(out)


def rune(i, x, y, s=1.0, cls='sc', sw=1.3, op=1, extra=''):
    o = f' opacity="{op}"' if op != 1 else ''
    return (f'<use href="#r{i % 14}" class="{cls}" stroke-width="{sw}" '
            f'transform="translate({n(x)},{n(y)}) scale({s:g})"{o} {extra}/>')


# --------------------------------------------------------------------------
# Общие defs: фильтры, паттерны
# --------------------------------------------------------------------------
def common_defs(t, W, H):
    return f"""<defs>
<filter id="glow" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur in="SourceGraphic" stdDeviation="2.6" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<filter id="glowS" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur in="SourceGraphic" stdDeviation="1.4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<filter id="glowL" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur in="SourceGraphic" stdDeviation="5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<filter id="grainf" x="0" y="0" width="1" height="1"><feTurbulence type="fractalNoise" baseFrequency=".85" numOctaves="1" seed="4" stitchTiles="stitch"/><feColorMatrix values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  1.6 0 0 0 -.62"/></filter>
<pattern id="grain" width="128" height="128" patternUnits="userSpaceOnUse"><rect width="128" height="128" filter="url(#grainf)" style="fill:{'#fff' if t['blend']=='screen' else '#3a2a00'}"/></pattern>
<pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="1.3" class="{'fb' if t['blend']=='screen' else 'fc'}"/></pattern>
<radialGradient id="gVig" cx=".5" cy=".5" r=".75"><stop offset=".55" style="stop-color:{t['shade']};stop-opacity:0"/><stop offset="1" style="stop-color:{t['shade']};stop-opacity:{t['vig_op']}"/></radialGradient>
{rune_paths()}
</defs>
"""


def overlays(t, W, H):
    return (f'<rect width="{W}" height="{H}" fill="url(#gVig)"/>'
            f'<rect width="{W}" height="{H}" fill="url(#scan)" opacity="{t["scan_op"]}"/>'
            f'<rect width="{W}" height="{H}" fill="url(#grain)" opacity="{t["grain_op"]}"/>')


def envelope_def(idn='env'):
    """письмо-конверт 24×17 (центр в 0,0); обводка наследуется от <use>."""
    return (f'<g id="{idn}"><rect x="-12" y="-8.5" width="24" height="17" rx="2" fill="none" stroke-width="4.5" opacity=".22"/>'
            f'<rect x="-12" y="-8.5" width="24" height="17" rx="2" style="fill:var(--muted)"/>'
            f'<path d="M-12,-8.5L0,1.5L12,-8.5" fill="none"/></g>')


def doc_def(idn='doc'):
    """готовый Word-документ 20×26 (центр 0,0)."""
    return (f'<g id="{idn}"><path d="M-10,-13H4L10,-7V13H-10Z" style="fill:var(--muted)"/>'
            f'<path d="M4,-13V-7H10M-6,-1H6M-6,4H6M-6,9H1" fill="none"/></g>')


def seal_path(R=40, lobes=22, wob=2.4):
    pts = []
    for k in range(180):
        a = k / 180 * math.tau
        r = R + wob * math.sin(lobes * a) + 1.0 * math.sin(3 * a + .6)
        pts.append((r * math.cos(a), r * math.sin(a)))
    return 'M' + 'L'.join(f'{n(x)},{n(y)}' for x, y in pts) + 'Z'
