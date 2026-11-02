#!/usr/bin/env python3
"""Splits the wall art into objects (each tower, each wall stretch between towers) so a whole object can fade out
when Kael walks behind it (CrossCode style).

  python3 tools/build_objects.py        (after tools/build_walls.py)

Writes the object id (1..255) into the B channel of art/game/walls/depth_*.png, and data/objmap.bin (PNG data): a half-size
RGBA map (R,G = ground line y/2 as 16 bit, B = object id) the game samples around Kael."""
import os, json
import numpy as np, cv2
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
L = json.load(open(os.path.join(ROOT, "data/layout.json")))
WW, WH = L["world"]
A = np.zeros((WH, WW), bool); RGB = np.zeros((WH, WW, 3), np.uint8); G = np.zeros((WH, WW), np.int32)
for c in L["chunks"]:
    if not c.get("wall"):
        continue
    x, y = c["x"], c["y"]
    w = np.array(Image.open(os.path.join(ROOT, "art/game/walls/wall_%d_%d.png" % (x, y))))
    d = np.array(Image.open(os.path.join(ROOT, "art/game/walls/depth_%d_%d.png" % (x, y))))
    h, ww = w.shape[:2]
    A[y:y + h, x:x + ww] = w[..., 3] > 0
    RGB[y:y + h, x:x + ww] = w[..., :3]
    G[y:y + h, x:x + ww] = d[..., 0].astype(np.int32) * 256 + d[..., 1]

ID = np.zeros((WH, WW), np.uint8)
# ---- towers: blue roofs, the tower = pixels under the roof (x range) down to the base, standing on ~the same ground line
c = RGB.astype(int)
blue = A & (c[..., 2] > c[..., 0] + 60) & (c[..., 2] > 140)
blue = cv2.morphologyEx(blue.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
n, lab, st, _ = cv2.connectedComponentsWithStats(blue)
nid = 0
towers = []
for i in range(1, n):
    x, y, w, h, area = st[i]
    if area < 1500:
        continue
    cx = x + w // 2
    yb = y
    lim = int(y + 2.6 * w)                      # tower body: ~2.5 roof widths below the roof top
    while yb + 1 < min(WH, lim) and A[yb + 1, cx]:
        yb += 1
    # tower silhouette: roof rows = the roof's own extent; below it the crenellated crown (~roof width) and the
    # cylindrical body (~0.86 roof width), centred on the roof
    rows = list(range(y, yb + 1))
    rb = y + h                                       # roof bottom
    Ls, Rs = [], []
    for yy in rows:
        hw_ = w * (0.47 if yy < rb + 0.40 * w else 0.42)
        Ls.append(int(cx - hw_)); Rs.append(int(cx + hw_))
    m = np.zeros((WH, WW), bool)
    rl = (lab == i)
    for yy, l, r in zip(rows, Ls, Rs):
        xs_ = np.nonzero(rl[yy])[0]
        if len(xs_):                                  # roof rows: the roof's own extent (+ its outline)
            l, r = xs_.min() - 3, xs_.max() + 3
        m[yy, max(0, l):min(WW, r + 1)] = A[yy, max(0, l):min(WW, r + 1)]
    # the golden finial above the roof
    m[max(0, y - 30):y, cx - int(w * 0.12):cx + int(w * 0.12)] = A[max(0, y - 30):y, cx - int(w * 0.12):cx + int(w * 0.12)]
    m |= (lab == i)
    m &= (ID == 0)
    nid += 1
    ID[m] = nid
    towers.append((nid, cx, y, yb))
print("towers", len(towers))
# ---- the rest: connected wall stretches (towers cut the ring into pieces)
rest = (A & (ID == 0)).astype(np.uint8)
n2, lab2, st2, _ = cv2.connectedComponentsWithStats(rest, connectivity=4)
for i in range(1, n2):
    if st2[i, 4] < 400:
        continue
    nid += 1
    if nid > 255:
        raise SystemExit("too many objects")
    ID[lab2 == i] = nid
# leftovers (specks) join the neighbouring object
left = A & (ID == 0)
if left.any():
    dil = cv2.dilate(ID, np.ones((15, 15), np.uint8))
    ID[left] = dil[left]
print("objects", nid)

# ---- write ids into the depth chunks (B channel)
for cc in L["chunks"]:
    if not cc.get("wall"):
        continue
    x, y = cc["x"], cc["y"]
    p = os.path.join(ROOT, "art/game/walls/depth_%d_%d.png" % (x, y))
    d = np.array(Image.open(p))
    h, w = d.shape[:2]
    d[..., 2] = ID[y:y + h, x:x + w]
    Image.fromarray(d).save(p)
# ---- half-size lookup map for the game
H2, W2 = WH // 2, WW // 2
g2 = (G[::2, ::2][:H2, :W2] // 2).astype(np.int32)
om = np.zeros((H2, W2, 4), np.uint8)
om[..., 0] = (g2 >> 8) & 255
om[..., 1] = g2 & 255
om[..., 2] = ID[::2, ::2][:H2, :W2]
om[..., 3] = 255
Image.fromarray(om).save(os.path.join(ROOT, "data/objmap.bin"), format="PNG")
# preview
pal = np.random.RandomState(3).randint(40, 255, (256, 3)).astype(np.uint8); pal[0] = 0
Image.fromarray(pal[ID[::6, ::6]]).save("/tmp/pics/objects.png")
