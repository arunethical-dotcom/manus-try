#!/usr/bin/env python3
"""Builds the palace wall ring from the wall kit (art/source/kit/*.png, pieces on magenta).

  python3 tools/build_kit.py

Layout (left half, mirrored about the gate axis): south wall = gatehouse + straight walls with towers,
SW corner = diagonal wall with towers, west wall = steep side runs, NW corner = diagonal, north wall = straight walls
with the open gate in the middle. A tower sits on every join. Pieces are normalised to one scale (by tower width /
merlon size) so a curtain wall is ~300 px tall; Kael stays 28 px.

Outputs: art/game/walls/{wall,depth,shadow}_<x>_<y>.png (512 px chunks), art/game/minimap.png, data/layout.json.
Draw order: each wall pixel knows the ground point it stands on (bottom of its column within its own piece);
Kael is drawn over the walls and the wall pixels in front of him are redrawn on top (shaders/wall_front.gdshader).
Collision: a band above the base line of every piece, gates open; the build fails if the ring is not sealed.
"""
import sys, os, json
import numpy as np, cv2
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIT = os.path.join(ROOT, "art/source/kit")
OUT = os.path.join(ROOT, "art/game/walls")
os.makedirs(OUT, exist_ok=True)
for f in os.listdir(OUT):
    os.remove(os.path.join(OUT, f))

TILE, CH, CELL, K = 16, 512, 8, 1
MX, MT, MB = 640, 560, 720           # world margins around the ring (px)
T = 48                               # footprint depth above a base line (px)
KX, KY, HCAP = 0.50, 0.20, 700       # shadow projection
N_SOUTH, N_SIDE = 3, 4               # straight walls per side of the south gate, side runs per side wall

# per piece: scale (native px -> game px) and anchors in native px
SC = {"wall_long": 0.46, "wall_tower": 0.577, "tower": 0.36, "gatehouse": 0.55, "gate_open": 0.54,
      "diag_towers": 0.605, "side_run": 0.577, "corner_l": 0.52}


