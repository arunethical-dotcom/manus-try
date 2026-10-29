#!/usr/bin/env python3
"""Builds every game asset + the level layout from the supplied source art.

  python3 tools/build_assets.py <wall_kit_dir> <floor_tile.png> <blueprint.png>

Scale contract (from the brief):  tile 16x16 px, Kael 28 px tall, viewport 960x540 (60x34 tiles),
palace ~430 tiles wide x ~320 tiles deep.

The blueprint is traced into wall centre-lines (hand-read coordinates, left half mirrored to the right
because the plan is symmetric) and into a per-tile ground grid (water / floor / rocky shore) by colour.
Blueprint px -> world px:  x * SX, y * SY  (non-uniform on purpose: the painted plan is foreshortened,
the game world is laid out flat so depth gets more room).
"""
import json, os, sys, shutil
import numpy as np
from PIL import Image, ImageDraw
import cv2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIT, FLOOR, BLUE = sys.argv[1], sys.argv[2], sys.argv[3]
SRC = os.path.join(ROOT, "art/source")
OUT = os.path.join(ROOT, "art/game")
os.makedirs(SRC, exist_ok=True)
os.makedirs(OUT, exist_ok=True)

TILE = 16
SX, SY = 5.0, 7.5          # blueprint px -> world px
WT, WH = 72, 46            # wall thickness (ground footprint, also top walkway width) / visible face height
KIT_SCALE = 0.16           # wall-kit texture scale (stone course ~7 px, next to a 16 px floor tile)
TOWER_SCALE = 0.24
BP_W, BP_H = 1672, 941
GW, GH = int(BP_W * SX / TILE), int(BP_H * SY / TILE)   # 522 x 441 tiles

# keep untouched copies of the supplied art
for f in sorted(os.listdir(KIT)):
    if f.endswith(".png"):
        shutil.copy(os.path.join(KIT, f), os.path.join(SRC, "wallkit_" + f))
shutil.copy(FLOOR, os.path.join(SRC, "floor_tile.png"))
shutil.copy(BLUE, os.path.join(SRC, "palace_blueprint.png"))


def kit(name):
    return Image.open(os.path.join(KIT, name)).convert("RGBA")


def down(im, s):
    """box-filter downscale (no blur halo), then hard alpha so edges stay pixel-crisp"""
    w, h = max(1, round(im.width * s)), max(1, round(im.height * s))
    o = im.resize((w, h), Image.BOX)
    a = np.array(o)
    a[..., 3] = np.where(a[..., 3] > 110, 255, 0)
    return Image.fromarray(a)


def crop_alpha(im):
    a = np.array(im)[..., 3] > 20
    ys, xs = np.nonzero(a)
    return im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))


# ---------------------------------------------------------------- textures from the wall kit
sw = kit("01_straight_wall.png")
# one clean run between pillars: 6 merlon periods (80 px each in the source)
face = sw.crop((302, 380, 302 + 480, 669))
down(face, KIT_SCALE).save(os.path.join(OUT, "wall_face.png"))
cw = kit("10_causeway.png")
top = cw.crop((300, 300, 300 + 540, 750)).convert("RGBA")
a = np.array(top); a[..., 3] = 255; top = Image.fromarray(a)
t = down(top, KIT_SCALE)
t = t.resize((t.width, WT), Image.NEAREST)
t.save(os.path.join(OUT, "wall_top.png"))

sprites = {}
for key, fn, s in [("tower", "07_watchtower.png", TOWER_SCALE), ("gatehouse", "08_gatehouse.png", TOWER_SCALE),
                   ("stairs", "09_stair_wall.png", KIT_SCALE), ("wall_end", "04_wall_end.png", KIT_SCALE),
                   ("causeway", "10_causeway.png", 0.18)]:
    im = down(crop_alpha(kit(fn)), s)
    im.save(os.path.join(OUT, key + ".png"))
    sprites[key] = [im.width, im.height]

