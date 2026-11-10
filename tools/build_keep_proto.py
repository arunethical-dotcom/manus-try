#!/usr/bin/env python3
"""Red Keep PROTOTYPE builder.

Inputs : art/source/keep/gen/*.png (generated sheets, magenta background), data/keep_plan_v2.json (approved plan)
Outputs: art/game/keep/exterior.png          keep sprite for the courtyard (1:1, bricks match the ring wall)
         art/game/keep/L0.png L1.png Lm1.png level art, 16 px per plan tile (252 x 120 tiles = 4032 x 1920)
         art/game/keep/fx_*.png ov_*.png      fire / smoke frames, gate overlays
         data/keep_proto.json                collision rects, gates, stairs, fire stages, routes, exterior info
"""
import json, math, os
import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEN = os.path.join(ROOT, 'art/source/keep/gen')
OUT = os.path.join(ROOT, 'art/game/keep')
T = 16
P = json.load(open(os.path.join(ROOT, 'data/keep_plan_v2.json')))
MW, MH = P['size']
os.makedirs(OUT, exist_ok=True)

# ------------------------------------------------------------------ keying
def sheet(name):
    return np.asarray(Image.open(os.path.join(GEN, name)).convert('RGB')).astype(np.float32)

BG = np.array([246, 4, 249], np.float32)

def key(rgb):
    """magenta background -> alpha; pink fringe removed (colour un-mixed from the background)"""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    m = np.clip((np.minimum(r, b) - g - 60.0) / (235.0 - 60.0), 0, 1)       # 1 = pure background
    m = np.where((np.abs(r - b) < 80) & (g < 140), m, 0.0)
    a = 1.0 - m
    a = np.where(a < 0.06, 0.0, a)
    a3 = np.maximum(a, 1e-3)[..., None]
    col = (rgb - (1 - a)[..., None] * BG) / a3
    col = np.clip(col, 0, 255)
    # remaining magenta cast on edge pixels: pull r/b down towards g-relative neutral
    edge = (a > 0) & (a < 0.98)
    mag = np.clip(np.minimum(col[..., 0], col[..., 2]) - col[..., 1] - 40, 0, None)
    col[..., 0] -= np.where(edge, mag * 0.8, 0); col[..., 2] -= np.where(edge, mag * 0.8, 0)
    return np.dstack([np.clip(col, 0, 255), a * 255])

def shrink(rgba, w, h=None):
    """premultiplied LANCZOS resize, then a hard alpha edge (pixel-art crisp)"""
    H0, W0 = rgba.shape[:2]
    if h is None:
        h = max(1, round(H0 * w / W0))
    a = rgba[..., 3:4] / 255.0
    pm = np.dstack([rgba[..., :3] * a, a * 255])
    im = Image.fromarray(np.clip(pm, 0, 255).astype(np.uint8), 'RGBA').resize((w, h), Image.LANCZOS)
    x = np.asarray(im).astype(np.float32)
    al = x[..., 3:4] / 255.0
    col = np.where(al > 0.01, x[..., :3] / np.maximum(al, 1e-3), 0)
    alpha = np.where(x[..., 3] > 110, 255.0, 0.0)
    return np.dstack([np.clip(col, 0, 255), alpha])

