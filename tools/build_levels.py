#!/usr/bin/env python3
"""Castle collision on two levels, as sectioned polygons (independent of the PNGs at runtime).

  python3 tools/build_levels.py      (after build_walls.py, build_collision.py, build_objects.py)

Level 0 - ground: one polygon set per section (each tower, each wall stretch) = the ground the stone stands on
          (3/4 art: footprint = silhouette eroded upwards by the wall height; towers capped to their base).
          Gate arches are open.
Level 1 - wall-walk: the paved battlement walkways (detected from the art) plus a passage through every tower the
          walkway runs into. Colliders = the parapet / drop-off band around that walkable area, cut into sections.
Access  - the art has no stairs, so access points sit at the four gate towers: press E there to climb / descend.

Writes into data/layout.json:
  colliders.ground / colliders.walk : [{"sec": name, "poly": [[x, y], ...]}, ...]
  access : [{"tower": id, "ground": [x, y], "walk": [x, y]}]
  walk_height : wall height used for depth sorting while on the wall-walk
and /tmp/pics/levels_*.png previews. Fails if a gate is blocked, the ring leaks, or the wall-walk is disconnected."""
import os, json
import numpy as np, cv2
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
L = json.load(open(os.path.join(ROOT, "data/layout.json")))
WW, WH = L["world"]
HWALL = 330
TOWERS = 22
TOWER_D = 0.42
SEC = 384                     # section size (px) for cutting long colliders into logical pieces
os.makedirs("/tmp/pics", exist_ok=True)

A = np.zeros((WH, WW), bool); RGB = np.zeros((WH, WW, 3), np.uint8); ID = np.zeros((WH, WW), np.uint8)
for c in L["chunks"]:
    if not c.get("wall"):
        continue
    x, y = c["x"], c["y"]
    w = np.array(Image.open(os.path.join(ROOT, "art/game/walls/wall_%d_%d.png" % (x, y))))
    d = np.array(Image.open(os.path.join(ROOT, "art/game/walls/depth_%d_%d.png" % (x, y))))
    h, ww = w.shape[:2]
    A[y:y + h, x:x + ww] = w[..., 3] > 0; RGB[y:y + h, x:x + ww] = w[..., :3]; ID[y:y + h, x:x + ww] = d[..., 2]

# ============================================================== level 0: ground footprint
S = cv2.morphologyEx(A.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((31, 1), np.uint8)).astype(bool)
S = cv2.morphologyEx(S.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((1, 9), np.uint8)).astype(bool)
run = np.zeros((WH, WW), np.int32); prev = np.zeros(WW, np.int32)
for yy in range(WH):
    prev = np.where(S[yy], prev + 1, 0); run[yy] = prev
FP = run >= HWALL
del run
tower_box = {}
for t in range(1, TOWERS + 1):
    m = ID == t
    if not m.any():
        continue
    ys, xs = np.nonzero(m)
    tw = xs.max() - xs.min()
    tower_box[t] = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
    for x in range(xs.min(), xs.max() + 1):
        col = np.nonzero(m[:, x])[0]
        if len(col) == 0:
            continue
        yb = col.max(); top = max(0, yb - int(TOWER_D * tw))
        FP[:top, x] &= ~m[:top, x]
        FP[top:yb + 1, x] |= S[top:yb + 1, x]
