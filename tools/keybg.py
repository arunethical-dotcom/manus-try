"""Background removal for the dark-backdrop wall sheets: flood from the image border over pixels close to the
backdrop colour (sampled from the corners), then soften the 1 px fringe."""
import numpy as np, cv2


def key(rgb, tol=26):
    h, w = rgb.shape[:2]
    corners = np.array([rgb[2, 2], rgb[2, w - 3], rgb[h - 3, 2], rgb[h - 3, w - 3]], float)
    bg = np.median(corners, axis=0)
    d = np.sqrt(((rgb.astype(float) - bg) ** 2).sum(-1))
    near = (d < tol).astype(np.uint8)
    # connected-to-border near-background = backdrop
    n, lab = cv2.connectedComponents(near, connectivity=4)
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    back = np.isin(lab, list(border)) & (near > 0)
    # also enclosed backdrop pockets (e.g. the ring interior / holes) when large and very close to bg
    pocket = (d < tol * 0.7) & ~back
    n2, lab2, st, _ = cv2.connectedComponentsWithStats(pocket.astype(np.uint8), connectivity=4)
    for i in range(1, n2):
        if st[i, cv2.CC_STAT_AREA] > 400:
            back |= lab2 == i
    a = (~back).astype(np.uint8) * 255
    a = cv2.morphologyEx(a, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    return np.dstack([rgb, a]), bg
