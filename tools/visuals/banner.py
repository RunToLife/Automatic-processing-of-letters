"""Главный баннер 1280×400: хаос писем (слева) → Око-палантир → порядок (справа)."""
import math
import random

from .core import (THEMES, MONO, n, esc, head, text, common_defs, overlays, envelope_def, doc_def,
                   smil, smil_tf, smil_discrete, smil_motion, ev, Curve, rune)
from .parts import seal, ridge, ridge_markup, nearest_peak, beacon, raven_def

# ======================= ТЕКСТЫ БАННЕРА (правьте здесь) =======================
TEXTS = dict(
    title='ГЕНДАЛЬФ',
    caption='// входящие → порядок',
    slogan='Письма из сканов — в Word. Автоматически.',
    detail='PDF · OCR rus+eng · таблицы · реестр «СКАНЫ»',
    kinds=['ТЕКСТ-СЛОЙ', 'СКАН · OCR', 'ТАБЛИЦА'],       # подписи каналов
    tags=['ТЕКСТ-СЛОЙ', 'OCR rus+eng', 'ТАБЛИЦА'],          # метки голограмм
    out='.docx',
)
# ==============================================================================

W, H = 1280, 400
D = 12.0            # длина бесшовного цикла, с
NL = 8              # писем-«героев» в цикле
SLOT = D / NL
CX, GY = 640, 316   # центр башни / ось врат
HOLO_DY = -122
YS = [258, 316, 374]
SX = 1112           # x стопок
KINDS = [1, 0, 1, 2, 1, 0, 1, 2]
RAVEN_LETTERS = (1, 5)

CLS = ['c', 'm', 'g']


def fc(k):
    return 'f' + CLS[k]


def sc(k):
    return 's' + CLS[k]


# ------------------------------------------------------------------- defs ---
def defs(t):
    return f"""{common_defs(t, W, H)}<defs>
<linearGradient id="gSky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" style="stop-color:var(--bg)"/><stop offset=".7" style="stop-color:var(--muted);stop-opacity:.75"/><stop offset="1" style="stop-color:var(--bg)"/></linearGradient>
<radialGradient id="gHor" cx=".5" cy=".5" r=".5"><stop offset="0" style="stop-color:var(--magenta);stop-opacity:{.5*t['haze']:.2f}"/><stop offset="1" style="stop-color:var(--magenta);stop-opacity:0"/></radialGradient>
<linearGradient id="gMount" x1="0" y1="0" x2="0" y2="1"><stop offset="0" style="stop-color:var(--muted);stop-opacity:.8"/><stop offset="1" style="stop-color:var(--bg);stop-opacity:1"/></linearGradient>
<linearGradient id="gTower" x1="0" y1="0" x2="0" y2="1"><stop offset="0" style="stop-color:var(--muted)"/><stop offset="1" style="stop-color:var(--bg)"/></linearGradient>
<linearGradient id="gBeam" x1="0" y1="0" x2="0" y2="1"><stop offset="0" style="stop-color:var(--red);stop-opacity:.95"/><stop offset=".45" style="stop-color:var(--gold);stop-opacity:.5"/><stop offset="1" style="stop-color:var(--cyan);stop-opacity:.25"/></linearGradient>
<radialGradient id="gEye" cx=".5" cy=".5" r=".5"><stop offset="0" style="stop-color:var(--gold)"/><stop offset=".55" style="stop-color:var(--red)"/><stop offset="1" style="stop-color:var(--red);stop-opacity:.15"/></radialGradient>
<radialGradient id="gBeacon" cx=".5" cy=".5" r=".5"><stop offset="0" style="stop-color:var(--gold);stop-opacity:.75"/><stop offset="1" style="stop-color:var(--gold);stop-opacity:0"/></radialGradient>
<linearGradient id="gShaft" x1="0" y1="1" x2="0" y2="0"><stop offset="0" style="stop-color:var(--gold);stop-opacity:.7"/><stop offset="1" style="stop-color:var(--gold);stop-opacity:0"/></linearGradient>
<linearGradient id="gPortal" x1="0" y1="0" x2="0" y2="1"><stop offset="0" style="stop-color:var(--gold);stop-opacity:.05"/><stop offset="1" style="stop-color:var(--gold);stop-opacity:.35"/></linearGradient>
<radialGradient id="gFogC" cx=".5" cy=".5" r=".5"><stop offset="0" style="stop-color:var(--cyan);stop-opacity:{.16*t['haze']:.2f}"/><stop offset="1" style="stop-color:var(--cyan);stop-opacity:0"/></radialGradient>
<radialGradient id="gFogM" cx=".5" cy=".5" r=".5"><stop offset="0" style="stop-color:var(--magenta);stop-opacity:{.16*t['haze']:.2f}"/><stop offset="1" style="stop-color:var(--magenta);stop-opacity:0"/></radialGradient>
<linearGradient id="gGround" x1="0" y1="0" x2="0" y2="1"><stop offset="0" style="stop-color:var(--magenta);stop-opacity:.0"/><stop offset="1" style="stop-color:var(--magenta);stop-opacity:.16"/></linearGradient>
{envelope_def()}{doc_def()}{raven_def(True)}
<text id="ttl" x="48" y="122" font-size="72" textLength="{n(len(TEXTS['title'])*72*.66)}" lengthAdjust="spacing">{esc(TEXTS['title'])}</text>
</defs>
"""


