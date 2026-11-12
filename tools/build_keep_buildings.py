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

data = {}
# ---------------------------------------------------------------- The Holdfast (v2 art: castle on a rock mound)
hf = np.array(Image.open(os.path.join(SRC, 'holdfast_v2_src.png')).convert('RGBA'))
hf[..., 3] = np.where(hf[..., 3] > 128, 255, 0)
lab_, n_ = ndimage.label(hf[..., 3] > 0)                     # drop stray specks, keep the castle
sz_ = ndimage.sum(np.ones_like(lab_), lab_, range(1, n_ + 1))
hf[..., 3] = np.where(lab_ == 1 + np.argmax(sz_), 255, 0)
ys_, xs_ = np.where(hf[..., 3] > 0)
CX0, CY0 = xs_.min(), ys_.min()
hf = hf[CY0:ys_.max() + 1, CX0:xs_.max() + 1]
# Size: as wide as the castle part of the earlier art (reference render). Place: north-west corner, the mound's
# foot on the courtyard floor clear of the ring wall (searched with the mound footprint).
W_HF = 1900
w = W_HF; s = w / hf.shape[1]
img = scaled(hf, w); h = img.shape[0]
ring = np.asarray(Image.open(os.path.join(ROOT, 'art/source/walls/ring_world_v2.png')))[..., 3] > 0
ringd = cv2.dilate(ring.astype(np.uint8), np.ones((17, 17), np.uint8)) > 0
yy, xx = np.indices((h, w))
TOP = round((640 - CY0) * s)                                # mound rim: below this the art stands on the ground
foot = (img[..., 3] > 0) & (yy >= TOP)
# exact place from the reference render: the bridge foot (source 750,1029) sits at ref (510,545) -> world (2374,2444)
x0 = round(2374 - (750 - CX0) * s); y1 = round(2444 + (h - 1 - (1029 - CY0) * s))
pos = (x0, y1 - h)
Image.fromarray(img).save(os.path.join(OUT, 'holdfast.png'))
sub_ring = ring[pos[1]:pos[1] + h, pos[0]:pos[0] + w]
col_mask = ndimage.binary_opening(foot & ~ringd[pos[1]:pos[1] + h, pos[0]:pos[0] + w], iterations=2)
data['holdfast'] = {'name': 'The Holdfast', 'image': 'res://art/game/keep/holdfast.png', 'pos': pos, 'size': [w, h],
                    'collision': polys(col_mask, pos[0], pos[1], 1.0), 'z_line': pos[1] + TOP}
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
                       'door': [round(pos[0] + 620 * s), round(pos[1] + 1030 * s)]}
json.dump(data, open(os.path.join(ROOT, 'data/keep_buildings.json'), 'w'), indent=1)
for k, v in data.items():
    print(k, 'pos', v['pos'], 'size', v['size'], 'z', v['z_line'], 'polys', len(v['collision']), 'door', v.get('door'))