# ---------------------------------------------------------------- floor: top-down slab tile
# crop the walkable top face (drop the transparent margin and the front lip), 8x8 tiles of 16 px
fl = Image.open(FLOOR).convert("RGBA").crop((104, 106, 1150, 1098))
fl = fl.resize((128, 128), Image.BOX)
a = np.array(fl); a[..., 3] = 255
Image.fromarray(a).save(os.path.join(OUT, "floor_atlas.png"))

# ---------------------------------------------------------------- generated tiles: water + rocky shore (64 px atlases)
rng = np.random.RandomState(3)


def tileable_noise(n, cells, seed):
    r = np.random.RandomState(seed)
    g = r.rand(cells, cells).astype(np.float32)
    g = np.tile(g, (3, 3))
    up = cv2.resize(g, (n * 3, n * 3), interpolation=cv2.INTER_CUBIC)
    return up[n:2 * n, n:2 * n]


def water_tex():
    n = 64
    a = tileable_noise(n, 8, 5)
    b = tileable_noise(n, 4, 6)
    v = a * 0.6 + b * 0.4
    img = np.zeros((n, n, 4), np.uint8)
    pal = [(24, 92, 168), (30, 110, 190), (38, 128, 204), (60, 150, 214)]
    q = np.clip((v - v.min()) / (v.max() - v.min()) * 3.99, 0, 3.99).astype(int)
    for i, col in enumerate(pal):
        img[q == i, :3] = col
    # sparse highlights
    hl = (tileable_noise(n, 16, 7) > 0.86)
    img[hl, :3] = (150, 205, 236)
    img[..., 3] = 255
    return img


def shore_tex():
    n = 64
    img = np.zeros((n, n, 4), np.uint8)
    base = tileable_noise(n, 6, 9)
    img[..., :3] = (np.array([156, 136, 108]) * (0.85 + 0.25 * base[..., None])).astype(np.uint8)
    # pebbles / boulders (wrapped so the tile repeats)
    r = np.random.RandomState(11)
    for _ in range(26):
        x, y, rad = r.randint(0, n), r.randint(0, n), r.randint(3, 8)
        tone = r.randint(0, 3)
        col = [(120, 112, 100), (140, 128, 112), (102, 94, 86)][tone]
        for dx in (-n, 0, n):
            for dy in (-n, 0, n):
                cv2.ellipse(img, (x + dx, y + dy), (rad, int(rad * 0.75)), 0, 0, 360, (*col, 255), -1)
                cv2.ellipse(img, (x + dx - 1, y + dy - 1), (max(1, rad - 3), max(1, int(rad * 0.4))), 0, 0, 360,
                            (min(255, col[0] + 45), min(255, col[1] + 40), min(255, col[2] + 34), 255), -1)
                cv2.ellipse(img, (x + dx, y + dy), (rad, int(rad * 0.75)), 0, 20, 160, (70, 62, 56, 255), 1)
    img[..., 3] = 255
    return img


Image.fromarray(water_tex()).save(os.path.join(OUT, "water_atlas.png"))
Image.fromarray(shore_tex()).save(os.path.join(OUT, "shore_atlas.png"))

