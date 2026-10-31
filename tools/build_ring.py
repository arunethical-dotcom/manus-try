#!/usr/bin/env python3
"""Builds the palace OUTER WALL RING from the supplied wall pieces, plus ground, collision, shadows and minimap.

  python3 tools/build_ring.py <wall_pieces.png> <ring_reference.png>

* wall_pieces.png  : 5 pieces on magenta (NW step, NW diagonal, west chain, SW corner, gatehouse).
* ring_reference.png: the assembled ring they were cut from. Each piece is located on it by template matching,
  so the pieces keep their true relative positions (scale per piece = matched scale * F).
* Only the outer ring exists: no inner walls. The ring is stretched to palace size with straight wall tiles and
  towers cut from the same pieces (top / bottom runs) and the west/east chain is extended by tiling the
  diagonal wall band.
* Collision is generated from the art (never the sprite rectangle): base band under every wall/tower, full alpha
  under thin chain walls, open gate arch.
Outputs: art/game/ring_*.png, art/game/ring_sh_*.png, art/game/minimap.png, data/layout.json
"""
import json, os, sys, shutil
import numpy as np
from PIL import Image
import cv2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIECES, REF = sys.argv[1], sys.argv[2]
SRC = os.path.join(ROOT, "art/source")
OUT = os.path.join(ROOT, "art/game")
os.makedirs(SRC, exist_ok=True); os.makedirs(OUT, exist_ok=True); os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
for s_, d_ in ((PIECES, "wall_pieces.png"), (REF, "ring_reference.png")):
    if os.path.abspath(s_) != os.path.join(SRC, d_):
        shutil.copy(s_, os.path.join(SRC, d_))

TILE = 16
F = 2.6                 # ring-reference px -> game px
S_EXT = 560             # horizontal stretch (ring px per side)
DIAG_EXT = 1                # number of extra diagonal band tiles scaling (see below)
WALL_T = 36             # ground depth of a wall footprint (px)
KX, KY = 0.50, 0.20     # shadow direction (light upper-left)