# -------------------------------------------------------------- пейзаж ------
def sky(anim, t):
    rnd = random.Random(5)
    out = [f'<rect width="{W}" height="{H}" fill="url(#gSky)"/>',
           f'<ellipse cx="{CX}" cy="318" rx="560" ry="110" fill="url(#gHor)"/>']
    if t['stars']:
        for k in range(46):
            x, y = rnd.uniform(10, W - 10), rnd.uniform(6, 230)
            r = rnd.choice([.6, .8, 1.0, 1.2])
            tw = ''
            if anim and k % 4 == 0:
                tw = smil('opacity', [(0, .25), (.5, 1), (1, .25)], rnd.uniform(2.2, 5), -rnd.uniform(0, 3))
            out.append(f'<circle cx="{n(x)}" cy="{n(y)}" r="{r}" class="fc" opacity=".55">{tw}</circle>')
    return ''.join(out)


BEACON_X = [150, 430, 870, 1035, 1205]


def mountains(anim, t):
    far_peaks = [(150, 46, 55), (300, 22, 40), (430, 52, 50), (610, 18, 50), (700, 30, 60), (870, 62, 55),
                 (1035, 48, 50), (1205, 42, 45), (1100, 20, 40)]
    far = ridge(292, far_peaks, step=26, seed=2)
    near = ridge(322, [(70, 30, 45), (250, 36, 55), (520, 20, 40), (780, 24, 40), (960, 38, 50), (1160, 30, 45)],
                 step=22, seed=8, jitter=4)
    parts_far = ridge_markup(far, 345, 'sm', 'url(#gMount)', seed=4, op=.75)
    parts_near = ridge_markup(near, 350, 'sc', 'url(#gMount)', seed=9, op=.62)
    bcs = []
    for j, bx in enumerate(BEACON_X):
        px, py = nearest_peak(far, bx)
        bcs.append(beacon(px, py + 1, anim, .02 + j * .045, D, scale=1.0))
    def par(content, amp, dur):
        if not anim:
            return f'<g>{content}</g>'
        return f'<g>{smil_tf("translate", [(0, (0, 0)), (.5, (-amp, 0)), (1, (0, 0))], dur)}{content}</g>'
    return par(parts_far + ''.join(bcs), 6, D) + par(parts_near, 11, D)


def fog(anim):
    items = [(300, 300, 380, 40, 'gFogM', 60), (900, 320, 420, 46, 'gFogC', -70), (640, 270, 300, 30, 'gFogM', 40)]
    out = []
    for cx, cy, rx, ry, g, dx in items:
        mv = smil_tf('translate', [(0, (0, 0)), (.5, (dx, 0)), (1, (0, 0))], D) if anim else ''
        out.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="url(#{g})">{mv}</ellipse>')
    return ''.join(out)


# ---------------------------------------------------------------- башня -----
TIERS = [(292, 345, 120), (246, 292, 92), (204, 246, 68), (168, 204, 48), (138, 168, 30)]


def tower(anim, t):
    rnd = random.Random(21)
    out = []
    # силуэт и грани
    fill = []
    edge = []
    over = []
    for idx, (y0, y1, hw) in enumerate(TIERS):
        pts = f'{CX - hw},{y1} {CX - hw + 5},{y0} {CX + hw - 5},{y0} {CX + hw},{y1}'
        fill.append(f'<polygon points="{pts}" fill="url(#gTower)"/>')
        edge.append(f'<polygon points="{pts}" fill="none"/>')
        a = .04 + idx * .035
        wave = smil('opacity', [(0, 0), (a, 0), (a + .03, 1), (a + .14, 0), (1, 0)], D, ease='soft') if anim else ''
        over.append(f'<polygon points="{pts}" fill="none" class="sg" stroke-width="2.4" opacity="{0 if anim else 0}">{wave}</polygon>')
    # шпиль и боковые башенки
    spire = f'{CX - 12},138 {CX},84 {CX + 12},138'
    fill.append(f'<polygon points="{spire}" fill="url(#gTower)"/>')
    edge.append(f'<polygon points="{spire}" fill="none"/>')
    for sx in (-96, 96):
        tp = f'{CX + sx - 10},292 {CX + sx - 10},266 {CX + sx},244 {CX + sx + 10},266 {CX + sx + 10},292'
        fill.append(f'<polygon points="{tp}" fill="url(#gTower)"/>')
        edge.append(f'<polygon points="{tp}" fill="none"/>')
    out.append(''.join(fill))
    # центральное ребро и «поясы» ярусов
    belts = ''.join(f'M{CX - hw},{y0}H{CX + hw}' for y0, y1, hw in TIERS)
    out.append(f'<path d="M{CX},84V292" class="sm" stroke-width=".8" opacity=".35"/>'
               f'<path d="{belts}" class="sc" stroke-width=".7" opacity=".4" fill="none"/>')
    out.append(f'<g class="sc" stroke-width="5" opacity=".2">{"".join(edge)}</g>'
               f'<g class="sc" stroke-width="1.5" opacity=".95">{"".join(edge)}</g>')
    out.append(''.join(over))
    # окна
    wins = []
    layout = [
        (0, 306, [-104, -84, -64, 64, 84, 104]), (0, 326, [-104, -84, -64, 64, 84, 104]),
        (1, 258, range(-72, 73, 24)), (1, 276, range(-72, 73, 24)),
        (2, 214, range(-48, 49, 24)), (2, 230, range(-48, 49, 24)),
        (3, 176, [-24, 0, 24]), (3, 190, [-24, 0, 24]),
        (4, 148, [-10, 10]),
    ]
    for _, y, cols in layout:
        for c in cols:
            if rnd.random() < .12:
                continue
            base = rnd.choice([.9, .55, .35, 1.0])
            if anim:
                seq = [rnd.choice([.12, .9, .55, 1, .3]) for _ in range(5)]
                seq.append(seq[0])
                dur = rnd.uniform(2.4, 7)
                a = smil('opacity', [(k / 5, v) for k, v in enumerate(seq)], dur, -rnd.uniform(0, 6), ease='soft')
                wins.append(f'<rect x="{CX + c - 3}" y="{y}" width="6" height="9" rx="1" class="fg" opacity="{base}">{a}</rect>')
            else:
                wins.append(f'<rect x="{CX + c - 3}" y="{y}" width="6" height="9" rx="1" class="fg" opacity="{base}"/>')
    out.append(''.join(wins))
    return ''.join(out)


