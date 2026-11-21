"""Hand fixes on the 1536 px v9 Holdfast sprite (game px), before the door is drawn.
The quarters' vertical join runs down the facade's centre pilaster: the pilaster, the wall beside it and the
battlements above were drawn differently on each side. The strip x 735..812 (wall + pilaster + battlements, from the
parapet down to the plinth) is replaced by the same strip one bay (183 px) to the right, which is intact."""
import numpy as np

def repair_plinth_brick(a):
    """Complete the lowest course immediately left of the centre pilaster."""
    # The pillar and its cast shadow above this course come from x + 347.
    # Carry that same bay down to the footing, tapering into the intact row.
    x0, x1 = 716, 767
    rows = np.rint(np.linspace(1752, 1761, 12)).astype(int)
    donor = a[rows, x0 + 347:x1 + 347].astype(float)
    region = a[1752:1764, x0:x1]
    blend = np.clip((np.arange(x0, x1) - x0) / 7, 0, 1)[None, :, None]
    region[:] = np.rint(region * (1 - blend) + donor * blend)


def _mincut(E):
    acc = E.copy(); bk = np.zeros(E.shape, np.int8); n = E.shape[1]
    for y in range(1, E.shape[0]):
        p = acc[y - 1]; l = np.r_[np.inf, p[:-1]]; r = np.r_[p[1:], np.inf]
        st = np.stack([l, p, r]); k = st.argmin(0); acc[y] += st[k, np.arange(n)]; bk[y] = k - 1
    path = np.zeros(E.shape[0], int); path[-1] = int(acc[-1].argmin())
    for y in range(E.shape[0] - 1, 0, -1): path[y - 1] = path[y] + bk[y, path[y]]
    return path

def paste_cut(a, y0, y1, x0, x1, dx, dy=0, ov=8, sides='lrtb'):
    """copy a[y0+dy:y1+dy, x0+dx:x1+dx] onto a[y0:y1, x0:x1]; each edge enters along a min-error path inside an
    ov-wide band, so no straight seam or blur shows"""
    src = a[y0 + dy:y1 + dy, x0 + dx:x1 + dx, :3].copy(); dst = a[y0:y1, x0:x1, :3]
    h, w = src.shape[:2]; use = np.ones((h, w), bool); E = np.abs(src - dst).sum(-1)
    if 'l' in sides:
        p = _mincut(E[:, :ov].copy()); [use.__setitem__((y, slice(0, p[y])), False) for y in range(h)]
    if 'r' in sides:
        p = _mincut(E[:, -ov:].copy()); [use.__setitem__((y, slice(w - ov + p[y] + 1, w)), False) for y in range(h)]
    if 't' in sides:
        p = _mincut(E[:ov].T.copy()); [use.__setitem__((slice(0, p[x]), x), False) for x in range(w)]
    if 'b' in sides:
        p = _mincut(E[-ov:].T.copy()); [use.__setitem__((slice(h - ov + p[x] + 1, h), x), False) for x in range(w)]
    dst[use] = src[use]

def fix(img):
    a = img.astype(np.float32)
    # the left half of the facade (tower-side pilaster to the centre) was drawn lower down the page than the right
    # half by an amount that grows with height: 0 at the eave, ~3 px at the parapet, 6-7 px from the battlement
    # cornice down to the plinth (measured). Each column of that strip is resampled to put every course on the
    # right half's line.
    SX1 = 740
    # shift ramp kept out of the eave band and dormer bases (0 down to the parapet wall, then easing in through
    # plain brick courses)
    ky = np.array([1250, 1295, 1335, 1420, 1600, 1770], np.float32)
    kd = np.array([0, 4, 6, 6.5, 7, 6], np.float32)
    YE = min(1785, a.shape[0]); Y = np.arange(1200, YE, dtype=np.float32)
    srcy = Y - np.interp(Y, ky, kd)
    # left boundary per row: it must not cut the tower-side pilaster, its capitals, the corbels or the merlon in
    # front of the little turret, so above the corbels it runs left of the turret, below them on the tower's edge
    def sx0(y):
        return 238 if y < 1266 else (195 if y < 1342 else (214 if y < 1362 else 229))
    x_lo = 195
    strip = a[:, x_lo:SX1].copy()
    out = a[1200:YE, x_lo:SX1].copy()
    for j in range(SX1 - x_lo):
        for c in range(4):
            col = np.interp(srcy, np.arange(strip.shape[0]), strip[:, j, c])
            out[:, j, c] = col
    for i, y in enumerate(range(1200, YE)):
        x0 = sx0(y)
        a[y, x0:SX1] = out[i, x0 - x_lo:]
    a[..., 3] = np.where(a[..., 3] > 127, 255, 0)
    # (a) the whole bay left of the centre pilaster plus the pilaster (x 612..812, from the shadowed edge of the
    #     left pilaster), below the parapet, is the intact bay right of the pilaster (183 px further right); the
    #     only remaining joins run down pilaster edges / along course lines
    paste_cut(a, 1352, 1758, 615, 750, 190, ov=6, sides='lrtb')    # the bay: left pilaster's dark edge 614 <-> 804
    # the centre pilaster and the wall right of it from the right-hand pilaster at x 1111 (string courses run into its
    # capitals, shading like every other pilaster); one piece from x 742, so no second edge
    paste_cut(a, 1352, 1758, 742, 808, 347, ov=5, sides='lrtb')
    paste_cut(a, 1262, 1356, 621, 840, 190, ov=4, sides='lrtb')      # battlements + corbels (merlon period 47.5)
    paste_cut(a, 1272, 1340, 622, 662, 40, ov=4, sides='lr')         # one merlon to close the phase gap
    # (b) parapet wall above the battlements and the roof slates above it, smeared along the join: rebuilt from a
    #     clean stretch of the same rows (no dormer / window glow / roof in a wall patch, all roof in a roof patch)
    def ok(y0, y1, x0, x1, roof):
        r = a[y0:y1, x0:x1]
        if (r[..., 3] == 0).any(): return False
        blue = r[..., 2] > r[..., 0] + 25; glow = (r[..., 0] > 200) & (r[..., 2] < 120)
        return (blue.mean() > 0.97) if roof else (blue.mean() < 0.01 and glow.mean() < 0.001)
    for (y0, y1, x0, x1, roof) in ((1228, 1256, 740, 835, False), (1160, 1198, 735, 845, True)):
        best = None
        for dx in (list(range(270, 420)) if not roof else list(range(-600, -130)) + list(range(130, 600))):
            if x0 - 8 + dx < 0 or x1 + 8 + dx > a.shape[1] or not ok(y0, y1, x0 + dx, x1 + dx, roof): continue
            e = np.abs(a[y0:y1, x0 - 6:x0, :3] - a[y0:y1, x0 - 6 + dx:x0 + dx, :3]).mean() + \
                np.abs(a[y0:y1, x1:x1 + 6, :3] - a[y0:y1, x1 + dx:x1 + 6 + dx, :3]).mean()
            if best is None or e < best[0]: best = (e, dx)
        if best: paste_cut(a, y0, y1, x0, x1, best[1], ov=8)
    repair_plinth_brick(a)
    return np.clip(a, 0, 255).astype(np.uint8)
