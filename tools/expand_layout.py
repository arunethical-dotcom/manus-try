#!/usr/bin/env python3
"""Move every stored world coordinate the way tools/expand_ring.py moved the wall art.
  import expand_layout; T = expand_layout.load(xform.json); T(x, y) -> (x', y')"""
import json

def load(path):
    data = json.load(open(path))
    if isinstance(data, list):                # several expansions applied in order
        Ts = [_one(d) for d in data]
        def TT(x, y):
            for t in Ts: x, y = t(x, y)
            return x, y
        return TT, data[-1]
    return _one(data), data

def _one(xf):
    def T(x, y):
        nx = x
        for c in xf['x']:                     # east first, then west (as applied)
            cut = c['x_north'] if y < c['y_split'] else c['x_south']
            if x >= cut: nx += c['d']
        ny = y
        for c in xf['y']:
            cut = c['y_west'] if nx < c['x_split_new'] else c['y_east']
            if y >= cut: ny += c['d']
        return nx, ny
    return T
