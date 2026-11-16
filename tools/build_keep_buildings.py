#!/usr/bin/env python3
"""Red Keep buildings placed from the master plan (design/keep/red-keep-plan.html).

The plan draws the wall image at (0,0)-(1794,1066) in its SVG; matched against the game world that image covers
world x 624..7252, y 320..4266  ->  world = (624 + X*6628/1794, 320 + Y*3946/1066).
Each building's art is scaled to the width of its plan footprint and stands with its base on the footprint's south edge.

Outputs: art/game/keep/<id>.png and data/keep_buildings.json
  per building: pos (top-left, world px), size, collision polygons (world px), z_line (world y: a player whose feet
  are north of it is behind the building), door (world px, optional)."""
import json, os
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
import cv2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'art/source/keep/v3')
OUT = os.path.join(ROOT, 'art/game/keep')
SX, SY = 6628 / 1794, 3946 / 1066
def W(X, Y): return 624 + X * SX, 320 + Y * SY

def key_checker(a):
    """baked grey/white checkerboard -> alpha (border-connected light neutral pixels)"""
    mx, mn = a.max(-1), a.min(-1)
    lab, _ = ndimage.label((mx - mn < 14) & (mx > 195))
    border = set(np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]])) - {0}
    bg = np.isin(lab, list(border))
    for _ in range(3):
        bg |= ndimage.binary_dilation(bg) & ~bg & (mx - mn < 22) & (mx > 150)
    al = np.where(bg, 0, 255).astype(np.uint8)
    lab2, n2 = ndimage.label(al > 0)
    sz = ndimage.sum(np.ones_like(lab2), lab2, range(1, n2 + 1))
    al[~np.isin(lab2, 1 + np.where(sz > 40)[0])] = 0
    return al

def scaled(rgba, w):
    h = round(rgba.shape[0] * w / rgba.shape[1])
    a = rgba[..., 3:4].astype(np.float32) / 255
    pm = np.dstack([rgba[..., :3] * a, a * 255]).astype(np.uint8)
    x = np.asarray(Image.fromarray(pm, 'RGBA').resize((w, h), Image.LANCZOS)).astype(np.float32)
    al = x[..., 3:4] / 255
    col = np.where(al > 0.01, x[..., :3] / np.maximum(al, 1e-3), 0)
    return np.dstack([np.clip(col, 0, 255), np.where(x[..., 3] > 120, 255, 0)]).astype(np.uint8)

def polys(mask, ox, oy, s):
    cs, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out = []
    for c in cs:
        c = cv2.approxPolyDP(c, 1.5, True)[:, 0, :]
        if len(c) >= 3:
            out.append([[round(ox + x * s, 1), round(oy + y * s, 1)] for x, y in c])
    return out