def gate(anim):
    scan = ''
    if anim:
        scan = (smil('y', [(0, 292), (.55, 338), (1, 338)], SLOT, ease='io') +
                smil('opacity', [(0, 0), (.04, .95), (.5, .95), (.56, 0), (1, 0)], SLOT, ease='lin'))
    return (f'<path d="M{CX - 20},345V312A20,20 0 0 1 {CX + 20},312V345Z" fill="url(#gPortal)"/>'
            f'<path d="M{CX - 28},345V312A28,28 0 0 1 {CX + 28},312V345" class="nf sg" stroke-width="3"/>'
            f'<path d="M{CX - 28},345V312A28,28 0 0 1 {CX + 28},312V345" class="nf sg" stroke-width="9" opacity=".22"/>'
            f'<path d="M{CX - 36},345V310A36,36 0 0 1 {CX + 36},310V345" class="nf sc" stroke-width="1" opacity=".55"/>'
            f'<rect x="{CX - 20}" y="292" width="40" height="2.2" class="fc" opacity="0">{scan}</rect>')


def ground(anim, t):
    out = [f'<rect x="0" y="345" width="{W}" height="55" fill="url(#gGround)"/>',
           f'<path d="M0,345H{W}" class="sm" stroke-width="1.2" opacity=".7"/>']
    # перспективные радиальные линии
    vx = []
    for xe in range(-900, 2200, 110):
        x0 = CX + (xe - CX) * .08
        vx.append(f'M{n(x0)},345L{xe},400')
    out.append(f'<path d="{"".join(vx)}" class="sm" stroke-width=".7" opacity=".28" fill="none"/>')
    # бегущие поперечные линии
    K, P = 6, 6.0
    for k in range(K):
        if anim:
            samples = [(i / 8, 345 + 55 * (((k / K) + i / 8 * 1.0) % 1.0 if False else 0)) for i in range(0)]
        # анимация y: фаза p от 0 до 1 за P секунд, сдвиг begin = -k*P/K
        ys = [(i / 8, 345 + 55 * (i / 8) ** 1.9) for i in range(9)]
        if anim:
            a = smil('y1', ys, P, -k * P / K, ease='lin') + smil('y2', ys, P, -k * P / K, ease='lin')
            a += smil('opacity', [(0, 0), (.15, .2), (1, .7)], P, -k * P / K, ease='lin')
            out.append(f'<line x1="0" x2="{W}" y1="345" y2="345" class="sm" stroke-width=".9" opacity="0">{a}</line>')
        else:
            p = (k + .5) / K
            y = 345 + 55 * p ** 1.9
            out.append(f'<line x1="0" x2="{W}" y1="{n(y)}" y2="{n(y)}" class="sm" stroke-width=".9" opacity="{.7 * p:.2f}"/>')
    return ''.join(out)


# ------------------------------------------------------- дождь рун ----------
def rain(anim, t):
    rnd = random.Random(17)
    cols = []
    for k in range(20):
        x = rnd.uniform(8, W - 8)
        cnt = rnd.randint(5, 8)
        sp = rnd.choice([14, 15, 16])
        glyphs = []
        for g in range(cnt):
            op = .22 + .6 * (g / cnt) ** 2
            cl = 'sc' if (k + g) % 5 else 'sm'
            glyphs.append(rune(rnd.randint(0, 13), 0, g * sp, .7, cl, 1.1, round(op, 2)))
        dur = rnd.uniform(5.5, 10)
        if anim:
            m = smil_tf('translate', [(0, (x, -cnt * sp)), (1, (x, H + 10))], dur, -rnd.uniform(0, dur), ease='lin')
            cols.append(f'<g opacity=".55">{m}{"".join(glyphs)}</g>')
        else:
            cols.append(f'<g transform="translate({n(x)},{n(rnd.uniform(-20, 330))})" opacity=".5">{"".join(glyphs)}</g>')
    return ''.join(cols)


# ---------------------------------------------- каналы, стопки, подписи -------
CH = []
for _ys in YS:
    if _ys == GY:
        CH.append(Curve([(CX, GY), (SX, GY)]))
    else:
        CH.append(Curve([(CX, GY), (CX + 95, GY), (CX + 150, (GY + _ys) / 2), (CX + 215, _ys), (SX - 120, _ys), (SX, _ys)]))


def channels(anim, t):
    out = []
    for k, c in enumerate(CH):
        d = c.d()
        flow = (f'<animate attributeName="stroke-dashoffset" values="0;-16" dur="0.8s" repeatCount="indefinite"/>' if anim else '')
        out.append(f'<path d="{d}" class="{sc(k)} nf" stroke-width="9" opacity=".10"/>'
                   f'<path d="{d}" class="{sc(k)} nf" stroke-width="1.6" opacity=".75"/>'
                   f'<path d="{d}" class="{sc(k)} nf" stroke-width="2.6" stroke-dasharray="1.5 14.5" opacity=".95">{flow}</path>')
    return ''.join(out)