# ---------------------------------------------------------------- Kael (16x28 frames, 4 dirs x 4 walk frames)
def kael():
    FW, FH = 16, 28
    sheet = Image.new("RGBA", (FW * 4, FH * 4), (0, 0, 0, 0))
    skin, hair, tunic, tunic_d, belt, pants, boot, cloak = (232, 190, 150), (92, 58, 36), (46, 92, 150), (32, 64, 108), \
        (120, 84, 44), (70, 60, 52), (52, 38, 30), (140, 40, 40)
    outline = (28, 22, 26)
    for row, face in enumerate(["down", "left", "right", "up"]):
        for f in range(4):
            im = Image.new("RGBA", (FW, FH), (0, 0, 0, 0)); g = ImageDraw.Draw(im)
            bob = 1 if f in (1, 3) else 0
            st = {0: 0, 1: 2, 2: 0, 3: -2}[f]
            y0 = 1 + bob
            # legs
            if face in ("down", "up"):
                g.rectangle([5, 19 + bob - min(0, st) // 2, 7, 25], fill=pants)
                g.rectangle([8, 19 + bob + max(0, st) // 2 - 1, 10, 25], fill=pants)
                g.rectangle([4, 25 - max(0, -st) // 2, 7, 27 - max(0, -st) // 2], fill=boot)
                g.rectangle([8, 25 - max(0, st) // 2, 11, 27 - max(0, st) // 2], fill=boot)
            else:
                g.rectangle([6 + st // 2, 19 + bob, 8 + st // 2, 25], fill=pants)
                g.rectangle([7 - st // 2, 19 + bob, 9 - st // 2, 25], fill=pants)
                g.rectangle([5 + st // 2, 25, 9 + st // 2, 27], fill=boot)
                g.rectangle([6 - st // 2, 25, 10 - st // 2, 27], fill=boot)
            # cloak behind (visible from back / sides)
            if face == "up":
                g.rectangle([3, 10 + y0, 12, 21 + y0], fill=cloak)
            elif face in ("left", "right"):
                cx = 10 if face == "left" else 3
                g.rectangle([cx, 10 + y0, cx + 3, 20 + y0], fill=cloak)
            # torso
            g.rectangle([4, 10 + y0, 11, 19 + y0], fill=tunic)
            g.rectangle([4, 17 + y0, 11, 18 + y0], fill=belt)
            g.line([4, 10 + y0, 4, 19 + y0], fill=tunic_d)
            if face == "up":
                g.rectangle([3, 10 + y0, 12, 19 + y0], fill=cloak)
            # arms
            sw_ = st // 2
            if face in ("down", "up"):
                g.rectangle([2, 11 + y0 + sw_, 3, 17 + y0 + sw_], fill=tunic_d)
                g.rectangle([12, 11 + y0 - sw_, 13, 17 + y0 - sw_], fill=tunic_d)
                g.point([(2, 18 + y0 + sw_), (13, 18 + y0 - sw_)], fill=skin)
            else:
                ax = 7 + sw_
                g.rectangle([ax, 11 + y0, ax + 2, 17 + y0], fill=tunic_d)
                g.point([(ax + 1, 18 + y0)], fill=skin)
            # head
            g.rectangle([4, 2 + y0, 11, 9 + y0], fill=skin)
            if face == "down":
                g.rectangle([4, 1 + y0, 11, 4 + y0], fill=hair)
                g.point([(4, 5 + y0), (11, 5 + y0)], fill=hair)
                g.point([(6, 6 + y0), (9, 6 + y0)], fill=(30, 30, 40))
            elif face == "up":
                g.rectangle([4, 1 + y0, 11, 8 + y0], fill=hair)
            elif face == "left":
                g.rectangle([4, 1 + y0, 11, 4 + y0], fill=hair)
                g.rectangle([9, 1 + y0, 11, 7 + y0], fill=hair)
                g.point([(5, 6 + y0)], fill=(30, 30, 40))
            else:
                g.rectangle([4, 1 + y0, 11, 4 + y0], fill=hair)
                g.rectangle([4, 1 + y0, 6, 7 + y0], fill=hair)
                g.point([(10, 6 + y0)], fill=(30, 30, 40))
            # 1 px dark outline around the silhouette
            a = np.array(im)
            m = a[..., 3] > 0
            ring = cv2.dilate(m.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & ~m
            a[ring] = (*outline, 255)
            sheet.paste(Image.fromarray(a), (f * FW, row * FH))
    sheet.save(os.path.join(OUT, "kael.png"))
    sh = Image.new("RGBA", (16, 6), (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse([0, 0, 15, 5], fill=(30, 24, 60, 110))
    sh.save(os.path.join(OUT, "kael_shadow.png"))


kael()

# ---------------------------------------------------------------- layout traced from the blueprint
# Wall centre-lines in blueprint px (the visible walkway line). LEFT HALF ONLY; mirrored about x = 836.
MID = 836
G = 24   # half width of a gatehouse gap in blueprint px  (24 * 5 = 120 world px)
OUTER_L = [(MID, 45), (770, 45), (705, 45), (705, 80), (612, 80), (570, 130), (492, 140), (380, 145), (300, 215),
           (240, 290), (232, 330), (155, 330), (152, 520), (262, 615), (355, 690), (620, 690), (625, 650),
           (MID - G, 650)]
INNER_L = [
    [(575, 140), (575, 215), (530, 240)],
    [(530, 240), (530, 280), (MID - G, 280)],
    [(240, 330), (240, 360), (530, 360), (540, 370), (605, 410), (605, 505)],
    [(540, 360), (750, 360), (775, 345)],
    [(605, 445), (790, 445)],
    [(775, 345), (775, 470)],
    [(620, 505), (620, 580), (740, 580)],
]
TOWERS_L = [(770, 45), (612, 80), (492, 140), (380, 145), (300, 215), (155, 330), (152, 520), (262, 615),
            (355, 690), (620, 690), (530, 240), (530, 360), (655, 280), (775, 345)]
STAIRS_L = [(420, 360), (700, 445), (MID, 445)]       # (centre on a wall line) -> wall is cut, stair sprite placed
GATES = [(MID, 650, "outer"), (MID, 280, "inner")]
TOWN_WALL_Y = 860
BRIDGE = (MID, 650, 870)   # x, from y, to y (blueprint)


def mirror(p):
    return (2 * MID - p[0], p[1])


def W(p):  # blueprint -> world, wall FOOT (visible walkway line + face height)
    return [round(p[0] * SX), round(p[1] * SY + WH)]


walls = []
outer = OUTER_L + [mirror(p) for p in reversed(OUTER_L)]
# split the closed outer loop at the gate (first/last points are the gate jambs) and at the top centre
walls.append(OUTER_L)
walls.append([mirror(p) for p in OUTER_L])
for pl in INNER_L:
    walls.append(pl)
    walls.append([mirror(p) for p in pl])
# town wall along the bottom (gap for the causeway)
walls.append([(0, TOWN_WALL_Y), (MID - 40, TOWN_WALL_Y)])
walls.append([(MID + 40, TOWN_WALL_Y), (BP_W, TOWN_WALL_Y)])
towers = TOWERS_L + [mirror(p) for p in TOWERS_L] + [(582, TOWN_WALL_Y), (1090, TOWN_WALL_Y)]
stairs = STAIRS_L + [mirror(p) for p in STAIRS_L if p[0] != MID]

# cut stair gaps out of horizontal wall segments
stair_half_bp = sprites["stairs"][0] * 0.5 / SX


def cut(pl, cx, cy, half):
    out, cur = [], [pl[0]]
    for a, b in zip(pl[:-1], pl[1:]):
        if abs(a[1] - cy) < 3 and abs(b[1] - cy) < 3 and min(a[0], b[0]) < cx < max(a[0], b[0]):
            d = 1 if b[0] > a[0] else -1
            cur.append((cx - d * half, cy))
            out.append(cur)
            cur = [(cx + d * half, cy), b]
        else:
            cur.append(b)
    out.append(cur)
    return [c for c in out if len(c) > 1]


for (cx, cy) in stairs:
    nw = []
    for pl in walls:
        nw += cut(pl, cx, cy, stair_half_bp)
    walls = nw
# the vertical lane walls also get cut where the centre stairs cross? (stairs sit between them: no cut needed)

layout = {
    "tile": TILE, "grid_w": GW, "grid_h": GH, "world": [GW * TILE, GH * TILE], "wall_thickness": WT, "wall_height": WH,
    "walls": [[W(p) for p in pl] for pl in walls],
    "towers": [W(p) for p in towers],
    "stairs": [W(p) for p in stairs],
    "gates": [W((x, y)) + [k] for x, y, k in GATES],
    "bridge": [round(BRIDGE[0] * SX), round(BRIDGE[1] * SY + WH), round(BRIDGE[2] * SY + WH)],
    "spawn": [round(MID * SX), round(905 * SY)],
    "sprites": sprites,
}

# ---------------------------------------------------------------- ground grid by colour + castle interior
bp = np.array(Image.open(BLUE).convert("RGB")).astype(int)
r, g, b = bp[..., 0], bp[..., 1], bp[..., 2]
water_bp = (b > r + 45) & (b > g + 10)
inside = np.zeros((BP_H, BP_W), np.uint8)
cv2.fillPoly(inside, [np.array(outer, np.int32)], 1)
# blue tower roofs are not water: drop small blue blobs, and inside the walls keep only the pond
water_bp = cv2.morphologyEx(water_bp.astype(np.uint8), cv2.MORPH_OPEN, np.ones((15, 15), np.uint8)).astype(bool)
pond = np.zeros_like(inside); cv2.rectangle(pond, (615, 470), (700, 615), 1, -1)
water_bp &= ~((inside > 0) & (pond == 0))
inside[TOWN_WALL_Y + 10:, :] = 1          # the paved quay south of the town wall
grid = []
for ty in range(GH):
    row = []
    for tx in range(GW):
        x = min(BP_W - 1, int((tx + 0.5) * TILE / SX))
        y = min(BP_H - 1, int((ty + 0.5) * TILE / SY))
        if water_bp[y, x] and not (abs(x - MID) < 11 and BRIDGE[1] <= y <= BRIDGE[2] + 12):
            ch = "W"
        elif inside[y, x]:
            ch = "F"
        else:
            ch = "S"
        row.append(ch)
    grid.append("".join(row))
# smooth single-tile specks
gm = np.array([list(r_) for r_ in grid])
layout["grid"] = grid

# water collision: run-merged rectangles (tile units); the causeway is left walkable
wm = (gm == "W").astype(np.uint8)
rects, active = [], {}
for y in range(GH + 1):
    runs = {}
    if y < GH:
        x = 0
        while x < GW:
            if wm[y, x]:
                x0 = x
                while x < GW and wm[y, x]:
                    x += 1
                runs[(x0, x - x0)] = True
            else:
                x += 1
    for k in list(active):
        if k not in runs:
            rects.append(active.pop(k))
    for k in runs:
        if k in active:
            active[k][3] += 1
        else:
            active[k] = [k[0], y, k[1], 1]
layout["water_rects"] = rects
os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
json.dump(layout, open(os.path.join(ROOT, "data/layout.json"), "w"))

# ---------------------------------------------------------------- minimap image (1 px per tile, walls drawn)
mm = np.zeros((GH, GW, 3), np.uint8)
mm[gm == "W"] = (40, 100, 170)
mm[gm == "F"] = (196, 186, 164)
mm[gm == "S"] = (130, 114, 92)
for pl in layout["walls"]:
    pts = np.array([[p[0] / TILE, (p[1] - WT * 0.5) / TILE] for p in pl], np.int32)
    cv2.polylines(mm, [pts], False, (92, 80, 70), 3)
for t_ in layout["towers"]:
    cv2.circle(mm, (int(t_[0] / TILE), int((t_[1] - 20) / TILE)), 4, (50, 80, 150), -1)
for gx, gy, _ in layout["gates"]:
    cv2.rectangle(mm, (int(gx / TILE) - 8, int(gy / TILE) - 5), (int(gx / TILE) + 8, int(gy / TILE)), (60, 50, 44), -1)
Image.fromarray(mm).save(os.path.join(OUT, "minimap.png"))
print("grid", GW, "x", GH, "tiles; world", GW * TILE, "x", GH * TILE, "px; walls", len(walls), "water rects", len(rects))
