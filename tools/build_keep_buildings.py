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
# ---------------------------------------------------------------- The Holdfast (plan: moat rect 350,310 340x220)
src = np.asarray(Image.open(os.path.join(SRC, 'holdfast_src.png')).convert('RGB'))
rgba = np.dstack([src, key_checker(src.astype(int))])
# crop away the outer ring of wooden stakes and its curb: keep the castle, the moat pit, the iron fence and both bridges
CROP = [(285,0),(1150,0),(1150,330),(1240,405),(1310,500),(1340,545),(1448,545),(1448,665),(1405,665),(1405,860),(1360,925),(1290,990),(1230,1040),(1120,1058),
        (690,1058),(690,1076),(572,1076),(572,1058),(260,1052),(200,1030),(170,935),(130,880),(128,455),(200,402),(285,372)]
cm = Image.new('L', (rgba.shape[1], rgba.shape[0]), 0); ImageDraw.Draw(cm).polygon(CROP, fill=255)
rgba[..., 3] = np.minimum(rgba[..., 3], np.asarray(cm))
ys_, xs_ = np.where(rgba[..., 3] > 0)
CX0, CY0 = xs_.min(), ys_.min()
rgba = rgba[CY0:ys_.max() + 1, CX0:xs_.max() + 1]
# Size from the reference town render (2132 px wide). Place: as close to the reference's north-west corner as the game's
# wall allows with the castle's own base on the courtyard floor (searched: base y 2740, right edge 3640). Its east
# bridge runs behind the Throne Hall towards the King's door, as in the plan.
x0, x1, y1 = 1508, 3640, 2740
w = round(x1 - x0); s = w / rgba.shape[1]
img = scaled(rgba, w); h = img.shape[0]
pos = (round(x0), round(y1 - h))
# extend the moat westwards so it runs on until it meets the ring wall (the reference has no gap): each row of the pit is
# continued to the left by mirrored repeats of its own leftmost 96 px
E = 360
ext = np.zeros((h, w + E, 4), np.uint8); ext[:, E:] = img
op = img[..., 3] > 0
# pit floor texture: the pit's own dirt colours (sampled from src x 140-200, y 470-860), pixel-art noise blobs
smp = src[470:860, 140:200].reshape(-1, 3).astype(np.float32)
lum = smp.mean(1); dirt = smp[(lum > 35) & (lum < 95) & (smp[:, 0] > smp[:, 2] + 12)]
pal = np.percentile(dirt, [15, 40, 65, 88], axis=0)
rng = np.random.default_rng(7)
nz = sum(cv2.resize(rng.random((h // f + 2, (E + 200) // f + 2)).astype(np.float32), ((E + 200) // 2 * 2, h // 2 * 2),
                    interpolation=cv2.INTER_CUBIC)[:h, :E + 200] * wgt for f, wgt in ((40, .5), (14, .3), (5, .2)))
nz = cv2.resize(nz[::3, ::3], (nz.shape[1], nz.shape[0]), interpolation=cv2.INTER_NEAREST)   # chunky pixels
q = np.digitize(nz, np.quantile(nz, [.2, .55, .85]))
tex = pal[q]
pebble = (rng.random(q.shape) > 0.9985)
pebble = cv2.dilate(pebble.astype(np.uint8), np.ones((4, 5), np.uint8)) > 0
tex[pebble] = pal[3] * 1.35
y_fence = int((870 - CY0) * s)                        # below this the west edge is the fence/curb diagonal
for y in range(h):
    xs_ = np.where(op[y])[0]
    if len(xs_) == 0 or xs_[0] > 12 * s + 4:
        continue
    L = xs_[0]; P = 112; strip = img[y, L + 4:L + 4 + P]
    if (strip[:, 3] == 0).any():
        continue
    if y < y_fence:
        n = E + L + 30
        row = tex[y, :n][::-1].copy()                  # row[k] = pixel k px west of the seam
        blend = np.clip((np.arange(n) - 6) / 24.0, 0, 1)[:, None]
        orig = np.array([strip[min(k, P - 1)][:3] for k in range(0)]) if False else None
        for k in range(n):
            xx = E + L + 30 - 1 - k
            if xx >= E + L:                           # overlap band: fade from the real pit edge into the texture
                bb = 1 - np.clip((xx - (E + L)) / 30.0, 0, 1)
                c = ext[y, xx, :3].astype(np.float32) * (1 - bb) + row[k] * bb
            else:
                c = row[k]
            ext[y, xx, :3] = np.clip(c, 0, 255); ext[y, xx, 3] = 255
    else:
        for k in range(E + L):
            ext[y, E + L - 1 - k] = strip[P - 1 - (k % P)]
img = ext; w = w + E; pos = (pos[0] - E, pos[1]); CX0 = CX0 - E / s
# the moat (everything that is not the castle) disappears under the ring wall, so it meets the wall like the reference
CASTLE = [(205,480),(280,250),(380,210),(515,200),(520,110),(610,0),(720,110),(720,220),(1040,220),(1090,170),(1150,240),
          (1150,520),(1370,515),(1370,690),(1100,700),(900,845),(760,845),(730,800),(520,800),(500,840),(380,845),(330,740),(205,720)]
cmask = Image.new('L', (w, h), 0)
ImageDraw.Draw(cmask).polygon([((x - CX0) * s, (y - CY0) * s) for x, y in CASTLE], fill=255)
castle = np.asarray(cmask) > 0
ring = np.asarray(Image.open(os.path.join(ROOT, 'art/source/walls/ring_world_v2.png')).crop((pos[0], pos[1], pos[0] + w, pos[1] + h)))[..., 3] > 0
under = ring & ~castle
img[..., 3] = np.where(under, 0, img[..., 3])
FLOOR_OK = ~ring
Image.fromarray(img).save(os.path.join(OUT, 'holdfast.png'))
# collision: the spiked moat oval (everything opaque below the oval's top rim); towers above the rim are walk-behind
H0, W0 = rgba.shape[:2]
cx, cy, rx, ry = 724 - CX0, 672 - CY0, 726, 412   # oval of the moat in the source image
yy, xx = np.indices((H0, W0))
oval = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1.0
col_mask = oval & (rgba[..., 3] > 0)
col_mask = ndimage.binary_opening(col_mask, iterations=2)
yy2 = np.indices((h, w))[0]
col_mask = FLOOR_OK & (img[..., 3] > 0) & (yy2 >= (380 - CY0) * s)
s_col = 1.0
data['holdfast'] = {'name': 'The Holdfast', 'image': 'res://art/game/keep/holdfast.png', 'pos': pos, 'size': [w, h],
                    'collision': polys(col_mask, pos[0], pos[1], s_col), 'z_line': round(pos[1] + cy * s)}
# ---------------------------------------------------------------- Throne Hall (plan: rect 760,520 270x150)
th = np.array(Image.open(os.path.join(SRC, 'throne_hall_src.png')).convert('RGBA'))
th[..., 3] = np.where(th[..., 3] > 128, 255, 0)
x0, y0 = W(760, 520); x1, y1 = W(760 + 270, 520 + 150)
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
