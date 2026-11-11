#!/usr/bin/env python3
"""Castle exterior blueprint (site plan, top view) drawn from the game's own data:
ring wall art (art/source/walls/ring_world_v2.png), data/layout.json (gates, colliders, wall-walk access),
data/keep_proto.json (keep exterior) and the keep placement used by World.gd.  Output: design/castle_exterior_blueprint.png"""
import json, math, os, re, collections
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage
Image.MAX_IMAGE_PIXELS = None
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
L = json.load(open(os.path.join(ROOT, 'data/layout.json')))
K = json.load(open(os.path.join(ROOT, 'data/keep_proto.json')))
FB = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'; FR = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
def f(s, b=False): return ImageFont.truetype(FB if b else FR, s)

WW, WH = L['world']; TILE = L['tile']
S = 0.25; ML, MT = 150, 170; LEG = 640
W = ML + int(WW * S) + 40 + LEG; H = MT + int(WH * S) + 40
BG = (11, 39, 66); GRID = (22, 57, 92); MAJ = (36, 82, 127); LINE = (232, 242, 255); DIM = (255, 214, 120)
im = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(im, 'RGBA')
P = lambda x, y: (ML + x * S, MT + y * S)

# grid: 16-tile squares, major every 1024 px
for x in range(0, WW + 1, 256):
    d.line([P(x, 0), P(x, WH)], fill=MAJ if x % 1024 == 0 else GRID, width=1)
for y in range(0, WH + 1, 256):
    d.line([P(0, y), P(WW, y)], fill=MAJ if y % 1024 == 0 else GRID, width=1)
