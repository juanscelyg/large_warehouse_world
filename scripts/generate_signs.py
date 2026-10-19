#!/usr/bin/env python3
# Copyright 2026 Juan S. Cely G.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Draw the sign textures (zone iconography, floor logos and safety signs) of large_warehouse_world.

The textures are written to models/large_warehouse_building/materials/textures. Requires
Pillow and the DejaVu and Font Awesome 4 fonts (apt packages fonts-dejavu-core and
fonts-font-awesome). Usage:

    python3 scripts/generate_signs.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PACKAGE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = PACKAGE_DIR / 'models' / 'large_warehouse_building' / 'materials' / 'textures'

FONT_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
FONT_ICONS = '/usr/share/fonts/truetype/font-awesome/fontawesome-webfont.ttf'

WHITE = (255, 255, 255)
BLACK = (25, 25, 25)

# Zones of the plan: id -> (title lines, subtitle, color, icon)
ZONES = {
    'warehouse_a': (['WAREHOUSE', 'A'], 'Almacén de estanterías altas', (21, 101, 192), 'rack'),
    'warehouse_b': (['WAREHOUSE', 'B'], 'Picking, embalaje y expedición', (46, 125, 50), 'rack'),
    'warehouse_c': (['WAREHOUSE', 'C'], 'Almacenaje masivo y cross-docking', (230, 81, 0), 'rack'),
    'reception': (['RECEPCIÓN', 'Y OFICINAS'], 'Recepción, oficinas y vestuarios', (106, 27, 154), 'reception'),
    'loading': (['ZONA CARGA', 'CAMIONES'], 'Muelles de carga y patio de maniobras', (249, 168, 37), 'truck'),
}


def font(size, bold=True):
    return ImageFont.truetype(FONT_BOLD if bold else FONT, size)


def icon_font(size):
    return ImageFont.truetype(FONT_ICONS, size)


def text_center(d, xy, text, f, fill):
    d.text(xy, text, font=f, fill=fill, anchor='mm')


def fit_font(d, text, max_w, size, bold=True):
    while size > 10 and d.textlength(text, font=font(size, bold)) > max_w:
        size -= 4
    return font(size, bold)


def draw_rack(d, box, color):
    """Pallet rack with boxes: 2 bays and 3 levels."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    t = w * 0.06
    for x in (x0, x0 + (w - t) / 2, x1 - t):                        # uprights
        d.rectangle([x, y0, x + t, y1], fill=color)
    levels = [y0 + h * 0.30, y0 + h * 0.63, y1 - t]
    for y in levels:                                                  # beams
        d.rectangle([x0, y, x1, y + t * 0.8], fill=color)
    bay = (w - 3 * t) / 2
    sizes = [(0.40, 0.17), (0.30, 0.12), (0.34, 0.20), (0.26, 0.14)]  # boxes (width, height)
    for i, y in enumerate(levels):
        for b in range(2):
            px = x0 + t + b * (bay + t) + bay * 0.06
            for k in range(2):
                bw, bh = sizes[(i + b + k) % len(sizes)]
                d.rectangle([px, y - h * bh, px + bay * bw, y - h * 0.02], fill=color)
                px += bay * (bw + 0.08)


def draw_reception(d, box, color):
    """Person behind a reception counter."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    cx = (x0 + x1) / 2
    r = w * 0.14
    d.ellipse([cx - r, y0 + h * 0.02, cx + r, y0 + h * 0.02 + 2 * r], fill=color)
    d.rounded_rectangle([cx - w * 0.27, y0 + h * 0.36, cx + w * 0.27, y0 + h * 0.80],
                        radius=w * 0.12, fill=color)
    d.rectangle([x0, y0 + h * 0.62, x1, y0 + h * 0.70], fill=color)       # counter top
    d.rectangle([x0 + w * 0.06, y0 + h * 0.70, x1 - w * 0.06, y1], fill=color)
    bell = w * 0.09                                                       # desk bell
    d.pieslice([x1 - w * 0.30, y0 + h * 0.62 - bell, x1 - w * 0.30 + 2 * bell, y0 + h * 0.62 + bell],
               180, 360, fill=color)


def draw_truck(d, box, color):
    x0, y0, x1, y1 = box
    h = y1 - y0
    f = icon_font(int(h * 1.05))
    text_center(d, ((x0 + x1) / 2, (y0 + y1) / 2 + h * 0.04), '', f, color)


def draw_forklift(d, box, color):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    wr = h * 0.13
    d.rectangle([x0 + w * 0.10, y0 + h * 0.45, x0 + w * 0.62, y1 - wr * 1.2], fill=color)     # body
    d.line([x0 + w * 0.16, y0 + h * 0.45, x0 + w * 0.26, y0 + h * 0.08, x0 + w * 0.56, y0 + h * 0.08,
            x0 + w * 0.56, y0 + h * 0.45], fill=color, width=int(w * 0.05))                   # cab
    d.rectangle([x0 + w * 0.66, y0, x0 + w * 0.72, y1 - wr * 0.5], fill=color)                # mast
    d.rectangle([x0 + w * 0.66, y1 - wr * 0.7, x1, y1 - wr * 0.3], fill=color)                # forks
    for cx in (x0 + w * 0.22, x0 + w * 0.52):                                                  # wheels
        d.ellipse([cx - wr, y1 - 2 * wr, cx + wr, y1], fill=color)


