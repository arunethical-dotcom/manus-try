"""Ring layout: places kit pieces on the design's tower positions. Imported by build_kit.py.

All design coordinates are in design px (ring_design.png); game px = design px * M.
A tower's ground point ("base") is its roof top + 2.5 * roof width.
"""
import numpy as np, cv2, os
from PIL import Image

M = 4.0
KIT = None  # set by build_kit
AX = 838.0  # gate axis in the design

# native anchors (x, y of a tower's ground point) and tower roof widths per kit piece
ANCH = {
    "diag_towers":   {"L": (128, 933, 229), "R": (1032, 596, 221)},    # wall rises to the right "/"
    "diag_towers_b": {"L": (117, 657, 214), "R": (965, 994, 244)},     # wall descends to the right "\"
    "wall_tower":    {"R": (1104, 738, 244)},
    "corner_l":      {"L": (147, 994, 267)},
    "side_run":      {"B": (183, 1061, 251), "T": (325, 452, 142)},
    "gatehouse":     {"L": (370, 769, 263), "R": (915, 769, 265), "C": (642, 769, 0)},
    "gate_open":     {"C": (516, 542, 0)},
}
SLOPE = {"diag_towers": -0.44, "diag_towers_b": 0.50}   # dy per dx of the wall base line

# design towers: name -> (cx, roof_top, roof_w)
DT = {
    "gL": (763, 618, 66), "t623": (623, 706, 60), "t276": (276, 712, 56), "t168": (168, 672, 53), "t43": (43, 607, 58),
    "t68": (68, 404, 57), "s92": (92, 328, 24), "t81": (81, 237, 56), "t222": (222, 135, 55), "t361": (361, 67, 53),
    "t619": (619, 34, 44), "s730": (730, 19, 33),
}


def dbase(n):
    cx, top, w = DT[n]
    return cx, top + 2.5 * w, w


class Piece:
    """a native-resolution piece with named anchors, supports cutting out / repeating a band"""

    def __init__(self, name, img, mirror=False):
        self.name = name
        self.img = img[:, ::-1].copy() if mirror else img.copy()
        self.mirror = mirror
        W = img.shape[1]
        self.anch = {}
        for k, (x, y, w) in ANCH.get(name, {}).items():
            self.anch[k] = ((W - 1 - x) if mirror else x, y, w)

    def cut_x(self, lo, hi, k):
        """remove columns [lo,hi): the right part moves left and by -k*(hi-lo) vertically (k = dy/dx of the wall)"""
        d = hi - lo
        L, R = self.img[:, :lo], self.img[:, hi:]
        dy = int(round(-k * d))
        H = self.img.shape[0]
        top = max(0, -dy)  # right part moved up by |dy| when dy<0 -> pad canvas on top of the left part
        bot = max(0, dy)
        out = np.zeros((H + top + bot, L.shape[1] + R.shape[1], 4), np.uint8)
        out[top:top + H, :lo] = L
        out[top + dy:top + dy + H, lo:] = R
        self._shift_anchors(lambda x, y: (x, y + top) if x < lo else (x - d, y + top + dy) if x >= hi else (lo, y + top))
        self.img = out
        return self

    def _shift_anchors(self, f):
        self.anch = {n: (*f(x, y), w) for n, (x, y, w) in self.anch.items()}


def scaled(img, s):
    h, w = img.shape[:2]
    nw, nh = max(1, int(round(w * s))), max(1, int(round(h * s)))
    rgb = cv2.resize(img[..., :3], (nw, nh), interpolation=cv2.INTER_AREA)
    a = cv2.resize(img[..., 3], (nw, nh), interpolation=cv2.INTER_AREA)
    return np.dstack([rgb, np.where(a > 127, 255, 0).astype(np.uint8)])