def stacks(anim, t):
    out = []
    for k, y in enumerate(YS):
        sheets = []
        for s in range(5):
            dx = (-1.5, 1.5, -.5, 1, 0)[s]
            sheets.append(f'<rect x="{SX - 24 + dx}" y="{y + 8 - s * 3.6}" width="48" height="12" rx="1.5" '
                          f'class="{sc(k)}" style="fill:var(--muted)" stroke-width="1" opacity="{.55 + s * .11:.2f}"/>')
        top = (f'<path d="M{SX - 16},{y - 11}H{SX + 16}M{SX - 16},{y - 6}H{SX + 10}M{SX - 16},{y - 1}H{SX + 13}" class="{sc(k)}" stroke-width="1.1" opacity=".8" fill="none"/>')
        out.append(f'<path d="M{SX - 34},{y + 12}H{SX + 34}" class="{sc(k)}" stroke-width="2" filter="url(#glowS)"/>'
                   f'{"".join(sheets)}{top}')
        out.append(text(SX + 44, y - 1, TEXTS['kinds'][k], 11, fc(k), 'start', extra='opacity=".95"'))
        out.append(text(SX + 44, y + 13, TEXTS['out'], 10, 'fc', 'start', extra='opacity=".7"'))
    return ''.join(out)


def landing_glows(anim):
    if not anim:
        return ''
    out = []
    for i in range(NL):
        k = KINDS[i]
        y = YS[k]
        a = smil('opacity', [(0, .3), (.07, 0), (.968, 0), (.978, .5), (1, .3)], D, -i * SLOT, ease='soft')
        out.append(f'<rect x="{SX - 28}" y="{y - 14}" width="56" height="28" rx="3" class="{fc(k)}" opacity="0">{a}</rect>')
    return ''.join(out)


# --------------------------------------------------------------- луч Ока ----
def beam(anim):
    f = ''
    f2 = ''
    sweep = ''
    if anim:
        f = smil('opacity', [(0, .65), (.12, 1), (.6, .7), (1, .65)], SLOT, ease='io')
        sweep = smil('points', [(0, f'{CX},74 {CX - 21},{GY} {CX + 21},{GY}'),
                                (.5, f'{CX},74 {CX - 31},{GY} {CX + 31},{GY}'),
                                (1, f'{CX},74 {CX - 21},{GY} {CX + 21},{GY}')], SLOT, ease='io')
    return (f'<polygon points="{CX},74 {CX - 46},{GY + 4} {CX + 46},{GY + 4}" fill="url(#gBeam)" opacity=".18"/>'
            f'<g opacity=".7">{f}<polygon points="{CX},74 {CX - 21},{GY} {CX + 21},{GY}" fill="url(#gBeam)">{sweep}</polygon></g>'
            f'<path d="M{CX},76V{GY}" class="sg" stroke-width="1.2" opacity=".6"/>')


# -------------------------------------------------------------------- Око ----
EYE_Y = 54


def eye(anim):
    rays = []
    for k in range(14):
        a = k / 14 * math.tau
        r0, r1 = 44, 62 if k % 2 else 52
        rays.append(f'M{n(r0 * math.cos(a))},{n(r0 * math.sin(a) * .8)}L{n(r1 * math.cos(a))},{n(r1 * math.sin(a) * .8)}')
    rot = smil_tf('rotate', [(0, 0), (1, 360)], D * 2, ease='lin') if anim else ''
    pup = smil_tf('translate', [(0, (0, 0)), (.25, (-7, 0)), (.75, (7, 0)), (1, (0, 0))], SLOT * 2, ease='io') if anim else ''
    blink = smil_tf('scale', [(0, (1, 1)), (.9, (1, 1)), (.94, (1, .08)), (.98, (1, 1)), (1, (1, 1))], 7.5, ease='lin') if anim else ''
    pulse = smil('ry', [(0, 12), (.5, 14.5), (1, 12)], 2.4) if anim else ''
    flare = smil('opacity', [(0, .55), (.5, 1), (1, .55)], 2.4) if anim else ''
    # веко/зрачок. Blink вокруг центра (0,0) — scale без смещения.
    return f"""<g transform="translate({CX},{EYE_Y})">
<g class="sg" stroke-width="1.1" opacity=".55"><g>{rot}<path d="{"".join(rays)}" fill="none"/></g></g>
<ellipse rx="60" ry="26" fill="url(#gEye)" opacity=".32"/>
<g>{blink}
<path d="M-36,0Q0,-30 36,0Q0,30 -36,0Z" fill="#1a0000" fill-opacity=".85" class="sr" stroke-width="2.2" filter="url(#glow)"/>
<circle r="15" fill="url(#gEye)"/>
<circle r="15" fill="none" class="sg" stroke-width="1" opacity=".8"/>
<g>{pup}<ellipse rx="3.4" ry="12" class="fb" opacity=".95">{pulse}</ellipse><ellipse rx="1.2" ry="9" class="fr" opacity=".9"/></g>
</g>
<ellipse rx="20" ry="9" fill="none" class="sr" opacity="0"/>
<g opacity=".0">{flare}</g>
</g>"""


