#!/usr/bin/env python3
"""Holdfast ground floor, drawn procedurally in pixels (no generated art).

in : data/holdfast_gf_grid.json  (tools/holdfast_gf_grid.py: the user's plan, 13 plan px = 1 tile)
out: art/game/holdfast/gf.png, data/holdfast_gf.json (solid rects, spawn, exits, stairs, room names)

Scale: 1 tile = 16 px. Kael (swordsman) is ~1.75 tiles tall. Inner walls 2 tiles, curtain 6 tiles, rooms ~14-20 tiles.
View: 3/4 top-down like the rest of the game: every wall shows its stone top, and where open floor lies south of a wall
the wall's front face (FACE tiles tall) is drawn over that floor. Light from the top-left."""
import json, os
import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
G = json.load(open(os.path.join(ROOT, 'data/holdfast_gf_grid.json')))
T = 16
FACE = 3                       # wall face height in tiles (inside rooms)
raw = np.array(G['grid']); H, W = raw.shape
rng = np.random.default_rng(7)

# ------------------------------------------------------------------ clean the grid
g = raw.copy()
inside = np.zeros((H, W), bool)                                   # inside the moat ring
mo = g == 'moat'
eastdoor = (g == 'door') & (np.arange(W)[None, :] >= int(W * 0.85))
ringc = ndimage.binary_closing(np.pad(mo | eastdoor, 14), structure=np.ones((15, 15)))[14:-14, 14:-14]
inside = ndimage.binary_fill_holes(ringc) & ~ringc
inside = ndimage.binary_opening(inside, iterations=1)
g[~inside & (g != 'grass') & (g != 'yard') & (g != 'door')] = 'moat'
g[~inside & (g == 'door')] = 'bridge'
g[(~inside) & (g == 'yard')] = 'gate'
g[(~inside) & ~np.isin(g, ['grass', 'gate', 'bridge'])] = 'moat'
gl2, _ = ndimage.label(g == 'grass')
bord = set(np.unique(np.r_[gl2[0], gl2[-1], gl2[:, 0], gl2[:, -1]])) - {0}
g[(g == 'grass') & ~np.isin(gl2, list(bord))] = 'moat'
g[0:4, :] = 'grass'; g[-4:, :] = 'grass'; g[:, :4] = 'grass'; g[:, -4:] = np.where(g[:, -4:] == 'gate', 'gate', 'grass')
wl_, nw_ = ndimage.label(g == 'wall')
szw = ndimage.sum(np.ones_like(wl_), wl_, range(1, nw_ + 1))
g[np.isin(wl_, 1 + np.where(szw < 40)[0])] = 'room'
walk_like = {'room', 'cloister', 'yard', 'stair', 'hidden'}
# castle body = everything inside the outer curtain: fill holes of the wall mask
wall = g == 'wall'
closed = ndimage.binary_closing(np.pad(wall | (g == 'hearth'), 12), structure=np.ones((13, 1)))[12:-12, 12:-12]
body = ndimage.binary_fill_holes(closed)
# never count bailey ground (the grey band connected to the moat edge) as castle
gl_, _ = ndimage.label(raw == 'ground')
edge_ids = set(np.unique(gl_[ndimage.binary_dilation(raw == 'moat', iterations=1)])) - {0}
body &= ~np.isin(gl_, list(edge_ids))
# floor inside the body: rooms / cloister / yard (text strokes and stray classes -> floor)
fl = body & ~wall & (g != 'hearth') & (g != 'well') & (g != 'door')
for t in ('ground', 'grass', 'moat', 'stair', 'hidden'):
    g[fl & (g == t)] = 'room'
g[inside & ~body & (g != 'gate') & (g != 'bridge') & (g != 'door')] = 'ground'
g[inside & ~body & (g == 'well')] = 'ground'
# gate passage: the yard-coloured run east of the courtyard to the drawbridge, plus its doors
gate_rows = np.where((raw == 'door')[:, int(W * 0.85):].sum(1) >= 6)[0]
GY0, GY1 = gate_rows.min(), gate_rows.max() + 1
g[(g == 'bridge') & ~np.isin(np.arange(H), np.arange(GY0, GY1))[:, None]] = 'moat'
g[(g == 'bridge') & (np.arange(W)[None, :] < int(W * 0.85))] = 'room'
for y in range(GY0, GY1):
    for x in range(int(W * 0.62), W):
        if raw[y, x] in ('yard', 'door') and g[y, x] != 'bridge':
            g[y, x] = 'gate'
