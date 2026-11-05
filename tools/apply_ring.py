#!/usr/bin/env python3
"""Writes a whole-world wall image (RGBA, world size) into the game's wall chunks.

  python3 tools/apply_ring.py <ring_rgba.png>

Updates art/game/walls/wall_*.png (and the copy in art/source/walls/chunks_orig), adds / removes chunk entries in
data/layout.json, and creates empty depth maps for new chunks. Then run, in order:
  build_objects.py, build_collision.py, build_objects.py, tools/build_shadows.py, build_levels.py, build_footprint.py --apply"""
import os, sys, json
import numpy as np
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
L = json.load(open(os.path.join(ROOT, "data/layout.json"))); WW, WH = L["world"]; CH = L["chunk"]
R = np.array(Image.open(sys.argv[1]).convert("RGBA")); assert R.shape[:2] == (WH, WW), R.shape
R[R[..., 3] < 128] = 0; R[..., 3] = np.where(R[..., 3] > 0, 255, 0)
OUT = os.path.join(ROOT, "art/game/walls"); ORIG = os.path.join(ROOT, "art/source/walls/chunks_orig")
old = {(c["x"], c["y"]): c for c in L["chunks"]}
chunks = []
for cy in range(0, WH, CH):
    for cx in range(0, WW, CH):
        a = R[cy:cy + CH, cx:cx + CH]
        e = dict(old.get((cx, cy), {"x": cx, "y": cy}))
        name = "wall_%d_%d.png" % (cx, cy)
        if a[..., 3].any():
            Image.fromarray(a).save(os.path.join(OUT, name)); Image.fromarray(a).save(os.path.join(ORIG, name))
            dp = os.path.join(OUT, "depth_%d_%d.png" % (cx, cy))
            if not os.path.exists(dp):
                d = np.zeros(a.shape[:2] + (4,), np.uint8); d[..., 3] = 255; Image.fromarray(d).save(dp)
            e["wall"] = True
        else:
            e.pop("wall", None)
            for f in (os.path.join(OUT, name), os.path.join(OUT, "depth_%d_%d.png" % (cx, cy))):
                if os.path.exists(f): os.remove(f)
        if e.get("wall") or e.get("shadow"):
            chunks.append(e)
L["chunks"] = chunks
json.dump(L, open(os.path.join(ROOT, "data/layout.json"), "w"))
print("wall chunks", sum(1 for c in chunks if c.get("wall")), "of", len(chunks))