# --------------------------------------------------- письма и голограммы -----
def letter_geom(i):
    rnd = random.Random(300 + i)
    ys = []
    last = rnd.randint(210, 380)
    for _ in range(4):
        y = rnd.randint(205, 385)
        while abs(y - last) < 60:
            y = rnd.randint(205, 385)
        ys.append(y)
        last = y
    jx = [rnd.randint(-30, 30) for _ in range(3)]
    pts = [(-70, ys[0]), (130 + jx[0], ys[1]), (290 + jx[1], ys[2]), (445 + jx[2], ys[3]), (CX, GY)]
    rot = [rnd.randint(-70, 70), rnd.randint(-45, 45), rnd.randint(-30, 30), rnd.randint(-18, 18), 0]
    sc_ = [(1.0, 1.0), (rnd.uniform(.7, 1.3), 1.2), (1.35, rnd.uniform(.8, 1.3)), (rnd.uniform(.8, 1.3), 1.35), (1.5, 1.5)]
    return Curve(pts), rot, sc_


APP_KEYS = [(0, 0), (.5, 1), (1, 1)]
APP_EASE = ['.22 .12 .34 1', 'lin']


def letter_markup(i, anim, u_static):
    k = KINDS[i]
    cv, rot, scl = letter_geom(i)
    begin = -i * SLOT
    # ключи
    rot_keys = [(0, rot[0]), (.14, rot[1]), (.28, rot[2]), (.4, rot[3]), (.5, 0), (1, 0)]
    sc_keys = [(0, scl[0]), (.14, scl[1]), (.28, scl[2]), (.4, scl[3]), (.5, scl[4]), (1, scl[4])]
    op_keys = [(0, 0), (.04, 1), (.5, 1), (.545, 0), (1, 0)]
    mot = smil_motion(cv.d(), [(0, 0), (.5, 1), (1, 1)], D, begin, APP_EASE) if anim else ''
    if anim:
        a_rot = smil_tf('rotate', rot_keys, D, begin, 'io')
        a_sc = smil_tf('scale', sc_keys, D, begin, 'io')
        a_op = smil('opacity', op_keys, D, begin, 'lin')
        st = ''
        op_attr = ' opacity="0"'
    else:
        u = u_static
        f = ev(APP_KEYS, u, APP_EASE)
        x, y = cv.at(f)
        r = ev(rot_keys, u)
        s = ev(sc_keys, u)
        o = ev(op_keys, u, 'lin')
        a_rot = a_sc = a_op = ''
        st = f' transform="translate({n(x)},{n(y)})"'
        op_attr = f' opacity="{o:.2f}"'
    # ворон (для некоторых писем)
    raven = ''
    if i in RAVEN_LETTERS:
        rk = [(0, 0), (.46, 0), (.54, -46), (1, -46)]
        ro = [(0, 0), (.04, 1), (.46, 1), (.54, 0), (1, 0)]
        if anim:
            rv = smil_tf('translate', [(u_, (0, y_)) for u_, y_ in rk], D, begin, 'io')
            rop = smil('opacity', ro, D, begin, 'lin')
            bob = smil_tf('translate', [(0, (0, 0)), (.5, (0, -3)), (1, (0, 0))], .62)
            raven = (f'<g opacity="0">{rop}<g>{rv}<g>{bob}'
                     f'<path d="M0,-6V4" class="sc" stroke-width=".8" opacity=".6"/>'
                     f'<use href="#raven" transform="translate(0,-26) scale(.85)"/></g></g></g>')
        else:
            u = u_static
            dy = ev(rk, u)[1] if isinstance(ev(rk, u), tuple) else ev(rk, u)
            raven = (f'<g opacity="{ev(ro, u, "lin"):.2f}"><use href="#raven" transform="translate(0,{n(-26 + ev([(a, b) for a, b in rk], u))}) scale(.85)"/></g>')
    inner = (f'<g>{a_rot}<g>{a_sc}<use href="#env" class="{sc(k)}" stroke-width="1.6"/></g></g>' if anim else
             f'<g transform="rotate({n(r)}) scale({s[0]:.2f},{s[1]:.2f})"><use href="#env" class="{sc(k)}" stroke-width="1.6"/></g>')
    return f'<g{op_attr}{st}>{mot}{a_op}{inner}{raven}</g>'


def docx_markup(i, anim, u_static):
    k = KINDS[i]
    cv = CH[k]
    begin = -i * SLOT
    m_keys = [(0, 0), (.6, 0), (.975, 1), (1, 1)]
    m_ease = ['lin', '.5 0 .35 1', 'lin']
    op_keys = [(0, 0), (.595, 0), (.615, 1), (.972, 1), (.995, 0), (1, 0)]
    sc_keys = [(0, .4), (.6, .4), (.64, 1.3), (1, 1.3)]
    if anim:
        mot = smil_motion(cv.d(), m_keys, D, begin, m_ease)
        return (f'<g opacity="0">{smil("opacity", op_keys, D, begin, "lin")}{mot}'
                f'<g>{smil_tf("scale", [(a, (b, b)) for a, b in sc_keys], D, begin, "io")}'
                f'<use href="#doc" class="{sc(k)}" stroke-width="1.6"/></g></g>')
    u = u_static
    o = ev(op_keys, u, 'lin')
    if o <= .01:
        return ''
    x, y = cv.at(ev([(a, b) for a, b in m_keys], u, m_ease))
    s = ev(sc_keys, u)
    return (f'<g opacity="{o:.2f}" transform="translate({n(x)},{n(y)}) scale({s:.2f})">'
            f'<use href="#doc" class="{sc(k)}" stroke-width="1.6"/></g>')


