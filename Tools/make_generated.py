#!/usr/bin/env python3
"""Procedural PLACEHOLDER art (NOT part of the supplied pack). Deterministic (fixed seeds).
The pack only supplies exterior buildings/props/ground, so interior floors, interior wall faces,
furniture, the 64px player and underground rock are generated here and documented as such."""
import os, random
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "Art", "Generated")
os.makedirs(OUT, exist_ok=True)

def cl(v): return max(0, min(255, int(v)))
def sh(c, d): return tuple(cl(x + d) for x in c)

def tile(name, base, seed, kind):
    r = random.Random(seed); w = h = 32
    im = Image.new("RGBA", (w, h), base + (255,)); d = ImageDraw.Draw(im)
    if kind == "planks":
        for row in range(4):
            c = sh(base, r.randint(-9, 9)); d.rectangle([0, row*8, 31, row*8+6], fill=c)
            d.line([0, row*8+7, 31, row*8+7], fill=sh(base, -38))
            jx = r.randint(4, 27); d.line([jx, row*8, jx, row*8+6], fill=sh(c, -26))
            for _ in range(2):
                x = r.randint(0, 24); d.line([x, row*8+3, x+r.randint(3, 6), row*8+3], fill=sh(c, -14))
    elif kind == "flags":      # irregular flagstones
        d.rectangle([0, 0, 31, 31], fill=sh(base, -34))
        for (x0, y0, x1, y1) in [(0,0,14,14),(16,0,31,10),(0,16,10,31),(12,16,31,31),(16,12,31,14)]:
            c = sh(base, r.randint(-8, 8)); d.rectangle([x0+1, y0+1, x1-1, y1-1], fill=c)
            d.line([x0+1, y0+1, x1-1, y0+1], fill=sh(c, 12))
    elif kind == "brick":
        d.rectangle([0, 0, 31, 31], fill=sh(base, -40))
        for row in range(4):
            off = 8 if row % 2 else 0
            for col in range(-1, 3):
                x0 = col*16 + off; y0 = row*8
                c = sh(base, r.randint(-9, 9)); d.rectangle([x0+1, y0+1, x0+14, y0+6], fill=c)
                d.line([x0+1, y0+1, x0+14, y0+1], fill=sh(c, 14))
    elif kind == "rock":
        px = im.load()
        for y in range(h):
            for x in range(w):
                px[x, y] = sh(base, r.randint(-7, 7)) + (255,)
        for _ in range(14):
            x, y = r.randrange(w), r.randrange(h); px[x, y] = sh(base, -22) + (255,)
    elif kind == "carpet":
        d.rectangle([0, 0, 31, 31], fill=base)
        d.rectangle([2, 2, 29, 29], outline=sh(base, 40))
        d.rectangle([5, 5, 26, 26], outline=sh(base, -30))
    im.save(os.path.join(OUT, name))

tile("floor_planks.png", (136, 96, 60), 1, "planks")
tile("floor_flags.png", (120, 114, 122), 2, "flags")
tile("floor_flags_dark.png", (74, 72, 88), 3, "flags")
tile("wall_brick.png", (132, 124, 118), 4, "brick")
tile("wall_brick_dark.png", (70, 70, 88), 5, "brick")
tile("cave_rock.png", (48, 50, 64), 6, "rock")
tile("carpet_red.png", (150, 40, 48), 7, "carpet")

def box(name, w, d, h, top, front, side=None, detail=None):
    """3/4 box: top face (w x d) over front face (w x h). Origin of use: bottom-centre."""
    im = Image.new("RGBA", (w, d + h), (0, 0, 0, 0)); g = ImageDraw.Draw(im)
    g.rectangle([0, 0, w-1, d-1], fill=top); g.line([0, 0, w-1, 0], fill=sh(top, 24))
    g.rectangle([0, d, w-1, d+h-1], fill=front); g.line([0, d, w-1, d], fill=sh(front, 20))
    g.line([0, d+h-1, w-1, d+h-1], fill=sh(front, -36)); g.rectangle([0, 0, w-1, d+h-1], outline=sh(front, -50))
    if detail: detail(g, w, d, h)
    im.save(os.path.join(OUT, name))

def planks_d(g, w, d, h):
    for x in range(8, w-4, 10): g.line([x, d+2, x, d+h-3], fill=(86, 56, 34))
