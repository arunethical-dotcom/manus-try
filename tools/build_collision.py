#!/usr/bin/env python3
"""Wall collision = only the ground each wall / tower stands on (its footprint), nothing else.

  python3 tools/build_collision.py      (after build_walls.py and build_objects.py)

The art is a 3/4 view: a wall of height h is drawn as its ground footprint pushed up by h. So a pixel is on the
footprint when the art is solid for the full wall height h above it (vertical erosion of the silhouette by h).
Towers (object ids 1..TOWERS) are taller, so their footprint is capped to the bottom part of the tower body.
Gate arches stay open automatically (the opening is transparent). Writes wall_rects in data/layout.json and fails if
the ring is not sealed except through the two gates."""
import os, json
import numpy as np, cv2
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
L = json.load(open(os.path.join(ROOT, "data/layout.json")))
WW, WH = L["world"]
HWALL = 330            # wall height above its footprint (px)
TOWER_D = 0.42         # tower footprint depth = TOWER_D * tower width
CELL = 8
A = np.zeros((WH, WW), bool); ID = np.zeros((WH, WW), np.uint8)
for c in L["chunks"]:
    if not c.get("wall"):
        continue
    x, y = c["x"], c["y"]
    a = np.array(Image.open(os.path.join(ROOT, "art/game/walls/wall_%d_%d.png" % (x, y))))[..., 3] > 0
    d = np.array(Image.open(os.path.join(ROOT, "art/game/walls/depth_%d_%d.png" % (x, y))))[..., 2]
    h, w = a.shape
    A[y:y + h, x:x + w] = a; ID[y:y + h, x:x + w] = d
# close small vertical gaps (between merlons, windows) so columns count as solid
S = cv2.morphologyEx(A.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((31, 1), np.uint8)).astype(bool)
S = cv2.morphologyEx(S.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((1, 9), np.uint8)).astype(bool)
# run length of solid pixels ending at each pixel (counted from above)
run = np.zeros((WH, WW), np.int32)
prev = np.zeros(WW, np.int32)
for yy in range(WH):
    prev = np.where(S[yy], prev + 1, 0)
    run[yy] = prev
FP = run >= HWALL
# towers: footprint only in the bottom part of the body
TOWERS = 22
for t in range(1, TOWERS + 1):
    m = ID == t
    if not m.any():
        continue
    ys, xs = np.nonzero(m)
    tw = xs.max() - xs.min()
    # bottom of the tower body per column
    for x in range(xs.min(), xs.max() + 1):
        col = np.nonzero(m[:, x])[0]
        if len(col) == 0:
            continue
        yb = col.max()
        FP[:max(0, yb - int(TOWER_D * tw)), x] &= ~m[:max(0, yb - int(TOWER_D * tw)), x]
        FP[yb - int(TOWER_D * tw):yb + 1, x] |= S[yb - int(TOWER_D * tw):yb + 1, x]
# ---- ground line per wall pixel, consistent with the footprint: a pixel stands on the ground HWALL below it, but never
# below the base of its own column (outer face pixels stand on the base); tower pixels stand on the tower base
runb = np.zeros((WH, WW), np.int32)
nxt = np.full(WW, -1, np.int32)
for yy in range(WH - 1, -1, -1):
    nxt = np.where(S[yy], np.where(nxt >= 0, nxt, yy), -1)
    runb[yy] = nxt
yy_ = np.arange(WH, dtype=np.int32)[:, None]
G = np.minimum(runb, yy_ + HWALL)
tw_ = (ID >= 1) & (ID <= TOWERS)
G[tw_] = runb[tw_]
G[~A] = 0
for c in L["chunks"]:
    if not c.get("wall"):
        continue
    x, y = c["x"], c["y"]
    p_ = os.path.join(ROOT, "art/game/walls/depth_%d_%d.png" % (x, y))
    d = np.array(Image.open(p_))
    h, w = d.shape[:2]
    g = G[y:y + h, x:x + w]
    d[..., 0] = (g >> 8) & 255
    d[..., 1] = g & 255
    Image.fromarray(d).save(p_)
del runb, G

# cells
gh, gw = WH // CELL, WW // CELL
C = FP[:gh * CELL, :gw * CELL].reshape(gh, CELL, gw, CELL).mean(axis=(1, 3)) > 0.35
C = cv2.morphologyEx(C.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8)).astype(bool)
n, lab, st, _ = cv2.connectedComponentsWithStats(C.astype(np.uint8), connectivity=8)
C = np.isin(lab, [i for i in range(1, n) if st[i, 4] >= 30])
# seal check: interior reachable from the outside only through the gates
free = (~C).astype(np.uint8)
n, lab = cv2.connectedComponents(free, connectivity=4)
ins = L["inside"]
inside_lab = lab[ins[1] // CELL, ins[0] // CELL]
outside_lab = lab[2, 2]
plug = C.copy()
for g in L["gates"].values():
    gx, gy = g[0] // CELL, g[1] // CELL
    plug[gy - 70:gy + 12, gx - 16:gx + 17] = True
n2, lab2 = cv2.connectedComponents((~plug).astype(np.uint8), connectivity=4)
sealed = lab2[ins[1] // CELL, ins[0] // CELL] != lab2[2, 2]
print("gates open:", inside_lab == outside_lab, " sealed without gates:", sealed)
if not sealed or inside_lab != outside_lab:
    dbg = np.zeros((gh, gw, 3), np.uint8); dbg[C] = (255, 60, 60); dbg[lab == inside_lab] = (40, 90, 40)
    Image.fromarray(dbg).save("/tmp/pics/col_dbg.png")
    raise SystemExit("collision check failed")


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
        for k in list(act):
            if k not in runs:
                out.append(act.pop(k))
        for k in runs:
            if k in act:
                act[k][3] += 1
            else:
                act[k] = [k[0], y, k[1], 1]
    return out


L["wall_rects"] = [[r[0] * CELL, r[1] * CELL, r[2] * CELL, r[3] * CELL] for r in run_merge(C)]
json.dump(L, open(os.path.join(ROOT, "data/layout.json"), "w"))
print("collision rects", len(L["wall_rects"]))
# overlay preview
S4 = 4
can = Image.new("RGBA", (WW // S4, WH // S4), (60, 80, 60, 255))
art = np.zeros((WH // S4, WW // S4, 4), np.uint8)
for c in L["chunks"]:
    if c.get("wall"):
        im = Image.open(os.path.join(ROOT, "art/game/walls/wall_%d_%d.png" % (c["x"], c["y"])))
        can.alpha_composite(im.resize((im.width // S4, im.height // S4)), (c["x"] // S4, c["y"] // S4))
ov = np.zeros((WH // S4, WW // S4, 4), np.uint8)
cs = np.kron(C, np.ones((2, 2), bool))[:WH // S4, :WW // S4]
ov[:cs.shape[0], :cs.shape[1]][cs] = (255, 0, 0, 150)
can.alpha_composite(Image.fromarray(ov)); can.save("/tmp/pics/col_all.png")