ROW_W = [
    [118, 96, 112, 84, 104],
    [108, 118, 76, 112, 92],
]
TOKENS = [['<h1>', '<p>', '<p>', '<p>', '<p>'], ['ocr()', '<p>', '300dpi', '<p>', 'rus+eng']]


def _reveal(a, b, off, on):
    return [(0, off), (a, off), (b, on), (.605, on), (.625, off), (1, off)]


def holo_markup(i, anim, u_static):
    k = KINDS[i]
    begin = -i * SLOT
    op_keys = [(0, 0), (.495, 0), (.515, 1), (.60, 1), (.625, 0), (1, 0)]
    ty_keys = [(0, 0), (.495, 0), (.55, HOLO_DY), (.595, HOLO_DY), (.625, -8), (1, 0)]
    ty_ease = ['lin', 'out', 'lin', 'in', 'lin']
    sc_keys = [(0, .3), (.495, .3), (.55, 1), (.595, 1), (.625, .3), (1, .3)]
    cls = sc(k)

    def A(attr, keys, ease='lin'):
        return smil(attr, keys, D, begin, ease) if anim else ''

    def shown(on=1.0):
        return ' opacity="0"' if anim else f' opacity="{on}"'

    body = [f'<rect x="-88" y="-56" width="176" height="112" rx="5" class="{cls} nf" stroke-width="5" opacity=".22"/>'
            f'<rect x="-88" y="-56" width="176" height="112" rx="5" class="fb {cls}" fill-opacity=".86" stroke-width="1.6"/>'
            f'<path d="M-88,-38H88" class="{cls}" stroke-width="1" opacity=".7"/>',
            text(-80, -43, TEXTS['tags'][k], 11, fc(k), 'start')]
    for q in range(3):
        body.append(rune(k * 3 + q, 56 + q * 11, -53, .55, 'sg', 1.4, .9))

    if k == 2:  # таблица: сетка с объединённой ячейкой (colspan)
        cw, ch = 40, 15
        n_cell = 0
        for r in range(4):
            for c in range(4):
                if (r, c) in ((1, 2), (2, 2)):
                    continue
                merged = (r, c) == (1, 1)
                w_ = cw * 2 - 3 if merged else cw - 3
                a_ = .516 + .005 * n_cell
                n_cell += 1
                fill = 'fg" fill-opacity=".2' if merged else 'nf'
                stroke_cls = f'{cls} {fill}' if not merged else f'{cls} {fill}'
                body.append(f'<rect x="{-80 + c * cw}" y="{-32 + r * 17}" width="{w_}" height="{ch}" rx="2" '
                            f'class="{stroke_cls}" stroke-width="1"{shown(.9)}>'
                            f'{A("opacity", _reveal(a_, a_ + .012, 0, .9))}</rect>')
        for r in range(4):
            yy = -25 + r * 17
            body.append(f'<path d="M-72,{yy}h20M-32,{yy}h16M8,{yy}h22M48,{yy}h14" class="fg" stroke-width="2"{shown(.55)}>'
                        f'{A("opacity", _reveal(.55, .57, 0, .55))}</path>')
    else:
        rows = ROW_W[k]
        for r in range(5):
            y = -30 + r * 14
            a_ = .516 + .006 * r
            tcls = 'fg' if r % 2 else 'fc'
            wmax = rows[r] - 40
            w_attr = 'width="0"' if anim else f'width="{wmax}"'
            body.append(f'<rect x="-48" y="{y}" height="5" rx="2.5" class="{tcls}" opacity=".85" {w_attr}>'
                        f'{A("width", _reveal(a_, a_ + .03, 0, wmax), "out")}</rect>')
            body.append(text(-80, y + 5.5, TOKENS[k][r], 8, 'fc', 'start', extra=shown(.9).strip(),
                             inner=A('opacity', _reveal(a_, a_ + .008, 0, .9))))
        for q in range(3):
            body.append(rune(q * 2 + k, 68, -30 + q * 28, .8, 'sm', 1.3, 1,
                             extra=shown(.9).strip()).replace('/>', f'>{A("opacity", _reveal(.53 + q * .01, .54 + q * .01, 0, .9))}</use>'))
    if anim:  # сканирующая линия внутри голограммы
        sl = (smil('y', [(0, -34), (.52, -34), (.585, 40), (1, 40)], D, begin, 'io') +
              smil('opacity', [(0, 0), (.52, .9), (.585, .9), (.592, 0), (1, 0)], D, begin, 'lin'))
        body.append(f'<rect x="-86" y="-34" width="172" height="2.4" class="fc" opacity="0">{sl}</rect>')
    body.append(f'<g{shown(1)}>{A("opacity", _reveal(.585, .6, 0, 1))}'
                + text(-80, 50, '→ DOCX', 11, 'fg', 'start') +
                '<path d="M58,46L64,52L76,40" class="nf sg" stroke-width="2.4"/></g>')
    content = ''.join(body)
    if anim:
        return (f'<g transform="translate({CX},{GY})"><g>{smil_tf("translate", [(a, (0, b)) for a, b in ty_keys], D, begin, ty_ease)}'
                f'<g>{smil_tf("scale", [(a, (b, b)) for a, b in sc_keys], D, begin, "io")}'
                f'<g opacity="0">{smil("opacity", op_keys, D, begin, "lin")}{content}</g></g></g></g>')
    u = u_static
    o = ev(op_keys, u, 'lin')
    if o <= .01:
        return ''
    ty = ev(ty_keys, u, ty_ease)
    s_ = ev(sc_keys, u)
    return f'<g transform="translate({CX},{n(GY + ty)}) scale({s_:.2f})" opacity="{o:.2f}">{content}</g>'


