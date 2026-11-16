"""Hand fixes on the 1536 px Holdfast sprite (game coords), applied by build_keep_buildings.py before saving.
1) The blue roof triangle beside the east-wing door (a stray piece of roof painted over the wall) becomes plain
   stone wall, tiled from the clean wall just right of it; the downpipe and the pillar cap stay."""
import numpy as np, cv2

def fix(a):
    """1) blue roof triangle beside the east-wing door -> stone wall, synthesised patch by patch from the clean wall
    right of the drainpipe (image quilting); pipe, pillar cap, rail and tower blocks kept."""
    rgb = a[..., :3].astype(np.float32)
    X0, Y0, X1, Y1 = 990, 960, 1140, 1160
    reg = a[Y0:Y1, X0:X1, :3].astype(int)
    blue = reg[..., 2] > reg[..., 0] + 6
    poly = np.array([(1100, 966), (1003, 1063), (1003, 1150), (1132, 1150), (1114, 1084), (1110, 966)]) - [X0, Y0]
    pm = np.zeros(blue.shape, np.uint8); cv2.fillPoly(pm, [poly], 1)
    m = (cv2.dilate(blue.astype(np.uint8), np.ones((9, 9))) > 0) & (pm > 0)
    m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((7, 7))) > 0
    m[:, 1093 - X0:1102 - X0] = False
    cap = np.s_[1094 - Y0:1160 - Y0, 1020 - X0:1080 - X0]; m[cap] &= blue[cap]
    src = rgb[1018:1080, 1110:1150]; ex = [src, src[:, ::-1]]
    B, O = 20, 6; H, W = Y1 - Y0, X1 - X0
    out = rgb[Y0:Y1, X0:X1].copy(); filled = ~m
    rng = np.random.default_rng(1)
    C = np.stack([e[y:y + B + O, x:x + B + O] for e in ex
                  for y in range(0, e.shape[0] - B - O + 1, 2) for x in range(0, e.shape[1] - B - O + 1, 2)])
    for by in range(-O, H, B):
        for bx in range(-O, W, B):
            y0, x0 = max(0, by), max(0, bx); y1, x1 = min(H, by + B + O), min(W, bx + B + O)
            if not m[y0:y1, x0:x1].any(): continue
            tgt = out[y0:y1, x0:x1]; known = filled[y0:y1, x0:x1]
            P = C[:, (y0 - by):(y0 - by) + (y1 - y0), (x0 - bx):(x0 - bx) + (x1 - x0)]
            err = ((P - tgt) ** 2).sum(-1)[:, known].mean(1) if known.any() else rng.random(len(P))
            patch = P[np.argsort(err)[:3][rng.integers(0, 3)]]
            kn = cv2.GaussianBlur(known.astype(np.float32), (0, 0), 1.0)
            newv = patch * (1 - kn[..., None]) + tgt * kn[..., None]
            sel = m[y0:y1, x0:x1]
            out[y0:y1, x0:x1][sel] = newv[sel]; filled[y0:y1, x0:x1] |= sel
    soft = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 0.8)[..., None]
    a[Y0:Y1, X0:X1, :3] = np.clip(rgb[Y0:Y1, X0:X1] * (1 - soft) + out * soft, 0, 255).astype(np.uint8)
    return fix_seam_windows(fix_tower_seam_row(fix_tower_windows(a)))


def fix_tower_windows(a):
    """2) The right-hand window of each of the tower's six rows was drawn narrower and up to 3 px higher than its
    neighbours (seam of the redrawn quarters): replaced by a copy of the left window of the same row, moved 137 px."""
    rows = [396, 504, 611, 725, 835, 946]             # top of the glass, left window
    DX = 137
    for t in rows:
        y0, y1, x0, x1 = t - 32, t + 46, 584, 651
        src = a[y0:y1, x0:x1].astype(float)
        dst = a[y0:y1, x0 + DX:x1 + DX].astype(float)
        h, w = src.shape[:2]
        fy = np.minimum(np.arange(h), np.arange(h)[::-1]); fx = np.minimum(np.arange(w), np.arange(w)[::-1])
        wgt = np.clip(np.minimum(fy[:, None], fx[None, :]) / 3.0, 0, 1)[..., None]
        a[y0:y1, x0 + DX:x1 + DX] = (src * wgt + dst * (1 - wgt)).astype(np.uint8)
    return a

def fix_tower_seam_row(a):
    """3) Bottom tower row: the quarters' horizontal seam (y ~957) cuts these windows and their lower halves are
    shifted ~3 px. Their lower half (y 950..993) is replaced with the same part of the intact row above (111 px up)."""
    y0, y1, D = 950, 988, 111
    for x0, x1 in ((586, 650), (654, 718), (723, 787)):
        src = a[y0 - D:y1 - D, x0:x1].astype(float); dst = a[y0:y1, x0:x1].astype(float)
        h, w = y1 - y0, x1 - x0
        fy = np.clip(np.minimum(np.arange(h) / 3.0, (h - 1 - np.arange(h)) / 3.0), 0, 1)[:, None]
        fx = np.clip(np.minimum(np.arange(w), w - 1 - np.arange(w)) / 3.0, 0, 1)[None, :]
        fy = (fy * fx)[..., None]
        a[y0:y1, x0:x1] = (src * fy + dst * (1 - fy)).astype(np.uint8)
    return a

def fix_seam_windows(a):
    """4) Every other window the horizontal quarter seam (y ~957) cuts: left and right bays beside the tower, the
    window by the east-wing door and the east block. Each gets its lower half (y 951..988) from the best-matching
    intact window: the same window one row up (offset searched), or, for the door window, the right bay's window."""
    g = a[..., :3].astype(float)
    def best(tx0, tx1, cands):
        top = g[924:951, tx0:tx1]
        sc = []
        for dx, dy in cands:
            s = g[924 + dy:951 + dy, tx0 + dx:tx1 + dx]
            if s.shape == top.shape: sc.append((np.abs(s - top).mean(), dx, dy))
        return min(sc)
    def paste(tx0, tx1, dx, dy, y0=951, y1=989):
        src = a[y0 + dy:y1 + dy, tx0 + dx:tx1 + dx].astype(float); dst = a[y0:y1, tx0:tx1].astype(float)
        h, w = y1 - y0, tx1 - tx0
        fy = np.clip(np.minimum(np.arange(h) / 3.0, (h - 1 - np.arange(h)) / 3.0), 0, 1)[:, None]
        fx = np.clip(np.minimum(np.arange(w), w - 1 - np.arange(w)) / 3.0, 0, 1)[None, :]
        f = (fy * fx)[..., None]
        a[y0:y1, tx0:tx1] = (src * f + dst * (1 - f)).astype(np.uint8)
    up = [(dx, dy) for dy in range(-126, -88) for dx in range(-4, 5)]
    done = []
    for tx0, tx1 in ((383, 445), (462, 521), (861, 917), (939, 993), (1364, 1419), (1421, 1480)):
        s, dx, dy = best(tx0, tx1, up); paste(tx0, tx1, dx, dy); done.append((tx0, round(s, 1), dx, dy))
    g = a[..., :3].astype(float)
    side = [(dx, dy) for dx in range(-112, -92) for dy in range(-4, 5)]
    s, dx, dy = best(1041, 1098, side); paste(1041, 1098, dx, dy); done.append((1041, round(s, 1), dx, dy))
    print('seam windows', done)
    return a