def bake_shadow(img, pos, name, apron=False):
    """Same look as tools/build_shadows.py (walls): cast shadow projected by height (KX 0.5, KY 0.2, cap 700) in
    (38,30,78) up to alpha 96, plus a contact shadow (alpha up to 215) under the base so the building sits on the
    ground. Ground line per column = lowest opaque pixel of that column (the base the building stands on)."""
    KX, KY, HCAP = 0.50, 0.20, 700
    a = img[..., 3] > 0
    h, w = a.shape
    has = a.any(0)
    gl = np.where(has, h - 1 - np.argmax(a[::-1], axis=0), -1)          # ground line per column (local y)
    PL, PR, PB = 40, 380, 180
    W2, H2 = w + PL + PR, h + PB
    yy, xx = np.nonzero(a)
    gy = gl[xx]
    hh = np.minimum(np.maximum(0, gy - yy), HCAP).astype(np.float32)
    tx = np.round(xx + KX * hh).astype(int) + PL
    ty = np.round(gy + KY * hh).astype(int)
    ok = (tx >= 0) & (tx < W2) & (ty >= 0) & (ty < H2)
    S = np.zeros((H2, W2), np.uint8); S[ty[ok], tx[ok]] = 255
    S = cv2.morphologyEx(S, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8)); S = cv2.GaussianBlur(S, (0, 0), 2.0)
    foot = np.zeros((H2, W2), bool)
    cols = np.where(has)[0]
    foot[gl[cols], cols + PL] = True
    D = 44
    C = np.zeros((H2, W2), np.float32)
    for k in range(1, D + 1):
        sh_ = np.zeros_like(foot); sh_[k:] = foot[:-k]
        C = np.maximum(C, sh_ * (1.0 - k / (D + 1)) ** 1.6)
    C = cv2.GaussianBlur(C, (0, 0), 2.5)
    C = np.maximum(C, cv2.GaussianBlur(foot.astype(np.float32), (0, 0), 3.0) * 1.4)
    al = np.maximum(S.astype(np.float32) / 255 * 96, np.clip(C * 1.5, 0, 1) * 225)
    al[:h, PL:PL + w][a] = 0                                              # never draw over the building itself
    out = np.zeros((H2, W2, 4), np.uint8); out[..., 0], out[..., 1], out[..., 2] = 38, 30, 78
    out[..., 3] = al.astype(np.uint8)
    if apron:
        # stone paving apron round the foot: floor-slab texture (art/game/floor_atlas.png), darkened to sit in the
        # shadow, 28 px wide in front, 14 px at the sides, with a 2 px dark edge; the shadow is drawn over it
        tex = np.asarray(Image.open(os.path.join(ROOT, 'art/game/floor_atlas.png')).convert('RGB')).astype(np.float32)
        base = np.zeros((H2, W2), np.uint8)
        base[gl[cols], cols + PL] = 1
        for k in range(1, 6):                                            # base = bottom 5 px of the building
            idx = gl[cols] - k; base[np.clip(idx, 0, H2 - 1), cols + PL] = 1
        ap = cv2.dilate(base, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (37, 21))) > 0
        for dd in (10, 20, 30):
            ap2 = np.zeros_like(ap); ap2[dd:] = ap[:-dd]; ap |= ap2                # deeper in front
        bmask = np.zeros((H2, W2), bool); bmask[:h, PL:PL + w] = a
        ap &= ~bmask
        Y, X = np.indices((H2, W2))
        col = tex[(Y + pos[1]) % 128, (X + pos[0] - PL) % 128] * 0.82
        edge = ap & ~cv2.erode(ap.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
        col[edge] = (60, 48, 44)
        sh = np.minimum(al / 255.0, 0.55)[..., None]
        mix = col * (1 - sh) + np.array([38, 30, 78], np.float32) * sh
        out[ap, :3] = mix[ap].astype(np.uint8); out[ap, 3] = 255
    Image.fromarray(out).save(os.path.join(OUT, name + '_shadow.png'))
    return {'image': 'res://art/game/keep/%s_shadow.png' % name, 'pos': [pos[0] - PL, pos[1]]}

data = {}
# ---------------------------------------------------------------- The Holdfast (v6 art: the user's redrawn quarters, joined)
# v9: the user's flame-free quarters, registered by feature matching and joined on min-error cuts
# (tools/holdfast_v9_register.py, tools/holdfast_v9_join.py)
HF_SRC = 'art/source/keep/v8/holdfast_v9_src.png'
hf = np.array(Image.open(os.path.join(ROOT, HF_SRC)).convert('RGBA'))
hf[..., 3] = np.where(hf[..., 3] > 128, 255, 0)
# Size: 1235 px wide (0.65 of the reference-render width, approved in review). Place: centred on the old Holdfast
# footprint (x 2489), base line as low as the slot allows with the whole ground footprint clear of the ring wall.
# Size matched to the interior (data/holdfast_gf.json): the ground floor measures 1536 px across its corner towers
# (96 tiles), so the outside is drawn 1536 px wide too; same 16 px tile, same Kael, inside == outside.
w = 1536; s = w / hf.shape[1]
img = scaled(hf, w); h = img.shape[0]
ring = np.asarray(Image.open(os.path.join(ROOT, 'art/source/walls/ring_world_v2.png')))[..., 3] > 0
ringd = cv2.dilate(ring.astype(np.uint8), np.ones((17, 17), np.uint8)) > 0
yy, xx = np.indices((h, w))
TOP = round(h * 0.60)                                     # front range + corner-tower bases stand on the ground
foot = (img[..., 3] > 0) & (yy >= TOP)
cx = 2489
x0 = cx - w // 2
y1 = 2445
while (ringd[y1 - h:y1, x0:x0 + w] & foot).any():
    y1 += 4
pos = (x0, y1 - h)
# front portal (tools/holdfast_door.py): centred on the facade, bottom step 4 px below the ground line of that column
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from holdfast_door import draw_door
dr = draw_door(); dh, dw = dr.shape[:2]
gcx = w // 2
gy = int(np.where(img[:, gcx, 3] > 0)[0].max())
img = np.vstack([img, np.zeros((8, w, 4), np.uint8)])          # room for the steps below the old base
dy0, dx0 = gy + 5 - dh, gcx - dw // 2
reg_ = img[dy0:dy0 + dh, dx0:dx0 + dw]
m_ = dr[..., 3] > 0
reg_[m_] = dr[m_]
h = img.shape[0]
yy, xx = np.indices((h, w))
foot = (img[..., 3] > 0) & (yy >= TOP)
DOOR = [pos[0] + gcx, pos[1] + gy + 18]
if 'v6' in HF_SRC:
    import holdfast_fixes; img = holdfast_fixes.fix(img)                          # where Kael stands to press E
Image.fromarray(img).save(os.path.join(OUT, 'holdfast.png'))
col_mask = ndimage.binary_opening(foot & ~ringd[pos[1]:pos[1] + h, pos[0]:pos[0] + w] & (yy <= gy), iterations=2)
# animated flames (game draws them): tower-top brazier, the two arcade fire bowls; the east lantern gets a glow
FL = [(692, 199, 2.0, 'fire'), (520, 1157, 1.4, 'fire'), (1053, 1157, 1.4, 'fire'), (1623, 756, 0.6, 'glow')]
flames = [[round(pos[0] + x * s), round(pos[1] + y * s), sc, k] for x, y, sc, k in FL]
data['holdfast'] = {'name': 'The Holdfast', 'image': 'res://art/game/keep/holdfast.png', 'pos': pos, 'size': [w, h],
                    'collision': polys(col_mask, pos[0], pos[1], 1.0), 'z_line': pos[1] + TOP, 'enter': DOOR,
                    'shadow': bake_shadow(img, pos, 'holdfast', apron=True), 'flames': flames}
# ---------------------------------------------------------------- Throne Hall (v7: the user's matched quarters at 2x,
# joined on a plain grid -> art/source/keep/v7/throne_hall_v4_src.png, 2171 x 2528)
th = np.array(Image.open(os.path.join(ROOT, 'art/source/keep/v7/throne_hall_v4_src.png')).convert('RGBA'))
th[..., 3] = np.where(th[..., 3] > 128, 255, 0)
# Placed on its plan footprint (design/keep/red-keep-plan.html: rect 760,520 270x150): the main body (corner towers,
# source x 640..2124) spans the footprint's width, the towers' base (source y 2450) stands on its south edge; the
# covered walkway on the west runs toward the waiting gallery (plan 560..740), as in the plan.
fx0, fy0 = W(760, 520); fx1, fy1 = W(1030, 670)
import sys as _s; _s.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if os.path.exists(os.path.join(ROOT, 'data/ring_xform.json')):
    import expand_layout; _T, _ = expand_layout.load(os.path.join(ROOT, 'data/ring_xform.json'))
    _dx = _T(fx0, fy1)[0] - fx0; fx0 += _dx; fx1 += _dx
AXIS, DOOR_Y, BODY0, BODY1, BASE_Y = 1482, 2093, 640, 2124, 2450
s = (fx1 - fx0) / (BODY1 - BODY0); w = round(th.shape[1] * s)
img = scaled(th, w); h = img.shape[0]
pos = (round(fx0 - BODY0 * s), round(fy1 - BASE_Y * s))
print('throne footprint world', round(fx0), round(fy0), round(fx1), round(fy1), 'scale', round(s, 3))
Image.fromarray(img).save(os.path.join(OUT, 'throne_hall.png'))
H0, W0 = th.shape[:2]
yy0, xx0 = np.indices((H0, W0))
m = (th[..., 3] > 0) & (yy0 >= 1150)          # ground footprint: the lower part (front range, towers, walkway base)
m &= ~((yy0 >= DOOR_Y - 20) & (xx0 >= 1030) & (xx0 <= 1930))   # the stairs up to the door stay walkable
m = ndimage.binary_opening(m, iterations=3)
data['throne_hall'] = {'name': 'Throne Hall', 'image': 'res://art/game/keep/throne_hall.png', 'pos': pos, 'size': [w, h],
                       'collision': polys(m, pos[0], pos[1], s), 'z_line': round(pos[1] + DOOR_Y * s),
                       'door': [round(pos[0] + AXIS * s), round(pos[1] + (DOOR_Y + 40) * s)],
                       'shadow': bake_shadow(img, pos, 'throne_hall')}
json.dump(data, open(os.path.join(ROOT, 'data/keep_buildings.json'), 'w'), indent=1)
for k, v in data.items():
    print(k, 'pos', v['pos'], 'size', v['size'], 'z', v['z_line'], 'polys', len(v['collision']), 'door', v.get('door'))