def layout(SRC):
    """returns placements (dict: n, img, x, y, z, gate) in game px, design origin (0,0) = ring_design top-left * M"""
    out = []

    def mk(name, mirror=False):
        return Piece(name, SRC[name], mirror)

    def add(p, anchor, target, s, crop=None, z=None, gate=None, tag=None, dx=0, dy=0):
        ax, ay, aw = p.anch[anchor]
        tx, ty, tw = dbase(target) if isinstance(target, str) else target
        X = tx * M - ax * s + dx
        Y = ty * M - ay * s + dy
        img = p.img
        x0 = 0
        if crop:
            c0, c1 = crop
            c0 = 0 if c0 is None else int(c0)
            c1 = img.shape[1] if c1 is None else int(c1)
            img = img[:, c0:c1]
            x0 = c0
        out.append(dict(n=tag or p.name, img=scaled(img, s), x=int(round(X + x0 * s)), y=int(round(Y)), z=z, gate=gate,
                        s=s, p=p))
        return X, Y

    def diag(name, mirror, a, ta, b, tb, drop=None, z=None, ta_s=None, tag=None):
        """diagonal piece with towers a (near) and b (far) placed on design towers ta and tb; the wall is shortened
        so the towers land the right distance apart. drop = 'A'/'B': leave that tower off (its neighbour has it)"""
        p = mk(name, mirror)
        ax, ay, aw = p.anch[a]
        bx, by, bw = p.anch[b]
        tax, tay, taw = dbase(ta) if isinstance(ta, str) else ta
        tbx, tby, tbw = dbase(tb) if isinstance(tb, str) else tb
        s = (ta_s or taw * M / aw)
        want = abs(tbx - tax) * M / s
        have = abs(bx - ax)
        d = have - want
        k = SLOPE[name] * (-1 if mirror else 1)
        if d > 20:
            mid = (ax + bx) / 2
            lo, hi = int(mid - d / 2), int(mid + d / 2)
            p.cut_x(lo, hi, k)
        else:
            print("diag %s %s->%s: no shortening (need %.0f native px more)" % (name, ta, tb, -d))
        ax, ay, aw = p.anch[a]
        bx, by, bw = p.anch[b]
        crop = None
        c0, c1 = None, None
        if drop and "B" in drop:
            cx = bx - 0.38 * bw if bx > ax else bx + 0.25 * bw
            if bx > ax:
                c1 = cx
            else:
                c0 = cx
        if drop and "A" in drop:
            cx = ax + 0.38 * aw if bx > ax else ax - 0.25 * aw
            if bx > ax:
                c0 = cx
            else:
                c1 = cx
        crop = (c0, c1) if (c0 is not None or c1 is not None) else None
        add(p, a, ta, s, crop=crop, z=z, tag=tag)
        return s, p

    # ---- south: gatehouse, L-step to the south wall
    sg = 66 * M / 263
    pg = mk("gatehouse")
    add(pg, "C", (AX, dbase("gL")[1], 0), sg, gate=("south", 530, 742, 640, 714), z=10**9)
    s623 = 60 * M / 267
    pc = mk("corner_l")
    add(pc, "L", "t623", s623)
    # straight wall between the towers 276 and 623
    sw = 60 * M / 244
    base623 = dbase("t623")
    x_from = dbase("t276")[0] * M
    x_to = base623[0] * M
    wl = SRC["wall_long"]
    seg = x_to - x_from
    y_wall = base623[1] * M - 28
    x = x_from
    while x < x_to - 4:
        w_ = wl.shape[1] * sw
        cw = min(w_, x_to + 20 - x)
        img = scaled(wl[:, :int(cw / sw)], sw)
        out.append(dict(n="wall_long", img=img, x=int(x), y=int(y_wall - 671 * sw), z=None, gate=None, s=sw, p=None))
        x += cw - 6
    # ---- SW corner: two "\" diagonals (up-left)
    diag("diag_towers_b", False, "R", "t276", "L", "t168", tag="diag_sw1")
    diag("diag_towers_b", False, "R", "t168", "L", "t43", drop="A", tag="diag_sw2")
    # ---- west wall: one steep run, big tower on the design's tower 68
    ps = mk("side_run")
    add(ps, "B", "t68", 57 * M / 251, tag="side_run", dy=170)
    # ---- NW corner: two "/" diagonals
    diag("diag_towers", False, "L", "t81", "R", "t222", drop=None, tag="diag_nw1")
    diag("diag_towers", False, "L", "t222", "R", "t361", drop="AB", tag="diag_nw2")
    # ---- north wall: L-step (corner piece) at tower 361 up to the flat wall, flat wall into tower 619 (wall_tower),
    # diagonal up to the small tower 730, then the open gate
    scn, swn = 0.66, 0.83          # the corner piece's flat wall is 25 % taller than the wall piece's: scale both to equal height
    pn = mk("corner_l")
    add(pn, "L", "t361", scn, tag="corner_l_n")
    # the corner piece's flat wall ends at native x=1008 and sits on base line y=664; the wall_tower's wall base is y=707
    xend = dbase("t361")[0] * M + (1008 - 147) * scn
    ybase = dbase("t361")[1] * M - (994 - 664) * scn
    pw = mk("wall_tower")
    x619, _, w619 = dbase("t619")
    X0 = x619 * M - 1104 * swn
    add(pw, "R", (x619, (ybase + (738 - 707) * swn) / M, w619), swn, crop=((xend - 60 - X0) / swn, None), tag="wall_tower_n")
    diag("diag_towers", False, "L", "t619", "R", "s730", drop="A", ta_s=0.72, tag="diag_n")
    pgo = mk("gate_open")
    add(pgo, "C", (AX, 106, 0), 0.8, gate=("north", 430, 602, 330, 542), z=10**9)
    # ---- mirror the left half about the gate axis
    res = []
    for q in out:
        res.append(q)
        if q["n"] in ("gatehouse", "gate_open"):
            continue
        m = dict(q)
        m["img"] = q["img"][:, ::-1]
        m["x"] = int(round(2 * AX * M - (q["x"] + q["img"].shape[1])))
        m["n"] = q["n"] + "_R"
        res.append(m)
    return res


