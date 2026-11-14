#!/usr/bin/env python3
"""Holdfast ground floor: plan image -> tile grid (13 plan px = 1 tile = 16 game px).
in : design/holdfast/plan.png (the user's layout sheet)   out: data/holdfast_gf_grid.json"""
import json, os, sys
import numpy as np
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
im = np.asarray(Image.open(os.path.join(ROOT, 'design/holdfast/plan.png')).convert('RGB')).astype(int)
g = (np.abs(im - [124, 155, 92]).sum(-1) < 30)
ys, xs = np.where(g[:2200, :2000])
a = im[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
H, W = a.shape[:2]
P = 13
K = {'grass': [124, 155, 92], 'moat': [44, 36, 34], 'ground': [139, 131, 124], 'wall': [106, 42, 42],
     'room': [243, 233, 215], 'cloister': [243, 226, 201], 'yard': [211, 203, 180], 'door': [184, 138, 90],
     'well': [70, 110, 160], 'hearth': [232, 112, 40], 'stair': [248, 248, 248], 'hidden': [150, 225, 205]}
names = list(K); cols = np.array([K[k] for k in names])
d = np.abs(a[:, :, None, :] - cols[None, None]).sum(-1)
L = d.argmin(-1)
gw, gh = W // P, H // P
grid = []
for ty in range(gh):
    row = []
    for tx in range(gw):
        c = L[ty * P:(ty + 1) * P, tx * P:(tx + 1) * P].ravel()
        cnt = np.bincount(c, minlength=len(names))
        k = {n: cnt[i] / c.size for i, n in enumerate(names)}
        if k['door'] > 0.12: t = 'door'
        elif k['hearth'] > 0.15: t = 'hearth'
        elif k['hidden'] > 0.2: t = 'hidden'
        elif k['well'] > 0.2: t = 'well'
        elif k['wall'] > 0.5: t = 'wall'
        elif k['moat'] > 0.6: t = 'moat'
        else:
            cnt[names.index('moat')] = 0 if k['moat'] < 0.6 else cnt[names.index('moat')]   # text strokes
            cnt[names.index('stair')] = 0
            t = names[int(cnt.argmax())]
        row.append(t)
    grid.append(row)
json.dump({'tile_plan_px': P, 'w': gw, 'h': gh, 'grid': grid}, open(os.path.join(ROOT, 'data/holdfast_gf_grid.json'), 'w'))
ch = {'grass': ',', 'moat': '#', 'ground': '.', 'wall': 'W', 'room': ' ', 'cloister': '-', 'yard': 'y', 'door': 'D',
      'well': 'O', 'hearth': 'H', 'stair': 'S', 'hidden': 'h'}
for r in grid: print(''.join(ch[t] for t in r))