def components(rgb, min_area=900):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    bg = (r > 170) & (g < 110) & (b > 170) & (np.abs(r - b) < 70)
    lab, _ = ndimage.label(ndimage.binary_dilation(~bg, iterations=6))
    bb = [(s[0].start, s[1].start, s[0].stop, s[1].stop) for s in ndimage.find_objects(lab)]
    bb = [b for b in bb if (b[2] - b[0]) * (b[3] - b[1]) > min_area]
    bb.sort(key=lambda b: (b[0] // 120, b[1]))
    return bb

def piece(rgb, bb, pad=2):
    y0, x0, y1, x1 = bb
    k = key(rgb[max(0, y0 - pad):y1 + pad, max(0, x0 - pad):x1 + pad])
    ys, xs = np.where(k[..., 3] > 0)
    return k[ys.min():ys.max() + 1, xs.min():xs.max() + 1]

TIL = sheet('red_keep_interior_tiles_2048.png')
PRO = sheet('red_keep_interior_props_2048.png')
UTL = sheet('red_keep_utilities_tiles_2048.png')
SPR = sheet('red_keep_sprite_2048.png')
bT, bP, bU = components(TIL), components(PRO), components(UTL)
assert len(bT) == 31 and len(bP) == 32 and len(bU) == 60, (len(bT), len(bP), len(bU))

PROPS = {  # name: (sheet, index)
 'throne': ('P', 0), 'bed_king': ('P', 1), 'bed_sister': ('P', 2), 'bed_red': ('P', 3), 'bed_blue': ('P', 4), 'crib': ('P', 5),
 'rocking_horse': ('P', 6), 'feast_table': ('P', 7), 'dining_table': ('P', 8), 'council_table': ('P', 9), 'desk': ('P', 10),
 'bookshelf': ('P', 11), 'scroll_rack': ('P', 12), 'wardrobe': ('P', 13), 'vanity': ('P', 14), 'settee': ('P', 15), 'armchair': ('P', 16),
 'strongbox': ('P', 17), 'harp': ('P', 18), 'embroidery': ('P', 19), 'fireplace': ('P', 20), 'tub': ('P', 21), 'privy': ('P', 22),
 'rug_red': ('P', 23), 'rug_teal': ('P', 24), 'rug_small': ('P', 25), 'statue_knight': ('P', 26), 'statue_kg': ('P', 27),
 'coffin': ('P', 28), 'banner': ('P', 29), 'candelabra': ('P', 30), 'altar': ('P', 31),
 'hearth': ('U', 0), 'oven': ('U', 1), 'prep_table': ('U', 2), 'pots': ('U', 3), 'barrels': ('U', 4), 'sacks': ('U', 5), 'meat': ('U', 6),
 'cheese': ('U', 7), 'well': ('U', 8), 'bunk': ('U', 9), 'woodpile': ('U', 10), 'hay': ('U', 11), 'washtubs': ('U', 12), 'lines': ('U', 13),
 'kennel': ('U', 14), 'cart': ('U', 15), 'oil_crates': ('U', 16), 'weapon_rack': ('U', 17), 'armour': ('U', 18), 'dummy': ('U', 19),
 'barracks_bunk': ('U', 20), 'winch': ('U', 21), 'bell': ('U', 22), 'oil_jars': ('U', 23), 'pitch': ('U', 24), 'pc_winch': ('U', 25),
 'cell_bars': ('U', 26), 'wine_rack': ('U', 27), 'casks': ('U', 28), 'treasure': ('U', 29), 'dock': ('U', 30), 'vault': ('U', 31),
 'bed_plain_r': ('U', 32), 'bed_plain_b': ('U', 33), 'crates': ('U', 34),
 'stairs_up': ('T', 22), 'stairs_down': ('T', 23), 'spiral': ('T', 24), 'bridge_down': ('T', 26), 'bridge_up': ('T', 27),
 'iron_gate': ('T', 28), 'portcullis': ('T', 20), 'door_locked': ('T', 19), 'grate': ('T', 29),
}
SH = {'T': (TIL, bT), 'P': (PRO, bP), 'U': (UTL, bU)}
_cache = {}
def prop(name, w_tiles, h_tiles=None):
    k = (name, w_tiles, h_tiles)
    if k not in _cache:
        s, i = PROPS[name]
        rgb, bb = SH[s]
        p = piece(rgb, bb[i])
        _cache[k] = shrink(p, int(w_tiles * T), int(h_tiles * T) if h_tiles else None)
    return _cache[k]

# ------------------------------------------------------------------ textures
def floor_tex(i, dark=1.0):
    y0, x0, y1, x1 = bT[i]
    c = key(TIL[y0 + 10:y1 - 10, x0 + 10:x1 - 10])[..., :3]
    t = np.asarray(Image.fromarray(c.astype(np.uint8)).resize((48, 48), Image.LANCZOS)).astype(np.float32)
    return t * dark
FL = {n: floor_tex(i) for i, n in enumerate(['flag', 'wood', 'marble', 'straw', 'cobble', 'grass', 'cellar', 'rock', 'carpet'])}
FL['rock_dark'] = FL['rock'] * 0.55
FL['void'] = np.full((48, 48, 3), (32, 36, 46), np.float32)
FL['outside'] = FL['grass'] * 0.45
y0, x0, y1, x1 = bT[9]                       # plain wall face: brick band only (no crenels, no grass)
face = key(TIL[y0 + 78:y1 - 26, x0 + 6:x1 - 6])[..., :3]
FACE = np.asarray(Image.fromarray(face.astype(np.uint8)).resize((round(face.shape[1] * 32 / face.shape[0]), 32), Image.LANCZOS)).astype(np.float32)
CAP = np.array([233, 184, 119], np.float32); CAP_TOP = key(TIL[bT[13][0] + 40:bT[13][0] + 70, bT[13][1] + 30:bT[13][3] - 30])[..., :3].reshape(-1, 3).mean(0); CAP_D = np.array([196, 146, 92], np.float32); OUTL = np.array([57, 41, 33], np.float32)

def tiled(tex, x0, y0, w, h):
    th, tw = tex.shape[:2]
    yy = (np.arange(y0, y0 + h) % th)[:, None]; xx = (np.arange(x0, x0 + w) % tw)[None, :]
    return tex[yy, xx]

# ------------------------------------------------------------------ level model
def zone_floor(label, zone, level):
    l = label.upper()
    if 'GARDEN' in l: return 'grass'
    if 'THRONE' in l: return 'marble'
    if 'BARRACKS' in l or 'BUNK' in l: return 'straw'
    if any(k in l for k in ['KITCHEN', 'BAKE', 'LARDER', 'SER-', 'BUT-', 'GREAT HALL', 'HALL\n', 'STORES', 'CORRIDOR', 'GATE', 'WIN-']): return 'flag'
    if 'DORMITORY' in l: return 'wood'
    if level == 'L-1': return 'cellar'
    return {'king': 'wood', 'sister': 'wood', 'hold': 'flag', 'gov': 'wood', 'mil': 'flag', 'serv': 'flag', 'court': 'cobble',
            'cer': 'flag', 'cell': 'cellar', 'fire': 'flag', 'safe': 'cellar'}[zone]

def pip(x, y, poly):
    ins = False; n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]; x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            ins = not ins
    return ins

def seg_dist(px, py, a, b):
    ax, ay = a; bx, by = b; dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0 if L2 == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))

CUR = P['curtain']
cx = np.arange(MW)[None, :] + 0.5; cy = np.arange(MH)[:, None] + 0.5
INSIDE = np.vectorize(lambda x, y: pip(x, y, CUR))(np.broadcast_to(cx, (MH, MW)), np.broadcast_to(cy, (MH, MW)))
CBAND = np.zeros((MH, MW), bool)
for i in range(len(CUR)):
    a, b = CUR[i], CUR[(i + 1) % len(CUR)]
    d = np.vectorize(lambda x, y: seg_dist(x, y, a, b))(np.broadcast_to(cx, (MH, MW)), np.broadcast_to(cy, (MH, MW)))
    CBAND |= d <= 1.6