# ======================================================================================= v2: fit pieces between towers
def fit(img, A, B, TA, TB, s):
    """Native piece `img` with tower ground points A=(x,y,halfw) and B=(x,y,halfw); returns (scaled image, game x, game y)
    so that A lands on game point TA and B on TB. Towers are kept rigid; the wall between them is resampled horizontally
    and sheared vertically (column offsets), never rotated."""
    flip = B[0] < A[0]
    if flip:
        W = img.shape[1]
        img = img[:, ::-1]
        A = (W - 1 - A[0], A[1], A[2]); B = (W - 1 - B[0], B[1], B[2])
        TA, TB = (-TA[0], TA[1]), (-TB[0], TB[1])
    xa, ya, ha = A; xb, yb, hb = B
    dxn = (TB[0] - TA[0]) / s
    dyn = (TB[1] - TA[1]) / s
    l0, l1 = int(round(xa + ha)), int(round(xb - hb))      # old wall band
    newband = max(4, int(round(dxn - ha - hb)))
    left, band, right = img[:, :l0], img[:, l0:l1], img[:, l1:]
    idx = np.clip((np.arange(newband) * band.shape[1] / newband).astype(int), 0, band.shape[1] - 1)
    band = band[:, idx]
    extra = dyn - (yb - ya)                                 # extra drop of B relative to A
    off = np.concatenate([np.zeros(left.shape[1]), np.linspace(0, extra, newband), np.full(right.shape[1], extra)])
    cols = np.concatenate([left, band, right], axis=1)
    lo, hi = min(0, off.min()), max(0, off.max())
    H = cols.shape[0] + int(np.ceil(hi - lo)) + 1
    out = np.zeros((H, cols.shape[1], 4), np.uint8)
    for x in range(cols.shape[1]):
        o = int(round(off[x] - lo))
        out[o:o + cols.shape[0], x] = cols[:, x]
    simg = scaled(out, s)
    gx = TA[0] - xa * s
    gy = TA[1] - (ya - lo) * s
    if flip:
        simg = simg[:, ::-1]
        gx = -(gx + simg.shape[1])
    return simg, gx, gy


def dpt(n):
    """design tower n -> game point of its roof top"""
    cx, top, w = DT[n]
    return (cx * M, top * M)


