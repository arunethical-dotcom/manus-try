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
# ---------------------------------------------------------------- The Holdfast (v5 art: grey stone, joined from 4 quadrants)
hf = np.array(Image.open(os.path.join(SRC, 'holdfast_v5_src.png')).convert('RGBA'))
hf[..., 3] = np.where(hf[..., 3] > 128, 255, 0)
# Size: 1235 px wide (0.65 of the reference-render width, approved in review). Place: centred on the old Holdfast
# footprint (x 2489), base line as low as the slot allows with the whole ground footprint clear of the ring wall.
w = 1235; s = w / hf.shape[1]
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
Image.fromarray(img).save(os.path.join(OUT, 'holdfast.png'))
col_mask = ndimage.binary_opening(foot & ~ringd[pos[1]:pos[1] + h, pos[0]:pos[0] + w], iterations=2)
data['holdfast'] = {'name': 'The Holdfast', 'image': 'res://art/game/keep/holdfast.png', 'pos': pos, 'size': [w, h],
                    'collision': polys(col_mask, pos[0], pos[1], 1.0), 'z_line': pos[1] + TOP,
                    'shadow': bake_shadow(img, pos, 'holdfast', apron=True)}
# ---------------------------------------------------------------- Throne Hall (plan: rect 760,520 270x150)
th = np.array(Image.open(os.path.join(SRC, 'throne_hall_src.png')).convert('RGBA'))
th[..., 3] = np.where(th[..., 3] > 128, 255, 0)
# From the reference town render (ref->world x = 558 + X*3.56, y = 705 + Y*3.19): hall spans ref x 828..1110,
# bottom step at ref y 812  ->  world x 3506..4510, base y 3295.
x0, x1, y1 = 3506, 4510, 3295
w = round(x1 - x0); s = w / th.shape[1]
img = scaled(th, w); h = img.shape[0]
pos = (round(x0), round(y1 - h))
Image.fromarray(img).save(os.path.join(OUT, 'throne_hall.png'))
H0, W0 = th.shape[:2]
m = np.zeros((H0, W0), bool)
m[560:1002, :] = th[560:1002, :, 3] > 0          # the hall itself, from its rear wall line to the front base
for bx0, bx1 in ((398, 470), (770, 842)):         # the two king statues on their plinths
    m[995:1112, bx0:bx1] = th[995:1112, bx0:bx1, 3] > 0
m[995:1150, 0:345] = th[995:1150, 0:345, 3] > 0     # the lower bases of the side wings
m[995:1150, 895:] = th[995:1150, 895:, 3] > 0
for bx0, bx1 in ((338, 392), (848, 902)):         # braziers
    m[1040:1135, bx0:bx1] = th[1040:1135, bx0:bx1, 3] > 0
m[995:1015, 548:692] = False                      # the door threshold stays reachable
m = ndimage.binary_opening(m, iterations=2)
data['throne_hall'] = {'name': 'Throne Hall', 'image': 'res://art/game/keep/throne_hall.png', 'pos': pos, 'size': [w, h],
                       'collision': polys(m, pos[0], pos[1], s), 'z_line': round(pos[1] + 1000 * s),
                       'door': [round(pos[0] + 620 * s), round(pos[1] + 1030 * s)],
                       'shadow': bake_shadow(img, pos, 'throne_hall')}
json.dump(data, open(os.path.join(ROOT, 'data/keep_buildings.json'), 'w'), indent=1)
for k, v in data.items():
    print(k, 'pos', v['pos'], 'size', v['size'], 'z', v['z_line'], 'polys', len(v['collision']), 'door', v.get('door'))
