"""Magenta background key for the ring art."""
import numpy as np, cv2


def key(rgb, tol=None):
    c = rgb.astype(int)
    r, g, b = c[..., 0], c[..., 1], c[..., 2]
    mag = (r - g > 60) & (b - g > 60) & (np.abs(r - b) < 90)
    a = (~mag).astype(np.uint8) * 255
    a = cv2.morphologyEx(a, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    out = rgb.copy()
    # de-spill the magenta fringe
    rim = (cv2.erode(a, np.ones((5, 5), np.uint8)) == 0) & (a > 0)
    px = out[rim].astype(int)
    px[:, 0] = np.minimum(px[:, 0], px[:, 1] + 40); px[:, 2] = np.minimum(px[:, 2], px[:, 1] + 30)
    out[rim] = px.astype(np.uint8)
    return np.dstack([out, a]), np.array([255, 0, 255])
