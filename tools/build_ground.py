#!/usr/bin/env python3
"""Stage 2 ground: grass everywhere from the supplied grass tile sheets, organic meadow / flower / dirt patches,
and a stone avenue (the supplied floor tile) from the south gate to the north gate with an approach road outside.

  python3 tools/build_ground.py      (run after tools/build_walls.py; reads data/layout.json)

Writes art/game/ground/g_<x>_<y>.webp (1024 px chunks) and adds "ground_chunks" to data/layout.json.
Deterministic (fixed random seed)."""
import os, json, glob
import numpy as np, cv2
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "art/source/ground")
OUT = os.path.join(ROOT, "art/game/ground")
os.makedirs(OUT, exist_ok=True)
for f in glob.glob(os.path.join(OUT, "*")):
    os.remove(f)
L = json.load(open(os.path.join(ROOT, "data/layout.json")))
WW, WH = L["world"]
S, CH = 128, 1024
rng = np.random.RandomState(7)

# ---------------------------------------------------------------- cut the tiles off the magenta sheets
tiles = []
for sh in sorted(glob.glob(os.path.join(SRC, "grass_sheet_*.png"))):
    a = np.array(Image.open(sh).convert("RGB")); c = a.astype(int)
    mag = (c[..., 0] - c[..., 1] > 60) & (c[..., 2] - c[..., 1] > 60)
    n, lab, st, _ = cv2.connectedComponentsWithStats((~mag).astype(np.uint8))
    comps = sorted([st[i] for i in range(1, n) if st[i, 4] > 5000], key=lambda s: (round(s[1] / 50), s[0]))
    for x, y, w, h, _ in comps:
        ix, iy = int(w * 0.13), int(h * 0.13)          # drop the ragged grass border of each tile
        tiles.append(cv2.resize(a[y + iy:y + h - iy, x + ix:x + w - ix], (S, S), interpolation=cv2.INTER_AREA))
T = np.array(tiles).astype(np.float32)
print("tiles", len(T))


def seamless(t):
    h = S // 2
    r = np.roll(np.roll(t, h, 0), h, 1)
    yy, xx = np.mgrid[0:S, 0:S]
    d = np.minimum(np.minimum(xx, S - 1 - xx), np.minimum(yy, S - 1 - yy)).astype(np.float32)
    w = np.clip(d / (S * 0.25), 0, 1)[..., None]
    return t * w + r * (1 - w)


# tile roles (indices in sheet order: sheet 1 = 0..47, sheet 2 = 48..97), picked by measured dirt / flower cover
GRASS = [0, 1, 2, 16, 17, 24, 32, 49, 53, 57, 69, 72, 73, 81, 86]
CLOVER = [40, 41, 42, 54, 55]
DIRT = [8, 9, 10, 58, 66, 70]
FLOWER = [3, 5, 6, 14, 20, 27, 28, 34, 35, 43, 44, 47, 83, 87, 94, 95, 96]
SEAM = [seamless(t) for t in T]
base = SEAM[0]
bm = base.reshape(-1, 3).mean(0)
def norm(i, k):
    return SEAM[i] + (bm - SEAM[i].reshape(-1, 3).mean(0)) * k
groups = {"grass": [norm(i, 0.7) for i in GRASS], "clover": [norm(i, 0.45) for i in CLOVER],
          "flower": [norm(i, 0.35) for i in FLOWER], "dirt": [norm(i, 0.2) for i in DIRT]}
print({k: len(v) for k, v in groups.items()})