# drawbridge spans the moat in the gate rows
for y in range(GY0, GY1):
    for x in range(W):
        if g[y, x] == 'moat' and x > W * 0.8:
            g[y, x] = 'bridge'
# courtyard: biggest 'yard' component inside the body
yl, n = ndimage.label(g == 'yard')
if n:
    big = np.argmax(ndimage.sum(np.ones_like(yl), yl, range(1, n + 1))) + 1
    court = yl == big
    g[(g == 'yard') & ~court] = 'room'
cy, cx = [int(v.mean()) for v in np.where(court)]
cyx = np.where(court); CY0, CY1, CX0, CX1 = cyx[0].min(), cyx[0].max() + 1, cyx[1].min(), cyx[1].max() + 1
g[court] = 'yard'
g[CY0:CY1, CX0:CX1] = 'yard'
g[(g == 'well') & ~ndimage.binary_dilation(court, iterations=2)] = 'room'
# cloister walk = floor ring around the courtyard (inside the central block)
cl = (cv := ndimage.binary_dilation(court, iterations=5)) & ~court & np.isin(g, ['room', 'cloister'])
g[np.isin(g, ['room', 'cloister'])] = 'room'
g[cl] = 'cloister'
g[(g == 'door') & ~body] = 'gate'

# ------------------------------------------------------------------ thinner outer curtain (user: more room inside,
# same outside size). The cleaned plan's curtain is 6 tiles thick; on every straight run between the corner towers
# it is cut to 3 tiles (the outer half stays, the inner half becomes floor of the room behind it). Laid out by hand
# against the grid (tiles): west x 20-25, east x 98-103, south y 82-87, north y 24-29 (kitchen, guardroom) and the
# projecting north block over the tower armoury y 20-25. Inner walls and the corner towers are not touched.
def isfl(v): return v in ('room', 'cloister', 'yard', 'door')
tot = 0
# grid columns/rows (checked on the printed grid): west curtain x 24-29, east x 98-103, south y 82-87, north over the
# kitchen and guardroom y 24-29; the outer three stay, the inner three become floor. Corner towers excluded.
for y in range(33, 80):
    if isfl(g[y, 30]) and all(g[y, x] == 'wall' for x in range(24, 30)):
        g[y, 27:30] = 'room'; tot += 3
    if isfl(g[y, 97]) and all(g[y, x] == 'wall' for x in range(98, 104)):
        g[y, 98:101] = 'room'; tot += 3
for x in range(33, 86):
    if isfl(g[81, x]) and all(g[y, x] == 'wall' for y in range(82, 88)):
        g[82:85, x] = 'room'; tot += 3
for x in list(range(33, 46)) + list(range(74, 86)):
    if isfl(g[30, x]) and all(g[y, x] in ('wall', 'hearth') for y in range(24, 30)):
        g[27:30, x] = 'room'; tot += 3
for x in range(33, 46):                                       # kitchen fireplace back into the new wall face
    if g[26, x] == 'wall' and raw[24:32, x].tolist().count('hearth'):
        g[25:27, x] = 'hearth'
# tower armoury block (x 46-73, y 20-37): outer wall y 20-22 (3 tiles), side walls 2 tiles (x 48-49, x 70-71);
# the old 2-tile sliver room above it joins the armoury, the kitchen and guardroom grow into the old side walls
# armoury runs down to the 2-tile wall over the cloister (y 42-43, door x 59-60 stays)
g[23:42, 50:70] = 'room'; g[20:23, 46:74] = 'wall'
g[23:42, 48:50] = 'wall'; g[23:42, 70:72] = 'wall'
for y in range(27, 42):
    if isfl(g[y, 45]): g[y, 46:48] = 'room'
    if isfl(g[y, 78]) or isfl(g[y - 1, 78]): g[y, 72:78] = 'room'
g[23:27, 46:48] = 'wall'; g[23:27, 72:74] = 'wall'
# SE tower: its west wall on the south run was a 7-tile block; 2 tiles like the SW tower, bunks room grows
for x in range(82, 91):
    if isfl(g[81, x]) and (g[82:85, x] == 'wall').all(): g[82:85, x] = 'room'; tot += 3
print('curtain thinned to 3 tiles:', tot, 'tiles became floor')

