"""polygon helpers shared by build_levels.py / build_barrier.py"""
import numpy as np, cv2
from shapely.geometry import Polygon, MultiPolygon
from shapely.validation import make_valid


def clean_polys(pts):
    """valid, simple, non-degenerate polygons (Godot's convex decomposition rejects self-touching outlines)"""
    g = Polygon(pts)
    if not g.is_valid:
        g = make_valid(g)
    g = g.buffer(0)
    parts = list(g.geoms) if hasattr(g, "geoms") else [g]
    out = []
    for p in parts:
        if not isinstance(p, Polygon) or p.area < 40:
            continue
        p = Polygon(p.exterior).simplify(0.75, preserve_topology=True)
        if not p.is_valid or p.area < 40:
            continue
        c = list(p.exterior.coords)[:-1]
        # drop duplicate / collinear vertices
        cc = []
        for i, q in enumerate(c):
            a, b = c[i - 1], c[(i + 1) % len(c)]
            cr = (q[0] - a[0]) * (b[1] - a[1]) - (q[1] - a[1]) * (b[0] - a[0])
            if abs(cr) > 0.01 and q != a:
                cc.append([round(q[0], 1), round(q[1], 1)])
        if len(cc) >= 3 and Polygon(cc).is_valid:
            out.append(cc)
    return out


def section_polys(mask, sec_ids, kind, SEC, TOWERS):
    """cut mask into sections (by object id where given, then SEC grid), one simple polygon per connected piece"""
    out = []
    H8, W8 = mask.shape
    for gy in range(0, H8, SEC):
        for gx in range(0, W8, SEC):
            sub = mask[gy:gy + SEC, gx:gx + SEC]
            if not sub.any():
                continue
            ids = sec_ids[gy:gy + SEC, gx:gx + SEC]
            for sid in np.unique(ids[sub]):
                piece = (sub & (ids == sid)).astype(np.uint8)
                pad = np.pad(piece, 1)
                cs, hier = cv2.findContours(pad, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
                if hier is None:
                    continue
                for ci, cnt in enumerate(cs):
                    if hier[0][ci][3] != -1 or cv2.contourArea(cnt) < 40:
                        continue
                    if (hier[0][ci][2] != -1):          # has holes: fill them (holes are outside this level's reach)
                        pass
                    ap = cv2.approxPolyDP(cnt, 1.5, True).reshape(-1, 2)
                    if len(ap) < 3:
                        continue
                    pts = [(float(p[0]) - 1 + gx, float(p[1]) - 1 + gy) for p in ap]
                    name = ("tower_%d" % sid) if 1 <= sid <= TOWERS else ("wall_%d" % sid)
                    for k_, poly in enumerate(clean_polys(pts)):
                        out.append({"sec": "%s_%s_%d_%d_%d" % (kind, name, gx // SEC, gy // SEC, k_), "poly": poly})
    return out


