"""Hand fixes on the 1536 px v9 Holdfast sprite (game px), before the door is drawn.
The quarters' vertical join runs down the facade's centre pilaster: the pilaster, the wall beside it and the
battlements above were drawn differently on each side. The strip x 735..812 (wall + pilaster + battlements, from the
parapet down to the plinth) is replaced by the same strip one bay (183 px) to the right, which is intact."""
import numpy as np

def fix(img):
    a = img.astype(np.float32)
    # the left half of the facade (tower-side pilaster to the centre) was drawn lower down the page than the right
    # half by an amount that grows with height: 0 at the eave, ~3 px at the parapet, 6-7 px from the battlement
    # cornice down to the plinth (measured). Each column of that strip is resampled to put every course on the
    # right half's line.
    SX0, SX1 = 238, 740
    ky = np.array([1228, 1245, 1300, 1330, 1420, 1600, 1770], np.float32)
    kd = np.array([0, 3, 4, 6, 6.5, 7, 6], np.float32)
    YE = min(1785, a.shape[0]); Y = np.arange(1200, YE, dtype=np.float32)
    srcy = Y - np.interp(Y, ky, kd)
    strip = a[:, SX0:SX1].copy()
    for c in range(4):
        for j in range(SX1 - SX0):
            a[1200:YE, SX0 + j, c] = np.interp(srcy, np.arange(strip.shape[0]), strip[:, j, c])
    a[..., 3] = np.where(a[..., 3] > 127, 255, 0)
    # (a) centre pilaster strip, (b) the bay left of it (window, wall, battlements), which the left quarter drew ~6 px
    #     higher than every other bay: taken from the bay right of the pilaster (window 873 -> 683)
    for y0, y1, x0, x1, D in ((1255, 1768, 735, 812, 183), (1262, 1335, 618, 740, 183)):
        src = a[y0:y1, x0 + D:x1 + D].copy(); dst = a[y0:y1, x0:x1]
        w = x1 - x0
        f = np.clip(np.minimum(np.arange(w), w - 1 - np.arange(w)) / 3.0, 0, 1)[None, :, None]
        both = (src[..., 3:] > 0) & (dst[..., 3:] > 0)
        a[y0:y1, x0:x1] = np.where(both, src * f + dst * (1 - f), dst)
    return np.clip(a, 0, 255).astype(np.uint8)
