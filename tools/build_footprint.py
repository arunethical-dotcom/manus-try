#!/usr/bin/env python3
"""Physically derived wall collision: the ground footprint of every wall.

  python3 tools/build_footprint.py [--apply]     (after build_walls.py / build_objects.py / build_levels.py)

The art is a 3/4 view from the south. A wall of height F standing on ground band [y_back, y_front] is drawn as its
top surface (parapet tops + walkway) between y_back - F and y_front - F, plus the visible south face below it down
to the foot (y_front). So, measured per column from the art:
  back_top  = top of the back parapet surface (silhouette top in the gaps between merlons)
  front_top = top of the front parapet surface (bottom of the walkway paving in the gaps between merlons)
  foot      = lowest pixel of the wall (follows the buttresses)
  F         = foot_panel - front_top            (height of the wall)
  footprint = ground rows [back_top + F, foot]  (depth = front_top - back_top = real wall thickness)
The back face gets the same buttress projections as the front face (mirrored), towers are not part of it (the
footprint is carried straight through behind each tower), gate arches stay open. East / west walls: the same
measurement done row by row (their walkway runs north-south), with F interpolated between the north and south walls.
Writes colliders.ground (sectioned polygons) with --apply, and preview images to /tmp/fp_*.png."""
import os, sys, json
import numpy as np, cv2
from PIL import Image
from scipy.ndimage import maximum_filter1d, minimum_filter1d, median_filter, uniform_filter1d
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_levels_polys as PP

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
L = json.load(open(os.path.join(ROOT, "data/layout.json")))
WW, WH = L["world"]
TOWERS, SEC = 22, 384
A = np.zeros((WH, WW), bool); R = np.zeros((WH, WW, 3), np.uint8); ID = np.zeros((WH, WW), np.uint8)
for c in L["chunks"]:
    if c.get("wall"):
        x, y = c["x"], c["y"]
        w = np.array(Image.open(os.path.join(ROOT, "art/source/walls/chunks_orig/wall_%d_%d.png" % (x, y))))
        d = np.array(Image.open(os.path.join(ROOT, "art/game/walls/depth_%d_%d.png" % (x, y))))[..., 2]
        h, ww = w.shape[:2]
        A[y:y + h, x:x + ww] = w[..., 3] > 0; R[y:y + h, x:x + ww] = w[..., :3]; ID[y:y + h, x:x + ww] = d
tower = (ID >= 1) & (ID <= TOWERS)
r, g, b = (R[..., i].astype(np.int16) for i in range(3))
mx_ = np.maximum(np.maximum(r, g), b); mn_ = np.minimum(np.minimum(r, g), b)
grey = A & ((mx_ - mn_) < 45) & (mx_ > 70) & (mx_ < 215)              # walkway paving
grey = cv2.morphologyEx(grey.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)).astype(bool)
del r, g, b, mx_, mn_
wall = A & ~tower
xs_all = np.nonzero(A.any(0))[0]; X0, X1 = int(xs_all.min()), int(xs_all.max()); RW = X1 - X0
ys_all = np.nonzero(A.any(1))[0]; YMID = int((ys_all.min() + ys_all.max()) // 2)
SIDE = 0.13
FP = np.zeros((WH, WW), bool)
meas = {}

def smooth_profile(v, ok, w):
    xi = np.arange(len(v))
    if ok.sum() < 5:
        return None
    v = np.interp(xi, xi[ok], v[ok])
    return v


# ---------------------------------------------------------------- north and south walls, column by column
for half, (ya, yb) in (("north", (0, YMID)), ("south", (YMID, WH))):
    xa, xb = int(X0 + SIDE * RW), int(X1 - SIDE * RW)
    n = xb - xa
    top = np.full(n, np.nan); gbot = np.full(n, np.nan); foot = np.full(n, np.nan)
    for i, x in enumerate(range(xa, xb)):
        col = wall[ya:yb, x]
        rr = np.nonzero(col)[0]
        if len(rr) < 40:
            continue
        t, f = rr.min() + ya, rr.max() + ya
        gr = np.nonzero(grey[t:t + 420, x])[0]
        if len(gr) < 15:
            continue
        # the walkway: first grey run below the top
        runs = np.split(gr, np.nonzero(np.diff(gr) > 6)[0] + 1)
        run = max(runs[:2], key=len)
        top[i], gbot[i], foot[i] = t, t + run.max(), f
    ok = ~np.isnan(top)
    if ok.sum() < 50:
        continue
    xi = np.arange(n)
    top = np.interp(xi, xi[ok], top[ok]); gbot = np.interp(xi, xi[ok], gbot[ok]); foot = np.interp(xi, xi[ok], foot[ok])
    P = 61                                                       # > one merlon period
    back_top = median_filter(maximum_filter1d(top, P), 41, mode="nearest")      # gap level of the back parapet
    front_top = median_filter(maximum_filter1d(gbot, P), 41, mode="nearest")    # gap level of the front parapet
    panel = median_filter(foot, 161, mode="nearest")                            # foot of the panels
    F = median_filter(panel - front_top, 161, mode="nearest")                   # wall height
    proj = np.clip(foot - panel, 0, 60)                                         # buttresses stick out at the foot
    proj = np.where(proj > 5, proj, 0)
    back_g = back_top + F                                                       # back face on the ground
    for i, x in enumerate(range(xa, xb)):
        if not ok[i] and not ok[max(0, i - 40):i + 40].any():
            continue
        y0 = int(round(back_g[i] - proj[i])); y1 = int(round(foot[i]))
        if y1 - y0 < 20 or y1 - y0 > 400:
            continue
        FP[y0:y1 + 1, x] = True
    meas[half] = dict(F=float(np.median(F[ok])), depth=float(np.median((front_top - back_top)[ok])))

# ---------------------------------------------------------------- east and west walls, row by row
Fn, Fs = meas["north"]["F"], meas["south"]["F"]
yN, yS = ys_all.min() + 300, ys_all.max() - 100
for side, (xa, xb) in (("west", (X0, int(X0 + SIDE * RW) + 60)), ("east", (int(X1 - SIDE * RW) - 60, X1 + 1))):
    for y in range(int(ys_all.min()), int(ys_all.max())):
        gr = np.nonzero(grey[y, xa:xb])[0]
        if len(gr) < 15:
            continue
        runs = np.split(gr, np.nonzero(np.diff(gr) > 6)[0] + 1)
        run = max(runs, key=len)
        if len(run) < 15:
            continue
        gl, grr = xa + run.min(), xa + run.max()
        # parapets: from the walkway to the silhouette on each side (capped at the walkway width)
        wl = np.nonzero(wall[y, max(0, gl - 120):gl])[0]
        wr = np.nonzero(wall[y, grr:grr + 120])[0]
        pl = (gl - (max(0, gl - 120) + wl.min())) if len(wl) else 0
        pr = (wr.max()) if len(wr) else 0
        pl = min(pl, 70); pr = min(pr, 70)
        Fy = Fn + (Fs - Fn) * np.clip((y - yN) / max(1, yS - yN), 0, 1)
        yg = int(round(y + Fy))
        if 0 <= yg < WH:
            FP[yg, gl - pl:grr + pr + 1] = True
    meas[side] = dict(F="%.0f..%.0f" % (Fn, Fs))
FP = cv2.morphologyEx(FP.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8)).astype(bool)
FP &= cv2.dilate(A.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)      # the ground under the wall only
FP &= ~tower
el = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
FP = cv2.morphologyEx(cv2.morphologyEx(FP.astype(np.uint8), cv2.MORPH_OPEN, el), cv2.MORPH_CLOSE, el).astype(bool)
n_, lab_, st_, _ = cv2.connectedComponentsWithStats(FP.astype(np.uint8), connectivity=8)
FP = np.isin(lab_, [i for i in range(1, n_) if st_[i, 4] >= 3000])
for gpt in L["gates"].values():
    gx, gy = gpt
    FP[gy - 700:gy + 60, gx - 62:gx + 63] = False
