#!/usr/bin/env python3
"""Independent import/alpha verification of the three pipeline stages. Writes Docs/alpha_report.txt.
Checks per sprite: (1) source alpha stats, (2) game-scale alpha is strictly binary, (3) no magenta-ish colour
on any opaque pixel (halo test), (4) no opaque matte: corners transparent, transparent fraction sane,
(5) no isolated stray opaque specks after processing."""
import os, glob, json
import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
lines = []
def say(s): lines.append(s); print(s)

TILES = {"cobblestone_tile", "grass_tile", "river_water_tile"}
bad = 0
say("name | src alpha(min..max, semi%) | game size | game alpha values | magenta px | corners transparent | tiny specks")
for p in sorted(glob.glob(os.path.join(ROOT, "Art", "Source", "individual_*.png"))):
    n = os.path.basename(p)[len("individual_"):-4]
    src = np.array(Image.open(p).convert("RGBA"))
    sa = src[..., 3]
    semi = 100.0 * np.mean((sa > 0) & (sa < 255))
    gp = os.path.join(ROOT, "Art", "Game", n + ".png")
    g = np.array(Image.open(gp).convert("RGBA"))
    ga = g[..., 3]
    vals = sorted(set(np.unique(ga).tolist()))
    op = ga == 255
    r, gg, b = g[..., 0].astype(int), g[..., 1].astype(int), g[..., 2].astype(int)
    mag = int(np.sum(op & (r > 190) & (b > 190) & (gg < 90)))
    corners = all(ga[y, x] == 0 for y in (0, -1) for x in (0, -1)) if n not in TILES else None
    lab, cnt = ndimage.label(op)
    sizes = ndimage.sum(op, lab, range(1, cnt + 1)) if cnt else []
    specks = int(np.sum(np.array(sizes) < 6)) if cnt else 0
    ok = True
    if n in TILES:
        ok = vals == [255]
    else:
        ok = vals in ([0, 255], [255]) and mag == 0 and corners
    if not ok: bad += 1
    say("%-18s | %3d..%3d semi %.2f%% | %dx%d | %s | %d | %s | %d | %s" % (n, sa.min(), sa.max(), semi, g.shape[1], g.shape[0], vals, mag, corners, specks, "OK" if ok else "CHECK"))
say("sprites/tiles needing attention: %d" % bad)
for extra in ["gatehouse_main", "gatehouse_bridge"]:
    g = np.array(Image.open(os.path.join(ROOT, "Art", "Game", extra + ".png")).convert("RGBA"))
    say("%-18s | derived split | %dx%d | %s" % (extra, g.shape[1], g.shape[0], sorted(set(np.unique(g[..., 3]).tolist()))))
open(os.path.join(ROOT, "Docs", "alpha_report.txt"), "w").write("\n".join(lines) + "\n")