box("prop_table.png", 64, 22, 18, (168, 122, 78), (118, 80, 48), detail=planks_d)
box("prop_bench.png", 56, 8, 10, (150, 108, 68), (104, 70, 42))
box("prop_barrel.png", 22, 6, 26, (150, 108, 70), (112, 76, 46), detail=lambda g,w,d,h: [g.line([0, d+6, w-1, d+6], fill=(60,60,66)) or g.line([0, d+18, w-1, d+18], fill=(60,60,66))])
box("prop_crate.png", 28, 8, 24, (160, 120, 76), (122, 86, 52), detail=lambda g,w,d,h: g.line([2, d+2, w-3, d+h-3], fill=(90, 60, 36)))
box("prop_bed.png", 34, 40, 14, (188, 70, 76), (110, 72, 44))
box("prop_bookcase.png", 72, 10, 70, (96, 66, 42), (112, 76, 46),
    detail=lambda g,w,d,h: [g.rectangle([3+i*7, d+4+j*22, 8+i*7, d+20+j*22], fill=[(150,50,56),(60,90,150),(70,130,80),(190,150,60)][(i+j)%4]) for i in range(9) for j in range(3)])
box("prop_altar.png", 56, 18, 26, (200, 196, 186), (150, 146, 140))
box("prop_sarcophagus.png", 60, 26, 20, (140, 136, 134), (100, 98, 100))
box("prop_pillar.png", 22, 8, 74, (150, 146, 142), (112, 108, 106))
box("prop_stove.png", 60, 24, 36, (70, 70, 74), (96, 70, 60), detail=lambda g,w,d,h: g.rectangle([18, d+12, 42, d+30], fill=(30, 20, 18)))
box("prop_anvilblock.png", 30, 12, 20, (60, 62, 70), (90, 76, 64))
box("prop_rack.png", 70, 8, 40, (96, 66, 42), (92, 74, 60))
box("prop_dummy.png", 20, 8, 56, (166, 130, 80), (140, 104, 62))
box("prop_cot.png", 30, 36, 8, (120, 130, 150), (96, 70, 44))
box("prop_hay.png", 44, 20, 14, (212, 176, 80), (176, 140, 56))
box("prop_throne.png", 36, 14, 60, (160, 40, 48), (120, 30, 40))
box("prop_stairs_down.png", 40, 40, 6, (34, 30, 40), (60, 56, 64))
box("prop_cage.png", 60, 30, 36, (40, 40, 48), (60, 60, 70), detail=lambda g,w,d,h: [g.line([x, d, x, d+h-1], fill=(20,20,26)) for x in range(4, w, 6)])
box("prop_lever.png", 12, 6, 22, (120, 100, 70), (90, 90, 96))
box("prop_grate.png", 40, 24, 4, (30, 34, 40), (50, 54, 60), detail=lambda g,w,d,h: [g.line([x, 0, x, d-1], fill=(110,110,120)) for x in range(4, w, 6)])
box("prop_shelf_jars.png", 60, 8, 44, (96, 66, 42), (112, 76, 46))

