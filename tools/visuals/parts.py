"""Повторно используемые элементы сцены: печать, маяки, горы, ворон."""
import math
import random

from .core import n, smil, smil_tf, seal_path, ev

# ---------------------------------------------------------------- печать ---
MONO_PATH = ('M-9,-17L-9,17M-9,-17L11,-9M-9,-1L10,-9M-9,6L7,14'
             'M-9,-17L-14,-21M11,-9L15,-14')


def seal(cx, cy, R, anim, uid='s', period=3.2):
    """золотая печать-сургуч с рунической монограммой; пульсирует как голограмма."""
    k = R / 40
    body = seal_path(40)
    pulse = ''
    ring = ''
    scan = ''
    glow = ''
    if anim:
        pulse = smil_tf('scale', [(0, (1, 1)), (.5, (1.045, 1.045)), (1, (1, 1))], period)
        ring = (smil('r', [(0, 44), (1, 60)], period, ease='out') +
                smil('opacity', [(0, .65), (1, 0)], period, ease='out'))
        scan = smil('y', [(0, -48), (1, 40)], period * 1.5, ease='io')
        glow = smil('opacity', [(0, .55), (.5, .95), (1, .55)], period)
    return f"""<g transform="translate({n(cx)},{n(cy)}) scale({k:g})">
<circle r="44" fill="none" class="sg" stroke-width="1.2" opacity=".0">{ring}</circle>
<g>{pulse}
<g filter="url(#glow)" opacity=".85">{('<animate attributeName="opacity" values=".6;1;.6" dur="%gs" repeatCount="indefinite"/>' % period) if anim else ''}
<path d="{body}" class="fg" fill-opacity=".16" stroke-width="2.2" style="stroke:var(--gold)"/>
</g>
<circle r="31" fill="none" class="sg" stroke-width="1.4" opacity=".9"/>
<circle r="27" fill="none" class="sg" stroke-width=".7" stroke-dasharray="2 3" opacity=".7"/>
<g class="sg" fill="none" stroke-width="3.2" filter="url(#glowS)"><path d="{MONO_PATH}"/></g>
<g clip-path="url(#sealClip{uid})"><rect x="-44" y="-48" width="88" height="3" class="fc" opacity=".8">{scan}</rect></g>
</g>
<clipPath id="sealClip{uid}"><circle r="30"/></clipPath>
</g>"""


# ----------------------------------------------------------------- горы ----
def ridge(base, peaks, step=26, seed=1, jitter=5):
    rnd = random.Random(seed)
    pts = []
    x = -20.0
    while x <= 1300:
        h = sum(a * math.exp(-abs(x - px) / w) for px, a, w in peaks)
        pts.append((x, base - h + rnd.uniform(-jitter, jitter)))
        x += step
    return pts


def ridge_markup(pts, base_y, line_cls, fill, facets=True, seed=3, op=.7, sw=1):
    """заливка + контур + «каркасные» грани (стиль synthwave)."""
    rnd = random.Random(seed)
    d = 'M' + 'L'.join(f'{n(x)},{n(y)}' for x, y in pts)
    out = [f'<path d="{d}L{n(pts[-1][0])},{base_y}L{n(pts[0][0])},{base_y}Z" fill="{fill}"/>']
    fac = []
    for i in range(0, len(pts) - 1):
        x, y = pts[i]
        if rnd.random() < .85:
            tx = x + rnd.choice([-34, -18, 0, 18, 34, 52])
            fac.append(f'M{n(x)},{n(y)}L{n(tx)},{base_y}')
        if rnd.random() < .5 and i + 2 < len(pts):
            fac.append(f'M{n(x)},{n(y)}L{n(pts[i + 2][0])},{n(pts[i + 2][1])}')
    if facets:
        out.append(f'<path d="{"".join(fac)}" class="{line_cls}" fill="none" stroke-width=".6" opacity="{op * .45:.2f}"/>')
    for off, o2 in ((0, 1), (12, .5), (26, .28)):
        dd = 'M' + 'L'.join(f'{n(x)},{n(y + off)}' for x, y in pts)
        out.append(f'<path d="{dd}" class="{line_cls}" fill="none" stroke-width="{sw}" opacity="{op * o2:.2f}"/>')
    return ''.join(out)