print("measured:", json.dumps(meas))

# ---------------------------------------------------------------- carry the footprint behind each tower (join pieces)
import build_barrier_join as BJ
FP = BJ.join(FP, L, WW, WH)

# ---------------------------------------------------------------- seal check
K = 4
bk = cv2.dilate(FP.astype(np.uint8), np.ones((7, 13), np.uint8))[::K, ::K].astype(bool)
nL, labL = cv2.connectedComponents((~bk).astype(np.uint8), connectivity=4)
Pt = lambda q: (q[1] // K, q[0] // K)
gates_open = labL[Pt(L["spawn"])] == labL[Pt(L["inside"])]
plug = bk.copy()
for gpt in L["gates"].values():
    gx, gy = gpt[0] // K, gpt[1] // K
    plug[gy - 130:gy + 14, gx - 30:gx + 31] = True
nP, labP = cv2.connectedComponents((~plug).astype(np.uint8), connectivity=4)
sealed = labP[Pt(L["inside"])] != labP[2, 2]
print("gates open:", bool(gates_open), " sealed:", bool(sealed))
np.save("/tmp/fp_FP.npy", FP)

# preview: footprint (where the feet are stopped) as an outline on the ground + filled lightly
full = Image.new("RGBA", (WW, WH), (90, 150, 60, 255))
for c in L["chunks"]:
    if c.get("wall"):
        full.alpha_composite(Image.open(os.path.join(ROOT, "art/game/walls/wall_%d_%d.png" % (c["x"], c["y"]))), (c["x"], c["y"]))
ov = np.zeros((WH, WW, 4), np.uint8); ov[FP] = (255, 0, 0, 110)
edge = FP & ~cv2.erode(FP.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
ov[edge] = (255, 255, 0, 255)
full.alpha_composite(Image.fromarray(ov))
full.crop((560, 560, 7330, 4430)).resize((6770 // 4, 3870 // 4)).convert("RGB").save("/tmp/fp_full.png")
full.crop((2300, 3650, 3700, 4450)).convert("RGB").save("/tmp/fp_south.png")
full.crop((2000, 850, 3500, 1550)).convert("RGB").save("/tmp/fp_north.png")
full.crop((600, 1400, 1500, 3300)).resize((450, 950)).convert("RGB").save("/tmp/fp_west.png")

if "--apply" in sys.argv:
    if not (gates_open and sealed):
        raise SystemExit("not applied: checks failed")
    secids = ID.copy()
    for _ in range(8):
        secids = np.where(secids == 0, cv2.dilate(secids, np.ones((9, 9), np.uint8)), secids)
    ground = PP.section_polys(FP, secids, "ground", SEC, TOWERS)
    L["colliders"]["ground"] = ground
    gm = np.zeros((WH, WW), np.uint8)
    for p in ground:
        cv2.fillPoly(gm, [np.array(p["poly"], np.int32)], 1)
    bk2 = cv2.dilate(gm, np.ones((15, 21), np.uint8))
    for a in L["access"]:
        x, y = a["ground"]
        d = -1 if a["gate"] == "south" else 1
        while bk2[y, x] or bk2[y - 6, x]:
            y += d * 4
        a["ground"] = [x, y + (d * 16 if (y, x) != tuple(a["ground"][::-1]) else 0)]
    L["footprint"] = meas
    json.dump(L, open(os.path.join(ROOT, "data/layout.json"), "w"))
    print("applied:", len(ground), "sections")
