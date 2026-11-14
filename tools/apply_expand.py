#!/usr/bin/env python3
"""Put the enlarged ring (tools/expand_ring.py output dir) into the game: new world size, wall + depth chunks,
moved gates / spawn / inside, data/ring_xform.json (for buildings placed in old world coordinates).
Then run: build_objects, build_collision, build_objects, build_shadows, build_levels, build_footprint --apply,
build_ground, build_keep_buildings, make_minimap."""
import os, sys, json, glob, shutil
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import expand_layout
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = sys.argv[1]
T, xf = expand_layout.load(os.path.join(D, 'xform.json'))
A = np.array(Image.open(os.path.join(D, 'wall.png'))); G = np.load(os.path.join(D, 'G.npy'))
L = json.load(open(os.path.join(ROOT, 'data/layout.json')))
NW, NH = xf['world']
OUT = os.path.join(ROOT, 'art/game/walls'); ORIG = os.path.join(ROOT, 'art/source/walls/chunks_orig')
for f in glob.glob(os.path.join(OUT, 'wall_*.png*')) + glob.glob(os.path.join(OUT, 'depth_*.png*')) + \
         glob.glob(os.path.join(OUT, 'shadow_*.png*')) + glob.glob(os.path.join(ORIG, 'wall_*.png*')):
    os.remove(f)
CH = L['chunk']; chunks = []
for cy in range(0, NH, CH):
    for cx in range(0, NW, CH):
        a = A[cy:cy + CH, cx:cx + CH]
        if not a[..., 3].any(): continue
        Image.fromarray(a).save(os.path.join(OUT, 'wall_%d_%d.png' % (cx, cy)))
        Image.fromarray(a).save(os.path.join(ORIG, 'wall_%d_%d.png' % (cx, cy)))
        g = G[cy:cy + CH, cx:cx + CH].astype(np.int32)
        d = np.zeros(a.shape[:2] + (4,), np.uint8); d[..., 0] = g >> 8; d[..., 1] = g & 255; d[..., 3] = 255
        Image.fromarray(d).save(os.path.join(OUT, 'depth_%d_%d.png' % (cx, cy)))
        chunks.append({'x': cx, 'y': cy, 'wall': True})
L['world'] = [NW, NH]; L['chunks'] = chunks
for k in ('spawn', 'inside', 'plaza'):
    L[k] = list(T(*L[k]))
L['gates'] = {k: list(T(*v)) for k, v in L['gates'].items()}
L['grid'] = []
json.dump(L, open(os.path.join(ROOT, 'data/layout.json'), 'w'))
Image.fromarray(A).save(os.path.join(ROOT, 'art/source/walls/ring_world_v2.png'))
shutil.copy(os.path.join(D, 'xform.json'), os.path.join(ROOT, 'data/ring_xform.json'))
print('world', NW, NH, 'chunks', len(chunks), 'gates', L['gates'], 'spawn', L['spawn'], 'inside', L['inside'])
