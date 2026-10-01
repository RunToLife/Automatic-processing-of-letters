#!/usr/bin/env python3
"""Генерирует все SVG-ассеты в assets/ (тёмная и светлая темы).

Запуск:  python3 tools/build_visuals.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from visuals import banner  # noqa: E402

from visuals import small, service  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'assets')
IMG = os.path.join(ROOT, 'letters', 'static', 'letters', 'img')


def write(name, content, out=None):
    path = os.path.join(out or OUT, name)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'{name:24s} {len(content.encode()) / 1024:7.1f} КБ')


def main():
    os.makedirs(OUT, exist_ok=True)
    only = set(sys.argv[1:])
    if not only or 'service' in only:
        os.makedirs(IMG, exist_ok=True)
        for name, fn in service.BUILD:
            write(name, fn(), IMG)
    for theme, suffix in (('dark', ''), ('light', '-light')):
        if not only or 'banner' in only:
            write(f'banner{suffix}.svg', banner.build(theme))
        for key, mod in (('divider', small.divider), ('footer', small.footer),
                         ('typing', small.typing), ('stack', small.stack)):
            if not only or key in only:
                write(f'{key}{suffix}.svg', mod(theme))


if __name__ == '__main__':
    main()
