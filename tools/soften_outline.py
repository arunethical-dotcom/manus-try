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
ORIG = "/tmp/wall_orig"
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
LINE = np.array([58, 36, 26], np.float32)         # thin warm outline colour
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
    band = dark & (dt <= 6.5)
    keep = band & (dt <= 2.0)                      # the new thin line
    fill = band & (dt > 2.0)                       # rest of the old black band -> stone
    out = rgb.astype(np.float32)
    if fill.any():
        src = rgb.copy()
        inp = cv2.inpaint(cv2.cvtColor(src, cv2.COLOR_RGB2BGR), (fill | (a == 0)).astype(np.uint8) * 255, 5, cv2.INPAINT_TELEA)
        inp = cv2.cvtColor(inp, cv2.COLOR_BGR2RGB).astype(np.float32)
        shade = (0.70 + 0.25 * np.clip((dt - 2) / 4.5, 0, 1))[..., None]   # a little darker next to the line
        out[fill] = (inp * shade)[fill]
    out[keep] = out[keep] * 0.25 + LINE * 0.75
    res = np.dstack([np.clip(out, 0, 255).astype(np.uint8), sub[..., 3]])
    ox, oy = x - x0, y - y0
    w = np.array(Image.open(os.path.join(ORIG, "wall_%d_%d.png" % (x, y))))
    Image.fromarray(res[oy:oy + w.shape[0], ox:ox + w.shape[1]]).save(os.path.join(WD, "wall_%d_%d.png" % (x, y)))
print("softened", len(chunks), "chunks")
