#!/usr/bin/env python3
"""Enlarge the castle ring without rescaling any art: each straight wall run is lengthened by inserting copies of a
stretch of the same run (towers, gates and corners keep their exact size), joined along minimum-error cut paths.

  python3 tools/expand_ring.py <out_dir>

Every run gets its own cut inside its flat, tower-free stretch; the block length P (shared by the two runs a cut
crosses, so the castle stays rectangular) and each cut position are chosen where the joint is least visible.
The cut between the north and the south part of a side runs through the empty courtyard, so the two runs can be cut
at different x (likewise y for the west / east runs).
Writes <out_dir>/wall.png (RGBA, new world size), <out_dir>/G.npy (ground line y per wall pixel) and
<out_dir>/xform.json (cuts, used by tools/expand_layout.py to move every other coordinate the same way)."""
import os, sys, json
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTD = sys.argv[1]; os.makedirs(OUTD, exist_ok=True)
L = json.load(open(os.path.join(ROOT, 'data/layout.json'))); WW, WH = L['world']
O = 32
N = int(os.environ.get('NX', 2))
YSPLIT, XSPLIT = int(os.environ.get('YSPLIT', 2600)), int(os.environ.get('XSPLIT', 3944))                  # courtyard lines separating north/south and west/east runs
# flat, tower-free stretches (world px, measured on the art)
SIDES_X = {'west': {'n': (2490, 3230), 's': (1950, 2850)}, 'east': {'n': (4700, 5380), 's': (5000, 6030)}}
if os.environ.get('SPANS'): SIDES_X = json.loads(os.environ['SPANS'])
SPAN_Y = {'w': (2895, 3120), 'e': (2895, 3120)}
if os.environ.get('SPANY'): SPAN_Y = json.loads(os.environ['SPANY'])   # both edges of the side walls are straight here (no stair step)

A = np.zeros((WH, WW, 4), np.uint8); G = np.zeros((WH, WW), np.float32)
for c in L['chunks']:
    if not c.get('wall'): continue
    x, y = c['x'], c['y']
    w = np.array(Image.open(os.path.join(ROOT, 'art/game/walls/wall_%d_%d.png' % (x, y))).convert('RGBA'))
    d = np.array(Image.open(os.path.join(ROOT, 'art/game/walls/depth_%d_%d.png' % (x, y))))
    h, ww = w.shape[:2]
    A[y:y + h, x:x + ww] = w; G[y:y + h, x:x + ww] = d[..., 0].astype(np.float32) * 256 + d[..., 1]
Hh = np.where(A[..., 3] > 0, G - np.arange(WH)[:, None], 0).astype(np.float32)   # height above own ground line

def mincut(E):
    acc = E.copy(); bk = np.zeros(E.shape, np.int8); n = E.shape[1]
    for y in range(1, E.shape[0]):
        p = acc[y - 1]; l = np.r_[np.inf, p[:-1]]; r = np.r_[p[1:], np.inf]
        st = np.stack([l, p, r]); k = st.argmin(0); acc[y] += st[k, np.arange(n)]; bk[y] = k - 1
    path = np.zeros(E.shape[0], int); path[-1] = int(acc[-1].argmin())
    for y in range(E.shape[0] - 1, 0, -1): path[y - 1] = path[y] + bk[y, path[y]]
    return path, float(acc[-1].min())

def err(a, b):
    a = a.astype(np.float32); b = b.astype(np.float32); al = a[..., 3] > 0; bl = b[..., 3] > 0
    return np.abs(a[..., :3] - b[..., :3]).sum(-1) * (al & bl) + 400.0 * (al != bl)

def seam_cost(A, X, P):
    return mincut(err(A[:, X - O:X], A[:, X - P - O:X - P]))[1]