ICONS = {'rack': draw_rack, 'reception': draw_reception, 'truck': draw_truck,
         'forklift': draw_forklift}


def zone_sign(zone):
    """2:1 sign for doors and facades: pictogram on the left and the zone name."""
    lines, subtitle, color, icon = ZONES[zone]
    fg = BLACK if zone == 'loading' else WHITE
    W, H = 2048, 1024
    im = Image.new('RGB', (W, H), color)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([20, 20, W - 20, H - 20], radius=60, outline=fg, width=18)
    d.rounded_rectangle([90, 112, 890, 912], radius=80, fill=WHITE)
    ICONS[icon](d, (190, 222, 790, 802), BLACK if zone == 'loading' else color)
    tx = 1460
    if lines[1] in ('A', 'B', 'C'):
        text_center(d, (tx, 250), lines[0], fit_font(d, lines[0], 1000, 170), fg)
        text_center(d, (tx, 560), lines[1], font(440), fg)
    else:
        text_center(d, (tx, 300), lines[0], fit_font(d, lines[0], 1020, 170), fg)
        text_center(d, (tx, 520), lines[1], fit_font(d, lines[1], 1020, 170), fg)
    text_center(d, (tx, 850), subtitle, fit_font(d, subtitle, 1040, 64, bold=False), fg)
    im.save(OUT_DIR / f'sign_{zone}.png')


def floor_logo(zone):
    """Square logo painted on the floor, readable from above."""
    lines, subtitle, color, icon = ZONES[zone]
    fg = BLACK if zone == 'loading' else WHITE
    S = 2048
    im = Image.new('RGB', (S, S), color)
    d = ImageDraw.Draw(im)
    d.rectangle([40, 40, S - 40, S - 40], outline=fg, width=40)
    ICONS[icon](d, (424, 230, 1624, 1250), fg)
    name = ' '.join(lines) if lines[1] not in ('A', 'B', 'C') else f'{lines[0]} {lines[1]}'
    if len(name) > 12:
        text_center(d, (S / 2, 1470), lines[0], fit_font(d, lines[0], 1800, 230), fg)
        text_center(d, (S / 2, 1740), lines[1], fit_font(d, lines[1], 1800, 230), fg)
    else:
        text_center(d, (S / 2, 1600), name, fit_font(d, name, 1800, 260), fg)
    im.save(OUT_DIR / f'floor_{zone}.png')


def forklift_warning():
    W, H = 1024, 1024
    im = Image.new('RGB', (W, H), WHITE)
    d = ImageDraw.Draw(im)
    tri = [(W / 2, 40), (W - 40, 760), (40, 760)]
    d.polygon(tri, fill=(255, 205, 0), outline=BLACK)
    d.line(tri + [tri[0]], fill=BLACK, width=40, joint='curve')
    draw_forklift(d, (330, 330, 700, 680), BLACK)
    text_center(d, (W / 2, 850), 'PRECAUCIÓN', font(110), BLACK)
    text_center(d, (W / 2, 960), 'CARRETILLAS', font(96), BLACK)
    im.save(OUT_DIR / 'sign_forklift_warning.png')


def extinguisher_sign():
    W, H = 1024, 1024
    im = Image.new('RGB', (W, H), (200, 16, 30))
    d = ImageDraw.Draw(im)
    d.rectangle([24, 24, W - 24, H - 24], outline=WHITE, width=24)
    text_center(d, (W / 2, 420), '', icon_font(560), WHITE)
    text_center(d, (W / 2, 860), 'EXTINTOR', font(150), WHITE)
    im.save(OUT_DIR / 'sign_extinguisher.png')


def exit_sign():
    W, H = 2048, 1024
    im = Image.new('RGB', (W, H), (0, 135, 68))
    d = ImageDraw.Draw(im)
    d.rectangle([24, 24, W - 24, H - 24], outline=WHITE, width=24)
    text_center(d, (420, H / 2), '', icon_font(560), WHITE)
    text_center(d, (1300, H / 2 - 90), 'SALIDA', font(300), WHITE)
    text_center(d, (1300, H / 2 + 200), 'EXIT', font(150, bold=False), WHITE)
    im.save(OUT_DIR / 'sign_exit.png')


def speed_limit_sign():
    S = 1024
    im = Image.new('RGB', (S, S), WHITE)
    d = ImageDraw.Draw(im)
    d.ellipse([10, 10, S - 10, S - 10], fill=(200, 16, 30))
    d.ellipse([130, 130, S - 130, S - 130], fill=WHITE)
    text_center(d, (S / 2, S / 2 - 40), '10', font(380), BLACK)
    text_center(d, (S / 2, S / 2 + 220), 'km/h', font(110), BLACK)
    im.save(OUT_DIR / 'sign_speed_limit.png')


def hazard_stripes():
    S = 512
    im = Image.new('RGB', (S, S), (255, 205, 0))
    d = ImageDraw.Draw(im)
    step = 128
    for k in range(-S, 2 * S, step):
        d.polygon([(k, 0), (k + step / 2, 0), (k + step / 2 - S, S), (k - S, S)], fill=BLACK)
    im.save(OUT_DIR / 'hazard_stripes.png')


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for zone in ZONES:
        zone_sign(zone)
        floor_logo(zone)
    forklift_warning()
    extinguisher_sign()
    exit_sign()
    speed_limit_sign()
    hazard_stripes()
    print(f'Textures written to {OUT_DIR}')


if __name__ == '__main__':
    main()