def ordered_flow(anim):
    """ровные цепочки готовых документов на каналах: порядок справа."""
    out = []
    for k, cv in enumerate(CH):
        for j in range(3):
            dur = 7.5
            beg = -j * dur / 3 - k * .9
            if anim:
                mo = smil_motion(cv.d(), [(0, .3), (1, 1)], dur, beg, 'lin')
                op = smil('opacity', [(0, 0), (.12, .85), (.9, .85), (1, 0)], dur, beg, 'lin')
                out.append(f'<g opacity="0">{op}{mo}<use href="#doc" class="{sc(k)}" stroke-width="1.4" transform="scale(.8)"/></g>')
            else:
                x, y = cv.at(.3 + .7 * (j + .5) / 3)
                out.append(f'<use href="#doc" class="{sc(k)}" stroke-width="1.4" opacity=".8" transform="translate({n(x)},{n(y)}) scale(.8)"/>')
    return ''.join(out)


# ---------------------------------------- фоновая толпа писем и вороны -------
def ambient(anim):
    rnd = random.Random(9)
    out = []
    for k in range(46):
        y0 = rnd.uniform(205, 392)
        y1 = y0 + rnd.uniform(-70, 70)
        y1 = max(205, min(390, y1))
        xe = rnd.uniform(330, 540)
        ym = (y0 + y1) / 2 + rnd.uniform(-40, 40)
        cv = Curve([(-40, y0), (xe / 2, ym), (xe, y1)])
        dur = rnd.uniform(6.5, 12)
        beg = -rnd.uniform(0, dur)
        s = rnd.uniform(.8, 1.5)
        kind = rnd.choice([0, 1, 1, 2])
        peak = rnd.uniform(.55, .95)
        r0 = rnd.uniform(-60, 60)
        if anim:
            mo = smil_motion(cv.d(), [(0, 0), (1, 1)], dur, beg, 'lin')
            op = smil('opacity', [(0, 0), (.1, peak), (.7, peak), (1, 0)], dur, beg, 'lin')
            ro = smil_tf('rotate', [(0, r0), (1, r0 + rnd.choice([-1, 1]) * rnd.uniform(200, 420))], dur, beg, 'lin')
            out.append(f'<g opacity="0">{op}{mo}<g transform="scale({s:.2f})"><g>{ro}<use href="#env" class="{sc(kind)}" stroke-width="1.5"/></g></g></g>')
        else:
            f = rnd.uniform(.05, .85)
            x, y = cv.at(f)
            pk = peak * min(1, f / .1, (1 - f) / .3)
            out.append(f'<g opacity="{pk:.2f}" transform="translate({n(x)},{n(y)}) scale({s:.2f}) rotate({n(r0 + f * 200)})"><use href="#env" class="{sc(kind)}" stroke-width="1.5"/></g>')
    # вороны-дроны
    for k, (y0, y1, dur, beg) in enumerate([(240, 200, 10.0, -2.0), (350, 300, 12.0, -7.5), (290, 230, 8.5, -5.0)]):
        cv = Curve([(-60, y0), (200, y0 - 36), (400, y1 + 10), (560, y1 - 40)])
        if anim:
            mo = smil_motion(cv.d(), [(0, 0), (1, 1)], dur, beg, 'lin', rotate=True)
            op = smil('opacity', [(0, 0), (.08, .95), (.78, .95), (1, 0)], dur, beg, 'lin')
            out.append(f'<g opacity="0">{op}{mo}<g transform="scale(.9)"><path d="M0,3V15" class="sc" stroke-width=".7" opacity=".6"/>'
                       f'<use href="#raven"/><use href="#env" class="sc" stroke-width="1.3" transform="translate(0,19) scale(.5)"/></g></g>')
        else:
            x, y = cv.at(.25 + k * .22)
            out.append(f'<g transform="translate({n(x)},{n(y)}) scale(.9)" opacity=".9"><use href="#raven"/>'
                       f'<use href="#env" class="sc" stroke-width="1.3" transform="translate(0,19) scale(.5)"/></g>')
    return ''.join(out)


# ----------------------------------------------------------- титул ----------
def title_block(anim, t):
    blend = f'style="mix-blend-mode:{t["blend"]}"' if t['blend'] != 'normal' else ''
    ch = ''
    if t['blend'] != 'normal':
        ch = (f'<use href="#ttl" class="fc" x="-2" opacity=".55" {blend}/><use href="#ttl" class="fm" x="2" opacity=".5" {blend}/>')
    flick = smil('opacity', [(0, 1), (.5, .92), (.52, 1), (1, 1)], 5.5, ease='lin') if anim else ''
    cursor = ''
    if anim:
        cursor = smil_discrete('opacity', [(0, 1), (.5, 0), (1, 1)], 1.1)
    runes = ''.join(rune(j * 3 + 1, 48 + j * 17, 28, .95, 'sm', 1.4, .95) for j in range(5))
    cur_x = 48 + len(TEXTS['title']) * 72 * .66 + 6
    return (f'<g>'
            f'{runes}'
            + text(146, 41, TEXTS['caption'], 13, 'fc', 'start', cw=.62, extra='opacity=".85"') +
            f'<use href="#ttl" class="fg sg" stroke-width="9" opacity=".2"/>'
            f'{ch}<g>{flick}<use href="#ttl" class="fg"/></g>'
            f'<rect x="{n(cur_x)}" y="74" width="20" height="48" class="fc" opacity="1" filter="url(#glowS)">{cursor}</rect>'
            + text(50, 156, TEXTS['slogan'], 19, 'fc', 'start', cw=.6) +
            text(50, 180, TEXTS['detail'], 12.5, 'fm', 'start', cw=.62, extra='opacity=".95"') +
            '</g>')