def keyed(name):
    rgb = np.array(Image.open(os.path.join(KIT, name + ".png")).convert("RGB")).astype(int)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mag = (r - g > 60) & (b - g > 60) & (np.abs(r - b) < 90)
    a = (~mag).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(a)
    big = max(range(1, n), key=lambda i: st[i, 4])
    a = (lab == big).astype(np.uint8)
    a = cv2.morphologyEx(a, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    a = cv2.erode(a, np.ones((3, 3), np.uint8))
    x, y, w, h = cv2.boundingRect(a)
    out = np.dstack([rgb.astype(np.uint8), a * 255])[y:y + h, x:x + w].copy()
    # pull the magenta spill out of the fringe
    rim = (cv2.erode(a, np.ones((5, 5), np.uint8)) == 0)[y:y + h, x:x + w] & (out[..., 3] > 0)
    px = out[rim].astype(int)
    px[:, 0] = np.minimum(px[:, 0], px[:, 1] + 40); px[:, 2] = np.minimum(px[:, 2], px[:, 1] + 30)
    out[rim] = px.astype(np.uint8)
    return out


SRC = {n: keyed(n) for n in SC}
SCALED = {}


def scaled(n, mirror):
    k = (n, mirror)
    if k not in SCALED:
        im = SRC[n][:, ::-1] if mirror else SRC[n]
        s = SC[n]
        w, h = max(1, int(round(im.shape[1] * s))), max(1, int(round(im.shape[0] * s)))
        rgb = cv2.resize(im[..., :3], (w, h), interpolation=cv2.INTER_AREA)
        a = cv2.resize(im[..., 3], (w, h), interpolation=cv2.INTER_AREA)
        SCALED[k] = np.dstack([rgb, np.where(a > 127, 255, 0).astype(np.uint8)])
    return SCALED[k]


P = []   # placements: dict(n, m, x, y, img, gate)


def place(n, ax, ay, X, Y, mirror=False, crop_w=None, gate=None, crop_l=0, crop_b=None, z=None):
    """put native anchor (ax, ay) of piece n at game point (X, Y); returns game pos of native point fn(nx, ny)"""
    img = scaled(n, mirror)
    s = SC[n]
    W0 = SRC[n].shape[1]
    if mirror:
        ax = W0 - 1 - ax
    x0, y0 = X - ax * s, Y - ay * s
    if crop_w is not None:
        img = img[:, :int(crop_w)]
    if crop_b is not None:
        img = img[:int(crop_b * s)]
    cl = int(crop_l)
    if cl:
        img = img[:, cl:]
    P.append(dict(n=n, m=mirror, x=int(round(x0)) + cl, y=int(round(y0)), img=img, gate=gate, z=z))

    def at(nx, ny):
        if mirror:
            nx = W0 - 1 - nx
        return x0 + nx * s, y0 + ny * s
    return at


def tower(X, Y):
    place("tower", 208, 1199, X, Y + 18)


# ---------------------------------------------------------------- left half (x < 0), following the ring design
# south: gatehouse set back, an L-step down to the south wall on each side (corner_l), straight wall,
# a diagonal corner, steep side runs, two diagonals at the north-west, the north wall and an L-step forward to the
# open gate flanked by towers.
g = place("gatehouse", 636, 714, 0, 0, gate=("south", 530, 742, 640, 714))
xl, _ = g(0, 714)
c = place("corner_l", 1008, 664, xl + 10, 0)
tx, ty = c(150, 1007)
SOUTH_Y = ty - 16
xl = tx
for i in range(N_SOUTH):
    w = place("wall_long", 1592, 671, xl + 30, SOUTH_Y)
    xl, _ = w(0, 671)
# SW corner: diagonal rising up-left (mirrored); its high tower is dropped, the first side run's big tower
# stands on the corner instead (that run starts at the tower: its lower stub is cut off)
d = place("diag_towers", 120, 947, xl + 10, SOUTH_Y + 14, mirror=True, crop_l=240 * SC["diag_towers"])
cx, cy = d(1048, 600)
zc = d(120, 947)[1] + 1
# west wall: steep runs rising up-right
for i in range(N_SIDE):
    if i == 0:
        r = place("side_run", 95, 945, cx, cy, crop_b=930, z=zc + 2000)
    else:
        r = place("side_run", 180, 1290, cx, cy + 4)
    cx, cy = r(538, 150)
# NW: two diagonals rising up-right; the first one's high tower is cut, the second one's low tower stands there
d = place("diag_towers", 120, 947, cx, cy + 6, crop_w=945 * SC["diag_towers"])
jx, jy = d(1048, 600)
zz = d(120, 947)[1] + 1
d = place("diag_towers", 120, 947, jx, jy, z=zz)
cx, cy = d(1090, 605)
nx, ny = cx, cy
NORTH_Y = ny - 14
# north wall: L-step forward to the gate; the gate section sits further north
step = 1008 - 150
GATE_Y = NORTH_Y + 16 - (1007 - 664) * SC["corner_l"]
gate_l = -516 * SC["gate_open"]
cl_tower_x = gate_l - 10 - step * SC["corner_l"]
x = nx
while x < cl_tower_x - 4:
    wl = SRC["wall_long"].shape[1] * SC["wall_long"]
    cw = min(wl, cl_tower_x + 24 - x)
    place("wall_long", 0, 671, x, NORTH_Y, crop_w=cw)
    x += cw - 6
    if x < cl_tower_x - 40:
        tower(x, NORTH_Y)
place("corner_l", 1008, 664, gate_l - 10, GATE_Y)
place("gate_open", 516, 542, 0, GATE_Y, gate=("north", 430, 602, 330, 542))
tower(gate_l + 10, GATE_Y)

# mirror the left half (everything placed left of the axis) about x = 0
for p in list(P):
    if p["n"] in ("gatehouse", "gate_open"):
        continue
    q = dict(p)
    q["img"] = p["img"][:, ::-1]
    q["x"] = -(p["x"] + p["img"].shape[1])
    q["m"] = not p["m"]
    P.append(q)

# ---------------------------------------------------------------- world frame
x0 = min(p["x"] for p in P); x1 = max(p["x"] + p["img"].shape[1] for p in P)
y0 = min(p["y"] for p in P); y1 = max(p["y"] + p["img"].shape[0] for p in P)
WW = ((x1 - x0 + 2 * MX + TILE - 1) // TILE) * TILE
WH = ((y1 - y0 + MT + MB + TILE - 1) // TILE) * TILE
OX = (WW - (x1 - x0)) // 2 - x0
OY = MT - y0
print("ring px", x1 - x0, y1 - y0, " world", WW, WH, " tiles", WW // TILE, WH // TILE)

A = np.zeros((WH, WW), bool)
RGB = np.zeros((WH, WW, 3), np.uint8)
G = np.zeros((WH, WW), np.int32)
FP = np.zeros((WH // CELL + 1, WW // CELL + 1), bool)
gate_px = {}
# paint back to front: by the lowest point of each piece (towers come after the walls they sit on)
order = sorted(P, key=lambda p: (p["z"] if p.get("z") is not None else p["y"] + p["img"].shape[0], p["n"] == "tower"))
for p in order:
    im = p["img"]; h, w = im.shape[:2]
    X, Y = p["x"] + OX, p["y"] + OY
    a = im[..., 3] > 0
    # ground line per pixel: bottom of its vertical run inside this piece (small gaps closed)
    ac = cv2.morphologyEx(a.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((25, 1), np.uint8)).astype(bool) | a
    g_ = np.zeros((h, w), np.int32)
    runb = np.full(w, -1)
    nxt = np.zeros(w, bool)
    for yy in range(h - 1, -1, -1):
        runb = np.where(ac[yy], np.where(~nxt, yy, runb), -1)
        g_[yy] = runb
        nxt = ac[yy]
    sl = (slice(Y, Y + h), slice(X, X + w))
    A[sl] |= a
    RGB[sl][a] = im[..., :3][a]
    G[sl][a] = (g_ + Y)[a]
    # footprint: band above the lowest base of each 8 px column, joined to the neighbour columns
    gate = p["gate"]
    if gate:
        nm, ga0, ga1, gyt, gyb = gate
        s = SC[p["n"]]
        gx0, gx1 = X + ga0 * s, X + ga1 * s
        gate_px[nm] = (int(gx0), int(gx1), int(Y + gyt * s), int(Y + gyb * s))
    cols = []
    cnt = a.sum(axis=0)
    for c0 in range(0, w, CELL):
        sub = a[:, c0:c0 + CELL]
        rows = np.nonzero(sub.any(axis=1))[0]
        # skip thin edge columns (roof eaves, flag poles): they are not wall bases
        thin = cnt[c0:c0 + CELL].max() < 0.3 * cnt.max() if p["n"] in ("tower", "gatehouse", "gate_open", "wall_long") else False
        cols.append(int(rows.max()) + Y if len(rows) and not thin else None)
    for i, b in enumerate(cols):
        if b is None:
            continue
        cxw = X + i * CELL + CELL // 2
        if gate and gate_px[gate[0]][0] + 6 <= cxw <= gate_px[gate[0]][1] - 6:
            continue
        lo, hi = b - T, b
        for j in (i - 1, i + 1):
            if 0 <= j < len(cols) and cols[j] is not None:
                lo = min(lo, cols[j] - T // 2); hi = max(hi, cols[j])
        FP[max(0, lo) // CELL:hi // CELL + 1, (X + i * CELL) // CELL:(X + i * CELL + CELL) // CELL + 1] = True
print("pieces", len(P))
# keep the gate openings clear
for gx0, gx1, gyt, gyb in gate_px.values():
    FP[(gyt - 40) // CELL:(gyb + 60) // CELL + 1, (gx0 + 8) // CELL:(gx1 - 8) // CELL + 1] = False

# close hairline gaps where two pieces meet
FP = cv2.morphologyEx(FP.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)).astype(bool)
for gx0, gx1, gyt, gyb in gate_px.values():
    FP[(gyt - 40) // CELL:(gyb + 60) // CELL + 1, (gx0 + 8) // CELL:(gx1 - 8) // CELL + 1] = False

# ---------------------------------------------------------------- seal check (interior only reachable through the gates)
plug = FP.copy()
for gx0, gx1, gyt, gyb in gate_px.values():
    plug[(gyt - 40) // CELL:(gyb + 60) // CELL + 1, gx0 // CELL:gx1 // CELL + 1] = True
seed = ((gate_px["south"][3] + gate_px["north"][3]) // 2 // CELL, (WW // 2) // CELL)
n_, lab = cv2.connectedComponents((~plug).astype(np.uint8), connectivity=4)
inside = lab == lab[seed]
leak = inside[0].any() or inside[-1].any() or inside[:, 0].any() or inside[:, -1].any()
print("interior cells", int(inside.sum()), " leaks:", bool(leak))
if os.environ.get("DEBUG") or leak:
    dbg = np.zeros(FP.shape + (3,), np.uint8)
    am = cv2.resize(A.astype(np.uint8) * 255, (FP.shape[1], FP.shape[0]), interpolation=cv2.INTER_AREA)
    for k_ in range(3):
        dbg[..., k_] = am // 3
    dbg[inside] = (40, 90, 40)
    dbg[FP] = (255, 60, 60)
    Image.fromarray(dbg).save("/tmp/na/fp_debug.png")
    Image.fromarray(np.dstack([RGB, A.astype(np.uint8) * 255])).resize((WW // 5, WH // 5), Image.LANCZOS).save("/tmp/na/ring_preview.png")
if os.environ.get("DEBUG"):
    from PIL import ImageDraw
    big = Image.fromarray(np.dstack([RGB, A.astype(np.uint8) * 255])); big.save("/tmp/na/nobox.png")
    dd = ImageDraw.Draw(big)
    for i, p in enumerate(P):
        X, Y = p["x"] + OX, p["y"] + OY
        h, w = p["img"].shape[:2]
        dd.rectangle([X, Y, X + w, Y + h], outline=(255, 0, 0), width=4)
        dd.text((X + 6, Y + 6), "%d %s" % (i, p["n"]), fill=(255, 255, 0))
    big.save("/tmp/na/boxes.png")
if leak:
    sys.exit("ring not sealed")
G = np.where(A, G, 0)
Ac = A

# ---------------------------------------------------------------- shadows
yy, xx = np.nonzero(A)
gy = G[yy, xx]
h = np.minimum(np.maximum(0, gy - yy), HCAP).astype(np.float32)
tx = np.round(xx + KX * h).astype(int)
ty = np.round(gy + KY * h).astype(int)
ok = (tx >= 0) & (tx < WW) & (ty >= 0) & (ty < WH)
S = np.zeros((WH, WW), np.uint8)
S[ty[ok], tx[ok]] = 255
S = cv2.morphologyEx(S, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
S = cv2.GaussianBlur(S, (0, 0), 2.0)
# the shadow lies on the ground: not under the wall footprint itself
core = (S > 100)

# ---------------------------------------------------------------- write chunks
chunks = []
for cy in range(0, WH, CH):
    for cx in range(0, WW, CH):
        a = A[cy:cy + CH, cx:cx + CH]
        s = S[cy:cy + CH, cx:cx + CH]
        has_w, has_s = a.any(), (s > 8).any()
        if not (has_w or has_s):
            continue
        e = {"x": cx, "y": cy}
        if has_w:
            im = np.dstack([RGB[cy:cy + CH, cx:cx + CH], a.astype(np.uint8) * 255])
            Image.fromarray(im).save(os.path.join(OUT, "wall_%d_%d.png" % (cx, cy)))
            g = G[cy:cy + CH, cx:cx + CH]
            d = np.zeros(g.shape + (4,), np.uint8)
            d[..., 0] = (g >> 8) & 255
            d[..., 1] = g & 255
            d[..., 3] = 255
            Image.fromarray(d).save(os.path.join(OUT, "depth_%d_%d.png" % (cx, cy)))
            e["wall"] = True
        if has_s:
            sh = np.zeros(s.shape + (4,), np.uint8)
            sh[..., 0], sh[..., 1], sh[..., 2] = 38, 30, 78
            sh[..., 3] = (s.astype(np.float32) / 255 * 96).astype(np.uint8)
            Image.fromarray(sh).save(os.path.join(OUT, "shadow_%d_%d.png" % (cx, cy)))
            e["shadow"] = True
        chunks.append(e)
print("chunks", len(chunks))

# ---------------------------------------------------------------- collision rects (8 px cells, merged)
def run_merge(m):
    out, act = [], {}
    for y in range(m.shape[0] + 1):
        runs = {}
        if y < m.shape[0]:
            x = 0
            while x < m.shape[1]:
                if m[y, x]:
                    x0 = x
                    while x < m.shape[1] and m[y, x]:
                        x += 1
                    runs[(x0, x - x0)] = True
                else:
                    x += 1
        for k_ in list(act):
            if k_ not in runs:
                out.append(act.pop(k_))
        for k_ in runs:
            if k_ in act:
                act[k_][3] += 1
            else:
                act[k_] = [k_[0], y, k_[1], 1]
    return out

rects = [[r[0] * CELL, r[1] * CELL, r[2] * CELL, r[3] * CELL] for r in run_merge(FP)]
print("collision rects", len(rects))

# ---------------------------------------------------------------- ground grid: floor inside, earth outside
ins_px = np.repeat(np.repeat(inside, CELL, 0), CELL, 1)[:WH, :WW]
ins_px = cv2.dilate(ins_px.astype(np.uint8), np.ones((2 * T + 1, 2 * T + 1), np.uint8)).astype(bool)
GW, GH = WW // TILE, WH // TILE
tin = ins_px[:GH * TILE, :GW * TILE].reshape(GH, TILE, GW, TILE).mean(axis=(1, 3)) > 0.5
# paved apron through each gate
grid = np.where(tin, "F", "E").astype("<U1")
for gx0, gx1, gyt, gyb in gate_px.values():
    grid[max(0, (gyt - 3 * T) // TILE):min(GH, (gyb + 3 * T) // TILE), gx0 // TILE:(gx1 + TILE - 1) // TILE] = "F"
rows = ["".join(r) for r in grid]

# ---------------------------------------------------------------- minimap (1 px per tile)
ga = np.zeros((GH, GW, 3), np.uint8)
ga[grid == "F"] = (196, 178, 140)
ga[grid == "E"] = (110, 124, 78)
mm = Image.fromarray(ga).resize((GW * 2, GH * 2), Image.NEAREST)
wl = Image.fromarray(np.dstack([RGB, A.astype(np.uint8) * 255])).resize((GW * 2, GH * 2), Image.LANCZOS)
mm = mm.convert("RGBA"); mm.alpha_composite(wl)
mm.convert("RGB").save(os.path.join(ROOT, "art/game/minimap.png"))

sg = gate_px["south"]
layout = {
    "tile": TILE, "world": [WW, WH], "chunk": CH, "grid": rows, "chunks": chunks, "wall_rects": rects,
    "gates": {k: [(v[0] + v[1]) // 2, v[3]] for k, v in gate_px.items()},
    "spawn": [(sg[0] + sg[1]) // 2, sg[3] + 160],
    "inside": [seed[1] * CELL, seed[0] * CELL],
    "scale": K,
}
os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
json.dump(layout, open(os.path.join(ROOT, "data/layout.json"), "w"))
print("done:", GW, "x", GH, "tiles")