ROOF = {   # kit towers: native (roof centre x, roof top y, roof width)
    "diag_towers": {"L": (128, 366, 229), "R": (1032, 0, 221)},
    "diag_towers_b": {"L": (117, 0, 214), "R": (965, 234, 244)},
    "corner_l": {"L": (147, 145, 267)},
    "tower": {"T": (208, 0, 372)},
    "gatehouse": {"L": (370, 0, 263), "R": (915, 0, 265)},
}


def tower_at(SRC, put, t):
    """the loose kit tower standing upright on design tower t"""
    st = DT[t][2] * M / 372
    x, y = dpt(t)
    put("tower", scaled(SRC["tower"], st), x - 208 * st, y, s=st, z=int(y + 1178 * st) + 600)


def side_v(SRC, put, ta, tb, tag):
    """steep west-wall run between design towers ta (lower) and tb (upper): the kit run without its big tower,
    scaled to the tower width horizontally and stretched vertically, rows sheared so both ends land on the towers"""
    im = SRC["side_run"].copy()
    im[400:, 40:330, 3] = 0                      # big tower (a loose tower stands there instead)
    ys, xs = np.nonzero(im[..., 3])
    im = im[:, :]
    s = DT[ta][2] * M / 251
    A = (183, 1061); B = (538, 150)              # native ground points: run foot and run top
    st_a = DT[ta][2] * M / 372; st_b = DT[tb][2] * M / 372
    TA = (dpt(ta)[0], dpt(ta)[1] + 1100 * st_a)
    TB = (dpt(tb)[0], dpt(tb)[1] + 1100 * st_b)
    sy = (TA[1] - TB[1]) / (A[1] - B[1])
    H, W = im.shape[:2]
    big = cv2.resize(im, (int(W * s), int(H * sy)), interpolation=cv2.INTER_AREA)
    big[..., 3] = np.where(big[..., 3] > 127, 255, 0)
    # shear rows: at row of A no shift, at row of B shift so that B.x lands on TB.x
    ya, yb = A[1] * sy, B[1] * sy
    xa, xb = A[0] * s, B[0] * s
    want = (TB[0] - TA[0]) - (xb - xa)
    pad = int(abs(want)) + 2
    out = np.zeros((big.shape[0], big.shape[1] + 2 * pad, 4), np.uint8)
    for y in range(big.shape[0]):
        t = min(1.0, max(0.0, (ya - y) / (ya - yb)))
        o = int(round(pad + want * t))
        out[y, o:o + big.shape[1]] = big[y]
    put(tag, out, TA[0] - xa - pad, TA[1] - ya, s=s)


RIGHT = {"gL": (913, 619, 60), "t623": (1053, 707, 55), "t276": (1413, 706, 56), "t168": (1511, 668, 57),
         "t43": (1632, 604, 57), "t68": (1610, 404, 51), "s92": (1586, 328, 27), "t81": (1596, 240, 53),
         "t222": (1454, 137, 55), "t361": (1316, 67, 52), "t619": (1061, 34, 49), "s730": (946, 18, 30)}


def layout_v2(SRC):
    global DT
    left_dt = dict(DT)
    left = _half(SRC, with_gates=True)
    DT = {k: (2 * AX - v[0], v[1], v[2]) for k, v in RIGHT.items()}
    right = _half(SRC, with_gates=False)
    DT = left_dt
    res = [q for q in left if q["n"] not in ("gatehouse", "gate_open")]
    res += [q for q in left if q["n"] in ("gatehouse", "gate_open")]
    for q in right:
        m = dict(q); m["img"] = q["img"][:, ::-1]
        m["x"] = int(round(2 * AX * M - (q["x"] + q["img"].shape[1]))); m["n"] = q["n"] + "_R"
        res.append(m)
    return res


