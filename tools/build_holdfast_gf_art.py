#!/usr/bin/env python3
"""Holdfast ground floor from the user's painted interior (art/source/holdfast/gf_v1/interior_gf_joined.png).
Walkable areas are laid out by hand on the art (H = half-resolution art px, 1352 x 1164), rooms named; everything
else inside the castle (walls, towers' masonry) and the background is solid; colonnade columns are small solids.
Game scale: the castle (2619 art px across the corner towers) = 1536 game px, the Holdfast's outside width.
Writes art/game/holdfast/gf_art.png, data/holdfast_gf_regions.png, data/holdfast_gf.json."""
import os, json
import numpy as np, cv2
from PIL import Image
from scipy import ndimage
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
art = Image.open(os.path.join(ROOT, 'art/source/holdfast/gf_v1/interior_gf_joined.png')).convert('RGB')
K = 1536 / 1309.5                        # game px per H px
GW, GH = round(1352 * K), round(1164 * K)
TILE = 16
img = art.resize((GW, GH), Image.LANCZOS)
os.makedirs(os.path.join(ROOT, 'art/game/holdfast'), exist_ok=True)
img.save(os.path.join(ROOT, 'art/game/holdfast/gf_art.png'))

# ---- walkable areas (H coords): (name, kind, shape)   kind r=rect (x0,y0,x1,y1), c=circle (cx,cy,r)
AREAS = [
    ('North-west tower', 'c', (140, 192, 70)), ('North-west tower', 'r', (165, 225, 245, 300)),
    ('Kitchen', 'r', (230, 212, 555, 350)), ('Kitchen', 'r', (160, 290, 245, 360)),
    ('Pantry', 'r', (160, 392, 400, 520)), ('Pantry', 'r', (265, 345, 400, 395)),
    ('Cloister', 'r', (265, 345, 460, 410)),
    ('Courtyard', 'r', (410, 380, 910, 765)),
    ('Tower armoury', 'r', (580, 195, 820, 372)), ('Tower armoury', 'r', (692, 368, 735, 395)),
    ('Guardroom', 'r', (850, 190, 1195, 372)), ('Guardroom', 'r', (850, 368, 905, 400)),
    ('North-east tower', 'c', (1180, 185, 68)), ('North-east tower', 'r', (1080, 228, 1195, 275)),
    ('Gate passage', 'r', (905, 445, 1352, 528)),
    ('Waiting room', 'r', (930, 562, 1168, 715)), ('Waiting room', 'r', (905, 680, 935, 718)),
    ("Guards' bunks", 'r', (855, 750, 1165, 955)), ("Guards' bunks", 'r', (855, 730, 910, 760)),
    ('South-east tower', 'c', (1215, 990, 62)), ('South-east tower', 'r', (1120, 940, 1200, 990)),
    ('Lower hall', 'r', (495, 760, 825, 955)), ('Lower hall', 'r', (650, 738, 690, 765)),
    ("Servants' room", 'r', (160, 575, 400, 775)), ("Servants' room", 'r', (395, 590, 425, 760)),
    ('West walk', 'r', (420, 400, 480, 955)),
    ('Stores', 'r', (160, 800, 470, 952)),
    ('South-west tower', 'c', (130, 985, 68)), ('South-west tower', 'r', (200, 930, 250, 975)),
]
COLS = [(482, 465), (537, 465), (590, 465), (645, 465), (750, 465), (805, 465), (860, 465),
        (472, 520), (472, 575), (472, 630), (860, 520), (860, 575), (860, 630),
        (482, 700), (537, 700), (590, 700), (645, 700), (697, 700), (750, 700), (805, 700), (860, 700),
        (305, 410), (422, 410), (470, 410), (645, 395), (860, 395), (905, 410),
        (432, 760), (472, 760), (645, 760), (692, 760), (860, 760), (905, 760)]
# room-name order (region ids 1..)
names = ['']
reg = np.zeros((GH, GW), np.uint8)
for nm, kind, sh in AREAS:
    if nm not in names: names.append(nm)
    rid = names.index(nm)
    m = np.zeros((GH, GW), np.uint8)
    if kind == 'r':
        x0, y0, x1, y1 = (round(v * K) for v in sh); m[y0:y1, x0:x1] = 1
    else:
        cv2.circle(m, (round(sh[0] * K), round(sh[1] * K)), round(sh[2] * K), 1, -1)
    reg[(m > 0) & (reg == 0)] = rid
