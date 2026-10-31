#!/usr/bin/env python3
"""Builds the generic art: floor atlas (from the supplied top-down tile), generated water + rocky shore atlases and Kael.

  python3 tools/build_assets.py <floor_tile.png>

then  python3 tools/build_ring.py <wall_pieces.png> <ring_reference.png>  builds the palace wall ring + layout.
Scale contract: tile 16x16 px, Kael 28 px tall, viewport 960x540 (60x34 tiles).
"""
import json, os, sys, shutil
import numpy as np
from PIL import Image, ImageDraw
import cv2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FLOOR = sys.argv[1]
SRC = os.path.join(ROOT, "art/source")
OUT = os.path.join(ROOT, "art/game")
os.makedirs(SRC, exist_ok=True)
os.makedirs(OUT, exist_ok=True)
TILE = 16
if os.path.abspath(FLOOR) != os.path.join(SRC, "floor_tile.png"):
    shutil.copy(FLOOR, os.path.join(SRC, "floor_tile.png"))

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

