#!/usr/bin/env python3
"""Softens the thick black outer outline of the wall art: the ~5 px black band along the silhouette becomes a thin
2 px warm dark-brown line, and the inner part of the band is filled from the neighbouring stone (inpainted, slightly
shaded). Silhouette, collision and depth are unchanged.

  python3 tools/soften_outline.py      (after build_walls.py; reads the untouched chunks from art/game/walls/orig/)"""
import os, json, shutil
import numpy as np, cv2
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WD = os.path.join(ROOT, "art/game/walls")
ORIG = os.path.join(ROOT, "art/source/walls/chunks_orig")
L = json.load(open(os.path.join(ROOT, "data/layout.json")))
WW, WH = L["world"]
os.makedirs(ORIG, exist_ok=True)
chunks = [c for c in L["chunks"] if c.get("wall")]
for c in chunks:                                  # keep the untouched art so the step can be re-run
    f = "wall_%d_%d.png" % (c["x"], c["y"])
    if not os.path.exists(os.path.join(ORIG, f)):
        shutil.copy(os.path.join(WD, f), os.path.join(ORIG, f))
IMG = np.zeros((WH, WW, 4), np.uint8)
for c in chunks:
    w = np.array(Image.open(os.path.join(ORIG, "wall_%d_%d.png" % (c["x"], c["y"]))))
    IMG[c["y"]:c["y"] + w.shape[0], c["x"]:c["x"] + w.shape[1]] = w
LINE = np.array([96, 64, 44], np.float32)         # thin, lighter warm outline colour
PAD = 24
for c in chunks:
    x, y = c["x"], c["y"]
    x0, y0 = max(0, x - PAD), max(0, y - PAD)
    sub = IMG[y0:y + 512 + PAD, x0:x + 512 + PAD]
    a = (sub[..., 3] > 0).astype(np.uint8)
    rgb = sub[..., :3].copy()
    lum = rgb.astype(np.int32).sum(-1)
    dt = cv2.distanceTransform(np.pad(a, 1), cv2.DIST_L2, 3)[1:-1, 1:-1]
    dark = (lum < 160) & (a > 0)
    band = dark & (dt <= 8.5)
    keep = band & (dt <= 1.0)                      # the new thin line
    fill = band & (dt > 1.0)                       # rest of the old black band -> stone
    out = rgb.astype(np.float32)
    if fill.any():
        src = rgb.copy()
        inp = cv2.inpaint(cv2.cvtColor(src, cv2.COLOR_RGB2BGR), (fill | (a == 0)).astype(np.uint8) * 255, 5, cv2.INPAINT_TELEA)
        inp = cv2.cvtColor(inp, cv2.COLOR_BGR2RGB).astype(np.float32)
        shade = (0.80 + 0.20 * np.clip((dt - 1) / 5.0, 0, 1))[..., None]   # a little darker next to the line
        out[fill] = (inp * shade)[fill]
    out[keep] = out[keep] * 0.35 + LINE * 0.65
    # inner lines: thin every dark line thicker than ~2 px (windows / openings - wide dark areas - stay)
    o8 = np.clip(out, 0, 255).astype(np.uint8)
    lum2 = o8.astype(np.int32).sum(-1)
    dk = ((lum2 < 150) & (a > 0)).astype(np.uint8)
    holes = cv2.dilate(cv2.morphologyEx(dk, cv2.MORPH_OPEN, np.ones((11, 11), np.uint8)), np.ones((5, 5), np.uint8))
    dd = cv2.distanceTransform(1 - dk, cv2.DIST_L2, 3)       # (unused) kept for clarity
    din = cv2.distanceTransform(dk, cv2.DIST_L2, 3)          # distance from a dark pixel to the nearest light one
    core = (dk > 0) & (holes == 0) & (din > 1.2) & (dt > 1.0)
    if core.any():
        inp = cv2.inpaint(cv2.cvtColor(o8, cv2.COLOR_RGB2BGR), (core | (a == 0)).astype(np.uint8) * 255, 4, cv2.INPAINT_TELEA)
        inp = cv2.cvtColor(inp, cv2.COLOR_BGR2RGB).astype(np.float32)
        out[core] = inp[core] * 0.82
    edge = (dk > 0) & (holes == 0) & ~core & (dt > 1.0)          # what is left of each line: warm dark brown
    out[edge] = out[edge] * 0.4 + LINE * 0.6
    res = np.dstack([np.clip(out, 0, 255).astype(np.uint8), sub[..., 3]])
    ox, oy = x - x0, y - y0
    w = np.array(Image.open(os.path.join(ORIG, "wall_%d_%d.png" % (x, y))))
    Image.fromarray(res[oy:oy + w.shape[0], ox:ox + w.shape[1]]).save(os.path.join(WD, "wall_%d_%d.png" % (x, y)))
print("softened", len(chunks), "chunks")