def _half(SRC, with_gates):
    out = []

    def put(name, img, x, y, z=None, gate=None, s=1.0):
        out.append(dict(n=name, img=img, x=int(round(x)), y=int(round(y)), z=z, gate=gate, s=s, p=None))

    def seg(piece, a, b, ta, tb, tag, crop_b_tower=False, crop_a_tower=False):
        im = SRC[piece]
        a = next(v for v in ROOF[piece].values() if v[0] == a[0] or abs(v[0] - a[0]) < 20)
        b = next(v for v in ROOF[piece].values() if abs(v[0] - b[0]) < 20)
        A = (a[0], a[1], a[2] * 0.5); B = (b[0], b[1], b[2] * 0.5)
        s = DT[ta][2] * M / a[2] if a[2] else 1
        TA, TB = dpt(ta), dpt(tb)
        simg, gx, gy = fit(im, A, B, TA, TB, s)
        # optionally remove one end tower (the neighbour piece brings it): cut its columns off
        if crop_b_tower or crop_a_tower:
            W = simg.shape[1]
            right_is_b = TB[0] > TA[0]
            hw = int((b[2] if crop_b_tower else a[2]) * 0.5 * s * 1.05)
            end_x = (TB if crop_b_tower else TA)[0] - gx
            if (crop_b_tower and right_is_b) or (crop_a_tower and not right_is_b):
                cut = int(end_x - hw)
                simg = simg[:, :max(1, cut)]
            else:
                cut = int(end_x + hw)
                simg = simg[:, cut:]; gx += cut
        put(tag, simg, gx, gy, s=s)

    # south gatehouse: its two tower roofs on the design's gate towers
    sg = (913 - 763) * M / (915 - 370)            # gate tower spacing: design / kit
    gp = SRC["gatehouse"]
    if with_gates:
      put("gatehouse", scaled(gp, sg), 763 * M - 370 * sg, dpt("gL")[1], z=10 ** 9,
        gate=("south", 530, 742, 640, 714), s=sg)
    # L-step from the gatehouse to tower 623
    s6 = DT["t623"][2] * M / 267
    cl = SRC["corner_l"]
    cx6, cy6 = dpt("t623")
    put("corner_l", scaled(cl, s6), cx6 - 147 * s6, cy6 - 145 * s6, s=s6)
    # flat south wall 276 -> 623: same wall height and base line as the corner piece's flat wall
    WTOP, WBOT = 733, 855                         # south wall top / base in the design (measured, x=350..1250)
    wbase = WBOT * M
    sw = (WBOT - WTOP) * M / 672
    wl = SRC["wall_long"]
    x, x_to = dpt("t276")[0], cx6
    while x < x_to - 4:
        w_ = min(wl.shape[1] * sw, x_to + 20 - x)
        im = scaled(wl[:, :int(w_ / sw)], sw)
        put("wall_long", im, x, wbase - 671 * sw, s=sw)
        x += w_ - 6
    # SW corner: 276 -> 168 -> 43, diagonal "\" pieces (towers rigid, fitted)
    dB = ANCH["diag_towers_b"]
    seg("diag_towers_b", dB["R"], dB["L"], "t276", "t168", "diag_sw1")
    seg("diag_towers_b", dB["R"], dB["L"], "t168", "t43", "diag_sw2", crop_a_tower=True)
    # west wall: 43 -> 68 -> 81, steep runs; their small top tower is cut, a big tower stands on each design tower
    side_v(SRC, put, "t43", "t68", "side1")
    side_v(SRC, put, "t68", "t81", "side2")
    for t in ("t43", "t68", "s92"):
        tower_at(SRC, put, t)
    # NW: 81 -> 222 -> 361, diagonal "/" pieces
    dT = ANCH["diag_towers"]
    seg("diag_towers", dT["L"], dT["R"], "t81", "t222", "diag_nw1")
    seg("diag_towers", dT["L"], dT["R"], "t222", "t361", "diag_nw2", crop_a_tower=True)
    # north wall 361 -> 619: diagonal-free flat run fitted between the two towers (corner piece's wall is flat)
    seg("diag_towers", dT["L"], dT["R"], "t361", "t619", "north1", crop_a_tower=True)
    # 619 -> small tower 730, then the open gate
    seg("diag_towers", dT["L"], dT["R"], "t619", "s730", "north2", crop_a_tower=True)
    sgo = 0.8
    if with_gates:
      put("gate_open", scaled(SRC["gate_open"], sgo), AX * M - 516 * sgo, (DT["s730"][1] + 20) * M,
        z=10 ** 9, gate=("north", 430, 602, 330, 542), s=sgo)
    return out