DRUM = np.zeros((MH, MW), bool)
for (x, y) in P['drum_towers']:
    DRUM |= (cx - x) ** 2 + (cy - y) ** 2 <= P['drum_radius'] ** 2
HO, HI = P['holdfast_moat_outer'], P['holdfast_inner']
MOAT = np.zeros((MH, MW), bool); MOAT[HO[1]:HO[3], HO[0]:HO[2]] = True; MOAT[HI[1]:HI[3], HI[0]:HI[2]] = False
BR = P['drawbridge']

EXTRA = {'L1': [(165, 27, 192, 30, 'covered bridge', 'mil')]}

def build(level):
    rooms = [tuple(r) for r in P['levels'][level]['rooms']] + EXTRA.get(level, [])
    owner = -np.ones((MH, MW), int)
    for i, (x0, y0, x1, y1, lab, z) in enumerate(rooms):
        owner[int(y0):int(y1), int(x0):int(x1)] = i
    inroom = owner >= 0
    wall = np.zeros((MH, MW), bool)
    facerow = np.zeros((MH, MW), int)       # 1/2 = first/second face row
    for i, (x0, y0, x1, y1, lab, z) in enumerate(rooms):
        x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
        own = owner == i
        m = np.zeros_like(own); m[y0, x0:x1] = True; m[y0:y1, x0] = True
        if x1 < MW: m[y0:y1, x1 - 1] |= ~inroom[y0:y1, x1]
        if y1 < MH: m[y1 - 1, x0:x1] |= ~inroom[y1, x0:x1]
        wall |= m & own
    # inner faces: under every horizontal wall run that has floor of the same room below
    for i, (x0, y0, x1, y1, lab, z) in enumerate(rooms):
        x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
        if y1 - y0 < 6: continue
        for x in range(x0, x1):
            for k, yy in enumerate((y0 + 1, y0 + 2)):
                if owner[yy, x] == i and wall[y0, x] and not wall[yy, x]:
                    facerow[yy, x] = k + 1
    # outer faces: a room's bottom wall seen from the open ground below it (yard / moat)
    if level == 'L0':
        for y in range(MH - 2):
            for x in range(MW):
                if wall[y, x] and inroom[y, x] and not inroom[y + 1, x] and not CBAND[y + 1, x]:
                    for k in (1, 2):
                        if y + k < MH and not inroom[y + k, x] and not CBAND[y + k, x] and not DRUM[y + k, x]:
                            facerow[y + k, x] = k
    gates, thresholds = [], []
    for (x, y, o, l, t) in P['levels'][level]['doors']:
        if l == 0 or t == 'H':
            continue
        if o == 'h':
            xs = range(int(math.floor(x)), int(math.ceil(x + l))); ys = range(int(y) - 1, int(y) + 3)
            for yy in ys:
                for xx in xs:
                    if 0 <= yy < MH and (wall[yy, xx] or facerow[yy, xx]):
                        wall[yy, xx] = False; facerow[yy, xx] = 0
            rect = (min(xs), int(y) - 1, len(xs), 2)
        else:
            ys = range(int(math.floor(y)), int(math.ceil(y + l))); xs = range(int(x) - 1, int(x) + 1)
            for yy in ys:
                for xx in xs:
                    wall[yy, xx] = False; facerow[yy, xx] = 0
            rect = (int(x) - 1, min(ys), 2, len(ys))
        thresholds.append((rect, t))
        gates.append(((x, y), rect, t))
    return rooms, owner, inroom, wall, facerow, gates, thresholds