FP = cv2.morphologyEx(FP.astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
n, lab, st, _ = cv2.connectedComponentsWithStats(FP, connectivity=8)
FP = np.isin(lab, [i for i in range(1, n) if st[i, 4] >= 2000])
# fill holes (enclosed pockets are unreachable anyway, and give simple polygons)
ff = FP.astype(np.uint8).copy(); msk = np.zeros((WH + 2, WW + 2), np.uint8); cv2.floodFill(ff, msk, (0, 0), 1)
FP |= ~ff.astype(bool)

# ============================================================== level 1: wall-walk
r, g, b = (RGB[..., i].astype(np.int16) for i in range(3))
pav = A & (r - b < 80) & (g - b < 45) & (r < 240) & (r > 55)
del r, g, b
pav = cv2.morphologyEx(pav.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
pav = cv2.morphologyEx(pav, cv2.MORPH_OPEN, np.ones((13, 13), np.uint8))
n, lab, st, _ = cv2.connectedComponentsWithStats(pav)
WALK = np.isin(lab, [i for i in range(1, n) if st[i, 4] > 8000]).astype(np.uint8)
WALK = cv2.morphologyEx(WALK, cv2.MORPH_CLOSE, np.ones((31, 31), np.uint8))
ff = WALK.copy(); msk = np.zeros((WH + 2, WW + 2), np.uint8); cv2.floodFill(ff, msk, (0, 0), 1)
WALK = (WALK.astype(bool) | ~ff.astype(bool)) & A
WALK &= ~((ID >= 1) & (ID <= TOWERS))
# tower passages: every tower the walkway runs into gets a passage through its body at walkway level, joining the
# walkway pieces that touch it
rooms = []
ROOM_ID = np.zeros((WH, WW), np.uint8)
near = cv2.dilate(WALK.astype(np.uint8), np.ones((41, 41), np.uint8)).astype(bool)
for t, (x0, y0, x1, y1) in tower_box.items():
    m = ID == t
    touch = m & near
    if touch.sum() < 200:
        continue
    ys, xs = np.nonzero(touch)
    ty0, ty1 = int(np.percentile(ys, 10)), int(np.percentile(ys, 90))
    room = np.zeros((WH, WW), bool)
    room[max(0, ty0 - 20):ty1 + 21, x0:x1 + 1] = m[max(0, ty0 - 20):ty1 + 21, x0:x1 + 1]
    room = cv2.erode(room.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)
    WALK |= room
    rooms.append(t)
    ROOM_ID[room] = t
WALK = cv2.morphologyEx(WALK.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((21, 21), np.uint8)).astype(bool) & A
n, lab, st, _ = cv2.connectedComponentsWithStats(WALK.astype(np.uint8), connectivity=8)
big = [i for i in range(1, n) if st[i, 4] > 8000]
WALK = np.isin(lab, big)
print("wall-walk pieces after tower passages:", len(big), " tower passages:", len(rooms))
BAND = cv2.dilate(WALK.astype(np.uint8), np.ones((49, 49), np.uint8)).astype(bool) & ~WALK


# ============================================================== polygons, sectioned
from shapely.geometry import Polygon, MultiPolygon
from shapely.validation import make_valid


def clean_polys(pts):
    """valid, simple, non-degenerate polygons (Godot's convex decomposition rejects self-touching outlines)"""
    g = Polygon(pts)
    if not g.is_valid:
        g = make_valid(g)
    g = g.buffer(0)
    parts = list(g.geoms) if hasattr(g, "geoms") else [g]
    out = []
    for p in parts:
        if not isinstance(p, Polygon) or p.area < 40:
            continue
        p = Polygon(p.exterior).simplify(0.75, preserve_topology=True)
        if not p.is_valid or p.area < 40:
            continue
        c = list(p.exterior.coords)[:-1]
        # drop duplicate / collinear vertices
        cc = []
        for i, q in enumerate(c):
            a, b = c[i - 1], c[(i + 1) % len(c)]
            cr = (q[0] - a[0]) * (b[1] - a[1]) - (q[1] - a[1]) * (b[0] - a[0])
            if abs(cr) > 0.01 and q != a:
                cc.append([round(q[0], 1), round(q[1], 1)])
        if len(cc) >= 3 and Polygon(cc).is_valid:
            out.append(cc)
    return out


def section_polys(mask, sec_ids, kind):
    """cut mask into sections (by object id where given, then SEC grid), one simple polygon per connected piece"""
    out = []
    H8, W8 = mask.shape
    for gy in range(0, H8, SEC):
        for gx in range(0, W8, SEC):
            sub = mask[gy:gy + SEC, gx:gx + SEC]
            if not sub.any():
                continue
            ids = sec_ids[gy:gy + SEC, gx:gx + SEC]
            for sid in np.unique(ids[sub]):
                piece = (sub & (ids == sid)).astype(np.uint8)
                pad = np.pad(piece, 1)
                cs, hier = cv2.findContours(pad, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
                if hier is None:
                    continue
                for ci, cnt in enumerate(cs):
                    if hier[0][ci][3] != -1 or cv2.contourArea(cnt) < 40:
                        continue
                    if (hier[0][ci][2] != -1):          # has holes: fill them (holes are outside this level's reach)
                        pass
                    ap = cv2.approxPolyDP(cnt, 1.5, True).reshape(-1, 2)
                    if len(ap) < 3:
                        continue
                    pts = [(float(p[0]) - 1 + gx, float(p[1]) - 1 + gy) for p in ap]
                    name = ("tower_%d" % sid) if 1 <= sid <= TOWERS else ("wall_%d" % sid)
                    for k_, poly in enumerate(clean_polys(pts)):
                        out.append({"sec": "%s_%s_%d_%d_%d" % (kind, name, gx // SEC, gy // SEC, k_), "poly": poly})
    return out


# sections: towers keep their id; wall stretches by their id; band pixels take the nearest object's id
sec_ids = ID.copy()
missing = (sec_ids == 0)
if missing.any():
    dil = sec_ids.copy()
    for _ in range(8):
        dil = np.where(dil == 0, cv2.dilate(dil, np.ones((9, 9), np.uint8)), dil)
    sec_ids = dil
ground = section_polys(FP, sec_ids, "ground")
walk = section_polys(BAND, sec_ids, "walk")
print("ground colliders:", len(ground), " wall-walk colliders:", len(walk))


# ============================================================== verify with the actual polygons (rasterised)
def raster(polys):
    m = np.zeros((WH, WW), np.uint8)
    for p in polys:
        cv2.fillPoly(m, [np.array(p["poly"], np.int32)], 1)
    return m.astype(bool)


G0 = raster(ground); G1 = raster(walk)
K = 4                           # verify on a 4 px grid with Kael's 12x6 box
def free_grid(block, box=(12, 6)):
    bk = cv2.dilate(block.astype(np.uint8), np.ones((box[1] + 1, box[0] + 1), np.uint8))
    return ~bk[::K, ::K].astype(bool)


f0 = free_grid(G0)
n0, lab0 = cv2.connectedComponents(f0.astype(np.uint8), connectivity=4)
P = lambda q: (q[1] // K, q[0] // K)
sp, ins = L["spawn"], L["inside"]
same = lab0[P(sp)] == lab0[P(ins)] and lab0[P(sp)] != 0
plug = ~f0
for gname, gpt in L["gates"].items():
    gx, gy = gpt[0] // K, gpt[1] // K
    plug[gy - 140:gy + 24, gx - 40:gx + 41] = True
n0b, lab0b = cv2.connectedComponents((~plug).astype(np.uint8), connectivity=4)
sealed = lab0b[P(ins)] != lab0b[2, 2]
print("ground: gates connect inside and outside:", same, " sealed apart from the gates:", sealed)
# wall-walk: everything walkable must be one connected loop
f1 = free_grid(G1) & WALK[::K, ::K]
n1, lab1, st1, _ = cv2.connectedComponentsWithStats(f1.astype(np.uint8), connectivity=4)
sizes = sorted([int(st1[i, 4]) for i in range(1, n1)], reverse=True)
main1 = 1 + int(np.argmax(st1[1:, 4])) if n1 > 1 else 0
cover = st1[main1, 4] / max(1, f1.sum())
print("wall-walk regions:", sizes[:6], " main loop covers %.1f%% of the walkable top" % (100 * cover))

# ============================================================== access points (gate towers)
access = []
gate_towers = []
for gname, gpt in L["gates"].items():
    cand = sorted(tower_box.items(), key=lambda kv: abs((kv[1][0] + kv[1][2]) / 2 - gpt[0]) + abs(kv[1][3] - gpt[1]))
    gate_towers += [(gname, cand[0][0]), (gname, cand[1][0])]
for gname, t in gate_towers:
    x0, y0, x1, y1 = tower_box[t]
    cx = (x0 + x1) // 2
    m = ID == t
    # ground spot: the inner side of the tower base (north of the south gate towers, south of the north gate towers)
    col = np.nonzero(G0[:, cx])[0]
    if gname == "south":
        top = col[(col > y0) & (col < y1 + 80)].min()
        gy_ = top - 18
        while gy_ > 0 and not f0[gy_ // K, cx // K]:
            gy_ -= 4
    else:
        bot = col[(col > y0) & (col < y1 + 80)].max()
        gy_ = bot + 18
        while gy_ < WH - 1 and not f0[gy_ // K, cx // K]:
            gy_ += 4
    # wall-walk spot: the walkable point of the main loop closest to the tower centre
    ys, xs = np.nonzero((lab1 == main1))
    d2 = (xs * K - cx) ** 2 + (ys * K - (y0 + y1) // 2) ** 2
    k = int(np.argmin(d2))
    access.append({"tower": int(t), "gate": gname, "ground": [int(cx), int(gy_)], "walk": [int(xs[k] * K), int(ys[k] * K)]})
print("access points:", [(a["gate"], a["tower"]) for a in access])

ok = same and sealed and cover > 0.97 and len(access) == 4
rm = np.zeros((WH // 2, WW // 2, 4), np.uint8); rm[..., 0] = ROOM_ID[::2, ::2][:WH // 2, :WW // 2]; rm[..., 3] = 255
Image.fromarray(rm).save(os.path.join(ROOT, "data/roommap.bin"), format="PNG")
L["colliders"] = {"ground": ground, "walk": walk}
L["access"] = access
L["walk_height"] = HWALL
L["wall_rects"] = []
json.dump(L, open(os.path.join(ROOT, "data/layout.json"), "w"))

# previews
Sx = 5
bg = Image.new("RGBA", (WW // Sx, WH // Sx), (40, 80, 40, 255))
bg.alpha_composite(Image.fromarray(np.dstack([RGB, A.astype(np.uint8) * 255])).resize((WW // Sx, WH // Sx)))
ov = np.zeros((WH // Sx, WW // Sx, 4), np.uint8)
sm = lambda m: cv2.resize(m.astype(np.uint8), (WW // Sx, WH // Sx), interpolation=cv2.INTER_NEAREST) > 0
ov[sm(WALK)] = (0, 140, 255, 120)
ov[sm(G1)] = (255, 220, 0, 150)
ov[sm(G0)] = (255, 0, 0, 160)
bg.alpha_composite(Image.fromarray(ov))
from PIL import ImageDraw
dr = ImageDraw.Draw(bg)
for a in access:
    for k_, col_ in (("ground", (255, 255, 255)), ("walk", (0, 255, 255))):
        x_, y_ = a[k_][0] // Sx, a[k_][1] // Sx
        dr.ellipse([x_ - 5, y_ - 5, x_ + 5, y_ + 5], outline=col_, width=2)
bg.save("/tmp/pics/levels_all.png")
if not ok:
    raise SystemExit("level checks failed")
print("ok")