# ------------------------------------------------------------------ servants' room bigger, stores smaller (user)
# servants x 27-43: was y 58-67, now y 54-71 (north wall moves up to y 52-53, south wall down to y 72-73);
# the cloister door x 46-49 at y 68-69 keeps a passage x 46-49 down into the stores (now y 74-84)
g[52:54, 27:44] = 'room'; g[54:56, 24:44] = 'wall'; g[56:58, 27:44] = 'room'   # pantry grows 2 rows (user)
g[68:72, 27:44] = 'room'; g[72:74, 24:46] = 'wall'
g[68:74, 44:46] = 'wall'; g[70:74, 46:50] = 'room'

# kitchen grows east into the armoury (wall x 48-49 -> x 52-53), guardroom takes the NE tower's wall block
g[27:42, 48:52] = 'room'; g[23:42, 52:54] = 'wall'
g[27:30, 86:94] = 'room'

# ------------------------------------------------------------------ rooms (for floor style + names)
floor = np.isin(g, ['room', 'door'])
rl, nr = ndimage.label(np.isin(g, ['room']))
# names by plan position (fractions of the castle body box)
bys, bxs = np.where(body); BY0, BY1, BX0, BX1 = bys.min(), bys.max() + 1, bxs.min(), bxs.max() + 1
LBL = [('Kitchen', 299, 418), ('Tower armoury', 448, 393), ('Guardroom', 597, 418),
       ("Servants' room", 280, 585), ('Waiting room', 616, 579), ('Stores', 299, 666), ('Lower hall', 448, 666),
       ("Guards' bunks", 597, 666), ('NW tower', 212, 355), ('NE tower', 684, 355), ('SW tower', 212, 729),
       ('SE tower', 684, 729), ('Pantry', 280, 505)]
names = {}
for nm, dx, dy in LBL:
    x = int((dx - 50) * 2.09 / 13); y = int((dy - 194) * 2.09 / 13)
    for r in range(0, 8):
        sub = rl[max(0, y - r):y + r + 1, max(0, x - r):x + r + 1]
        ids = [i for i in np.unique(sub) if i > 0 and int(i) not in names]
        if ids:
            names[int(ids[0])] = nm; break
STYLE = {'Kitchen': 'flag', 'Pantry': 'flag', 'Servants\' room': 'wood', 'Stores': 'flag', 'Tower armoury': 'dark',
         'Guardroom': 'dark', 'Guards\' bunks': 'wood', 'Waiting room': 'wood', 'Lower hall': 'wood'}

# ------------------------------------------------------------------ palette + textures
OUT_ = np.array([52, 40, 38])
ST = {'hi': np.array([226, 212, 196]), 'lt': np.array([204, 188, 172]), 'md': np.array([176, 158, 146]),
      'dk': np.array([136, 118, 108]), 'mo': np.array([104, 88, 82])}
