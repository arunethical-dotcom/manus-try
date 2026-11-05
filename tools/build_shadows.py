#!/usr/bin/env python3
"""Baked wall shadows from the wall art + ground lines (same projection as build_walls.py).

  python3 tools/build_shadows.py      (after build_collision.py)"""
import os, json
import numpy as np, cv2
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
L = json.load(open(os.path.join(ROOT, "data/layout.json"))); WW, WH = L["world"]; CH = L["chunk"]
KX, KY, HCAP = 0.50, 0.20, 700
OUT = os.path.join(ROOT, "art/game/walls")
A = np.zeros((WH, WW), bool); G = np.zeros((WH, WW), np.int32)
for c in L["chunks"]:
    if c.get("wall"):
        x, y = c["x"], c["y"]
        a = np.array(Image.open(os.path.join(OUT, "wall_%d_%d.png" % (x, y))))[..., 3] > 0
        d = np.array(Image.open(os.path.join(OUT, "depth_%d_%d.png" % (x, y))))
        h, w = a.shape; A[y:y + h, x:x + w] = a; G[y:y + h, x:x + w] = d[..., 0].astype(np.int32) * 256 + d[..., 1]
yy, xx = np.nonzero(A); gy = G[yy, xx]
h = np.minimum(np.maximum(0, gy - yy), HCAP).astype(np.float32)
tx = np.round(xx + KX * h).astype(int); ty = np.round(gy + KY * h).astype(int)
ok = (tx >= 0) & (tx < WW) & (ty >= 0) & (ty < WH)
S = np.zeros((WH, WW), np.uint8); S[ty[ok], tx[ok]] = 255
S = cv2.morphologyEx(S, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)); S = cv2.GaussianBlur(S, (0, 0), 2.0)
byk = {(c["x"], c["y"]): c for c in L["chunks"]}
for f in os.listdir(OUT):
    if f.startswith("shadow_") and f.endswith(".png"): os.remove(os.path.join(OUT, f))
for cy in range(0, WH, CH):
    for cx in range(0, WW, CH):
        s = S[cy:cy + CH, cx:cx + CH]
        e = byk.get((cx, cy))
        if (s > 8).any():
            if e is None:
                e = {"x": cx, "y": cy}; L["chunks"].append(e); byk[(cx, cy)] = e
            sh = np.zeros(s.shape + (4,), np.uint8); sh[..., 0], sh[..., 1], sh[..., 2] = 38, 30, 78
            sh[..., 3] = (s.astype(np.float32) / 255 * 96).astype(np.uint8)
            Image.fromarray(sh).save(os.path.join(OUT, "shadow_%d_%d.png" % (cx, cy))); e["shadow"] = True
        elif e is not None:
            e.pop("shadow", None)
L["chunks"] = [c for c in L["chunks"] if c.get("wall") or c.get("shadow")]
json.dump(L, open(os.path.join(ROOT, "data/layout.json"), "w"))
print("shadow chunks", sum(1 for c in L["chunks"] if c.get("shadow")))