# ---------------------------------------------------------------- base: two grass tiles mixed with a soft low-frequency mask
ground = np.zeros((WH, WW, 3), np.float32)
g2 = groups["grass"][1]
ty, tx = (WH + S - 1) // S, (WW + S - 1) // S
B1 = np.tile(base, (ty, tx, 1))[:WH, :WW]
B2 = np.tile(g2, (ty, tx, 1))[:WH, :WW]
noise = cv2.resize(rng.rand(WH // 256 + 2, WW // 256 + 2).astype(np.float32), (WW, WH), interpolation=cv2.INTER_CUBIC)
m = np.clip((noise - 0.35) * 3, 0, 1)[..., None]
ground = B1 * (1 - m) + B2 * m


def blob(rx, ry):
    """organic soft mask (0..1) of about rx x ry"""
    h, w = int(ry * 2.6), int(rx * 2.6)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = ((xx - w / 2) / rx) ** 2 + ((yy - h / 2) / ry) ** 2
    nz = cv2.resize(rng.rand(8, 8).astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC)
    v = 1.0 - d + (nz - 0.5) * 0.9
    return np.clip(v * 2.2, 0, 1) ** 2


def stamp(tex, cx, cy, rx, ry):
    mk = blob(rx, ry)
    h, w = mk.shape
    x0, y0 = int(cx - w / 2), int(cy - h / 2)
    ox, oy = rng.randint(0, S), rng.randint(0, S)
    big = np.tile(tex, (h // S + 2, w // S + 2, 1))[oy:oy + h, ox:ox + w]
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(WW, x0 + w), min(WH, y0 + h)
    if xb <= xa or yb <= ya:
        return
    mm = mk[ya - y0:yb - y0, xa - x0:xb - x0, None]
    ground[ya:yb, xa:xb] = ground[ya:yb, xa:xb] * (1 - mm) + big[ya - y0:yb - y0, xa - x0:xb - x0] * mm


# avenue geometry (kept free of patches)
sx, sy = L["gates"]["south"]; nx, ny = L["gates"]["north"]
AW = 150                                             # half width of the avenue (px)
def on_avenue(x, y, pad=0):
    return abs(x - (sx + nx) / 2) < AW + pad


ins = L["inside"]
for k, count, rr in (("grass", 140, (200, 420)), ("clover", 40, (100, 220)), ("flower", 170, (90, 240)), ("dirt", 25, (60, 120))):
    for _ in range(count):
        cx, cy = rng.randint(0, WW), rng.randint(0, WH)
        if on_avenue(cx, cy, 200):
            continue
        rx = rng.randint(*rr); ry = int(rx * rng.uniform(0.6, 1.0))
        stamp(groups[k][rng.randint(len(groups[k]))], cx, cy, rx, ry)

# ---------------------------------------------------------------- uneven greenery: large soft colour zones
# (lush dark green, sunny yellow-green, dry olive, cool blue-green), so the grass is not one flat colour
def lowfreq(cell, seed):
    r = np.random.RandomState(seed)
    g = r.rand(WH // cell + 3, WW // cell + 3).astype(np.float32)
    return cv2.resize(g, (WW + 3 * cell, WH + 3 * cell), interpolation=cv2.INTER_CUBIC)[cell:cell + WH, cell:cell + WW]
def zone(n, lo, hi):
    return np.clip((n - lo) / (hi - lo), 0, 1) ** 1.5
n1, n2, n3 = lowfreq(900, 11), lowfreq(520, 12), lowfreq(1400, 13)
fine = lowfreq(160, 14)
LUSH, SUN, DRY, COOL = (np.array(v, np.float32) for v in ([0.70, 0.92, 0.62], [1.22, 1.16, 0.72], [1.18, 1.06, 0.62], [0.82, 0.98, 1.10]))
for y0 in range(0, WH, 256):                     # in strips (memory)
    sl = slice(y0, min(WH, y0 + 256))
    g = ground[sl]
    lush = (0.50 * zone(n1[sl], 0.55, 0.85))[..., None]
    sun = (0.45 * zone(n2[sl], 0.60, 0.90))[..., None]
    dry = (0.60 * zone(1 - n1[sl], 0.62, 0.92) * zone(n3[sl], 0.35, 0.7))[..., None]
    cool = (0.35 * zone(n3[sl], 0.68, 0.95))[..., None]
    g = g * (1 - lush + lush * LUSH)
    g = g * (1 - sun + sun * SUN)
    g = g * (1 - dry) + g.mean(-1, keepdims=True) * DRY * dry
    g = g * (1 - cool + cool * COOL)
    ground[sl] = g * (0.90 + 0.20 * fine[sl])[..., None]
del n1, n2, n3, fine

# ---------------------------------------------------------------- mud roads (supplied mud tiles), layout after
# art/source/ground/reference_layout_2.png: ring road inside the walls, two cross streets, diagonals to the corners,
# a round plaza at the centre, and a road out of the north gate.
mt = []
for sh in sorted(glob.glob(os.path.join(SRC, "mud_sheet_*.png"))):
    a = np.array(Image.open(sh).convert("RGB")); c = a.astype(int)
    mag = (c[..., 0] - c[..., 1] > 60) & (c[..., 2] - c[..., 1] > 60)
    n, lab, st, _ = cv2.connectedComponentsWithStats((~mag).astype(np.uint8))
    comps = sorted([st[i] for i in range(1, n) if st[i, 4] > 5000], key=lambda s: (round(s[1] / 50), s[0]))
    for x, y, w, h, _ in comps:
        ix, iy = int(w * 0.12), int(h * 0.12)
        mt.append(cv2.resize(a[y + iy:y + h - iy, x + ix:x + w - ix], (S, S), interpolation=cv2.INTER_AREA).astype(np.float32))
MUD_USE = [2, 8, 10, 16, 17, 18, 23, 0, 1, 3, 9, 19]       # calmer tiles first; cracked / ridged ones only as accents
mseam = [seamless(mt[i]) for i in MUD_USE]
mmean = np.mean([t.reshape(-1, 3).mean(0) for t in mseam[:7]], axis=0)
mseam = [t + (mmean - t.reshape(-1, 3).mean(0)) * 0.6 for t in mseam]
for i, t in enumerate(mseam):                                       # slightly calmer, earthier orange
    lum = t.mean(-1, keepdims=True)
    mseam[i] = (lum + (t - lum) * 0.8) * 0.92
print("mud tiles", len(mt))
# mud field: the tiles laid evenly on a regular 128 px grid, cycling through them in a fixed order
gyc, gxc = (WH + S - 1) // S, (WW + S - 1) // S
ORDER = [0, 1, 2, 3, 4, 5, 6, 0, 2, 4, 1, 3, 5, 6, 7, 8, 9, 10, 11]
pick = np.array([[ORDER[(yy * 7 + xx * 3) % len(ORDER)] for xx in range(gxc)] for yy in range(gyc)])
MUD = np.zeros((gyc * S, gxc * S, 3), np.float32)
for yy in range(gyc):
    for xx in range(gxc):
        MUD[yy * S:(yy + 1) * S, xx * S:(xx + 1) * S] = mseam[pick[yy, xx]]
# hide the cell grid: blend with a half-cell-shifted copy of a calm tile field
calm = np.tile(mseam[0], (gyc + 1, gxc + 1, 1))[S // 2:S // 2 + gyc * S, S // 2:S // 2 + gxc * S]
yy_, xx_ = np.mgrid[0:S, 0:S]
dd = np.minimum(np.minimum(xx_, S - 1 - xx_), np.minimum(yy_, S - 1 - yy_)).astype(np.float32)
wcell = np.tile(np.clip(dd / 28, 0, 1), (gyc, gxc))[..., None]
MUD = (MUD * wcell + calm * (1 - wcell))[:WH, :WW]

# interior of the ring (walls flood-filled at 1/8 scale)
K8 = 8
wall = np.zeros((WH // K8 + 1, WW // K8 + 1), np.uint8)
for c in L["chunks"]:
    if c.get("wall"):
        al = np.array(Image.open(os.path.join(ROOT, "art/game/walls/wall_%d_%d.png" % (c["x"], c["y"]))))[..., 3]
        sm = cv2.resize(al, (al.shape[1] // K8, al.shape[0] // K8), interpolation=cv2.INTER_AREA) > 20
        y0_, x0_ = c["y"] // K8, c["x"] // K8
        wall[y0_:y0_ + sm.shape[0], x0_:x0_ + sm.shape[1]] |= sm
wall = cv2.morphologyEx(wall, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
nl, lab8 = cv2.connectedComponents((1 - wall).astype(np.uint8), connectivity=4)
inside8 = (lab8 == lab8[L["inside"][1] // K8, L["inside"][0] // K8]).astype(np.uint8)
ys8, xs8 = np.nonzero(inside8)
IX0, IX1, IY0, IY1 = xs8.min() * K8, xs8.max() * K8, ys8.min() * K8, ys8.max() * K8
print("interior box", IX0, IY0, IX1, IY1)
dist = cv2.distanceTransform(inside8, cv2.DIST_L2, 5) * K8          # px from the wall's inner edge

# road network = the supplied road plan (art/source/ground/road_plan.png, orange on magenta), its bounding box
# stretched onto the interior of the ring; its central spine runs on the gate axis.
pa = np.array(Image.open(os.path.join(SRC, "road_plan.png")).convert("RGB")).astype(int)
pm = ((pa[..., 1] > 110) & (pa[..., 0] > 180) & (pa[..., 2] < 180)).astype(np.uint8)
pm = cv2.morphologyEx(pm, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
pys, pxs = np.nonzero(pm)
pm = pm[pys.min():pys.max() + 1, pxs.min():pxs.max() + 1]
MARG = 120                                            # px kept between the plan and the wall foot
bx0, bx1 = IX0 + MARG, IX1 - MARG
by0, by1 = IY0 + MARG, IY1 + 40                       # bottom: the spine runs down into the south gate
axis = (sx + nx) / 2
half = max(axis - bx0, bx1 - axis)                    # keep the plan symmetric about the gate axis
bx0, bx1 = axis - half, axis + half
# the plan, scaled straight to full resolution (clean edges, exactly its shape)
PW, PH = int(bx1 - bx0), int(by1 - by0)
pr = cv2.resize(cv2.GaussianBlur(pm.astype(np.float32), (0, 0), 0.6), (PW, PH), interpolation=cv2.INTER_CUBIC) > 0.5
rmask = np.zeros((WH, WW), bool)
X0p, Y0p = int(bx0), int(by0)
yb, xb = min(WH, Y0p + PH), min(WW, X0p + PW)
rmask[Y0p:yb, X0p:xb] = pr[:yb - Y0p, :xb - X0p]
# the plan's central spine continues straight down to the south gate (same width)
ax_ = int(axis)
yl = int(np.nonzero(rmask[:, ax_])[0].max())
row = rmask[yl - 8]
l_ = ax_
while row[l_ - 1]: l_ -= 1
r_ = ax_
while row[r_ + 1]: r_ += 1
rmask[yl - 8:int(sy) + 40, l_:r_ + 1] = True
L["plaza"] = [int(axis), int((by0 + by1) / 2)]
# outside: road from the north gate to the north edge, same width as the plan's main lines
rmask[0:max(0, ny - 40), int(nx) - 75:int(nx) + 75] = True
soft = cv2.GaussianBlur(rmask.astype(np.float32), (0, 0), 1.2)[..., None]
ground = ground * (1 - soft) + MUD * soft
# dark rim + shade on the grass side, like the tiles' own edges
edge = cv2.dilate(rmask.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & ~rmask
shade = cv2.GaussianBlur((cv2.dilate(rmask.astype(np.uint8), np.ones((13, 13), np.uint8)) > 0).astype(np.float32), (0, 0), 3)
ground *= (1 - 0.18 * shade * (~rmask))[..., None]
ground[edge] = ground[edge] * 0.45 + np.array([70, 40, 20], np.float32) * 0.55

# ---------------------------------------------------------------- stone avenue (supplied floor tile), with a dark kerb
floor = np.array(Image.open(os.path.join(ROOT, "art/game/floor_atlas.png")).convert("RGB")).astype(np.float32)
fl = np.tile(floor, (WH // 128 + 2, WW // 128 + 2, 1))
ax = int((sx + nx) / 2)
y_top, y_bot = sy - 60, WH
x0, x1 = ax - AW, ax + AW
ground[y_top:y_bot, x0:x1] = fl[y_top:y_bot, x0 - ax % 128 + 128:x1 - ax % 128 + 128]
kerb = np.array([92, 78, 60], np.float32)
for xx in (x0, x0 + 1, x1 - 2, x1 - 1):
    ground[y_top:y_bot, xx] = kerb
for d in range(1, 9):                                 # soft grass shadow along the kerb
    f = 0.75 + 0.25 * d / 8
    ground[y_top:y_bot, x0 - d] *= f
    ground[y_top:y_bot, x1 - 1 + d] *= f

g8 = np.clip(ground, 0, 255).astype(np.uint8)
chunks = []
for cy in range(0, WH, CH):
    for cx in range(0, WW, CH):
        Image.fromarray(g8[cy:cy + CH, cx:cx + CH]).save(os.path.join(OUT, "g_%d_%d.webp" % (cx, cy)), quality=88, method=6)
        chunks.append([cx, cy])
L["ground_chunks"] = chunks
L["ground_chunk"] = CH
json.dump(L, open(os.path.join(ROOT, "data/layout.json"), "w"))

# minimap: real ground (downscaled) + walls on top
GW, GH = WW // 16, WH // 16
mm = Image.fromarray(g8).resize((GW * 2, GH * 2), Image.BOX).convert("RGBA")
wl = Image.new("RGBA", (WW, WH))
for c in L["chunks"]:
    if c.get("wall"):
        wl.alpha_composite(Image.open(os.path.join(ROOT, "art/game/walls/wall_%d_%d.png" % (c["x"], c["y"]))), (c["x"], c["y"]))
mm.alpha_composite(wl.resize((GW * 2, GH * 2), Image.LANCZOS))
mm.convert("RGB").save(os.path.join(ROOT, "art/game/minimap.png"))
Image.fromarray(g8).resize((WW // 6, WH // 6), Image.BOX).save("/tmp/gr/ground_preview.png")
print("ground chunks", len(chunks), "size MB", round(sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT)) / 1e6, 1))