def noise(h, w, s, seed):
    r = np.random.default_rng(seed)
    n = r.random((h // s + 2, w // s + 2))
    return np.kron(n, np.ones((s, s)))[:h, :w]

def bricks(h, w, bh, bw, base, seed, mortar=0.62, hl=True):
    """running-bond blocks with 1px mortar, per-block tone, top-left highlight"""
    yy, xx = np.indices((h, w))
    row = yy // bh
    off = (row % 2) * (bw // 2)
    col = (xx + off) // bw
    tone = (np.sin(row * 12.9898 + col * 78.233) * 43758.5453) % 1.0
    img = base[None, None, :] * (0.90 + 0.16 * tone)[..., None]
    by, bx = yy % bh, (xx + off) % bw
    img = np.where(((by == 0) | (bx == 0))[..., None], base * mortar, img)
    if hl:
        img = np.where(((by == 1) & (bx > 0))[..., None], np.minimum(img * 1.12, 255), img)
        img = np.where(((by == bh - 1) & (bx > 0))[..., None], img * 0.88, img)
    img *= (0.97 + 0.06 * noise(h, w, 2, seed))[..., None]
    return img

def planks(h, w, seed):
    yy, xx = np.indices((h, w))
    row = yy // 6
    seg = (xx + (row * 37) % 48) // 48
    tone = (np.sin(row * 7.1 + seg * 3.3) * 9876.5) % 1.0
    base = np.array([150, 104, 66], float)
    img = base * (0.86 + 0.2 * tone)[..., None]
    img = np.where(((yy % 6) == 0)[..., None], base * 0.55, img)
    img = np.where((((xx + (row * 37) % 48) % 48) == 0)[..., None], base * 0.6, img)
    grain = noise(h, w, 1, seed) * 0.08
    return img * (0.96 + grain)[..., None]

def cobbles(h, w, seed):
    r = np.random.default_rng(seed)
    pts = np.stack([r.uniform(0, h, h * w // 60), r.uniform(0, w, h * w // 60)], 1)
    from scipy.spatial import cKDTree
    t = cKDTree(pts)
    yy, xx = np.indices((h, w))
    d, i = t.query(np.stack([yy.ravel(), xx.ravel()], 1), k=2)
    edge = (d[:, 1] - d[:, 0] < 1.6).reshape(h, w)
    tone = ((i[:, 0] * 2654435761) % 1000 / 1000.0).reshape(h, w)
    base = np.array([172, 162, 148], float)
    img = base * (0.84 + 0.22 * tone)[..., None]
    img[edge] = base * 0.55
    return img

def grass(h, w, seed):
    n = noise(h, w, 3, seed) * 0.6 + noise(h, w, 1, seed + 1) * 0.4
    a = np.array([86, 132, 60], float); b = np.array([112, 160, 72], float); c = np.array([70, 110, 52], float)
    img = np.where((n > .62)[..., None], b, np.where((n < .3)[..., None], c, a))
    return img

def earth(h, w, seed, dark=1.0):
    n = noise(h, w, 2, seed)
    a = np.array([98, 84, 70], float) * dark; b = np.array([82, 70, 60], float) * dark; c = np.array([114, 98, 82], float) * dark
    return np.where((n > .7)[..., None], c, np.where((n < .3)[..., None], b, a))

def packed(h, w, seed):
    n = noise(h, w, 2, seed) * .7 + noise(h, w, 6, seed + 3) * .3
    a = np.array([150, 136, 118], float)
    img = a * (0.88 + 0.2 * n)[..., None]
    peb = np.random.default_rng(seed).random((h, w)) > 0.992
    img[peb] = a * 0.7
    return img

PH, PW = H * T, W * T
TEX = {
    'flag': bricks(PH, PW, 16, 24, np.array([178, 166, 150]), 1, mortar=0.7),
    'dark': bricks(PH, PW, 16, 16, np.array([142, 130, 120]), 2, mortar=0.7),
    'wood': planks(PH, PW, 3),
    'clo': bricks(PH, PW, 12, 12, np.array([196, 184, 166]), 4, mortar=0.78),
    'yard': cobbles(PH, PW, 5),
    'grass': grass(PH, PW, 6),
    'ground': packed(PH, PW, 7),
    'moat': earth(PH, PW, 8, 0.62),
    'cap': bricks(PH, PW, 8, 16, np.array([120, 104, 98]), 9, mortar=0.78),
    'face': bricks(PH, PW, 12, 24, np.array([150, 128, 118]), 10, mortar=0.58),
    'gate': bricks(PH, PW, 16, 16, np.array([168, 156, 142]), 11, mortar=0.68),
}

img = np.zeros((PH, PW, 3), float)
def paint(mask_tiles, tex):
    m = np.kron(mask_tiles, np.ones((T, T), bool))
    img[m] = tex[m]
def pmask(mask_tiles): return np.kron(mask_tiles, np.ones((T, T), bool))

paint(g == 'grass', TEX['grass'])
paint(g == 'ground', TEX['ground'])
paint(g == 'moat', TEX['moat'])
paint(g == 'yard', TEX['yard'])
paint(g == 'cloister', TEX['clo'])
paint(g == 'gate', TEX['gate'])
for rid in range(1, nr + 1):
    st = STYLE.get(names.get(rid, ''), 'flag')
    paint(rl == rid, TEX[st])
paint(g == 'door', TEX['flag'])

# moat: north pit wall (earth face) under the ground edge, iron spikes on the floor
mo = (g == 'moat')
face_m = np.zeros_like(mo)
for k in range(1, 3):
    sh = np.zeros_like(mo); sh[k:] = ~mo[:-k] & (g[:-k] != 'bridge')
    face_m |= mo & sh & ~face_m
fmp = pmask(face_m)
pit = earth(PH, PW, 12, 0.85)
yy, xx = np.indices((PH, PW))
img[fmp] = (pit * (0.75 + 0.25 * ((yy % 32) / 32.0))[..., None])[fmp]
img[fmp & ((yy % 8) == 0)] *= 0.8
spk = mo & ~face_m
for ty, tx in zip(*np.where(spk)):
    if (tx * 7 + ty * 13) % 5: continue
    px, py = tx * T + 8 + (ty % 2) * 4 - 2, ty * T + 13
    img[py:py + 2, px - 3:px + 4] = (40, 34, 30)
    img[py - 11:py, px:px + 2] = (70, 72, 80)
    img[py - 11:py, px] = (150, 152, 162)
    img[py - 13:py - 11, px] = (200, 202, 210)

# drawbridge: planks across the moat, chains
bm = pmask(g == 'bridge')
img[bm] = planks(PH, PW, 13).transpose(1, 0, 2)[:PH, :PW][bm] if PW == PH else np.rot90(planks(PW, PH, 13))[:PH, :PW][bm]
bys_, bxs_ = np.where(g == 'bridge')
if len(bys_):
    y0, y1, x0, x1 = bys_.min() * T, (bys_.max() + 1) * T, bxs_.min() * T, (bxs_.max() + 1) * T
    img[y0:y0 + 3, x0:x1] = (90, 60, 36); img[y1 - 3:y1, x0:x1] = (60, 40, 26)
    for cyb in (y0 + 6, y1 - 8):
        for x in range(x0, x1, 4):
            img[cyb:cyb + 2, x:x + 3] = (80, 82, 90)

# walls: stone caps; faces below every wall edge that has open floor/ground to its south
wallm = np.isin(g, ['wall', 'hearth'])
open_ = ~wallm & (g != 'moat') & (g != 'grass')
facem = np.zeros_like(wallm); fdepth = np.zeros((H, W), int)
for k in range(1, FACE + 1):
    sh = np.zeros_like(wallm); sh[k:] = wallm[:-k]
    above_ok = np.ones_like(wallm)
    for j in range(1, k): s2 = np.zeros_like(wallm); s2[j:] = open_[:-j]; above_ok &= s2
    hit = open_ & sh & above_ok & ~facem & (g != 'door') & (g != 'bridge')
    facem |= hit; fdepth[hit] = k
fm = pmask(facem)
img[fm] = TEX['face'][fm]
# darker toward the floor (ambient occlusion) and a lit top edge
fd = np.kron(fdepth, np.ones((T, T), int)); rowin = (yy % T) + (fd - 1) * T
img[fm] *= (1.0 - 0.25 * (rowin[fm] / (FACE * T)))[:, None]
foot_ = fm & ~np.roll(fm, -1, 0)
img[foot_] = OUT_; img[np.roll(foot_, 1, 0) & fm] *= 0.6
cm = pmask(wallm)
img[cm] = TEX['cap'][cm]
# cap rim: light line on the south edge of every cap that has a face below it, outline round all caps
cap_s = wallm & np.roll(facem, -1, 0)
cs = pmask(cap_s) & ((yy % T) >= T - 3)
img[cs & ((yy % T) == T - 3)] = ST['hi']
img[cs & ((yy % T) > T - 3)] = ST['dk']
edge = cm & ~(np.roll(cm, 1, 0) & np.roll(cm, -1, 0) & np.roll(cm, 1, 1) & np.roll(cm, -1, 1))
img[edge] = OUT_
fedge = fm & ~(np.roll(fm, 1, 1) & np.roll(fm, -1, 1))
img[fedge] = OUT_
# hearth in the kitchen wall: fire opening on the face below it
hy, hx = np.where(g == 'hearth')
if len(hy):
    y0 = (hy.max() + 1) * T; x0, x1 = hx.min() * T + 6, (hx.max() + 1) * T - 6
    img[y0:y0 + FACE * T - 6, x0:x1] = (40, 28, 24)
    img[y0 + FACE * T - 16:y0 + FACE * T - 6, x0 + 6:x1 - 6] = (230, 120, 40)
    img[y0 + FACE * T - 22:y0 + FACE * T - 14, x0 + 14:x1 - 14] = (250, 200, 80)
    img[y0 - 2:y0 + 3, x0 - 4:x1 + 4] = ST['dk']
# doors: dark arched opening in the face above each doorway
dl, nd = ndimage.label(g == 'door')
for i, s in enumerate(ndimage.find_objects(dl)):
    y0, y1, x0, x1 = s[0].start * T, s[0].stop * T, s[1].start * T, s[1].stop * T
    img[y0:y1, x0:x1] = TEX['flag'][y0:y1, x0:x1] * 0.9
    img[y0:y1, x0:x0 + 2] = OUT_; img[y0:y1, x1 - 2:x1] = OUT_
# exterior face of the south curtain over the bailey ground (taller: 5 tiles)
# (already covered by facem since 'ground' is open)

# well
wy, wx = np.where(g == 'well')
wtx, wty = int((448 - 50) * 2.09 / 13), int((540 - 194) * 2.09 / 13)
wy, wx = np.array([wty - 1, wty + 2]), np.array([wtx - 1, wtx + 2])
g[wty - 1:wty + 2, wtx - 1:wtx + 2] = 'well'
if len(wy):
    cyw, cxw = (wy.mean() + .5) * T, (wx.mean() + .5) * T; r = max(np.ptp(wy), np.ptp(wx)) * T / 2 + 6
    d2 = ((yy - cyw) / 0.8) ** 2 + (xx - cxw) ** 2
    ring = (d2 <= r * r) & (d2 > (r - 7) ** 2); hole = d2 <= (r - 7) ** 2
    img[ring] = TEX['face'][ring] * 1.05; img[hole] = (36, 48, 70)
    img[hole & (((yy - cyw) / 0.8) ** 2 + (xx - cxw - 3) ** 2 < (r - 12) ** 2)] = (56, 82, 120)
    img[(d2 <= (r + 1) ** 2) & (d2 > r * r)] = OUT_
# arcade columns round the courtyard (every 4 tiles on its edge)
cols = []
for x in range(CX0, CX1 + 1, 4):
    cols += [(CY0 - 1, x), (CY1, x)]
for y in range(CY0 + 3, CY1, 4):
    cols += [(y, CX0 - 1), (y, CX1)]
for ty, tx in cols:
    if not (0 <= ty < H and 0 <= tx < W) or g[ty, tx] not in ('cloister', 'yard'): continue
    px, py = tx * T + 8, ty * T + 12
    img[py - 34:py, px - 6:px + 6] = ST['lt']; img[py - 34:py, px + 3:px + 6] = ST['dk']
    img[py - 34:py, px - 6:px - 4] = ST['hi']
    img[py - 38:py - 34, px - 8:px + 8] = ST['md']; img[py - 2:py + 2, px - 8:px + 8] = ST['md']
    img[py - 38:py + 2, px - 8] = OUT_; img[py - 38:py + 2, px + 7] = OUT_
    img[py + 2:py + 5, px - 7:px + 9] *= 0.7
# spiral stairs in the towers (plan: NE guards' stair, SW royal stair) + armoury stair + cellar stair
stairs = []
def spiral(cx_t, cy_t, r=26):
    cxp, cyp = cx_t * T + 8, cy_t * T + 8
    d = np.hypot(yy - cyp, xx - cxp); a = np.arctan2(yy - cyp, xx - cxp)
    disc = d <= r
    step = ((a + np.pi) / (2 * np.pi) * 10).astype(int)
    tone = 0.75 + 0.25 * ((step % 10) / 10.0)
    img[disc] = (ST['lt'][None, :] * tone[disc][:, None])
    img[disc & (np.abs(((a + np.pi) / (2 * np.pi) * 10) % 1) < 0.08)] = ST['mo']
    img[d <= 5] = ST['dk']; img[(d > r) & (d <= r + 1.5)] = OUT_
def tower_centre(nm):
    for rid, n in names.items():
        if n == nm:
            ys_, xs_ = np.where(rl == rid); return int(xs_.mean()), int(ys_.mean())
def ptile(dx, dy): return int((dx - 50) * 2.09 / 13), int((dy - 194) * 2.09 / 13)
for (dx, dy), lab_, r in (((684, 355), "Guards' stair (up)", 26), ((212, 729), 'Royal stair (up)', 26), ((510, 392), 'Tower stair (up)', 16)):
    tx_, ty_ = ptile(dx, dy); spiral(tx_, ty_, r); stairs.append({'name': lab_, 'pos': [tx_ * T + 8, ty_ * T + 8]})
tx_, ty_ = ptile(323, 693)
x0, y0 = (tx_ - 3) * T, (ty_ - 1) * T
for i in range(6):
    img[y0:y0 + 2 * T, x0 + i * 16:x0 + i * 16 + 16] = ST['md'] * (1 - i * 0.1)
    img[y0:y0 + 2 * T, x0 + i * 16] = OUT_
img[y0:y0 + 2 * T, x0 + 96] = OUT_; img[y0, x0:x0 + 97] = OUT_; img[y0 + 2 * T - 1, x0:x0 + 97] = OUT_
stairs.append({'name': 'Stair to the cellars (down)', 'pos': [x0 + 48, y0 + 16]})

# soft shadow on floors under walls/faces (light from the top-left)
solid_px = cm | fm
shade = np.ones((PH, PW))
for k in range(1, 13):
    shade = np.where(np.roll(solid_px, k, 0) & ~solid_px, np.minimum(shade, 0.6 + 0.4 * k / 13), shade)
for k in range(1, 7):
    shade = np.where(np.roll(solid_px, k, 1) & ~solid_px, np.minimum(shade, 0.78 + 0.22 * k / 7), shade)
img *= shade[..., None]

os.makedirs(os.path.join(ROOT, 'art/game/holdfast'), exist_ok=True)
Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(os.path.join(ROOT, 'art/game/holdfast/gf.png'), optimize=True)

# ------------------------------------------------------------------ collision + data
block = wallm | facem | (g == 'moat') | (g == 'well') | (g == 'grass')
block[(g == 'grass')] = False
block[0, :] = block[-1, :] = True; block[:, 0] = block[:, -1] = True
for ty, tx in cols:
    if 0 <= ty < H and 0 <= tx < W and g[ty, tx] in ('cloister', 'yard'): block[ty, tx] = True
def rects(b):
    out = []; open_r = {}
    for y in range(H + 1):
        runs = []
        if y < H:
            x = 0
            while x < W:
                if b[y, x]:
                    s = x
                    while x < W and b[y, x]: x += 1
                    runs.append((s, x))
                else: x += 1
        new = {}
        for r in runs: new[r] = open_r.pop(r) if r in open_r else y
        for (s, e), y0 in open_r.items(): out.append([int(s * T), int(y0 * T), int((e - s) * T), int((y - y0) * T)])
        open_r = new
    return out
br = np.where(g == 'bridge'); gr = np.where(g == 'gate')
spawn = [int(gr[1].max()) * T, int((GY0 + GY1) / 2) * T + 8]
labels = []
for rid, nm in names.items():
    ys_, xs_ = np.where(rl == rid); labels.append({'name': nm, 'pos': [int(xs_.mean() * T), int(ys_.mean() * T)]})
labels.append({'name': 'Courtyard', 'pos': [int(cx * T), int(cy * T)]})
# ------------------------------------------------------------------ room-reveal regions (same scheme as the keep)
# doorways from the plan's brown door lines (any tile with door brown in it), plus the wall gaps they sit in
pim = np.asarray(Image.open(os.path.join(ROOT, 'design/holdfast/plan.png')).convert('RGB')).astype(int)
gm = (np.abs(pim - [124, 155, 92]).sum(-1) < 30); ys0, xs0 = np.where(gm[:2200, :2000])
pa = pim[ys0.min():ys0.max() + 1, xs0.min():xs0.max() + 1]
brown = (np.abs(pa - [184, 138, 90]).sum(-1) < 40)
P_ = G['tile_plan_px']
bf = brown[:H * P_, :W * P_].reshape(H, P_, W, P_).mean((1, 3))
walk = ~block
solidm = wallm | facem
closedw = ndimage.binary_closing(np.pad(solidm, 8), structure=np.ones((7, 7)))[8:-8, 8:-8]
outside = walk & ~body
gate_t = walk & (g == 'gate') & body
inner = walk & body & ~closedw & ~gate_t
cc_ = np.isin(g, ['yard', 'cloister'])
lab_r, n_in = ndimage.label(inner & ~cc_)
lab_r[inner & cc_] = n_in + 1
nxt = lab_r.max() + 1
lab_r[outside] = nxt; lab_r[gate_t] = nxt + 1
u = np.unique(lab_r); u = u[u > 0]
comp = np.zeros(lab_r.max() + 1, int); comp[u] = np.arange(1, len(u) + 1); lab_r = comp[lab_r]; nreg = len(u)
OUT_ID, GATE_ID = comp[nxt], comp[nxt + 1]
# tiny pockets (< 6 tiles) join their largest neighbour
for r in range(1, nreg + 1):
    m = lab_r == r
    if 0 < m.sum() < 6:
        nb = lab_r[ndimage.binary_dilation(m, iterations=2) & ~m]; nb = nb[nb > 0]
        if len(nb): lab_r[m] = np.bincount(nb).argmax()
slots = np.zeros((3, H, W), np.int32); slots[0] = lab_r
fill_ = lab_r == 0
offs = sorted([(dx, dy) for dx in range(-3, 4) for dy in range(-3, 4)], key=lambda o: o[0] ** 2 + o[1] ** 2)
for dx, dy in offs:
    sh_ = np.roll(np.roll(lab_r, dy, 0), dx, 1)
    ok = fill_ & (sh_ > 0)
    for k in range(3):
        put = ok & (slots[k] == 0)
        for j in range(k): put &= (slots[j] != sh_)
        slots[k] = np.where(put, sh_, slots[k])
        ok &= ~put & ~((slots[:k + 1] == sh_).any(0))
# faces below a wall belong to the room in front of them only (not to the room behind the wall)
dist, (iy, ix) = ndimage.distance_transform_edt(slots[0] == 0, return_indices=True)
far = (slots[0] == 0) & (dist <= 10); slots[0] = np.where(far, slots[0][iy, ix], slots[0])
rnames = [''] * (nreg + 1)
for lb in [{'name': 'Courtyard', 'pos': [int(cx * T), int(cy * T)]}] + labels:
    tx_, ty_ = lb['pos'][0] // T, lb['pos'][1] // T
    rid = lab_r[ty_, tx_] if lab_r[ty_, tx_] else (slots[0][ty_, tx_])
    if rid and not rnames[rid]: rnames[rid] = lb['name']
rnames[OUT_ID] = 'Outside the Holdfast'; rnames[GATE_ID] = 'Gate passage'
for i in range(1, nreg + 1):
    if not rnames[i]:
        ys_, xs_ = np.where(lab_r == i); fy_, fx_ = (ys_.mean() - BY0) / (BY1 - BY0), (xs_.mean() - BX0) / (BX1 - BX0)
        if (fy_ < .2 or fy_ > .8) and (fx_ < .2 or fx_ > .8):
            rnames[i] = ('North' if fy_ < .5 else 'South') + ('-west' if fx_ < .5 else '-east') + ' tower'
        else:
            rnames[i] = 'Passage'
regimg = np.dstack([slots[0], slots[1], slots[2], np.full((H, W), 255)]).astype(np.uint8)
Image.fromarray(regimg, 'RGBA').save(os.path.join(ROOT, 'data/holdfast_gf_regions.png'))
# wall torches: iron sconce on the north face of every room, 1-3 per room
torches = []
for r in range(1, nreg + 1):
    m = lab_r == r
    if m.sum() < 30 or rnames[r] in ('Outside the Holdfast', 'Courtyard'): continue
    ys_, xs_ = np.where(m)
    top = ys_.min()
    row = [x for x in range(xs_.min() + 2, xs_.max() - 1) if top - 1 >= 0 and facem[top - 1, x] and facem[top - 1, x - 1] and facem[top - 1, x + 1]]
    if not row:
        continue
    n = max(1, min(3, len(row) // 9))
    for j in range(n):
        x = row[int((j + 0.5) * len(row) / n)]
        px, py = x * T + 8, (top - 1) * T + 2
        img[py:py + 10, px - 1:px + 2] = (40, 34, 30); img[py + 1:py + 9, px] = (90, 80, 70)
        img[py - 1:py + 1, px - 3:px + 4] = (40, 34, 30)
        torches.append([int(px), int(py - 2), int(r)])
Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(os.path.join(ROOT, 'art/game/holdfast/gf.png'), optimize=True)
json.dump({'tile': T, 'size': [PW, PH], 'image': 'res://art/game/holdfast/gf.png', 'solid': rects(block),
           'spawn': spawn, 'exit': spawn, 'stairs': stairs, 'rooms': labels,
           'regions': 'res://data/holdfast_gf_regions.png', 'region_names': rnames, 'torches': torches}, open(os.path.join(ROOT, 'data/holdfast_gf.json'), 'w'))
print('map', PW, PH, 'rooms', {v for v in names.values()}, 'stairs', len(stairs), 'spawn', spawn)