# ------------------------------------------------------------------ props per level: (name, x, y, w_tiles[, block])
PL = {
 'L-1': [('oil_jars', 26, 58, 2), ('oil_jars', 26, 61.5, 2), ('oil_jars', 29, 58, 2), ('pitch', 32, 58, 2), ('pitch', 32, 61.5, 2), ('oil_crates', 29, 62, 2),
         ('stairs_up', 38, 57, 2), ('sacks', 44, 58, 2), ('sacks', 47, 58, 2), ('barrels', 52, 58, 1), ('barrels', 53.2, 58, 1), ('crates', 56, 63, 2),
         ('wine_rack', 69, 56.5, 4), ('wine_rack', 75, 56.5, 4), ('wine_rack', 81, 56.5, 4), ('casks', 70, 64, 3), ('casks', 76, 64, 3), ('casks', 88, 64, 3),
         ('coffin', 104, 53, 2), ('coffin', 110, 53, 2), ('coffin', 116, 53, 2), ('coffin', 134, 53, 2), ('coffin', 140, 53, 2), ('coffin', 146, 53, 2),
         ('candelabra', 123, 54, 1), ('candelabra', 129, 54, 1), ('treasure', 89, 16, 3), ('treasure', 95, 16, 3),
         ('vault', 130.5, 14.6, 3), ('bed_plain_r', 120, 17, 2), ('bed_plain_r', 123, 17, 2), ('bed_plain_b', 140, 17, 2), ('bed_plain_b', 143, 17, 2),
         ('crates', 127, 21, 2), ('crates', 136, 21, 2), ('cell_bars', 27, 88, 3), ('cell_bars', 32, 88, 3), ('cell_bars', 37, 88, 3), ('cell_bars', 42, 88, 3),
         ('cell_bars', 47, 88, 3), ('desk', 70, 92, 3), ('casks', 28, 25, 3), ('barrels', 140, 33, 1), ('crates', 150, 33, 2),
         ('spiral', 108, 15, 3, False), ('spiral', 192, 36, 3, False), ('spiral', 124.5, 47, 3, False), ('grate', 1, 51.5, 2, False)],
 'L0': [('stairs_down', 38, 57, 2), ('hearth', 44, 54.6, 4), ('prep_table', 44, 61, 3), ('prep_table', 50, 61, 3), ('pots', 55, 57, 2), ('barrels', 58, 58, 1),
        ('sacks', 55, 64, 2), ('oven', 27, 55, 3), ('prep_table', 27, 62, 3), ('well', 28, 72, 2), ('woodpile', 33, 72, 3), ('hay', 38, 72, 3),
        ('kennel', 43, 78, 2), ('cart', 30, 79, 3), ('cheese', 50, 72, 2), ('meat', 54, 72, 2), ('bunk', 50, 78, 2), ('bunk', 54, 78, 2),
        ('barrels', 62, 48, 1), ('prep_table', 61.5, 60, 3), ('feast_table', 70, 52, 6), ('feast_table', 70, 61, 6), ('feast_table', 84, 52, 6),
        ('feast_table', 84, 61, 6), ('fireplace', 80, 45.4, 4), ('banner', 68, 46, 1), ('banner', 96, 46, 1),
        ('throne', 122, 47.5, 8), ('banner', 104, 46, 1), ('banner', 110, 46, 1), ('banner', 141, 46, 1), ('banner', 147, 46, 1),
        ('statue_knight', 106, 56, 2), ('statue_knight', 144, 56, 2), ('statue_knight', 106, 64, 2), ('statue_knight', 144, 64, 2),
        ('candelabra', 119, 49, 1), ('candelabra', 132, 49, 1), ('dining_table', 128, 16, 6), ('altar', 148, 31, 4),
        ('weapon_rack', 90, 15, 3), ('armour', 96, 16, 1), ('armour', 98, 16, 1), ('winch', 117.5, 32.5, 3), ('barrels', 90, 33, 1), ('crates', 93, 33, 2),
        ('barracks_bunk', 27, 90, 2), ('barracks_bunk', 30, 90, 2), ('barracks_bunk', 33, 90, 2), ('barracks_bunk', 36, 90, 2), ('barracks_bunk', 39, 90, 2),
        ('barracks_bunk', 42, 90, 2), ('barracks_bunk', 27, 99, 2), ('barracks_bunk', 30, 99, 2), ('barracks_bunk', 33, 99, 2), ('barracks_bunk', 36, 99, 2),
        ('barracks_bunk', 39, 99, 2), ('barracks_bunk', 42, 99, 2), ('weapon_rack', 68, 89, 3), ('weapon_rack', 73, 89, 3), ('dummy', 79, 90, 1),
        ('feast_table', 69, 100, 6), ('bell', 95, 79, 2), ('scroll_rack', 27, 25, 2), ('scroll_rack', 31, 25, 2), ('scroll_rack', 35, 25, 2),
        ('desk', 30, 42, 3), ('council_table', 175, 49, 5), ('scroll_rack', 178, 61, 2), ('scroll_rack', 183, 61, 2), ('bookshelf', 195, 71, 3),
        ('bookshelf', 200, 71, 3), ('bookshelf', 205, 71, 3), ('statue_kg', 172, 90, 2), ('desk', 156, 61, 3)],
 'L1': [('stairs_up', 88, 25.6, 2, False), ('bed_king', 130, 14, 4), ('wardrobe', 120, 15, 2), ('fireplace', 139, 12.6, 4), ('rug_red', 125, 19, 3),
        ('armchair', 137, 18, 1), ('desk', 92, 17, 3), ('bookshelf', 88, 13.6, 3), ('strongbox', 99, 15, 1), ('settee', 89, 33, 3), ('harp', 95, 33, 1),
        ('bed_red', 101, 33, 2), ('dummy', 107, 33, 1), ('tub', 112, 34, 3), ('bed_red', 137, 33, 2), ('vanity', 142, 33, 2), ('crib', 149, 33, 2),
        ('rocking_horse', 152, 35, 2), ('bed_red', 158, 33, 2), ('bed_sister', 199, 39, 4), ('rug_teal', 202, 45, 3), ('wardrobe', 194, 40, 2),
        ('settee', 212, 40, 3), ('harp', 216, 45, 1), ('desk', 221, 41, 3), ('bed_blue', 202, 27, 2), ('bed_blue', 209, 27, 2), ('bed_plain_b', 216, 28, 2),
        ('bunk', 27, 57, 2), ('bunk', 31, 57, 2), ('bunk', 35, 57, 2), ('bunk', 39, 57, 2), ('bunk', 43, 57, 2), ('bunk', 47, 57, 2), ('desk', 51, 73, 3),
        ('strongbox', 56, 73, 1), ('desk', 30, 26, 3), ('bookshelf', 25.5, 22.6, 3), ('bed_red', 27, 41, 2), ('desk', 158, 49, 3), ('scroll_rack', 166, 48, 2),
        ('treasure', 178, 48, 3), ('desk', 196, 57, 3), ('pc_winch', 123, 105, 4), ('desk', 172, 91, 3), ('bed_plain_b', 190, 90, 2), ('bed_plain_b', 195, 90, 2),
        ('bed_plain_b', 200, 90, 2), ('statue_kg', 121, 32, 2)],
}

