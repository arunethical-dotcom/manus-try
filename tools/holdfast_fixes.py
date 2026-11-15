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
    return a