# --- player: 4 facings x 4 frames, 32x64 (64 px tall = scale anchor). PLACEHOLDER art, original.
def player():
    SK, HAIR, TUN, TUN2, BOOT, BELT, TROU = (236, 190, 150), (96, 58, 38), (54, 92, 170), (36, 64, 130), (70, 44, 30), (190, 150, 60), (92, 88, 100)
    W, H = 32, 64
    sheet = Image.new("RGBA", (W*4, H*4), (0, 0, 0, 0))
    for row, face in enumerate(["down", "left", "right", "up"]):
        for f in range(4):
            im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); g = ImageDraw.Draw(im)
            bob = 1 if f in (1, 3) else 0
            step = {0: 0, 1: 3, 2: 0, 3: -3}[f]
            # shadow
            g.ellipse([6, 58, 25, 63], fill=(0, 0, 0, 70))
            # legs
            ly = 44 - bob
            if face in ("down", "up"):
                g.rectangle([10, ly, 14, 58 + max(0, step)//2], fill=TROU); g.rectangle([17, ly, 21, 58 + max(0, -step)//2], fill=TROU)
                g.rectangle([9, 56 + max(0, step)//2, 15, 59 + max(0, step)//2], fill=BOOT); g.rectangle([16, 56 + max(0, -step)//2, 22, 59 + max(0, -step)//2], fill=BOOT)
            else:
                g.rectangle([13 + step, ly, 18 + step, 58], fill=TROU); g.rectangle([13 - step, ly, 18 - step, 58], fill=sh(TROU, -14))
                g.rectangle([12 + step, 56, 20 + step, 59], fill=BOOT); g.rectangle([12 - step, 56, 20 - step, 59], fill=sh(BOOT, -10))
            # torso
            ty = 26 - bob
            g.rectangle([8, ty, 23, ty + 20], fill=TUN); g.rectangle([8, ty + 14, 23, ty + 16], fill=BELT)
            g.rectangle([8, ty, 10, ty + 20], fill=TUN2)
            # arms
            if face in ("down", "up"):
                g.rectangle([4, ty + 2, 7, ty + 14 + step//2], fill=TUN2); g.rectangle([24, ty + 2, 27, ty + 14 - step//2], fill=TUN)
                g.rectangle([4, ty + 15 + step//2, 7, ty + 17 + step//2], fill=SK); g.rectangle([24, ty + 15 - step//2, 27, ty + 17 - step//2], fill=SK)
            else:
                g.rectangle([13 - step//2, ty + 3, 18 - step//2, ty + 15], fill=TUN2); g.rectangle([13 - step//2, ty + 15, 18 - step//2, ty + 17], fill=SK)
            # head
            hy = 8 - bob
            g.rectangle([9, hy + 2, 22, hy + 17], fill=SK)
            if face == "down":
                g.rectangle([9, hy, 22, hy + 6], fill=HAIR); g.rectangle([8, hy + 2, 9, hy + 10], fill=HAIR); g.rectangle([22, hy + 2, 23, hy + 10], fill=HAIR)
                g.rectangle([12, hy + 9, 13, hy + 11], fill=(30, 30, 40)); g.rectangle([18, hy + 9, 19, hy + 11], fill=(30, 30, 40))
            elif face == "up":
                g.rectangle([8, hy, 23, hy + 14], fill=HAIR)
            elif face == "left":
                g.rectangle([9, hy, 22, hy + 6], fill=HAIR); g.rectangle([15, hy + 2, 22, hy + 12], fill=HAIR)
                g.rectangle([10, hy + 9, 11, hy + 11], fill=(30, 30, 40)); g.rectangle([8, hy + 11, 9, hy + 12], fill=sh(SK, -20))
            else:
                g.rectangle([9, hy, 22, hy + 6], fill=HAIR); g.rectangle([9, hy + 2, 16, hy + 12], fill=HAIR)
                g.rectangle([20, hy + 9, 21, hy + 11], fill=(30, 30, 40)); g.rectangle([22, hy + 11, 23, hy + 12], fill=sh(SK, -20))
            sheet.paste(im, (f * W, row * H))
    sheet.save(os.path.join(OUT, "player_sheet.png"))
player()

def door():
    im = Image.new("RGBA", (44, 66), (0, 0, 0, 0)); g = ImageDraw.Draw(im)
    g.rectangle([0, 6, 43, 65], fill=(74, 70, 76)); g.pieslice([0, 0, 43, 24], 180, 360, fill=(74, 70, 76))
    g.rectangle([5, 14, 38, 65], fill=(112, 74, 44)); g.pieslice([5, 4, 38, 32], 180, 360, fill=(112, 74, 44))
    for x in (12, 20, 28): g.line([x, 10, x, 65], fill=(82, 52, 30))
    g.rectangle([5, 36, 38, 38], fill=(60, 60, 66)); g.rectangle([31, 44, 34, 48], fill=(200, 170, 70))
    im.save(os.path.join(OUT, "prop_door.png"))
door()
def mat():
    im = Image.new("RGBA", (64, 14), (0, 0, 0, 0)); g = ImageDraw.Draw(im)
    g.rectangle([0, 0, 63, 13], fill=(74, 70, 76)); g.rectangle([3, 3, 60, 13], fill=(236, 212, 150))
    g.rectangle([3, 3, 60, 5], fill=(255, 238, 190)); g.rectangle([8, 8, 55, 10], fill=(196, 168, 110))
    im.save(os.path.join(OUT, "prop_mat.png"))
mat()

def ladder():
    im = Image.new("RGBA", (28, 72), (0, 0, 0, 0)); g = ImageDraw.Draw(im)
    g.rectangle([3, 0, 6, 71], fill=(120, 86, 52)); g.rectangle([21, 0, 24, 71], fill=(120, 86, 52))
    for y in range(6, 70, 10): g.rectangle([6, y, 21, y + 3], fill=(150, 108, 66))
    im.save(os.path.join(OUT, "prop_ladder.png"))
ladder()
print(sorted(os.listdir(OUT)))