# stairs / links / exits (tile coords)
LINKS = [  # (level_a, pos_a, level_b, pos_b, label)
 ('L-1', (39, 61), 'L0', (39, 61), 'stairs'),
 ('L0', (90, 28.5), 'L1', (90, 28.5), 'Holdfast grand stair'),
 ('L0', (162, 28.5), 'L1', (162, 28.5), 'Holdfast east stair'),
 ('L0', (55.5, 31), 'L1', (51, 31), 'Hand tower stair'),
 ('L0', (205, 47), 'L1', (205, 47), 'apartments stair'),
 ('L1', (120, 21), 'L-1', (110.5, 17.5), 'secret stair K'),
 ('L1', (195.5, 48), 'L-1', (193.5, 35), 'secret stair S'),
 ('L0', (131.5, 50.5), 'L-1', (126, 46), 'secret stair T'),
]
EXITS = [('L-1', (3, 52.5), 'Leave through the river drain'), ('L-1', (237.5, 52.5), 'Escape: River tunnel to the hidden dock'),
         ('L-1', (14, 48.5), 'Escape: Forest tunnel to the ruined watchtower')]
SPAWN = ('L-1', (4, 52.5))
IGNITE = ('L-1', (30.5, 66))
FIRE_STAGES = [  # (id, level, room-label keywords, origin, seconds after ignition at design speed)
 ('F0', 'L-1', ['OIL'], (30, 64), 0), ('F1', 'L-1', ['Root'], (40, 60), 20), ('F2', 'L0', ['KITCHEN'], (40, 60), 45),
 ('F3', 'L0', ['Bake', 'Service Court', "Servants'"], (36, 66), 75), ('F4', 'L1', ["Servants' dorm", 'Steward'], (40, 60), 110),
 ('F5', 'L0', ['GREAT HALL', 'Ser-', 'But-'], (66, 60), 180)]
GOLD_ROUTE = [(86, 92), (86, 86), (20, 86), (20, 77.5), (27, 77.5)]
KG_ROUTE = [(126, 34), (126, 40.5), (126, 44), (126, 48.5), (118, 58), (100, 58.5), (90, 58.5), (66, 63), (61, 63), (52, 65)]

