"""Furniture and fittings for interiors, drawn top-down (3/4) and sized to Kael (26 px tall, about 14 px wide).

Every function returns (RGBA image, ox, oy): the sprite and the offset of the anchor point (top-left unless noted).
Light comes from the top-left: lit edges top/left, shaded edges bottom/right, dark outline around everything.
"""
import numpy as np
from PIL import Image, ImageDraw

OUT = (40, 26, 18, 255)
WOOD = (150, 94, 50)
WOOD_L = (186, 124, 70)
WOOD_D = (98, 58, 30)
IRON = (74, 74, 82)
IRON_L = (150, 150, 160)


def _img(w, h):
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)


def _shade(c, k):
    return tuple(int(max(0, min(255, v * k))) for v in c[:3]) + ((c[3],) if len(c) > 3 else (255,))


def _boards(d, x0, y0, x1, y1, base, rng, horiz=True, bw=5):
    """Fill a rect with boards (planks) incl. seams and lit edge."""
    if horiz:
        for i, y in enumerate(range(y0, y1, bw)):
            k = 0.92 + 0.16 * rng.random()
            d.rectangle((x0, y, x1, min(y + bw - 1, y1)), fill=_shade(base, k))
            d.line((x0, y, x1, y), fill=_shade(base, k * 1.15))
            if y > y0: d.line((x0, y - 1, x1, y - 1), fill=_shade(base, 0.62))
    else:
        for i, x in enumerate(range(x0, x1, bw)):
            k = 0.92 + 0.16 * rng.random()
            d.rectangle((x, y0, min(x + bw - 1, x1), y1), fill=_shade(base, k))
            d.line((x, y0, x, y1), fill=_shade(base, k * 1.15))
            if x > x0: d.line((x - 1, y0, x - 1, y1), fill=_shade(base, 0.62))