walk = reg > 0
# courtyard well and columns are solid
for cx, by in COLS:
    x, y = round(cx * K), round(by * K)
    walk[y - 16:y, x - 12:x + 12] = False
wx, wy = round(665 * K), round(570 * K)
walk[wy - 30:wy + 22, wx - 34:wx + 34] = False
# ---- collision: solid = not walkable, as merged rects on an 8 px grid
C = 8
gw, gh = GW // C + 1, GH // C + 1
sol = np.ones((gh, gw), bool)
for j in range(gh):
    for i in range(gw):
        b = walk[j * C:(j + 1) * C, i * C:(i + 1) * C]
        if b.size and b.mean() > 0.5: sol[j, i] = False
rects = []; used = np.zeros_like(sol)
for j in range(gh):
    i = 0
    while i < gw:
        if sol[j, i] and not used[j, i]:
            i1 = i
            while i1 + 1 < gw and sol[j, i1 + 1] and not used[j, i1 + 1]: i1 += 1
            j1 = j
            while j1 + 1 < gh and sol[j1 + 1, i:i1 + 1].all() and not used[j1 + 1, i:i1 + 1].any(): j1 += 1
            used[j:j1 + 1, i:i1 + 1] = True
            rects.append([i * C, j * C, (i1 - i + 1) * C, (j1 - j + 1) * C]); i = i1 + 1
        else: i += 1
# ---- regions per 16 px tile (3 slots like before: the fog shader reads R)
tw, th = (GW + TILE - 1) // TILE, (GH + TILE - 1) // TILE
R = np.zeros((th, tw, 3), np.uint8)
for j in range(th):
    for i in range(tw):
        b = reg[j * TILE:(j + 1) * TILE, i * TILE:(i + 1) * TILE]
        v = b[b > 0]
        if v.size: R[j, i, 0] = np.bincount(v).argmax()
# walls take the nearest room so a room's walls light up with it
_, (iy, ix) = ndimage.distance_transform_edt(R[..., 0] == 0, return_indices=True)
near = R[..., 0][iy, ix]; d = ndimage.distance_transform_edt(R[..., 0] == 0)
R[..., 0] = np.where(d <= 3, near, R[..., 0])
Image.fromarray(R).save(os.path.join(ROOT, 'data/holdfast_gf_regions.png'))
# ---- torches: flame centres of the painted torches (H coords, read off the art); each gets our animated flame + light
FLAMES = [(150, 120), (265, 255), (540, 255), (180, 420), (335, 205), (368, 205),
          (600, 190), (752, 190), (873, 190), (1060, 190), (1262, 105),
          (183, 592), (378, 592), (970, 592), (1142, 592), (547, 780), (797, 780), (1125, 780),
          (218, 825), (83, 900), (1132, 945)]
torches = []
for hx, hy in FLAMES:
    x, y = round(hx * K), round(hy * K)
    j, i = min(th - 1, y // TILE), min(tw - 1, x // TILE)
    rid = int(R[j, i, 0])
    if rid == 0:
        ys_, xs_ = np.nonzero(R[..., 0]); k = np.argmin((ys_ - j) ** 2 + (xs_ - i) ** 2); rid = int(R[ys_[k], xs_[k], 0])
    torches.append([x, y, rid, 1])
P = lambda x, y: [round(x * K), round(y * K)]
D = {'tile': TILE, 'size': [GW, GH], 'image': 'res://art/game/holdfast/gf_art.png', 'solid': rects,
     'spawn': P(1325, 488), 'exit': P(1340, 488),
     'stairs': [{'name': "Guards' stair (up)", 'pos': P(1150, 235)}, {'name': 'Royal stair (up)', 'pos': P(165, 960)}],
     'regions': 'res://data/holdfast_gf_regions.png', 'region_names': names, 'torches': torches}
json.dump(D, open(os.path.join(ROOT, 'data/holdfast_gf.json'), 'w'))
print('map', GW, GH, 'rects', len(rects), 'rooms', names[1:], 'torches', len(torches))