for x in range(0, WW + 1, 1024):
    d.text((P(x, 0)[0] - 14, MT - 44), str(x), font=f(14), fill=(150, 190, 230)); d.text((P(x, 0)[0] - 14, MT - 26), 't%d' % (x // TILE), font=f(11), fill=(110, 150, 190))
for y in range(0, WH + 1, 1024):
    d.text((ML - 70, P(0, y)[1] - 16), str(y), font=f(14), fill=(150, 190, 230)); d.text((ML - 70, P(0, y)[1] + 1), 't%d' % (y // TILE), font=f(11), fill=(110, 150, 190))
d.rectangle([P(0, 0), P(WW, WH)], outline=MAJ, width=2)

# ring wall (drawn extent of the art) + outline
ring = np.asarray(Image.open(os.path.join(ROOT, 'art/source/walls/ring_world_v2.png')))[..., 3] > 0
sm = np.asarray(Image.fromarray(ring.astype(np.uint8) * 255).resize((int(WW * S), int(WH * S)), Image.BOX)) > 100
fill = Image.new('RGBA', sm.shape[::-1], (0, 0, 0, 0)); fa = np.zeros(sm.shape + (4,), np.uint8)
fa[sm] = (44, 106, 160, 255)
yy, xx = np.indices(sm.shape)
hatch = sm & (((xx + yy) % 10) == 0)
fa[hatch] = (70, 140, 200, 255)
edge = sm & ~ndimage.binary_erosion(sm)
fa[ndimage.binary_dilation(edge)] = (*LINE, 255)
im.paste(Image.fromarray(fa, 'RGBA'), (ML, MT), Image.fromarray(fa, 'RGBA'))
d = ImageDraw.Draw(im, 'RGBA')

# wall-walk limits (walk-layer colliders) and ground blocking lines (hand-drawn wall feet)
for q in L['colliders']['walk']:
    pts = [P(*p) for p in q['poly']]
    d.line(pts + [pts[0]], fill=(127, 211, 255, 150), width=1)
for q in L['colliders']['ground']:
    pts = [P(*p) for p in q['poly']]
    d.line(pts + [pts[0]], fill=(255, 224, 138, 255), width=2)

# towers
T = collections.defaultdict(list)
for q in L['colliders']['walk']:
    m = re.match(r'walk_tower_(\d+)', q['sec'])
    if m: T[int(m.group(1))] += q['poly']
for k, pts in T.items():
    c = np.array(pts).mean(0); x, y = P(*c)
    d.ellipse([x - 13, y - 13, x + 13, y + 13], fill=(11, 39, 66, 230), outline=LINE, width=2)
    tw = d.textlength(str(k), font=f(12, True)); d.text((x - tw / 2, y - 8), str(k), font=f(12, True), fill=LINE)

# keep (placement = World.gd: KEEP_AXIS_X 3944, KEEP_DOOR_Y 3100)
ex = K['exterior']; kx0 = 3944 - ex['door_x']; ky0 = 3100 - ex['door_y']; kw, kh = ex['size']
ka = np.asarray(Image.open(os.path.join(ROOT, 'art/game/keep/exterior.png')))[..., 3] > 0
ks = np.asarray(Image.fromarray(ka.astype(np.uint8) * 255).resize((int(kw * S), int(kh * S)), Image.BOX)) > 100
kf = np.zeros(ks.shape + (4,), np.uint8)
yy, xx = np.indices(ks.shape)
kf[ks] = (190, 80, 60, 120); kf[ks & (((xx - yy) % 8) == 0)] = (255, 140, 110, 200)
ke = ks & ~ndimage.binary_erosion(ks); kf[ndimage.binary_dilation(ke)] = (255, 170, 140, 255)
kimg = Image.fromarray(kf, 'RGBA'); im.paste(kimg, (int(P(kx0, ky0)[0]), int(P(kx0, ky0)[1])), kimg)
d = ImageDraw.Draw(im, 'RGBA')
kb = [ky0 + b for b in ex['bottom'] if b >= 0]
d.line([P(kx0, 3100), P(kx0 + kw, 3100)], fill=(255, 170, 140, 160), width=1)
x, y = P(3944, 3100); d.polygon([(x, y + 2), (x - 9, y + 16), (x + 9, y + 16)], fill=(255, 210, 120))
d.text(P(kx0 + 640, ky0 + 560), 'RED KEEP', font=f(26, True), fill=(255, 225, 205))
d.text(P(kx0 + 470, ky0 + 700), '%d x %d px  (%d x %d tiles)' % (kw, kh, round(kw / 16), round(kh / 16)), font=f(15), fill=(255, 225, 205))
d.text(P(kx0 + 420, ky0 + 790), 'scale 1:1 - bricks match the ring wall', font=f(13), fill=(255, 205, 185))
d.text(P(kx0 + 470, ky0 + 870), 'enter: E at the gate (3944, 3100)', font=f(13), fill=(255, 205, 185))

# gates, access stairs, spawn
def tag(x, y, txt, col, dx=14, dy=-10, sz=13):
    X, Y = P(x, y); d.text((X + dx, Y + dy), txt, font=f(sz, True), fill=col, stroke_width=3, stroke_fill=BG)
for g, (x, y) in L['gates'].items():
    X, Y = P(x, y); d.rectangle([X - 7, Y - 7, X + 7, Y + 7], fill=(255, 120, 90), outline=LINE, width=2)
tag(3944, 1000, 'NORTH GATE', (255, 160, 130), 26, -12, 15)
tag(3944, 3960, 'SOUTH GATE (main)', (255, 160, 130), 30, -12, 15)
for a in L['access']:
    g = P(*a['ground']); w = P(*a['walk'])
    d.line([g, w], fill=(120, 255, 160), width=2)
    d.ellipse([g[0] - 6, g[1] - 6, g[0] + 6, g[1] + 6], fill=(120, 255, 160)); d.rectangle([w[0] - 5, w[1] - 5, w[0] + 5, w[1] + 5], outline=(120, 255, 160), width=2)
X, Y = P(*L['spawn']); d.ellipse([X - 7, Y - 7, X + 7, Y + 7], outline=(255, 255, 255), width=3); tag(*L['spawn'], 'player spawn', LINE, 12, -8, 12)

# dimension lines
def dim(a, b, txt, side=0, col=DIM, off=(0, 0)):
    (x1, y1), (x2, y2) = P(*a), P(*b)
    d.line([(x1, y1), (x2, y2)], fill=col, width=2)
    ang = math.atan2(y2 - y1, x2 - x1)
    for (x, y), s_ in (((x1, y1), 1), ((x2, y2), -1)):
        for da in (0.45, -0.45):
            d.line([(x, y), (x + s_ * 11 * math.cos(ang + da), y + s_ * 11 * math.sin(ang + da))], fill=col, width=2)
    mx, my = (x1 + x2) / 2 + off[0], (y1 + y2) / 2 + off[1]
    tw = d.textlength(txt, font=f(13, True))
    d.rectangle([mx - tw / 2 - 4, my - 9, mx + tw / 2 + 4, my + 9], fill=(11, 39, 66, 230))
    d.text((mx - tw / 2, my - 8), txt, font=f(13, True), fill=col)
def px(n): return '%d px (%d t)' % (n, round(n / 16))
ys, xs = np.where(ring); X0, X1, Y0, Y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
dim((X0, 4560), (X1, 4560), 'castle drawn width ' + px(X1 - X0))
d.line([P(X0, Y1), P(X0, 4590)], fill=(255, 214, 120, 120)); d.line([P(X1, Y1), P(X1, 4590)], fill=(255, 214, 120, 120))
dim((380, Y0), (380, Y1), 'height ' + px(Y1 - Y0), off=(0, 0))
d.line([P(380, Y0), P(X0 + 400, Y0)], fill=(255, 214, 120, 120))
def run(v):
    i = np.where(np.diff(v.astype(int)) != 0)[0] + 1; return list(i)
r2400 = run(ring[2400]); c3000 = run(ring[:, 3000])
cw0, cw1 = r2400[1], r2400[2]                     # courtyard clear width at y 2400
dim((cw0, 2400), (cw1, 2400), 'courtyard clear width ' + px(cw1 - cw0) + '  @ y 2400', off=(0, 0))
cd0, cd1 = c3000[1], c3000[2]
dim((3000, cd0), (3000, cd1), 'clear depth ' + px(cd1 - cd0) + ' @ x 3000', off=(0, -300))
dim((r2400[0], 2250), (r2400[1], 2250), 'W ' + str(r2400[1] - r2400[0]), off=(0, -22))
dim((r2400[2], 2250), (r2400[3], 2250), 'E ' + str(r2400[3] - r2400[2]), off=(0, -22))
dim((3000, c3000[0]), (3000, c3000[1]), 'N ' + str(c3000[1] - c3000[0]), off=(46, 0))
dim((3000, c3000[2]), (3000, c3000[3]), 'S ' + str(c3000[3] - c3000[2]), off=(46, 0))
dim((cw0, 2900), (kx0, 2900), 'west lane ' + px(kx0 - cw0))
dim((kx0 + kw, 2900), (cw1, 2900), 'east lane ' + px(cw1 - kx0 - kw))
c3944 = run(ring[:, 3944])
dim((4450, 3100), (4450, c3944[2] if len(c3944) > 2 else 3482), 'front court ' + str((c3944[2] if len(c3944) > 2 else 3482) - 3100), off=(70, 0))
def hole(y, a=3600, b=4300):
    v = ~ring[y, a:b]; i = np.where(v)[0]; return a + i.min(), a + i.max() + 1
n0, n1 = hole(1000); s0, s1 = hole(3950)
dim((n0, 1060), (n1, 1060), 'passage %d' % (n1 - n0), off=(0, 26))
dim((s0, 4000), (s1, 4000), 'passage %d' % (s1 - s0), off=(0, 26))

# north arrow + scale bar
nx, ny = P(7550, 300)
d.polygon([(nx, ny - 40), (nx - 14, ny + 6), (nx, ny - 4), (nx + 14, ny + 6)], fill=LINE); d.text((nx - 6, ny + 10), 'N', font=f(18, True), fill=LINE)
sx, sy = P(5900, 4700)
d.rectangle([sx, sy, sx + 1024 * S, sy + 8], outline=LINE, width=2); d.rectangle([sx, sy, sx + 512 * S, sy + 8], fill=LINE)
d.text((sx, sy + 12), '0      512      1024 px  (64 tiles)', font=f(12), fill=LINE)

# title + legend
d.rectangle([0, 0, W, 96], fill=(6, 22, 40))
d.text((20, 14), 'CASTLE EXTERIOR - BLUEPRINT', font=f(40, True), fill=LINE)
d.text((22, 62), 'Site plan, top view.  Drawn from the game data (ring wall art, colliders, gates, keep placement).  1 px here = 4 world px.', font=f(18), fill=(160, 195, 230))
lx = ML + int(WW * S) + 40; ly = MT
def sw(y, kind, col, txt):
    if kind == 'fill': d.rectangle([lx, y, lx + 34, y + 18], fill=col, outline=LINE)
    elif kind == 'line': d.line([lx, y + 9, lx + 34, y + 9], fill=col, width=3)
    elif kind == 'thin': d.line([lx, y + 9, lx + 34, y + 9], fill=col, width=1)
    elif kind == 'dot': d.ellipse([lx + 10, y + 2, lx + 24, y + 16], fill=col)
    elif kind == 'ring': d.ellipse([lx + 6, y - 1, lx + 28, y + 19], outline=LINE, width=2); d.text((lx + 12, y + 1), '7', font=f(12, True), fill=LINE)
    d.text((lx + 46, y), txt, font=f(15), fill=LINE)
d.text((lx, ly), 'KEY', font=f(22, True), fill=LINE); ly += 38
for kind, col, txt in [('fill', (44, 106, 160), 'Ring wall, drawn extent (faces + tops)'), ('line', (255, 224, 138), 'Ground blocking line (wall foot)'),
                       ('thin', (127, 211, 255), 'Wall-walk limits (upper layer)'), ('ring', None, 'Tower number (22 towers)'),
                       ('dot', (255, 120, 90), 'Gate'), ('line', (120, 255, 160), 'Stair: ground -> wall-walk (4)'),
                       ('fill', (190, 80, 60), 'Red Keep (sprite silhouette, solid)'), ('line', DIM, 'Dimension (px, t = 16-px tiles)')]:
    sw(ly, kind, col, txt); ly += 30
ly += 14; d.text((lx, ly), 'FACTS', font=f(22, True), fill=LINE); ly += 36
facts = ['World  %d x %d px  (%d x %d tiles)' % (WW, WH, WW // 16, WH // 16), 'Tile 16 px,  chunk 512 px',
         'Castle drawn extent  %d x %d px' % (X1 - X0, Y1 - Y0), 'Courtyard clear  %d x %d px' % (cw1 - cw0, cd1 - cd0),
         'Wall bands (drawn): N %d  S %d  W %d  E %d' % (c3000[1] - c3000[0], c3000[3] - c3000[2], r2400[1] - r2400[0], r2400[3] - r2400[2]),
         'Gate axis x = 3944.  North gate (%d, %d)' % tuple(L['gates']['north']), 'South (main) gate (%d, %d)' % tuple(L['gates']['south']),
         'Gate passages: north %d px, south %d px wide' % (n1 - n0, s1 - s0), 'Wall-walk drawn %d px above the ground' % L['walk_height'],
         'Stairs to the wall-walk: towers 1, 2 (north), 15, 16 (south)', 'Keep: top-left (%d, %d), gate (3944, 3100)' % (kx0, ky0),
         'Keep size %d x %d px, lanes W %d / E %d, front court %d' % (kw, kh, kx0 - cw0, cw1 - kx0 - kw, (c3944[2] if len(c3944) > 2 else 3482) - 3100),
         'Player spawn (%d, %d), outside the south gate' % tuple(L['spawn'])]
for t_ in facts:
    d.text((lx, ly), t_, font=f(14), fill=(200, 222, 245)); ly += 24
ly += 12
d.text((lx, ly), 'Notes', font=f(18, True), fill=LINE); ly += 28
for t_ in ['The view is 3/4 top-down: the blue band is what is', 'drawn (wall tops + front faces), the yellow line is', 'where a character standing on the ground is stopped.',
           'North wall: you see its inner face from the courtyard.', 'South wall: you see its outer face from outside.']:
    d.text((lx, ly), t_, font=f(13), fill=(170, 200, 230)); ly += 21
os.makedirs(os.path.join(ROOT, 'design'), exist_ok=True)
out = os.path.join(ROOT, 'design/castle_exterior_blueprint.png')
im.save(out); print(out, im.size)
