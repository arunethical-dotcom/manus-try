"""Hand fixes on the 1536 px Holdfast sprite (game coords), applied by build_keep_buildings.py before saving.
1) The blue roof triangle beside the east-wing door (a stray piece of roof painted over the wall) becomes plain
   stone wall, tiled from the clean wall just right of it; the downpipe and the pillar cap stay."""
import numpy as np, cv2

def fix(a):
    rgb = a[..., :3].astype(float)
    S = rgb[1018:1080, 1112:1152]
    bw, bh = 37, 54
    T = S[:bh, :bw]
    X0, Y0, X1, Y1 = 1000, 960, 1135, 1150
    H, W = Y1 - Y0, X1 - X0
    fill = np.tile(T, (H // bh + 2, W // bw + 2, 1))
    oy = (Y0 - 1018) % bh; ox = (X0 - 1112) % bw
    fill = fill[oy:oy + H, ox:ox + W]
    reg = a[Y0:Y1, X0:X1, :3].astype(int); blue = reg[..., 2] > reg[..., 0] + 8
    poly = np.array([(1098, 974), (1010, 1062), (1010, 1146), (1126, 1146), (1108, 1084), (1104, 974)]) - [X0, Y0]
    pm = np.zeros(blue.shape, np.uint8); cv2.fillPoly(pm, [poly], 1)
    m = pm > 0
    m[974 - Y0:1146 - Y0, 1089 - X0:1104 - X0] = False
    cap = np.s_[1096 - Y0:1146 - Y0, 1022 - X0:1078 - X0]; m[cap] = blue[cap]
    m |= blue & (pm > 0)
    soft = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 0.7)[..., None]
    a[Y0:Y1, X0:X1, :3] = np.clip(rgb[Y0:Y1, X0:X1] * (1 - soft) + fill * soft, 0, 255).astype(np.uint8)
    return fix_tower_seam_row(fix_tower_windows(a))

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