def nearest_peak(pts, x):
    best = min(pts, key=lambda p: abs(p[0] - x))
    return best


# ---------------------------------------------------------------- маяк -----
def beacon(x, y, anim, start_u, D, lit=None, scale=1.0, uid=''):
    """маяк Гондора: вспыхивает на start_u (доля цикла D), гаснет медленно."""
    a = start_u
    keys = [(0, .16), (a, .16), (min(a + .02, .97), 1), (min(a + .30, .98), .85), (min(a + .5, .99), .16), (1, .16)]
    # keyTimes должны возрастать — подчистим
    clean = []
    for u, v in keys:
        if clean and u <= clean[-1][0]:
            u = clean[-1][0] + .001
        clean.append((min(u, 1), v))
    clean[-1] = (1, .16)
    anim_g = smil('opacity', clean, D, ease='soft') if anim else ''
    op = '' if anim else f' opacity="{(lit if lit is not None else 1):g}"'
    flick = ''
    if anim:
        flick = smil_tf('scale', [(0, (1, 1)), (.5, (1, 1.18)), (1, (1, 1))], 0.9, ease='io')
    return f"""<g transform="translate({n(x)},{n(y)}) scale({scale:g})">
<path d="M-7,0L-5,-4H5L7,0Z" class="fu" stroke-width="1" style="stroke:var(--gold)" fill-opacity=".9"/>
<g{op}>{anim_g}
<circle cy="-12" r="19" fill="url(#gBeacon)"/>
<rect x="-1.2" y="-84" width="2.4" height="76" fill="url(#gShaft)"/>
<g transform="translate(0,-4)"><g>{flick}
<path d="M0,0C-6,-5 -3,-12 0,-19C3,-12 6,-5 0,0Z" class="fg" filter="url(#glowS)"/>
<path d="M0,-1C-2.5,-4 -1.2,-8 0,-11C1.2,-8 2.5,-4 0,-1Z" fill="#fff" opacity=".75"/></g></g>
</g></g>"""


# --------------------------------------------------------------- ворон ----
RAVEN_BODY = 'M-18,2Q-8,-8 6,-5Q14,-4 18,-1L27,1L18,3.5Q10,8 -2,8Q-12,8 -18,2Z'
RAVEN_TAIL = 'M-17,3L-31,-2L-28,4L-31,9L-16,6Z'
WING_UP = 'M-3,-5Q-5,-24 -19,-31Q-12,-16 0,-3Z'
WING_DN = 'M-3,-3Q-9,8 -20,16Q-8,10 0,0Z'


def raven_def(anim, idn='raven'):
    wing = f'<path d="{WING_UP}" class="fb" style="stroke:var(--cyan)" stroke-width="1.2">'
    if anim:
        wing += (f'<animate attributeName="d" values="{WING_UP};{WING_DN};{WING_UP}" '
                 f'dur=".62s" repeatCount="indefinite" calcMode="spline" keySplines=".4 0 .6 1;.4 0 .6 1"/>')
    wing += '</path>'
    return (f'<g id="{idn}">'
            f'<path d="{RAVEN_TAIL}" class="fb" style="stroke:var(--cyan)" stroke-width="1"/>'
            f'<path d="{RAVEN_BODY}" class="fb" style="stroke:var(--cyan)" stroke-width="1.4"/>'
            f'{wing}'
            f'<circle cx="12.6" cy="-2.4" r="3.6" class="fc" opacity=".28"/>'
            f'<circle cx="12.6" cy="-2.4" r="1.5" class="fc" filter="url(#glowS)"/></g>')