# ---------------------------------------------------------------- 1. cut the 5 pieces out of the magenta sheet
sheet = np.array(Image.open(PIECES).convert("RGB")).astype(int)
mag = (abs(sheet[..., 0] - 255) < 70) & (sheet[..., 1] < 110) & (abs(sheet[..., 2] - 255) < 70)
alpha = cv2.morphologyEx((~mag).astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
n, lab, st, _ = cv2.connectedComponentsWithStats(cv2.dilate(alpha, np.ones((15, 15), np.uint8)))
boxes = sorted([tuple(st[k][:4]) for k in range(1, n) if st[k][4] > 20000], key=lambda b: (b[1] // 600, b[0]))
# order on the sheet: p_diag(NW), p_step(top), p_chain, p_corner, p_gate  (by position)
boxes = sorted(boxes, key=lambda b: b[0])
names = {}
for b in boxes:
    names[b[0]] = b
bx = sorted(boxes, key=lambda b: b[0])
# x positions: 93 step, 599 chain, 1903 corner, 2009 diag, 3263 gate
order = {93: "step", 599: "chain", 1903: "corner", 2009: "diag", 3263: "gate"}
pieces = {}
rgba = np.dstack([sheet.astype(np.uint8), (alpha * 255).astype(np.uint8)])
for (x, y, w, h) in boxes:
    pieces[order[x]] = rgba[y:y + h, x:x + w].copy()


def defringe(p, r=2):
    p = p.copy()
    a = cv2.erode((p[..., 3] > 0).astype(np.uint8), np.ones((2 * r + 1, 2 * r + 1), np.uint8))
    p[..., 3] = a * 255
    return p


# ---------------------------------------------------------------- 2. locate each piece on the reference (relative placement)
ref = np.array(Image.open(REF).convert("RGB"))
refg = cv2.cvtColor(ref, cv2.COLOR_RGB2GRAY)
match = {}
for k, p in pieces.items():
    best = None
    for s in np.arange(0.12, 0.40, 0.005):
        w, h = int(p.shape[1] * s), int(p.shape[0] * s)
        if w >= ref.shape[1] or h >= ref.shape[0] or w < 20:
            continue
        pr = cv2.resize(p, (w, h), interpolation=cv2.INTER_AREA)
        g = cv2.cvtColor(pr[..., :3], cv2.COLOR_RGB2GRAY)
        m = (pr[..., 3] > 128).astype(np.uint8) * 255
        r = np.nan_to_num(cv2.matchTemplate(refg, g, cv2.TM_CCOEFF_NORMED, mask=m))
        _, mx, _, loc = cv2.minMaxLoc(r)
        if best is None or mx > best[0]:
            best = (mx, s, loc)
    match[k] = best
    print("match", k, "score %.2f scale %.3f at %s" % best)

# ---------------------------------------------------------------- helpers
def scaled(p, k):
    w, h = max(1, round(p.shape[1] * k)), max(1, round(p.shape[0] * k))
    im = cv2.resize(p, (w, h), interpolation=cv2.INTER_AREA)
    im[..., 3] = np.where(im[..., 3] > 120, 255, 0)
    return im


def crop(p, x0, y0, x1, y1):
    return p[y0:y1, x0:x1].copy()


def hflip(p):
    return p[:, ::-1].copy()


sprites = []     # dicts: name, img(np RGBA), x, y
def add(name, img, x, y):
    sprites.append({"name": name, "img": img, "x": int(round(x)), "y": int(round(y))})


sc = {k: match[k][1] * F for k in pieces}          # source px -> game px per piece
P = {k: defringe(pieces[k], 3) for k in pieces}

# gate: left half (x < arch centre) mirrored -> perfectly symmetric gatehouse
GATE_CX = 1170
gl = crop(P["gate"], 0, 0, GATE_CX, P["gate"].shape[0])
gate_full = np.concatenate([gl, hflip(gl)], axis=1)
# step piece: stop at its right tower (drop the stub of the diagonal that continues off the sheet)
step = P["step"].copy(); step[:, 1305:, 3] = 0
# corner piece: drop its left tower (it is the same tower as the chain piece's last tower)
corner = P["corner"].copy()
chain = P["chain"]; diag = P["diag"]

# ring-px coordinates of the pieces on the reference
loc = {k: np.array(match[k][2], float) for k in pieces}
AXIS = loc["gate"][0] + GATE_CX * match["gate"][1]          # ring-px x of the gate axis
S = S_EXT
X0 = 700 - (loc["chain"][0] - S) * F
Y0 = 700 - loc["step"][1] * F
def gx(rx, shift=0.0): return (rx - shift) * F + X0
def gy(ry, shift=0.0): return (ry + shift) * F + Y0
XA = gx(AXIS)                                           # gate axis in game px
D = 0                                                    # extra vertical drop (diagonal extension, game px)

# left-arm placements (game px)
L_step = (gx(loc["step"][0], S), gy(loc["step"][1]))
L_diag = (gx(loc["diag"][0], S), gy(loc["diag"][1]))
L_chain = (gx(loc["chain"][0], S), gy(loc["chain"][1]))
L_corner = (gx(loc["corner"][0], S), gy(loc["corner"][1]))
L_gate = (XA - GATE_CX * sc["gate"], gy(loc["gate"][1]))

img_step, img_diag = scaled(step, sc["step"]), scaled(diag, sc["diag"])
img_chain, img_corner = scaled(chain, sc["chain"]), scaled(corner, sc["corner"])
img_gate = scaled(gate_full, sc["gate"])

# ---------------------------------------------------------------- straight wall tiles + towers from the same art
def best_period(tile, lo, hi):
    """seamless repeat length (px) of a horizontal wall strip"""
    g = cv2.cvtColor(tile[..., :3], cv2.COLOR_RGB2GRAY).astype(float)
    best = None
    for P_ in range(lo, hi):
        a, b = g[:, :-P_], g[:, P_:]
        d = np.abs(a - b).mean()
        if best is None or d < best[0]:
            best = (d, P_)
    return best[1]


# top run: flat part of the step piece (x 575..1105, crenel top .. base)
top_src = P["step"][318:512, 575:1105]
bot_src = P["gate"][598:806, 4:368]
for nm, src in (("top", top_src), ("bot", bot_src)):
    per = best_period(src, 60, min(260, src.shape[1] // 2))
    print("tile", nm, "period", per)
    nper = max(1, src.shape[1] // per)
    src = src[:, :per * nper]
    if nm == "top": top_src = src
    else: bot_src = src
TOP_K, BOT_K = sc["step"], sc["gate"]
tower_src = P["step"][0:530, 1118:1300]               # right tower of the step piece
TOWER_K = sc["step"]

# base lines (game px) of the straight runs, taken from the placed pieces
top_base = L_step[1] + 512 * sc["step"]
bot_base = L_gate[1] + 806 * sc["gate"]


def run(x0, x1, base_y, tile, k, tower, tk, spacing, tag, flip=False):
    """fill [x0,x1] with tiles (+ a tower every `spacing` px); returns list of placed items"""
    t_img = scaled(tile, k)
    tw = t_img.shape[1]
    tw_img = scaled(tower, tk)
    x = x0
    items = []
    since = 0
    while x < x1:
        if since >= spacing and x + tw_img.shape[1] < x1 - tw:
            items.append((tag + "_tower", tw_img, int(x), int(base_y - tw_img.shape[0] + 8 * tk)))
            x += tw_img.shape[1]
            since = 0
            continue
        w_ = int(min(tw, x1 - x))
        if w_ <= 0:
            break
        im = t_img[:, :w_]
        items.append((tag + "_tile", im, int(x), int(base_y - t_img.shape[0])))
        x += w_ - (3 if w_ == tw else 0)   # 3 px overlap hides the eroded tile edges
        since += w_
    return items


# ---------------------------------------------------------------- 3. assemble the left half
add("step", img_step, *L_step)
add("diag", img_diag, *L_diag)
add("chain", img_chain, *L_chain)
add("corner", img_corner, *L_corner)
add("gate", img_gate, *L_gate)
left_items = []
# gap between the NW diagonal piece (cut on the right) and the step piece (cut on the left): continue the diagonal wall
dk = sc["diag"]
BX0, BX1 = 792, 856
band = diag[:, BX0:BX1]                                 # wall right of the diagonal piece's last tower
ab = band[..., 3] > 0
def col_bottom(c, step):
    while not ab[:, c].any():
        c += step
    return np.nonzero(ab[:, c])[0].max(), c
(bb0, c0), (bb1, c1) = col_bottom(4, 1), col_bottom(band.shape[1] - 4, -1)
slope_dy = (bb1 - bb0) / max(1, (c1 - c0))                # source px per px (negative = rising)
diag_right = L_diag[0] + BX1 * dk
gap = L_step[0] - diag_right
print("NW gap px", gap, "slope", slope_dy)
bimg = scaled(band, dk)
nt = int(np.ceil(max(0, gap + 6) / bimg.shape[1]))
for i in range(nt):
    left_items.append(("diagfill", bimg, int(diag_right + i * (bimg.shape[1] - 3)),
                       int(L_diag[1] + slope_dy * bimg.shape[1] * (i + 1))))
# top run: from the step piece's right tower to the axis
step_right = L_step[0] + 1305 * sc["step"]
left_items += run(step_right, XA, top_base, top_src, TOP_K, tower_src, TOWER_K, 900, "top")
# bottom run: from the corner piece's right end to the gate piece
corner_right = L_corner[0] + corner.shape[1] * sc["corner"]
left_items += run(corner_right - 2, L_gate[0] + 2, bot_base, bot_src, BOT_K, tower_src, TOWER_K, 900, "bot")
print("runs", step_right, XA, corner_right, L_gate[0], len(left_items))
for i, (nm, im, x, y) in enumerate(left_items):
    add("%s_%d" % (nm, i), im, x, y)

n_left = len(sprites)
# mirror: right half = every sprite except the (already symmetric) gate, flipped about the axis
mirrored = []
for s in list(sprites):
    if s["name"] == "gate":
        continue
    im = s["img"][:, ::-1].copy()
    mx = 2 * XA - s["x"] - im.shape[1]
    mirrored.append({"name": s["name"] + "_R", "img": im, "x": int(round(mx)), "y": s["y"]})
sprites += mirrored

# ---------------------------------------------------------------- 4. world size, bridge, ground
all_x1 = max(s["x"] + s["img"].shape[1] for s in sprites)
WORLD_W = int(all_x1 + 700) // TILE * TILE
gate_foot = L_gate[1] + 806 * sc["gate"]
BRIDGE_LEN = 900
QUAY_Y = int(gate_foot + BRIDGE_LEN)
WORLD_H = (QUAY_Y + 600) // TILE * TILE
GW, GH = WORLD_W // TILE, WORLD_H // TILE
print("world", WORLD_W, WORLD_H, "tiles", GW, GH, "sprites", len(sprites))

# ---------------------------------------------------------------- 5. per-sprite strips (y-sort feet), collision rects, shadows
def opaque_bottom(a, x0, x1):
    cols = a[:, x0:x1, 3] > 0
    rows = np.nonzero(cols.any(axis=1))[0]
    return int(rows.max()) if len(rows) else -1


placed = []
rects = []
CELL = 8
for s in sprites:
    im = s["img"]; h, w = im.shape[:2]
    Image.fromarray(im).save(os.path.join(OUT, "ring_%s.png" % s["name"]))
    strips = []
    for x0 in range(0, w, 32):
        x1 = min(w, x0 + 32)
        yb = opaque_bottom(im, x0, x1)
        strips.append(yb if yb >= 0 else 0)
    # collision
    a = im[..., 3] > 0
    nm = s["name"]
    is_gate = nm.startswith("gate")
    # thin chain walls: full alpha. detect thin structures = alpha minus its opening with a big disc
    k = max(9, int(0.0))
    thin = np.zeros_like(a)
    if True:
        big = cv2.morphologyEx(a.astype(np.uint8), cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (47, 47))).astype(bool)
        thin = a & ~big
        nlab, labm, stt, _ = cv2.connectedComponentsWithStats(thin.astype(np.uint8))
        keep = np.zeros_like(thin)
        for i in range(1, nlab):
            if stt[i, 4] > 2500 and stt[i, 3] > 70:
                keep |= labm == i
        thin = keep
    # footprint: the WALL_T px above the lowest opaque pixel of every 8-px column. Sprites that stack several objects
    # vertically (the west chain) are handled per object: towers = connected components of the "fat" part of the alpha,
    # thin walls = full alpha.
    foot = np.zeros_like(a)
    ncol = (w + CELL - 1) // CELL
    def band_cols(mask):
        lo = np.full(ncol, -1); hi = np.full(ncol, -1)
        for ci in range(ncol):
            col = mask[:, ci * CELL:(ci + 1) * CELL]
            ys_ = np.nonzero(col.any(axis=1))[0]
            if len(ys_):
                hi[ci] = ys_.max(); lo[ci] = max(0, hi[ci] - WALL_T)
        lo2, hi2 = lo.copy(), hi.copy()
        for ci in range(ncol):            # connect neighbouring columns whose base lines differ (wall meets tower)
            for nb_ in (ci - 1, ci + 1):
                if 0 <= nb_ < ncol and hi[ci] >= 0 and hi[nb_] >= 0:
                    lo2[ci] = min(lo2[ci], min(hi[nb_], hi[ci]))
                    hi2[ci] = max(hi2[ci], max(lo[nb_], lo[ci]))
        for ci in range(ncol):
            if hi2[ci] >= 0:
                foot[lo2[ci]:hi2[ci] + 1, ci * CELL:(ci + 1) * CELL] = True
    big = cv2.morphologyEx(a.astype(np.uint8), cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (47, 47))).astype(bool)
    nb, lb = cv2.connectedComponents(big.astype(np.uint8))
    for i in range(1, nb):
        band_cols(lb == i)
    if is_gate:
        mid = w / 2
        arch_half = 95 * sc["gate"]
        xs_ = np.arange(w)
        foot[:, np.abs(xs_ - mid) < arch_half] = False
    foot |= thin
    if nm.startswith("chain"):              # the wall runs on behind each tower: close vertical gaps down to the next base
        cell = np.zeros(((h + CELL - 1) // CELL, ncol), np.uint8)
        for cy in range(cell.shape[0]):
            for ci in range(ncol):
                cell[cy, ci] = foot[cy * CELL:(cy + 1) * CELL, ci * CELL:(ci + 1) * CELL].any()
        cell = cv2.morphologyEx(cell, cv2.MORPH_CLOSE, np.ones((int(260 / CELL), 3), np.uint8))
        for cy in range(cell.shape[0]):
            for ci in range(ncol):
                if cell[cy, ci]:
                    foot[cy * CELL:(cy + 1) * CELL, ci * CELL:(ci + 1) * CELL] = True
    for cy in range(0, h, CELL):
        for cx in range(0, w, CELL):
            if foot[cy:cy + CELL, cx:cx + CELL].any():
                rects.append([s["x"] + cx, s["y"] + cy, CELL, CELL])
    placed.append({"img": "ring_%s" % nm, "x": s["x"], "y": s["y"], "w": w, "h": h, "strips": strips})

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


# exact merge: join vertically-adjacent rects with identical x/width
from collections import defaultdict
_col = defaultdict(list)
for r in rects:
    _col[(r[0], r[2])].append((r[1], r[3]))
rects = []
for (x_, w_), lst in _col.items():
    lst.sort()
    cy, ch = lst[0]
    for y_, h_ in lst[1:]:
        if y_ <= cy + ch:
            ch = max(ch, y_ + h_ - cy)
        else:
            rects.append([x_, cy, w_, ch]); cy, ch = y_, h_
    rects.append([x_, cy, w_, ch])
print("collision rects", len(rects))

# shadows (one light, upper-left): per-sprite projected alpha, two-tone, blue-violet
CORE, CORE_A, RIM_A = (38, 30, 78), 92, 46
for pl, s in zip(placed, sprites):
    im = s["img"]; h, w = im.shape[:2]
    a = im[..., 3] > 0
    ys, xs = np.nonzero(a)
    # ground line per 32-px strip
    foot = np.array([pl["strips"][min(len(pl["strips"]) - 1, x // 32)] for x in xs])
    ht = np.maximum(0, foot - ys).astype(float)
    ht = np.minimum(ht, 150.0)
    pad_r, pad_b = int(KX * 150) + 8, int(KY * 150) + 14
    mask = np.zeros((h + pad_b, w + pad_r), np.uint8)
    tx = np.round(xs + KX * ht).astype(int)
    ty = np.round(foot + KY * ht).astype(int)
    ok = (tx >= 0) & (tx < mask.shape[1]) & (ty >= 0) & (ty < mask.shape[0])
    mask[ty[ok], tx[ok]] = 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    yy, xx = np.nonzero(mask)
    if len(yy) == 0:
        continue
    y0_, y1_, x0_, x1_ = yy.min(), yy.max() + 1, xx.min(), xx.max() + 1
    m = mask[y0_:y1_, x0_:x1_]
    core = cv2.erode(m, np.ones((3, 3), np.uint8))
    sh = np.zeros(m.shape + (4,), np.uint8)
    sh[..., :3] = CORE
    sh[..., 3] = np.where(core > 0, CORE_A, np.where(m > 0, RIM_A, 0))
    Image.fromarray(sh).save(os.path.join(OUT, "ring_sh_%s.png" % s["name"]))
    pl["shadow"] = {"img": "ring_sh_%s" % s["name"], "x": s["x"] + int(x0_), "y": s["y"] + int(y0_)}

# ---------------------------------------------------------------- 6. ground: flood the inside of the ring on a 4 px grid
SEALG = 4
gw4, gh4 = WORLD_W // SEALG, WORLD_H // SEALG
blocked = np.zeros((gh4, gw4), np.uint8)
for r in rects:
    blocked[r[1] // SEALG:(r[1] + r[3]) // SEALG + 1, r[0] // SEALG:(r[0] + r[2]) // SEALG + 1] = 1
# plug the gate arch so the inside can be isolated
arch_x0 = int(L_gate[0] + (GATE_CX - 95) * sc["gate"]); arch_x1 = int(L_gate[0] + (GATE_CX + 95) * sc["gate"])
plug = blocked.copy()
arch_y = L_gate[1] + 540 * sc["gate"]
plug[int(arch_y - 70) // SEALG:int(arch_y + 20) // SEALG + 1, arch_x0 // SEALG:arch_x1 // SEALG + 1] = 1
seed = (int(XA) // SEALG, int(arch_y - 380) // SEALG)
free = (plug == 0).astype(np.uint8)
nlab, lab4 = cv2.connectedComponents(free, connectivity=4)
inside4 = lab4 == lab4[seed[1], seed[0]]
touch_border = inside4[0].any() or inside4[-1].any() or inside4[:, 0].any() or inside4[:, -1].any()
print("inside area (tiles^2): %d  leaks to world border: %s" % (inside4.sum() * SEALG * SEALG // (TILE * TILE), touch_border))
np.save("/tmp/inside4.npy", inside4)
inside = cv2.resize(inside4.astype(np.uint8), (GW, GH), interpolation=cv2.INTER_AREA) > 0
blk = cv2.resize(blocked, (GW, GH), interpolation=cv2.INTER_AREA) > 0
floor = inside | (blk & cv2.dilate(inside.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool))
bridge_tx0, bridge_tx1 = int((XA - 56) // TILE), int((XA + 56) // TILE)
rng = np.random.RandomState(4)


def noise_blob(shape, seed, scale):
    r = np.random.RandomState(seed)
    g = r.rand(shape[0] // scale + 2, shape[1] // scale + 2).astype(np.float32)
    g = cv2.GaussianBlur(g, (0, 0), 1.2)
    up = cv2.resize(g, (shape[1], shape[0]), interpolation=cv2.INTER_CUBIC)
    return (up - up.min()) / (up.max() - up.min())


dist = cv2.distanceTransform((~floor).astype(np.uint8), cv2.DIST_L2, 5)
nz = noise_blob((GH, GW), 5, 9)
shore = dist < (30 + 34 * nz)
# quay (south) + causeway
qy0 = QUAY_Y // TILE
quay = np.zeros_like(floor)
quay[qy0:, :] = True
gate_ty = int(gate_foot // TILE)
causeway = np.zeros_like(floor)
causeway[gate_ty - 2:qy0 + 1, bridge_tx0:bridge_tx1 + 1] = True
grid = np.full((GH, GW), "W", dtype="<U1")
grid[shore] = "S"
grid[floor] = "F"
grid[quay] = "F"
grid[causeway & ~floor] = "S"
# quay shore fringe
qs = cv2.dilate(quay.astype(np.uint8), np.ones((17, 17), np.uint8)).astype(bool) & ~quay
grid[qs & (grid == "W")] = "S"
grid[:, :4] = "W"; grid[:, -4:] = "W"
grid[:3, :] = "W"
rows = ["".join(r) for r in grid]

# water collision rects (run-merged), causeway columns stay open
wrects = run_merge((grid == "W").astype(np.uint8))

# causeway sprite (kit art, unchanged)
cw = Image.open(os.path.join(SRC, "wallkit_10_causeway.png")).convert("RGBA")
top = cw.crop((300, 300, 840, 750)); a_ = np.array(top); a_[..., 3] = 255
t_ = Image.fromarray(a_)
t_ = t_.resize((max(1, round(t_.width * 0.16)), 72), Image.BOX)
t_.save(os.path.join(OUT, "causeway.png"))

layout = {
    "tile": TILE, "world": [WORLD_W, WORLD_H], "grid": rows, "water_rects": wrects,
    "sprites": placed, "wall_rects": rects,
    "bridge": [int(XA), int(gate_foot - 8), int(QUAY_Y + 20)],
    "spawn": [int(XA), int(QUAY_Y + 120)],
    "gate": [int(XA), int(arch_y)], "inside_seed": [seed[0] * SEALG, seed[1] * SEALG],
    "wall_height": 90,
}
json.dump(layout, open(os.path.join(ROOT, "data/layout.json"), "w"))

# ---------------------------------------------------------------- 7. minimap (1 px = 1 tile)
mm = np.zeros((GH, GW, 3), np.uint8)
mm[grid == "W"] = (40, 100, 170); mm[grid == "F"] = (196, 186, 164); mm[grid == "S"] = (130, 114, 92)
wall_mask = cv2.resize((blocked * 255).astype(np.uint8), (GW, GH), interpolation=cv2.INTER_AREA) > 60
mm[wall_mask] = (92, 80, 70)
Image.fromarray(mm).save(os.path.join(OUT, "minimap.png"))
print("done: %d x %d tiles, %d sprites" % (GW, GH, len(placed)))
