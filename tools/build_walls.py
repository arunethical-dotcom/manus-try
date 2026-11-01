#!/usr/bin/env python3
"""Builds the palace wall ring for Godot from the overall wall design.

  python3 tools/build_walls.py <ring_design.png> <ring_design_x4.png>

ring_design_x4.png is the design upscaled 4x (tools/upscale/esrgan_np.py, Real-ESRGAN anime 6B run in numpy).
Scale: 1 design px = K game px. Kael stays 28 px tall; only the walls are big.

Outputs
  art/game/walls/wall_<cx>_<cy>.png     wall art in 512 px chunks (only chunks that contain wall)
  art/game/walls/depth_<cx>_<cy>.png    per-pixel ground line (y of the point on the ground under that pixel, 16 bit in R,G)
  art/game/walls/shadow_<cx>_<cy>.png   baked shadow (one light from the upper-left)
  art/game/minimap.png, data/layout.json (grid, collision rects, chunks, gates, spawn)
Draw order: Kael is drawn over the walls, then the wall pixels whose ground line is south of Kael's feet are drawn
again on top of him (shader). Collision = the wall footprint on the ground (a band above each wall base line).
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, cv2
from PIL import Image
from keybg import key

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "art/game/walls")
os.makedirs(OUT, exist_ok=True)
for f in os.listdir(OUT):
    os.remove(os.path.join(OUT, f))

TILE, K, CH = 16, 4, 512
MX, MT, MB = 640, 640, 800          # world margins (px) around the ring: sides, top, bottom
T = 64                               # footprint depth of a wall above its base line (px)
HW, TB = 200, 112                    # wall height above its inner base, and footprint thickness of the inner band (px)
KX, KY, HCAP = 0.50, 0.20, 700       # shadow projection

# gate openings in design px: (x0, x1, y_top_of_opening, y_base)
GATES_D = {"south": (807, 865, 770, 792), "north": (833, 859, 80, 100)}

src = np.array(Image.open(sys.argv[1]).convert("RGB"))
rgba, _ = key(src)
ys, xs = np.nonzero(rgba[..., 3])
bx0, by0, bx1, by1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
up = np.array(Image.open(sys.argv[2]).convert("RGB"))[by0 * K:by1 * K, bx0 * K:bx1 * K]
a_small = rgba[by0:by1, bx0:bx1, 3].astype(np.float32)
alpha = cv2.resize(a_small, (up.shape[1], up.shape[0]), interpolation=cv2.INTER_CUBIC) > 127
alpha = cv2.erode(alpha.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)

RW, RH = up.shape[1], up.shape[0]
WW = ((RW + 2 * MX + TILE - 1) // TILE) * TILE
WH = ((RH + MT + MB + TILE - 1) // TILE) * TILE
OX, OY = (WW - RW) // 2, MT
print("ring px", RW, RH, " world", WW, WH, " tiles", WW // TILE, WH // TILE)

def d2w(x, y):
    return (x - bx0) * K + OX, (y - by0) * K + OY

# full-world wall layer
A = np.zeros((WH, WW), bool)
A[OY:OY + RH, OX:OX + RW] = alpha
RGB = np.zeros((WH, WW, 3), np.uint8)
RGB[OY:OY + RH, OX:OX + RW] = up

# ---------------------------------------------------------------- base lines + footprint
# runs: vertical opaque stretches per column (small vertical gaps such as crenels closed)
Ac = cv2.morphologyEx(A.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((25, 1), np.uint8)).astype(bool) | A
below = np.zeros_like(Ac); below[:-1] = Ac[1:]
is_bottom = Ac & ~below
gate_px = {}
for g, (x0, x1, yt, yb) in GATES_D.items():
    gx0, gyt = d2w(x0, yt); gx1, gyb = d2w(x1, yb)
    gate_px[g] = (int(gx0), int(gx1), int(gyt), int(gyb))

CELL = 8
gw = WW // CELL
# per 8px column group: all base points (bottoms of runs), skipping tiny runs
bases = [[] for _ in range(gw)]
for c in range(gw):
    cols = is_bottom[:, c * CELL:(c + 1) * CELL].any(axis=1)
    for y in np.nonzero(cols)[0]:
        # run length above this bottom (in the group's middle column)
        xm = c * CELL + CELL // 2
        top = y
        while top > 0 and Ac[top - 1, xm]:
            top -= 1
        if y - top < 24:
            continue
        cx = c * CELL + CELL // 2
        in_gate = any(gx0 + 12 <= cx <= gx1 - 12 and gyt - 40 <= y <= gyb + 40 for gx0, gx1, gyt, gyb in gate_px.values())
        if in_gate:
            continue
        bases[c].append(int(y))
for c in range(gw):
    bases[c] = sorted(set(bases[c]))
    merged = []
    for y in bases[c]:
        if merged and y - merged[-1] < T:
            merged[-1] = y
        else:
            merged.append(y)
    bases[c] = merged

FP = np.zeros((WH // CELL + 1, gw), bool)
for c in range(gw):
    for y in bases[c]:
        lo, hi = y - T, y
        # connect to the nearest base of the neighbouring columns (steep walls)
        for nc in (c - 1, c + 1):
            if 0 <= nc < gw and bases[nc]:
                ny = min(bases[nc], key=lambda v: abs(v - y))
                if abs(ny - y) < 6 * T:
                    lo = min(lo, ny - T // 2)
                    hi = max(hi, ny)
        FP[max(0, lo) // CELL:hi // CELL + 1, c] = True
# edge bands: follow the inside edge (the hole in the art) and the outside edge of the ring all the way round, moved
# down to the ground by the part of the wall height that faces the viewer: 0 where the base is visible (north wall
# from inside, south wall from outside), HW where the top is the visible edge, HW/2 on the side walls.
cA = cv2.resize(A.astype(np.uint8), (gw, WH // CELL + 1), interpolation=cv2.INTER_AREA) > 0
nl, labh = cv2.connectedComponents((~cA).astype(np.uint8), connectivity=4)
hole = labh == labh[WH // 2 // CELL, gw // 2]
outer = labh == labh[0, 0]
disc = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31))

def edge_band(region):
    region = cv2.morphologyEx(region.astype(np.uint8), cv2.MORPH_CLOSE, disc).astype(bool)
    hb = cv2.GaussianBlur(region.astype(np.float32), (0, 0), 4)
    gy_, gx_ = np.gradient(hb)
    edge = region & (cv2.dilate((~region).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0)
    img = np.zeros(FP.shape, np.uint8)
    for cy, cx in zip(*np.nonzero(edge)):
        nx, ny = -gx_[cy, cx], -gy_[cy, cx]
        nn = np.hypot(nx, ny)
        if nn < 1e-6:
            continue
        nx, ny = nx / nn, ny / nn
        sh = HW * (1 + ny) / 2 / CELL
        p0 = (cx + 0.5, cy + 0.5 + sh)
        p1 = (p0[0] + nx * TB / CELL, p0[1] + ny * TB / CELL)
        px_, py_ = p0[0] * CELL, p0[1] * CELL
        if any(gx0 - 8 <= px_ <= gx1 + 8 and gyt - 700 <= py_ <= gyb + 160 for gx0, gx1, gyt, gyb in gate_px.values()):
            continue
        cv2.line(img, (int(p0[0]), int(p0[1])), (int(p1[0]), int(p1[1])), 1, 3)
    return img > 0

FP |= edge_band(hole)
FP |= edge_band(outer)
# drop stray specks (flag poles poking past the edges)
n_, lab_, st_, _ = cv2.connectedComponentsWithStats(FP.astype(np.uint8), connectivity=8)
FP = np.isin(lab_, [i for i in range(1, n_) if st_[i, cv2.CC_STAT_AREA] >= 200])
# gates: keep the jambs solid beside each opening
for gx0, gx1, gyt, gyb in gate_px.values():
    FP[(gyb - T) // CELL:gyb // CELL + 1, max(0, gx0 // CELL - 2):gx0 // CELL + 1] = True
    FP[(gyb - T) // CELL:gyb // CELL + 1, gx1 // CELL:gx1 // CELL + 3] = True
    for c in range(gx0 // CELL + 1, gx1 // CELL):
        FP[(gyb - T) // CELL:gyb // CELL + 1, c] = False

# ---------------------------------------------------------------- seal check (interior only reachable through the gates)
blocked = FP.copy()
plug = blocked.copy()
for gx0, gx1, gyt, gyb in gate_px.values():
    plug[(gyb - T - 16) // CELL:(gyb + 8) // CELL + 1, gx0 // CELL:gx1 // CELL + 1] = True
seed = (WH // 2 // CELL, WW // 2 // CELL)
ff = (~plug).astype(np.uint8)
n, lab = cv2.connectedComponents(ff, connectivity=4)
inside = lab == lab[seed]
leak = inside[0].any() or inside[-1].any() or inside[:, 0].any() or inside[:, -1].any()
print("interior cells", int(inside.sum()), " leaks:", bool(leak))
if os.environ.get("DEBUG") or leak:
    dbg = np.zeros(FP.shape + (3,), np.uint8)
    am = cv2.resize(A.astype(np.uint8) * 255, (FP.shape[1], FP.shape[0]), interpolation=cv2.INTER_AREA)
    dbg[..., 0] = am // 3; dbg[..., 1] = am // 3; dbg[..., 2] = am // 3
    dbg[inside] = (40, 90, 40)
    dbg[FP] = (255, 60, 60)
    Image.fromarray(dbg).save("/tmp/w2/fp_debug.png")
if leak:
    sys.exit("ring not sealed")

# ---------------------------------------------------------------- per-pixel ground line
FPpx = np.repeat(np.repeat(FP, CELL, 0), CELL, 1)[:WH, :WW] & Ac
BIG = 1 << 30
G = np.zeros((WH, WW), np.int32)
cur = np.full(WW, BIG, np.int64)
runb = np.full(WW, BIG, np.int64)
nxt = np.zeros(WW, bool)
for y in range(WH - 1, -1, -1):
    op = Ac[y]
    runb = np.where(op, np.where(~nxt, y, runb), BIG)
    cur = np.where(op, np.where(FPpx[y], y, cur), BIG)
    G[y] = np.where(op, np.minimum(cur, runb), 0)
    nxt = op
# a pixel stands on the first footprint row below it within its own run; without one, on the run bottom
G = np.where(A, G, 0)

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