def insert_cols(A, Hh, X, P, N):
    left_A, left_H = A[:, :X].copy(), Hh[:, :X].copy()
    blkA, blkH = A[:, X - P - O:X], Hh[:, X - P - O:X]
    for _ in range(N):
        path, _ = mincut(err(left_A[:, -O:], blkA[:, :O]))
        use_b = np.arange(O)[None, :] >= path[:, None]
        ovA = np.where(use_b[..., None], blkA[:, :O], left_A[:, -O:]); ovH = np.where(use_b, blkH[:, :O], left_H[:, -O:])
        left_A = np.concatenate([left_A[:, :-O], ovA, blkA[:, O:]], 1); left_H = np.concatenate([left_H[:, :-O], ovH, blkH[:, O:]], 1)
    return np.concatenate([left_A, A[:, X:]], 1), np.concatenate([left_H, Hh[:, X:]], 1)

def best(Aband_n, Aband_s, span_n, span_s, Ps):
    res = []
    for P in Ps:
        def bx(Ab, span):
            cands = [X for X in range(span[0] + P + O + 8, span[1] - 8, 8)]
            if not cands: return None
            return min((seam_cost(Ab, X, P), X) for X in cands)
        a, b = bx(Aband_n, span_n), bx(Aband_s, span_s)
        if a and b: res.append((a[0] + b[0], P, a[1], b[1]))
    return min(res)

xf = {'old_world': [WW, WH], 'x': [], 'y': []}
# --- widen: east side first (so the west cut positions stay valid), north band / south band cut separately
for side in (() if os.environ.get('ONLYY') else ('east', 'west')):
    sp = SIDES_X[side]
    nb, sb = A[:YSPLIT], A[YSPLIT:]
    cost, P, Xn, Xs = best(nb, sb, sp['n'], sp['s'], range(int(os.environ.get('PX0', 256)), int(os.environ.get('PX1', 400)), 16))
    An, Hn = insert_cols(A[:YSPLIT], Hh[:YSPLIT], Xn, P, N)
    As, Hs = insert_cols(A[YSPLIT:], Hh[YSPLIT:], Xs, P, N)
    A = np.concatenate([An, As], 0); Hh = np.concatenate([Hn, Hs], 0)
    xf['x'].append({'side': side, 'x_north': Xn, 'x_south': Xs, 'y_split': YSPLIT, 'd': P * N})
    print(side, 'P', P, 'N', N, 'cuts', Xn, Xs, 'cost', round(cost))
D_x = sum(c['d'] for c in xf['x'])
xsplit = XSPLIT + (xf['x'][1]['d'] if xf['x'] else 0)
NY = int(os.environ.get('NY', N))             # courtyard centre after the west insertion
# --- heighten: west band / east band cut separately (rows)  (skipped with NOY=1: the side walls lean, copies step)
if not os.environ.get('NOY'):
    At, Ht = A.transpose(1, 0, 2), Hh.T
    wb, eb = At[:xsplit], At[xsplit:]
    cost, P, Yw, Ye = best(wb, eb, SPAN_Y['w'], SPAN_Y['e'], range(int(os.environ.get('PY0', 96)), int(os.environ.get('PY1', 192)), 16))
    Aw, Hw = insert_cols(At[:xsplit], Ht[:xsplit], Yw, P, NY)
    Ae, He = insert_cols(At[xsplit:], Ht[xsplit:], Ye, P, NY)
    A = np.concatenate([Aw, Ae], 0).transpose(1, 0, 2); Hh = np.concatenate([Hw, He], 0).T
    xf['y'].append({'y_west': Yw, 'y_east': Ye, 'x_split_new': xsplit, 'd': P * NY})
    print('rows P', P, 'N', NY, 'cuts', Yw, Ye, 'cost', round(cost))
NH, NW = A.shape[:2]
A[A[..., 3] < 128] = 0; A[..., 3] = np.where(A[..., 3] > 0, 255, 0)
Gn = np.where(A[..., 3] > 0, Hh + np.arange(NH)[:, None], 0)
Image.fromarray(A).save(os.path.join(OUTD, 'wall.png'))
np.save(os.path.join(OUTD, 'G.npy'), np.clip(np.round(Gn), 0, 65535).astype(np.uint16))
xf['world'] = [NW, NH]
json.dump(xf, open(os.path.join(OUTD, 'xform.json'), 'w'), indent=1)
print('world', WW, WH, '->', NW, NH)
