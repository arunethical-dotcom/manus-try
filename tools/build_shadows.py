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
# contact shadow: where the wall meets the ground, the grass right under its foot is shaded (ambient occlusion),
# so the wall sits on the ground instead of floating. Foot pixel = bottom edge of the art that stands on the ground.
below = np.zeros_like(A); below[:-1] = A[1:]
yy_ = np.arange(WH, dtype=np.int32)[:, None]
foot = A & ~below & (np.abs(G - yy_) < 12)
D = 34
C = np.zeros((WH, WW), np.float32)
acc = foot.copy()
for k in range(1, D + 1):
    sh_ = np.zeros_like(foot); sh_[k:] = foot[:-k]
    C = np.maximum(C, sh_ * (1.0 - k / (D + 1)) ** 1.6)
C = cv2.GaussianBlur(C, (0, 0), 2.5)
C = np.maximum(C, cv2.GaussianBlur(foot.astype(np.float32), (0, 0), 3.0) * 1.4)   # a little to the sides too
S = np.maximum(S.astype(np.float32) / 255 * 96, np.clip(C * 1.35, 0, 1) * 215).astype(np.uint8)
byk = {(c["x"], c["y"]): c for c in L["chunks"]}
for f in os.listdir(OUT):
    if f.startswith("shadow_") and f.endswith(".png"): os.remove(os.path.join(OUT, f))
for cy in range(0, WH, CH):
    for cx in range(0, WW, CH):
        s = S[cy:cy + CH, cx:cx + CH]
        e = byk.get((cx, cy))
        if (s > 3).any():
            if e is None:
                e = {"x": cx, "y": cy}; L["chunks"].append(e); byk[(cx, cy)] = e
            sh = np.zeros(s.shape + (4,), np.uint8); sh[..., 0], sh[..., 1], sh[..., 2] = 38, 30, 78
            sh[..., 3] = s
            Image.fromarray(sh).save(os.path.join(OUT, "shadow_%d_%d.png" % (cx, cy))); e["shadow"] = True
        elif e is not None:
            e.pop("shadow", None)
L["chunks"] = [c for c in L["chunks"] if c.get("wall") or c.get("shadow")]
json.dump(L, open(os.path.join(ROOT, "data/layout.json"), "w"))
print("shadow chunks", sum(1 for c in L["chunks"] if c.get("shadow")))
