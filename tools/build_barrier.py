#!/usr/bin/env python3
"""Ground barrier = the lower band of the wall faces (ground line up to LEVEL px above it): the recessed panels and
the buttresses, as in the reference drawing (pink panels / red buttresses). Replaces colliders.ground in
data/layout.json with sectioned polygons; gate arches stay open; fails if the ring leaks.

  python3 tools/build_barrier.py      (after build_levels.py)"""
import os, json, sys
import numpy as np, cv2
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
L = json.load(open(os.path.join(ROOT, "data/layout.json")))
WW, WH = L["world"]
LEVEL, TOWERS, SEC = 165, 22, 384
A = np.zeros((WH, WW), bool); ID = np.zeros((WH, WW), np.uint8); RGB = np.zeros((WH, WW, 3), np.uint8)
for c in L["chunks"]:
    if not c.get("wall"):
        continue
    x, y = c["x"], c["y"]
    w = np.array(Image.open(os.path.join(ROOT, "art/source/walls/chunks_orig/wall_%d_%d.png" % (x, y))))
    d = np.array(Image.open(os.path.join(ROOT, "art/game/walls/depth_%d_%d.png" % (x, y))))
    h, ww = w.shape[:2]
    A[y:y + h, x:x + ww] = w[..., 3] > 0; ID[y:y + h, x:x + ww] = d[..., 2]; RGB[y:y + h, x:x + ww] = w[..., :3]
# ground line per column (arches / windows / crenel gaps closed so each column runs to its real base)
Sx = cv2.morphologyEx(A.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((420, 1), np.uint8)).astype(bool) | A
for g in L["gates"].values():
    gx, gy = g
    Sx[gy - 700:gy + 20, gx - 200:gx + 200] |= cv2.morphologyEx(A[gy - 700:gy + 20, gx - 200:gx + 200].astype(np.uint8),
                                                               cv2.MORPH_CLOSE, np.ones((1, 401), np.uint8)).astype(bool)
runb = np.zeros((WH, WW), np.int32); nxt = np.full(WW, -1, np.int32)
for yy in range(WH - 1, -1, -1):
    nxt = np.where(Sx[yy], np.where(nxt >= 0, nxt, yy), -1); runb[yy] = nxt
hgt = runb - np.arange(WH, dtype=np.int32)[:, None]
del runb
band = A & (hgt >= 0) & (hgt <= LEVEL)
tower = (ID >= 1) & (ID <= TOWERS)
# the barrier is exactly the strip painted in the reference (art/source/walls/barrier_reference.png, pink panels / red
# buttresses), registered onto the art (scale REF_S, offset REF_O), then snapped to the full-resolution art pixels
REF = os.path.join(ROOT, "art/source/walls/barrier_reference.png")
REF_S, REF_O = 4.09, (134, 131)
r = np.array(Image.open(REF).convert("RGB")).astype(np.int16)
pink = (r[..., 0] > 180) & (r[..., 2] > 120) & (r[..., 1] < 120)
red = (r[..., 0] > 170) & (r[..., 1] < 110) & (r[..., 2] < 110)
Mr = (pink | red).astype(np.float32)
Xg = (np.arange(WW, dtype=np.float32) / REF_S - REF_O[0])
Yg = (np.arange(WH, dtype=np.float32) / REF_S - REF_O[1])
B = np.zeros((WH, WW), bool)
for y0_ in range(0, WH, 512):                     # in strips (memory)
    ys_ = slice(y0_, min(WH, y0_ + 512))
    U, V = np.meshgrid(Xg, Yg[ys_])
    B[ys_] = cv2.remap(Mr, U, V, cv2.INTER_LINEAR, borderValue=0) > 0.35
B = cv2.dilate(B.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)   # reference is ~4x coarser
B &= A                                             # snap to the art: its real silhouette
# reach the real foot of the wall: carry every barrier column down through the solid art below it
flag = np.zeros(WW, bool)
for yy in range(WH):
    flag = (flag & Sx[yy]) | B[yy]
    B[yy] = flag & A[yy]
B = cv2.morphologyEx(B.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)).astype(bool)
# the gatehouses are not painted in the reference: their piers get the lower-band barrier, only the arch stays open
for g in L["gates"].values():
    gx, gy = g
    reg = np.zeros((WH, WW), bool); reg[gy - 420:gy + 60, gx - 330:gx + 331] = True
    B |= reg & band
    B[gy - 420:gy + 60, gx - 62:gx + 63] = False