# --- tables & seats ----------------------------------------------------------------------------------------------
def table(rng, w=120, h=26, items=True, cloth=None):
    im, d = _img(w + 2, h + 6)
    # legs/apron visible under the south edge
    d.rectangle((2, h - 2, w - 2, h + 3), fill=WOOD_D)
    for lx in (3, w - 7): d.rectangle((lx, h, lx + 4, h + 5), fill=_shade(WOOD_D, 0.8))
    _boards(d, 0, 0, w - 1, h - 1, WOOD, rng, horiz=True, bw=6)
    d.rectangle((0, 0, w - 1, h - 1), outline=OUT)
    if cloth:
        d.rectangle((w // 6, 2, w - w // 6, h - 3), fill=cloth)
        d.line((w // 6, 2, w - w // 6, 2), fill=_shade(cloth, 1.2))
    if items:
        n = max(2, w // 26)
        for i in range(n):
            x = int(8 + (w - 16) * (i + 0.5) / n)
            y = 6 if i % 2 == 0 else h - 11
            r = rng.random()
            if r < 0.4:      # pewter plate with food
                d.ellipse((x - 4, y, x + 4, y + 6), fill=(176, 176, 184), outline=(90, 90, 98))
                d.ellipse((x - 2, y + 1, x + 1, y + 4), fill=(170, 110, 60))
            elif r < 0.7:    # tankard
                d.ellipse((x - 3, y, x + 2, y + 5), fill=(130, 90, 56), outline=(60, 40, 24))
                d.ellipse((x - 2, y + 1, x + 1, y + 3), fill=(220, 190, 120))
            elif r < 0.85:   # bread
                d.ellipse((x - 5, y, x + 4, y + 5), fill=(200, 150, 80), outline=(110, 70, 30))
                d.line((x - 3, y + 2, x + 2, y + 2), fill=(230, 190, 120))
            else:            # candle
                d.ellipse((x - 2, y + 1, x + 2, y + 5), fill=(80, 70, 60))
                d.rectangle((x - 1, y - 2, x, y + 3), fill=(236, 226, 200))
                d.point((x, y - 3), fill=(255, 210, 120))
    return im, 0, 0


def bench(rng, w=110, h=8, vertical=False):
    if vertical:
        im, ox, oy = bench(rng, w, h)
        return im.rotate(90, expand=True), 0, 0
    im, d = _img(w + 1, h + 3)
    d.rectangle((2, h - 1, w - 3, h + 2), fill=WOOD_D)
    _boards(d, 0, 0, w - 1, h - 1, WOOD, rng, horiz=True, bw=4)
    d.rectangle((0, 0, w - 1, h - 1), outline=OUT)
    return im, 0, 0


def stool(rng, r=5):
    im, d = _img(2 * r + 2, 2 * r + 4)
    d.ellipse((0, 3, 2 * r, 2 * r + 3), fill=WOOD_D)
    d.ellipse((0, 0, 2 * r, 2 * r), fill=WOOD, outline=OUT)
    d.arc((2, 2, 2 * r - 2, 2 * r - 2), 180, 270, fill=WOOD_L)
    return im, 0, 0


def chair(rng, facing='S'):
    im, d = _img(14, 16)
    d.rectangle((1, 4, 12, 14), fill=WOOD, outline=OUT)
    d.rectangle((1, 0, 12, 4), fill=WOOD_D, outline=OUT)   # back
    d.line((2, 5, 11, 5), fill=WOOD_L)
    if facing == 'N': im = im.rotate(180)
    elif facing == 'E': im = im.rotate(90, expand=True)
    elif facing == 'W': im = im.rotate(-90, expand=True)
    return im, 0, 0


# --- beds -------------------------------------------------------------------------------------------------------
def bed(rng, w=24, h=40, blanket=(60, 84, 150), bunk=False, head='N'):
    im, d = _img(w + 2, h + 4)
    d.rectangle((0, 2, w - 1, h + 1), fill=WOOD_D)
    d.rectangle((0, 0, w - 1, h - 1), fill=WOOD, outline=OUT)
    # mattress
    d.rectangle((2, 2, w - 3, h - 3), fill=(222, 210, 180))
    # pillow
    d.rounded_rectangle((4, 3, w - 5, 10), 2, fill=(240, 236, 224), outline=(150, 140, 120))
    d.line((5, 4, w - 6, 4), fill=(255, 255, 250))
    # blanket with a turned-down sheet and folds
    by = 13
    d.rectangle((2, by, w - 3, h - 3), fill=blanket)
    d.rectangle((2, by, w - 3, by + 2), fill=(236, 230, 214))
    for fy in range(by + 7, h - 4, 7):
        d.line((3, fy, w - 4, fy + 1), fill=_shade(blanket, 0.78))
        d.line((3, fy - 1, w - 4, fy), fill=_shade(blanket, 1.18))
    d.line((2, by + 3, 2, h - 3), fill=_shade(blanket, 1.25))
    d.line((w - 3, by + 3, w - 3, h - 3), fill=_shade(blanket, 0.7))
    # foot board
    d.rectangle((0, h - 3, w - 1, h - 1), fill=WOOD_D, outline=OUT)
    if bunk:
        for px, py in ((0, 0), (w - 4, 0), (0, h - 4), (w - 4, h - 4)):
            d.rectangle((px, py, px + 3, py + 3), fill=WOOD_L, outline=OUT)
        d.line((1, 11, w - 2, 11), fill=WOOD_D)
    if head == 'S': im = im.rotate(180)
    elif head == 'W': im = im.rotate(90, expand=True)
    elif head == 'E': im = im.rotate(-90, expand=True)
    return im, 0, 0


# --- storage ----------------------------------------------------------------------------------------------------
def barrel(rng, r=8):
    s = 2 * r + 2
    im, d = _img(s, s + 3)
    d.ellipse((0, 3, 2 * r, 2 * r + 3), fill=_shade(WOOD_D, 0.8))
    d.ellipse((0, 0, 2 * r, 2 * r), fill=WOOD, outline=OUT)
    d.ellipse((2, 2, 2 * r - 2, 2 * r - 2), outline=IRON)
    d.ellipse((4, 4, 2 * r - 4, 2 * r - 4), fill=_shade(WOOD, 1.08), outline=_shade(WOOD, 0.7))
    for k in range(-1, 2): d.line((r + k * 3, 5, r + k * 3, 2 * r - 5), fill=_shade(WOOD, 0.8))
    d.arc((1, 1, 2 * r - 1, 2 * r - 1), 200, 290, fill=IRON_L)
    return im, 0, 0


def crate(rng, s=18):
    im, d = _img(s + 2, s + 5)
    d.rectangle((0, 4, s - 1, s + 3), fill=_shade(WOOD_D, 0.9), outline=OUT)
    for x in range(1, s - 1, 4): d.line((x, s, x, s + 2), fill=_shade(WOOD_D, 0.7))
    _boards(d, 0, 0, s - 1, s - 1, (176, 128, 74), rng, horiz=False, bw=4)
    d.rectangle((0, 0, s - 1, s - 1), outline=OUT)
    d.rectangle((1, 1, s - 2, s - 2), outline=(120, 80, 40))
    d.line((2, 2, s - 3, s - 3), fill=(120, 80, 40), width=2)
    return im, 0, 0


def sack(rng, w=14, h=16, c=(196, 172, 124)):
    im, d = _img(w + 2, h + 3)
    d.ellipse((0, 4, w - 1, h + 1), fill=_shade(c, 0.6))
    d.ellipse((0, 2, w - 1, h - 1), fill=c, outline=(96, 76, 44))
    d.ellipse((w // 2 - 3, 0, w // 2 + 2, 5), fill=_shade(c, 0.9), outline=(96, 76, 44))
    d.line((w // 2 - 3, 4, w // 2 + 2, 4), fill=(110, 70, 30))
    d.arc((2, 4, w - 3, h - 3), 190, 260, fill=_shade(c, 1.15))
    if rng.random() < 0.5:     # grain spilling from the neck
        d.ellipse((w // 2 - 2, 0, w // 2 + 1, 2), fill=(226, 200, 130))
    return im, 0, 0


def chest(rng, w=26, h=15, iron=True):
    im, d = _img(w + 2, h + 6)
    d.rectangle((0, 5, w - 1, h + 4), fill=WOOD_D, outline=OUT)      # front of the chest
    d.rectangle((0, 0, w - 1, h - 1), fill=WOOD, outline=OUT)        # lid
    d.line((1, 1, w - 2, 1), fill=WOOD_L)
    if iron:
        for bx in (4, w - 7):
            d.rectangle((bx, 0, bx + 2, h + 4), fill=IRON, outline=(30, 30, 36))
        d.rectangle((w // 2 - 2, h - 1, w // 2 + 1, h + 3), fill=(200, 170, 70), outline=(70, 50, 10))
    return im, 0, 0


def shelf(rng, w=60, h=12, items='jars'):
    im, d = _img(w + 2, h + 4)
    d.rectangle((0, 0, w - 1, h - 1), fill=WOOD_D, outline=OUT)
    d.rectangle((1, h - 4, w - 2, h - 1), fill=WOOD, outline=OUT)
    x = 3
    while x < w - 6:
        kind = rng.random()
        if items == 'jars':
            c = [(150, 90, 60), (90, 120, 150), (190, 180, 150), (110, 140, 90)][int(rng.integers(0, 4))]
            r = int(rng.integers(2, 4))
            d.ellipse((x, 2, x + 2 * r, 2 + 2 * r), fill=c, outline=_shade(c, 0.5))
            d.point((x + 1, 3), fill=_shade(c, 1.4))
            x += 2 * r + 2
        elif items == 'books':
            c = [(120, 40, 40), (40, 70, 110), (70, 90, 50), (130, 100, 50)][int(rng.integers(0, 4))]
            d.rectangle((x, 1, x + 2, h - 5), fill=c, outline=_shade(c, 0.5))
            x += 3
        else:  # helmets / tools
            d.ellipse((x, 2, x + 6, 7), fill=IRON_L, outline=IRON)
            x += 9
    return im, 0, 0


# --- arms ------------------------------------------------------------------------------------------------------
def weapon_rack(rng, w=44, kind='spears'):
    """Free-standing rack against a north wall: a wooden frame with weapons standing in it (seen from above-front)."""
    h = 30
    im, d = _img(w + 2, h + 2)
    d.rectangle((0, h - 7, w - 1, h - 1), fill=WOOD, outline=OUT)            # base trough
    d.line((1, h - 6, w - 2, h - 6), fill=WOOD_L)
    d.rectangle((0, 3, w - 1, 6), fill=WOOD_D, outline=OUT)                  # top rail
    for x in range(5, w - 3, 6):
        if kind == 'spears':
            d.line((x, 0, x, h - 6), fill=(120, 82, 48))
            d.polygon([(x - 1, 2), (x + 1, 2), (x, -2)], fill=IRON_L)
            d.line((x - 1, 1, x + 1, 1), fill=(220, 220, 230))
        elif kind == 'swords':
            d.line((x, 1, x, h - 9), fill=(200, 204, 214))
            d.line((x + 1, 1, x + 1, h - 9), fill=(120, 124, 134))
            d.line((x - 2, h - 9, x + 3, h - 9), fill=(150, 120, 50))
            d.rectangle((x, h - 8, x + 1, h - 6), fill=(80, 50, 30))
        else:   # bows
            d.arc((x - 3, 2, x + 3, h - 7), 270, 90, fill=(130, 90, 50))
            d.line((x, 3, x, h - 8), fill=(220, 220, 200))
    return im, 0, 0


def armour_stand(rng, c=(170, 174, 186)):
    im, d = _img(20, 30)
    d.rectangle((6, 22, 13, 28), fill=WOOD_D, outline=OUT)                   # foot
    d.rectangle((9, 8, 10, 24), fill=WOOD)
    d.rounded_rectangle((2, 9, 17, 22), 4, fill=c, outline=(50, 52, 60))     # breastplate
    d.line((9, 10, 9, 21), fill=_shade(c, 1.2))
    d.arc((3, 10, 16, 21), 180, 260, fill=(240, 240, 250))
    d.ellipse((5, 0, 14, 9), fill=_shade(c, 0.95), outline=(50, 52, 60))     # helm
    d.line((6, 5, 13, 5), fill=(30, 30, 36))
    d.ellipse((7, 1, 9, 3), fill=(240, 240, 250))
    return im, 0, 0


def shield_wall(rng, c=(150, 40, 40), emblem=(220, 180, 60)):
    """Heater shield hung on a wall face."""
    im, d = _img(14, 17)
    d.polygon([(0, 0), (13, 0), (13, 8), (7, 16), (6, 16), (0, 8)], fill=c, outline=(40, 20, 20))
    d.polygon([(5, 3), (8, 3), (8, 7), (11, 7), (11, 9), (8, 9), (8, 13), (5, 13), (5, 9), (2, 9), (2, 7), (5, 7)],
              fill=emblem)
    d.line((1, 1, 12, 1), fill=_shade(c, 1.35))
    return im, 0, 0


def anvil(rng):
    im, d = _img(26, 20)
    d.rectangle((6, 8, 18, 18), fill=WOOD_D, outline=OUT)                    # stump
    d.polygon([(0, 4), (18, 4), (24, 6), (18, 9), (2, 9)], fill=(70, 70, 78), outline=(26, 26, 30))
    d.line((2, 5, 18, 5), fill=(170, 170, 182))
    return im, 0, 0


def grindstone(rng):
    im, d = _img(26, 22)
    d.rectangle((2, 12, 23, 20), fill=WOOD, outline=OUT)
    d.ellipse((6, 2, 19, 15), fill=(150, 140, 126), outline=(60, 56, 50))
    d.ellipse((11, 7, 14, 10), fill=(80, 70, 60))
    d.line((19, 8, 25, 8), fill=WOOD_D, width=2)
    return im, 0, 0


# --- fire --------------------------------------------------------------------------------------------------------
def hearth(rng, w=64, mat=((214, 182, 122), (132, 100, 58), (170, 136, 82))):
    """Fireplace built against a north wall: stone jambs + hood, dark firebox with logs and embers, hearthstone."""
    top, mortar, face = mat
    h = 34
    im, d = _img(w + 2, h + 2)
    d.rectangle((0, 0, w - 1, 12), fill=face, outline=OUT)                    # hood / mantel
    for x in range(0, w, 10): d.line((x, 1, x, 11), fill=mortar)
    d.line((1, 1, w - 2, 1), fill=_shade(top, 1.1))
    d.rectangle((0, 12, 7, 26), fill=top, outline=OUT)                        # jambs
    d.rectangle((w - 8, 12, w - 1, 26), fill=top, outline=OUT)
    d.rectangle((8, 12, w - 9, 26), fill=(30, 20, 16))                         # firebox
    for i in range(3):                                                         # logs
        x = 12 + i * (w - 28) // 3
        d.rounded_rectangle((x, 19, x + (w - 28) // 3 + 4, 24), 2, fill=(92, 56, 30), outline=(40, 22, 12))
    for _ in range(14):                                                        # embers
        x, y = int(rng.integers(10, w - 10)), int(rng.integers(20, 26))
        d.point((x, y), fill=(255, int(rng.integers(90, 200)), 40))
    d.rectangle((0, 26, w - 1, h - 1), fill=_shade(top, 0.92), outline=OUT)   # hearthstone
    d.line((1, 27, w - 2, 27), fill=_shade(top, 1.1))
    return im, 0, 0


def cauldron(rng, r=9):
    im, d = _img(2 * r + 4, 2 * r + 6)
    d.ellipse((0, 4, 2 * r + 2, 2 * r + 5), fill=(30, 30, 34))
    d.ellipse((0, 0, 2 * r + 2, 2 * r + 2), fill=(52, 52, 58), outline=(18, 18, 22))
    d.ellipse((3, 3, 2 * r - 1, 2 * r - 1), fill=(120, 90, 50))
    d.arc((1, 1, 2 * r + 1, 2 * r + 1), 200, 280, fill=(140, 140, 150))
    return im, 0, 0


# --- textiles ----------------------------------------------------------------------------------------------------
def rug(rng, w=80, h=50, c=(140, 40, 40), border=(210, 170, 80)):
    im, d = _img(w, h)
    d.rectangle((0, 0, w - 1, h - 1), fill=_shade(c, 0.8))
    d.rectangle((3, 3, w - 4, h - 4), fill=border)
    d.rectangle((6, 6, w - 7, h - 7), fill=c)
    cx, cy = w // 2, h // 2
    d.polygon([(cx, 9), (w - 12, cy), (cx, h - 10), (11, cy)], outline=border)
    d.polygon([(cx, 15), (w - 20, cy), (cx, h - 16), (19, cy)], fill=_shade(c, 1.2))
    for x in range(0, w, 3):                                                   # fringe
        d.point((x, 0), fill=(230, 220, 190)); d.point((x, h - 1), fill=(230, 220, 190))
    return im, 0, 0


def desk(rng, w=40, h=20):
    im, d = _img(w + 2, h + 6)
    d.rectangle((1, h - 2, w - 2, h + 4), fill=WOOD_D, outline=OUT)
    d.rectangle((0, 0, w - 1, h - 1), fill=(126, 76, 40), outline=OUT)
    d.line((1, 1, w - 2, 1), fill=(170, 110, 64))
    d.rectangle((6, 4, 20, 13), fill=(232, 220, 190), outline=(150, 130, 100))  # papers
    d.line((8, 7, 18, 7), fill=(120, 110, 100)); d.line((8, 10, 16, 10), fill=(120, 110, 100))
    d.ellipse((26, 5, 30, 9), fill=(30, 30, 40))                              # inkpot
    d.line((29, 4, 33, 0), fill=(240, 240, 240))                              # quill
    d.rectangle((w - 9, 3, w - 5, 9), fill=(236, 226, 200))                   # candle
    return im, 0, 0


def wall_rack_pegs(rng, w=40):
    """Cloak pegs with cloaks hanging, on a north wall face."""
    im, d = _img(w, 16)
    d.rectangle((0, 0, w - 1, 2), fill=WOOD_D, outline=OUT)
    for x in range(3, w - 6, 10):
        c = [(110, 40, 40), (60, 70, 110), (80, 80, 60)][int(rng.integers(0, 3))]
        d.polygon([(x, 2), (x + 7, 2), (x + 8, 14), (x - 1, 14)], fill=c, outline=_shade(c, 0.5))
        d.line((x + 1, 3, x + 1, 13), fill=_shade(c, 1.25))
    return im, 0, 0


def water_butt(rng):
    im, ox, oy = barrel(rng, 9)
    d = ImageDraw.Draw(im)
    d.ellipse((5, 5, 13, 13), fill=(70, 100, 130), outline=(40, 60, 80))
    d.point((7, 7), fill=(190, 220, 240))
    return im, 0, 0


def firewood(rng, w=26):
    im, d = _img(w, 14)
    for row in range(3):
        for i in range(w // 7):
            x = 1 + i * 7 + (row % 2) * 3; y = 8 - row * 4
            d.ellipse((x, y, x + 6, y + 5), fill=(150, 104, 60), outline=(70, 44, 22))
            d.point((x + 3, y + 2), fill=(200, 160, 110))
    return im, 0, 0


def mop_bucket(rng):
    im, d = _img(12, 12)
    d.ellipse((1, 2, 10, 11), fill=(120, 84, 50), outline=OUT)
    d.ellipse((3, 4, 8, 9), fill=(80, 110, 140))
    return im, 0, 0


def pillar(rng, r=11, mat=((214, 182, 122), (132, 100, 58), (170, 136, 82)), square=False):
    """Stone pillar holding up the floor above: cut top (wall-top stone) with its south face showing below."""
    top, mortar, face = mat
    s = 2 * r + 2
    im, d = _img(s + 2, s + 20)
    # shaft face (visible south half, drawn as a band below the top)
    if square:
        d.rectangle((0, r, 2 * r, 2 * r + 12), fill=face, outline=OUT)
        for yy in range(r + 4, 2 * r + 12, 6): d.line((1, yy, 2 * r - 1, yy), fill=mortar)
        d.rectangle((0, 0, 2 * r, 2 * r), fill=top, outline=OUT)
        d.rectangle((2, 2, 2 * r - 2, 2 * r - 2), outline=_shade(top, 1.1))
    else:
        F = 18
        d.rectangle((0, r, 2 * r, r + F), fill=face)
        d.ellipse((0, F, 2 * r, 2 * r + F), fill=face, outline=OUT)
        d.line((0, r, 0, r + F), fill=OUT); d.line((2 * r, r, 2 * r, r + F), fill=OUT)
        for yy in range(r + 6, r + F + r, 6):
            d.arc((0, yy - r, 2 * r, yy + r), 20, 160, fill=_shade(face, 0.8))
        d.rectangle((1, r, 4, r + F), fill=_shade(face, 1.12))
        d.rectangle((2 * r - 5, r, 2 * r - 1, r + F), fill=_shade(face, 0.78))
        d.ellipse((0, 0, 2 * r, 2 * r), fill=top, outline=OUT)
        d.ellipse((3, 3, 2 * r - 3, 2 * r - 3), outline=_shade(top, 0.85))
        d.arc((1, 1, 2 * r - 1, 2 * r - 1), 190, 280, fill=_shade(top, 1.18))
    return im, r, r


def big_hearth(rng, w=96, mat=((214, 182, 122), (132, 100, 58), (170, 136, 82)), pot=True):
    """Large fireplace against a north wall, with a fire burning and (optionally) a cauldron on a crane."""
    top, mortar, face = mat
    h = 46
    im, d = _img(w + 2, h + 2)
    # chimney breast top (projecting from the wall)
    d.rectangle((0, 0, w - 1, 10), fill=top, outline=OUT)
    for x in range(0, w, 20): d.line((x, 0, x, 10), fill=mortar)
    # its south face: hood
    d.rectangle((0, 10, w - 1, 20), fill=face, outline=OUT)
    d.line((1, 11, w - 2, 11), fill=_shade(face, 0.7))
    for x in range(10, w, 20): d.line((x, 12, x, 19), fill=mortar)
    # jambs
    d.rectangle((0, 20, 9, 38), fill=face, outline=OUT)
    d.rectangle((w - 10, 20, w - 1, 38), fill=face, outline=OUT)
    # firebox
    d.rectangle((10, 20, w - 11, 38), fill=(22, 14, 10))
    d.rectangle((10, 20, w - 11, 23), fill=(10, 6, 4))
    for i in range(3):
        x = 16 + i * (w - 40) // 3
        d.rounded_rectangle((x, 30, x + (w - 40) // 3 + 6, 35), 2, fill=(92, 56, 30), outline=(40, 22, 12))
    # flames (static base; the game animates on top)
    for i in range(7):
        fx = 18 + i * (w - 36) // 7
        fh = int(rng.integers(6, 12))
        d.polygon([(fx - 4, 33), (fx + 4, 33), (fx + 1, 33 - fh), (fx - 1, 33 - fh + 2)], fill=(255, 150, 40))
        d.polygon([(fx - 2, 33), (fx + 2, 33), (fx, 33 - fh // 2)], fill=(255, 230, 140))
    for _ in range(20):
        x, y = int(rng.integers(12, w - 12)), int(rng.integers(34, 38))
        d.point((x, y), fill=(255, int(rng.integers(90, 200)), 40))
    if pot:
        cx = w // 2
        d.line((cx - 18, 21, cx + 2, 21), fill=(40, 40, 44), width=2)          # crane arm
        d.line((cx, 21, cx, 25), fill=(40, 40, 44))
        d.ellipse((cx - 8, 24, cx + 8, 36), fill=(46, 46, 52), outline=(16, 16, 18))
        d.ellipse((cx - 6, 25, cx + 6, 29), fill=(110, 80, 46))
        d.arc((cx - 7, 25, cx + 7, 35), 200, 280, fill=(130, 130, 140))
    # hearthstone apron
    d.rectangle((-1, 38, w, h - 1), fill=_shade(top, 0.94), outline=OUT)
    d.line((1, 39, w - 2, 39), fill=_shade(top, 1.12))
    for x in range(14, w, 22): d.line((x, 39, x, h - 2), fill=mortar)
    return im, 0, 0


def serving_table(rng, w=60, h=20):
    im, ox, oy = table(rng, w, h, items=False)
    d = ImageDraw.Draw(im)
    for i in range(w // 12):
        x = 5 + i * 12
        d.ellipse((x, 4, x + 8, 10), fill=(176, 176, 184), outline=(90, 90, 98))
    d.ellipse((w - 18, 10, w - 6, 18), fill=(120, 84, 50), outline=OUT)
    d.ellipse((w - 16, 12, w - 8, 16), fill=(200, 160, 90))
    return im, 0, 0


def shield_stand(rng):
    im, d = _img(34, 26)
    d.rectangle((0, 18, 33, 24), fill=WOOD, outline=OUT)
    for i, c in enumerate([(150, 40, 40), (40, 70, 130), (60, 110, 60)]):
        x = 1 + i * 11
        d.polygon([(x, 2), (x + 10, 2), (x + 10, 11), (x + 5, 20), (x, 11)], fill=c, outline=(30, 20, 20))
        d.rectangle((x + 4, 5, x + 6, 13), fill=(220, 180, 60))
        d.line((x + 1, 3, x + 9, 3), fill=_shade(c, 1.4))
    return im, 0, 0


def arrow_barrel(rng):
    im, ox, oy = barrel(rng, 8)
    d = ImageDraw.Draw(im)
    for _ in range(9):
        x, y = int(rng.integers(5, 13)), int(rng.integers(5, 13))
        d.point((x, y), fill=(240, 240, 240)); d.point((x + 1, y), fill=(200, 60, 50))
    return im, 0, 0


def wardrobe(rng, w=36):
    im, d = _img(w + 2, 22)
    d.rectangle((0, 6, w - 1, 20), fill=WOOD_D, outline=OUT)
    d.rectangle((0, 0, w - 1, 8), fill=WOOD, outline=OUT)
    d.line((w // 2, 8, w // 2, 20), fill=OUT)
    d.point((w // 2 - 2, 14), fill=(200, 170, 70)); d.point((w // 2 + 2, 14), fill=(200, 170, 70))
    return im, 0, 0


def workbench(rng, w=70, h=22):
    im, ox, oy = table(rng, w, h, items=False)
    d = ImageDraw.Draw(im)
    d.line((6, 6, 20, 6), fill=(90, 90, 100), width=2)             # file
    d.rectangle((26, 4, 32, 10), fill=(90, 90, 100))               # vice
    d.line((40, 12, 52, 8), fill=(200, 200, 210))                  # blade
    d.line((52, 8, 56, 7), fill=(120, 80, 40), width=2)
    d.ellipse((w - 14, 5, w - 6, 13), fill=(176, 176, 184), outline=(90, 90, 98))
    return im, 0, 0