# ------------------------------------------------------------------ render one level
def render(level):
    rooms, owner, inroom, wall, facerow, gates, thr = build(level)
    W, H = MW * T, MH * T
    img = np.zeros((H, W, 4), np.float32); img[..., 3] = 255
    walk = np.zeros((MH, MW), bool)
    base = {'L0': 'outside', 'L1': 'void', 'L-1': 'rock_dark'}[level]
    img[..., :3] = tiled(FL[base], 0, 0, W, H)
    if level == 'L0':
        yard = INSIDE & ~CBAND & ~inroom
        m = np.kron(yard, np.ones((T, T), bool))
        img[..., :3] = np.where(m[..., None], tiled(FL['cobble'], 0, 0, W, H), img[..., :3])
        walk |= yard
    for i, (x0, y0, x1, y1, lab, z) in enumerate(rooms):
        own = owner == i
        tex = FL[zone_floor(lab, z, level)]
        m = np.kron(own, np.ones((T, T), bool))
        img[..., :3] = np.where(m[..., None], tiled(tex, 0, 0, W, H), img[..., :3])
        walk |= own
    # carpet runner up the throne hall
    if level == 'L0':
        img[53 * T:72 * T, 124 * T:128 * T, :3] = tiled(FL['carpet'], 124 * T, 53 * T, 4 * T, 19 * T)
    # tunnels + drain (L-1)
    tun = np.zeros((MH, MW), bool); drain = np.zeros((MH, MW), bool)
    if level == 'L-1':
        for k, pts in P['tunnels'].items():
            for a, b in zip(pts, pts[1:]):
                d = np.vectorize(lambda x, y: seg_dist(x, y, a, b))(np.broadcast_to(cx, (MH, MW)), np.broadcast_to(cy, (MH, MW)))
                tun |= d <= 1.15
        for a, b in zip(P['drain'], P['drain'][1:]):
            d = np.vectorize(lambda x, y: seg_dist(x, y, a, b))(np.broadcast_to(cx, (MH, MW)), np.broadcast_to(cy, (MH, MW)))
            drain |= d <= 1.15
        for msk, tex in ((tun, FL['rock']), (drain, FL['cellar'] * np.array([0.7, 0.85, 1.15], np.float32))):
            m = np.kron(msk, np.ones((T, T), bool))
            img[..., :3] = np.where(m[..., None], tiled(tex, 0, 0, W, H), img[..., :3])
        wall &= ~(tun | drain); facerow[tun | drain] = 0
        walk |= tun | drain
    # moat + bridge (L0)
    if level == 'L0':
        m = np.kron(MOAT, np.ones((T, T), bool))
        img[..., :3] = np.where(m[..., None], np.array([42, 34, 30], np.float32), img[..., :3])
        for y in range(HO[1], HO[3]):
            for x in range(HO[0], HO[2]):
                if MOAT[y, x] and (x + y) % 2 == 0:
                    px, py = x * T + 8, y * T + 10
                    for j in range(6):
                        img[py - j, px - (6 - j) // 2:px + (6 - j) // 2 + 1, :3] = (165, 165, 175) if j < 5 else (230, 230, 235)
        walk &= ~MOAT
        bx0, by0, bx1, by1 = BR
        walk[by0:by1, bx0:bx1] = True                 # walkable when the drawbridge is down (dynamic collider while raised)
    # walls (caps) and faces
    capm = wall | (CBAND & (level != 'L-1')) | (DRUM & (level != 'L-1'))
    if level == 'L1':
        capm = wall | CBAND | DRUM
    cm = np.kron(capm, np.ones((T, T), bool))
    yy, xx = np.indices((H, W))
    rnd = (np.sin((xx // 32) * 12.9898 + (yy // 16) * 78.233) * 43758.5453) % 1.0
    stone = CAP_TOP[None, None, :] * (0.95 + 0.07 * rnd)[..., None]
    joint = ((xx + (yy // 16 % 2) * 16) % 32 == 0) | (yy % 16 == 0)
    stone = np.where(joint[..., None], CAP_TOP * 0.84, stone)
    img[..., :3] = np.where(cm[..., None], stone, img[..., :3])
    below_open = capm & ~np.roll(capm, -1, 0) & (facerow == 0)          # cap whose lower edge is open (no face below)
    lip = np.kron(below_open, np.ones((T, T), bool)) & (yy % T >= T - 5)
    img[..., :3] = np.where((lip & (yy % T == T - 5))[..., None], np.array([255, 244, 214], np.float32), img[..., :3])
    img[..., :3] = np.where((lip & (yy % T > T - 5))[..., None], CAP_TOP * 0.72, img[..., :3])
    for k in (1, 2):
        fm = np.kron(facerow == k, np.ones((T, T), bool))
        ft = tiled(FACE, 0, (k - 1) * T, W, H)    # row band of the face texture
        rows = (np.arange(H) % T + (k - 1) * T)[:, None]
        cols = (np.arange(W) % FACE.shape[1])[None, :]
        img[..., :3] = np.where(fm[..., None], FACE[rows, cols], img[..., :3])
    # outlines: cap / face edges against walkable ground
    solid = capm | (facerow > 0)
    if level == 'L-1':
        solid |= ~(walk) & ~wall
    edge = np.kron(solid, np.ones((T, T), bool))
    sh = edge & ~np.roll(edge, 1, 0) | edge & ~np.roll(edge, -1, 0) | edge & ~np.roll(edge, 1, 1) | edge & ~np.roll(edge, -1, 1)
    sh = ndimage.binary_dilation(sh, iterations=1) & edge
    img[..., :3] = np.where(sh[..., None], OUTL, img[..., :3])
    walk &= ~(wall | (facerow > 0))
    if level != 'L-1':
        walk &= ~(CBAND | DRUM)
    # ambient occlusion: floor darkens under walls/faces (light from the top-left -> also a soft shadow to the right)
    solidpx = np.kron(capm | (facerow > 0) | (~walk & ~inroom & (level == 'L-1')), np.ones((T, T), bool))
    shade = np.ones((H, W), np.float32)
    for k in range(1, 15):
        shade = np.where(np.roll(solidpx, k, 0) & ~solidpx, np.minimum(shade, 0.52 + 0.48 * k / 15), shade)
    for k in range(1, 9):
        shade = np.where(np.roll(solidpx, k, 1) & ~solidpx, np.minimum(shade, 0.70 + 0.30 * k / 9), shade)
    img[..., :3] *= shade[..., None]
    # torches on the inner faces (art = iron sconce; the flame + light are added in the game)
    torches = []
    if level != 'L-1' or True:
        for i, (x0, y0, x1, y1, lab, z) in enumerate(rooms):
            if z == 'court' or 'corridor' in lab or (x1 - x0) < 7:
                continue
            row = int(y0) + 1
            xs = [x for x in range(int(x0) + 2, int(x1) - 2) if facerow[row, x] == 1 and facerow[row, x - 1] == 1 and facerow[row, x + 1] == 1]
            if not xs: continue
            n = max(1, min(3, (int(x1) - int(x0)) // 10))
            picks = [xs[int((j + 0.5) * len(xs) / n)] for j in range(n)]
            for x in picks:
                px, py = x * T + 8, row * T + 10
                img[py:py + 9, px - 1:px + 2, :3] = (40, 34, 30); img[py + 1:py + 8, px, :3] = (90, 80, 70)
                img[py - 1:py + 1, px - 3:px + 4, :3] = (40, 34, 30)
                torches.append([px, py - 2])
    # door thresholds
    tc = {'d': (150, 95, 50), 'L': (190, 40, 40), 'G': (40, 40, 40)}
    for (rx, ry, rw, rh), t in thr:
        if t in tc:
            if rw >= rh: img[(ry + 1) * T - 3:(ry + 1) * T + 1, rx * T:(rx + rw) * T, :3] = tc[t]
            else: img[ry * T:(ry + rh) * T, (rx + 1) * T - 2:(rx + 1) * T + 2, :3] = tc[t]
    # props, back to front
    items = sorted(PL[level], key=lambda p: p[2] + prop(p[0], p[3]).shape[0] / T)
    for it in items:
        name, x, y, w = it[:4]
        block = it[4] if len(it) > 4 else True
        pr = prop(name, w)
        ph, pw = pr.shape[:2]
        X, Y = int(x * T), int(y * T)
        a = pr[..., 3:4] / 255.0
        sl = img[Y:Y + ph, X:X + pw, :3]
        img[Y:Y + ph, X:X + pw, :3] = sl * (1 - a[:sl.shape[0], :sl.shape[1]]) + pr[:sl.shape[0], :sl.shape[1], :3] * a[:sl.shape[0], :sl.shape[1]]
        if block and name not in ('rug_red', 'rug_teal', 'rug_small', 'banner', 'fireplace'):
            # the lower part (what stands on the floor) blocks
            bx0, bx1 = int(math.floor(x + 0.15)), int(math.ceil(x + pw / T - 0.15))
            by1 = int(math.ceil(y + ph / T - 0.2)); by0 = max(int(math.floor(y + ph / T * 0.45)), by1 - 3)
            walk[by0:by1, bx0:bx1] = False
    # ---- visibility regions: floor areas separated by walls and doorways; walls/faces/doors belong to the rooms they touch
    floor = ~wall & (facerow == 0)
    if level == 'L0':
        floor &= (inroom | (INSIDE & ~CBAND)) & ~DRUM & ~MOAT
        floor[BR[1]:BR[3], BR[0]:BR[2]] = True
    elif level == 'L1':
        floor &= inroom & ~DRUM
    else:
        floor &= (inroom | tun | drain)
    doorc = np.zeros((MH, MW), bool)
    for (rx, ry, rw, rh), t in thr:
        doorc[ry:ry + rh, rx:rx + rw] = True
    lab, nreg = ndimage.label(floor & ~doorc)
    assert nreg < 255, nreg
    slots = np.zeros((3, MH, MW), np.int32)
    slots[0] = lab
    offs = sorted([(dx, dy) for dx in range(-3, 4) for dy in range(-3, 4)], key=lambda o: o[0] ** 2 + o[1] ** 2)
    fill = ~(floor & ~doorc)                     # only non-floor cells (walls, faces, doors, outside) take neighbours
    for dx, dy in offs:
        sh_ = np.roll(np.roll(lab, dy, 0), dx, 1)
        ok = fill & (sh_ > 0)
        for k in range(3):
            put = ok & (slots[k] == 0)
            if k > 0:
                for j in range(k): put &= (sh_ != slots[j])
            if k > 0: put &= (slots[0] > 0)
            put &= ~((slots[:k] == sh_).any(0)) if k > 0 else True
            slots[k] = np.where(put, sh_, slots[k])
            ok &= ~put & (slots[k] != sh_)
    # cells still unassigned (drum interiors, thick curtain, ground just outside) take the nearest region within 9 cells
    dist, (iy, ix) = ndimage.distance_transform_edt(slots[0] == 0, return_indices=True)
    far = (slots[0] == 0) & (dist <= 9)
    slots[0] = np.where(far, slots[0][iy, ix], slots[0])
    names = ['']
    for r in range(1, nreg + 1):
        o = owner[lab == r]; o = o[o >= 0]
        if len(o) == 0: names.append('Courtyard' if level == 'L0' else ''); continue
        raw = rooms[np.bincount(o).argmax()][4].replace('-\n', '')
        parts = []
        for ln in raw.split('\n'):
            ln = ln.strip()
            if ln.startswith('(') or ln.startswith('+') or ',' in ln or (len(ln.split()) >= 3 and ln[:1].islower()):
                break
            parts.append(ln.split('(')[0].strip())
        nm = ' '.join(parts).replace(' - ', ' ').strip()
        nm = ' '.join(w[:1].upper() + w[1:].lower() for w in nm.split())
        names.append(nm)
    regimg = np.dstack([slots[0], slots[1], slots[2], np.full((MH, MW), 255)]).astype(np.uint8)
    tor_reg = [int(lab[min(MH - 1, (ty + 24) // T), tx // T]) for tx, ty in torches]
    return img, walk, gates, rooms, owner, regimg, names, [[a, b, r] for (a, b), r in zip(torches, tor_reg)]

def rects(block):
    """merge blocked cells into rectangles (row runs, then stacked)"""
    H, W = block.shape; out = []; open_ = {}
    for y in range(H + 1):
        runs = []
        if y < H:
            row = block[y]; x = 0
            while x < W:
                if row[x]:
                    s = x
                    while x < W and row[x]: x += 1
                    runs.append((s, x))
                else: x += 1
        new = {}
        for r in runs:
            if r in open_: new[r] = open_.pop(r)
            else: new[r] = y
        for (s, e), y0 in open_.items():
            out.append([s * T, y0 * T, (e - s) * T, (y - y0) * T])
        open_ = new
    return out

data = {'tile': T, 'size': [MW, MH], 'levels': {}}
DYN = {}
for lv, fn in (('L0', 'L0'), ('L1', 'L1'), ('L-1', 'Lm1')):
    img, walk, gates, rooms, owner, regimg, names, torches = render(lv)
    import io
    buf = io.BytesIO(); Image.fromarray(regimg, 'RGBA').save(buf, 'PNG')
    open(os.path.join(ROOT, 'data/keep_%s_regions.bin' % fn), 'wb').write(buf.getvalue())
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), 'RGBA').convert('RGB').save(os.path.join(OUT, fn + '.png'), optimize=True)
    for (a, pa, b, pb, lab) in LINKS:
        for l, p in ((a, pa), (b, pb)):
            if l == lv and not walk[int(p[1]), int(p[0])]:
                print('WARNING link not walkable', lv, p, lab)
    stages = []
    for sid, l, kws, org, t in FIRE_STAGES:
        if l != lv: continue
        pts = []
        for i, r in enumerate(rooms):
            if any(k in r[4] for k in kws):
                ys, xs = np.where((owner == i) & walk)
                rng = np.random.default_rng(1000 + i)
                order = rng.permutation(len(xs)); taken = []
                for j in order:                       # scattered, at least 2.2 tiles apart
                    xx, yy = xs[j] + rng.uniform(0.15, 0.85), ys[j] + rng.uniform(0.3, 0.95)
                    if all((xx - a) ** 2 + (yy - b) ** 2 > 2.2 ** 2 for a, b in taken):
                        taken.append((xx, yy)); pts.append([int(xx * T), int(yy * T)])
        stages.append({'id': sid, 'origin': [org[0] * T, org[1] * T], 'points': pts, 't': t})
    data['levels'][lv] = {'image': 'res://art/game/keep/%s.png' % fn, 'solid': rects(~walk), 'regions': 'res://data/keep_%s_regions.bin' % fn,
                          'region_names': names, 'torches': torches,
                          'fire': stages}
    if lv == 'L0':
        GID = {(120, 114): 'main_outer', (120, 102): 'main_inner', (84, 42): 'lane_w', (168, 42): 'lane_e', (123, 39): 'hold_gate', (123, 45): 'kings_door'}
        dyn = {}
        for (xy, r, t) in gates:
            if tuple(xy) in GID:
                dyn[GID[tuple(xy)]] = {'level': 'L0', 'rect': [r[0] * T, r[1] * T, r[2] * T, r[3] * T]}
        DYN.update(dyn)
    print(lv, 'solid rects', len(data['levels'][lv]['solid']), 'fire pts', [len(s['points']) for s in stages])
# named dynamic gates (opened by the fire at F3)
def gate_px(x, y, w, h): return [x * T, y * T, w * T, h * T]
DYN['bridge'] = {'level': 'L0', 'rect': gate_px(BR[0], BR[1], BR[2] - BR[0], BR[3] - BR[1])}
data['dyn_gates'] = DYN
print('dyn gates', sorted(DYN))
data['links'] = [{'a': a, 'pa': [pa[0] * T, pa[1] * T], 'b': b, 'pb': [pb[0] * T, pb[1] * T], 'label': lab} for a, pa, b, pb, lab in LINKS]
data['exits'] = [{'level': l, 'pos': [p[0] * T, p[1] * T], 'label': lab} for l, p, lab in EXITS]
data['spawn'] = {'level': SPAWN[0], 'pos': [SPAWN[1][0] * T, SPAWN[1][1] * T]}
data['ignite'] = {'level': IGNITE[0], 'pos': [IGNITE[1][0] * T, IGNITE[1][1] * T]}
data['routes'] = {'gold': [[x * T, y * T] for x, y in GOLD_ROUTE], 'kingsguard': [[x * T, y * T] for x, y in KG_ROUTE]}
data['guards'] = {lv: [[g[0] * T, g[1] * T] for g in P['levels'][lv].get('guards', [])] for lv in ('L0', 'L1')}
data['goal'] = {'level': 'L1', 'pos': [126 * T, 27 * T], 'label': "the King's door"}

# gate overlays
def save(arr, name):
    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGBA').save(os.path.join(OUT, name))
save(prop('bridge_up', 6), 'ov_bridge_up.png'); save(prop('bridge_down', 6), 'ov_bridge_down.png')
save(prop('portcullis', 6), 'ov_portcullis.png'); save(prop('door_locked', 6), 'ov_door_locked.png'); save(prop('iron_gate', 3), 'ov_iron_gate.png')

# fx sheets: frames bottom-centred in equal cells
def strip(idxs, w, name):
    fr = [shrink(piece(UTL, bU[i]), w) for i in idxs]
    for f in fr:                                   # flames/smoke: no magenta left in the colours
        c = f[..., :3]; pink = (c[..., 2] > c[..., 1] + 25) & (c[..., 0] > 120)
        c[..., 2] = np.where(pink, np.minimum(c[..., 2], c[..., 1]), c[..., 2])
        a = f[..., 3]; mag = (c[..., 0] > 200) & (c[..., 1] < 90) & (a > 0)
        f[..., 3] = np.where(mag & pink, 0, a)
    ch = max(f.shape[0] for f in fr); cw = max(f.shape[1] for f in fr)
    out = np.zeros((ch, cw * len(fr), 4), np.float32)
    for k, f in enumerate(fr):
        out[ch - f.shape[0]:, k * cw + (cw - f.shape[1]) // 2:k * cw + (cw - f.shape[1]) // 2 + f.shape[1]] = f
    save(out, name); return [cw, ch, len(fr)]
data['fx'] = {'fire_m': strip([48, 49, 50, 51], 22, 'fx_fire_m.png'), 'fire_l': strip([38, 40, 41, 43], 40, 'fx_fire_l.png'),
              'smoke': strip([52, 53, 54, 55, 56], 28, 'fx_smoke.png'), 'scorch': strip([57, 58, 59], 30, 'fx_scorch.png')}

# exterior sprite at 1:1
ext = key(SPR)
ys, xs = np.where(ext[..., 3] > 110)
ext = ext[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
ext[..., 3] = np.where(ext[..., 3] > 110, 255, 0)
save(ext, 'exterior.png')
h, w = ext.shape[:2]
bottom = [int(np.where(ext[:, x, 3] > 0)[0].max()) if (ext[:, x, 3] > 0).any() else -1 for x in range(w)]
DOOR_X = 1023 - xs.min()
data['exterior'] = {'size': [w, h], 'door_x': int(DOOR_X), 'door_y': int(bottom[DOOR_X]), 'bottom': bottom}
json.dump(data, open(os.path.join(ROOT, 'data/keep_proto.json'), 'w'))
print('exterior', w, h, 'door', DOOR_X, bottom[DOOR_X])