K = 4
def check(block):
    bk = cv2.dilate(block.astype(np.uint8), np.ones((7, 13), np.uint8))[::K, ::K].astype(bool)
    f = ~bk
    n, lab = cv2.connectedComponents(f.astype(np.uint8), connectivity=4)
    P = lambda q: (q[1] // K, q[0] // K)
    same = lab[P(L["spawn"])] == lab[P(L["inside"])] and lab[P(L["inside"])] != 0
    plug = bk.copy()
    for g in L["gates"].values():
        gx, gy = g[0] // K, g[1] // K
        plug[gy - 130:gy + 14, gx - 30:gx + 31] = True
    n2, lab2 = cv2.connectedComponents((~plug).astype(np.uint8), connectivity=4)
    return same, lab2[P(L["inside"])] != lab2[2, 2]

def bridge(B):
    """join the strip pieces along the wall line: nearest-neighbour links (shortest first, union-find), never across a
    gate, so the barrier becomes one band broken only at the two gates"""
    small = cv2.resize(B.astype(np.uint8), (WW // 8, WH // 8), interpolation=cv2.INTER_NEAREST)
    n, lab, st, _ = cv2.connectedComponentsWithStats(small, connectivity=8)
    comps = [i for i in range(1, n) if st[i, 4] >= 4]
    pts = {i: np.argwhere(lab == i)[:, ::-1] for i in comps}
    gates = [(g[0] // 8, g[1] // 8) for g in L["gates"].values()]
    pairs = []
    for ii, i in enumerate(comps):
        for j in comps[ii + 1:]:
            a_, b_ = pts[i], pts[j]
            if len(a_) > 400: a_ = a_[::len(a_) // 400]
            if len(b_) > 400: b_ = b_[::len(b_) // 400]
            d = np.sqrt(((a_[:, None, :] - b_[None, :, :]) ** 2).sum(-1))
            k = np.unravel_index(np.argmin(d), d.shape)
            if d[k] > 160:
                continue
            pa, pb = a_[k[0]], b_[k[1]]
            mid = (pa + pb) / 2
            if any(abs(mid[0] - gx) < 25 and abs(mid[1] - gy) < 70 for gx, gy in gates):
                continue
            pairs.append((float(d[k]), i, j, tuple(int(v) for v in pa), tuple(int(v) for v in pb)))
    pairs.sort()
    par = {i: i for i in comps}
    def f(i):
        while par[i] != i:
            par[i] = par[par[i]]; i = par[i]
        return i
    out = B.copy()
    for d, i, j, pa, pb in pairs:
        if f(i) == f(j):
            continue
        par[f(i)] = f(j)
        m = np.zeros((WH, WW), np.uint8)
        cv2.line(m, (pa[0] * 8 + 4, pa[1] * 8 + 4), (pb[0] * 8 + 4, pb[1] * 8 + 4), 1, 28)
        out |= m.astype(bool)
    return out


same, sealed = check(B)
print("strip only: gates open", same, " sealed", sealed)
if not sealed:
    B = bridge(B)                   # only where the reference leaves a gap the player could slip through
    same, sealed = check(B)
    print("strip joined along the wall line: gates open", same, " sealed", sealed)
used_towers = False
if not sealed and False:
    # where a tower interrupts the strip, carry the strip through the tower's base band
    B = B | (band & tower)
    B = cv2.morphologyEx(B.astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8)).astype(bool)
    for g in L["gates"].values():
        gx, gy = g
        B[gy - 200:gy + 40, gx - 60:gx + 61] = False
    used_towers = True
    same, sealed = check(B)
    print("strip + tower base bands: gates open", same, " sealed", sealed)
if not (same and sealed):
    S = 5
    v = np.full((WH // S, WW // S, 3), 255, np.uint8)
    bs = cv2.resize(B.astype(np.uint8), (WW // S, WH // S), interpolation=cv2.INTER_NEAREST) > 0
    am = cv2.resize(A.astype(np.uint8), (WW // S, WH // S), interpolation=cv2.INTER_NEAREST) > 0
    v[am] = (200, 200, 200); v[bs] = (235, 40, 200)
    bk = cv2.dilate(B.astype(np.uint8), np.ones((7, 13), np.uint8))[::4, ::4].astype(bool)
    plug = bk.copy()
    for g in L["gates"].values():
        gx, gy = g[0] // 4, g[1] // 4
        plug[gy - 130:gy + 14, gx - 30:gx + 31] = True
    n2, lab2 = cv2.connectedComponents((~plug).astype(np.uint8), connectivity=4)
    ins = lab2 == lab2[L["inside"][1] // 4, L["inside"][0] // 4]
    v[cv2.resize(ins.astype(np.uint8), (WW // S, WH // S), interpolation=cv2.INTER_NEAREST) > 0] = (120, 200, 120)
    Image.fromarray(v).save("/tmp/pics/barrier_fail.png")
    raise SystemExit("barrier check failed")

import build_levels_polys as P_
secids = ID.copy()
for _ in range(8):
    secids = np.where(secids == 0, cv2.dilate(secids, np.ones((9, 9), np.uint8)), secids)
ground = P_.section_polys(B, secids, "ground", SEC, TOWERS)
L["colliders"]["ground"] = ground
json.dump(L, open(os.path.join(ROOT, "data/layout.json"), "w"))
print("ground barrier sections:", len(ground), " towers in barrier:", used_towers)

# preview like the reference: pink panels, red buttresses
S = 5
v = np.full((WH // S, WW // S, 3), 255, np.uint8)
art = cv2.resize(np.where(A[..., None], RGB, 255).astype(np.uint8), (WW // S, WH // S), interpolation=cv2.INTER_AREA)
v = (art * 0.35 + 255 * 0.65).astype(np.uint8)
bs = cv2.resize(B.astype(np.uint8), (WW // S, WH // S), interpolation=cv2.INTER_NEAREST) > 0
v[bs] = (235, 40, 200)
Image.fromarray(v).save("/tmp/pics/barrier.png")