# ------------------------------------------------------------ глитч ---------
GL = 7.0


def glitch():
    def disp(on):  # окна показа внутри GL
        keys = [(0, 'none')]
        for a, b in on:
            keys += [(a, 'inline'), (b, 'none')]
        keys.append((1, 'none'))
        return smil_discrete('display', keys, GL)

    clips = ('<clipPath id="gA"><rect x="0" y="84" width="1280" height="26"/></clipPath>'
             '<clipPath id="gB"><rect x="0" y="214" width="1280" height="20"/></clipPath>'
             '<clipPath id="gC"><rect x="0" y="296" width="1280" height="9"/></clipPath>'
             '<clipPath id="gD"><rect x="0" y="40" width="1280" height="14"/></clipPath>')
    sl = (f'<g display="none">{disp([(.925, .94), (.955, .975)])}<g clip-path="url(#gA)"><use href="#world" x="18"/></g></g>'
          f'<g display="none">{disp([(.93, .948), (.962, .98)])}<g clip-path="url(#gB)"><use href="#world" x="-26"/></g></g>'
          f'<g display="none">{disp([(.935, .955)])}<g clip-path="url(#gC)"><use href="#world" x="14"/></g></g>'
          f'<g display="none">{disp([(.94, .96)])}<g clip-path="url(#gD)"><use href="#world" x="-12"/></g></g>')
    rgb = (f'<g display="none">{disp([(.925, .945), (.955, .98)])}'
           f'<use href="#ttl" class="fc" x="-5" style="mix-blend-mode:screen" opacity=".6"/>'
           f'<use href="#ttl" class="fm" x="5" style="mix-blend-mode:screen" opacity=".6"/></g>')
    bars = (f'<g display="none">{disp([(.925, .94), (.95, .97)])}'
            f'<rect x="0" y="152" width="1280" height="3" class="fc" opacity=".55"/>'
            f'<rect x="0" y="260" width="1280" height="2" class="fm" opacity=".6"/>'
            f'<rect x="0" y="332" width="1280" height="5" class="fc" opacity=".35"/></g>')
    return f'<g pointer-events="none">{clips}{sl}{rgb}{bars}</g>'


# ----------------------------------------------------------- интро ----------
def intro(markup, delay, dur=1.0, pat='A'):
    pats = {
        'A': [(0, 0), (.12, 1), (.22, .15), (.34, .9), (.44, .3), (.56, 1), (.7, .6), (1, 1)],
        'B': [(0, 0), (.2, .7), (.3, 0), (.5, 1), (.62, .4), (.8, 1), (1, 1)],
        'C': [(0, 0), (.3, .5), (.6, 1), (1, 1)],
    }
    a = smil('opacity', pats[pat], dur, delay, 'lin', repeat=False, freeze=True)
    return f'<g opacity="0">{a}{markup}</g>'


# ----------------------------------------------------------- сборка ---------
def scene(anim, t):
    u0 = .56
    us = [(u0 - i * (1 / NL)) % 1 for i in range(NL)]
    L = [('sky', sky(anim, t), None), ('mount', mountains(anim, t), ('B', .2, 1.1)), ('fog', fog(anim), None),
         ('tower', tower(anim, t) + gate(anim), ('A', 1.0, 1.3)), ('ground', ground(anim, t), ('C', .9, 1.0)),
         ('rain', rain(anim, t), ('C', 1.8, 1.4)),
         ('chan', channels(anim, t) + stacks(anim, t) + landing_glows(anim) + ordered_flow(anim), ('A', 2.2, 1.0)),
         ('beam', beam(anim), ('B', 1.7, 1.0)),
         ('amb', ambient(anim), ('C', 2.4, 1.2)),
         ('letters', ''.join(docx_markup(i, anim, us[i]) + letter_markup(i, anim, us[i]) for i in range(NL)), ('C', 2.4, 1.2)),
         ('holo', ''.join(holo_markup(i, anim, us[i]) for i in range(NL)), ('A', 2.6, 1.0)),
         ('eye', eye(anim), ('A', 1.5, 1.2)),
         ('title', title_block(anim, t), ('A', .5, 1.2)),
         ('seal', seal(1190, 74, 42, anim, 'b' + ('l' if anim else 's')), ('B', 2.9, 1.0))]
    out = []
    for name, mk, intro_ in L:
        if anim and intro_:
            out.append(intro(mk, intro_[1], intro_[2], intro_[0]))
        else:
            out.append(mk)
    return ''.join(out)


def build(theme):
    t = THEMES[theme]
    parts = [head(W, H, t, f'{TEXTS["title"]} — {TEXTS["slogan"]}',
                  'Анимация: хаотичные письма и вороны слева пролетают врата под сканирующим Оком, '
                  'разворачиваются в голограммы и ложатся ровными стопками .docx справа; на горах зажигаются маяки.'),
             defs(t),
             f'<g id="live"><g id="world">{scene(True, t)}</g>{glitch()}</g>',
             f'<g id="still">{scene(False, t)}</g>',
             overlays(t, W, H),
             '</svg>']
    return ''.join(parts)
