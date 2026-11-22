"""Holdfast exterior prototype, built from the layout plan (plans-holdfast.png), not from painted art.

Method: the castle is modelled as solid blocks on a 1-px ground grid (a height field, plus a second "floating" layer
for things with open space under them: the covered bridge and the drawbridge). It is then projected the way the game
draws the world: a point (x, y, z) lands on screen at (x, y - z). Nearer (more southern) things are painted last, so
hidden surfaces sort themselves. Every wall face is textured in its own (u, z) coordinates, so masonry courses, string
courses, loops and windows sit at true storey heights.

Scale:
  * footprint: the plan's ground floor is scaled so the castle (towers included) is 1586 px wide, the same as the
    painted ground-floor interior, so inside and outside line up.
  * height: one storey = 5 tiles = 80 px (the plan's "each floor about 5 tiles tall"). Kael is 26 px tall (about 1.75 m),
    so a storey is about 5.4 m floor to floor.

Run:  python3 tools/holdfast_proto.py out.png
"""
import sys
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

# ---------------------------------------------------------------------------------------------------------------------
# plan → world.  Plan coordinates are pixels of the full-size plan image (3800 x 4276), ground-floor drawing.
S = 1586 / (1561 - 314)              # castle incl. towers is 314..1561 on the plan
PX0, PY0 = 105, 406                   # top-left of the plan's grass border
EXTRA_S = 150                         # extra ground south of the plan so the covered bridge can be seen leaving


def wx(px): return (px - PX0) * S
def wy(py): return (py - PY0) * S


W = int(round(wx(1768)))
H = int(round(wy(1860))) + EXTRA_S
STOREY = 80
ZB = 64                               # height-field offset so the dry moat (negative z) stays >= 0

# ---------------------------------------------------------------------------------------------------------------------
# palette
STONE = np.array((190, 168, 160.))    # rose-grey ashlar, as the current Holdfast
STONE_TOP = np.array((206, 186, 178.))
MORTAR = np.array((120, 100, 96.))
SLATE = np.array((74, 90, 150.))
LEAD = np.array((132, 136, 146.))
GRASS = np.array((104, 138, 70.))
BERM = np.array((168, 160, 150.))
EARTH = np.array((96, 78, 60.))
COBBLE = np.array((150, 144, 138.))
TIMBER = np.array((132, 86, 48.))
IRON = np.array((54, 54, 60.))
GLASS = np.array((60, 76, 104.))

# material ids
M_GRASS, M_BERM, M_MOAT, M_STONE, M_WALK, M_SLATE, M_COBBLE, M_TIMBER, M_IRON, M_LEAD, M_WATER, M_DECK = range(12)

Hf = np.zeros((H, W), np.float32)         # base height field (world z)
MAT = np.zeros((H, W), np.int16)
OBJ = np.zeros((H, W), np.int16)
# floating layer: [B2, T2] occupied, else T2 < B2
B2 = np.full((H, W), 1e9, np.float32)
T2 = np.full((H, W), -1e9, np.float32)
MAT2 = np.zeros((H, W), np.int16)
OBJ2 = np.zeros((H, W), np.int16)

YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
OBJS = {}


def obj(oid, **kw):
    OBJS[oid] = kw
    return oid


def rect_mask(x0, y0, x1, y1):
    return (XX >= x0) & (XX < x1) & (YY >= y0) & (YY < y1)


def circ_mask(cx, cy, r):
    return (XX - cx) ** 2 + (YY - cy) ** 2 < r * r


def put(mask, z, mat, oid, mode='max'):
    """Raise the height field to z over mask (z may be an array)."""
    zz = np.broadcast_to(np.asarray(z, np.float32), Hf.shape)
    if mode == 'max':
        m = mask & (zz >= Hf)
    else:
        m = mask
    Hf[m] = zz[m]
    MAT[m] = mat
    OBJ[m] = oid


def put_float(mask, zb, zt, mat, oid):
    zt = np.broadcast_to(np.asarray(zt, np.float32), Hf.shape)
    B2[mask] = zb
    T2[mask] = zt[mask]
    MAT2[mask] = mat
    OBJ2[mask] = oid


def crenel_ring_mask(mask, thick):
    """Outer band of a footprint, `thick` px wide."""
    inner = ndimage.binary_erosion(mask, iterations=int(thick))
    return mask & ~inner


def merlon_pattern(mask_band, along):
    """1 where a merlon stands: 14 px merlon, 9 px crenel, measured along the band."""
    return ((along % 23) < 14) & mask_band


# ---------------------------------------------------------------------------------------------------------------------
# GEOMETRY (plan px → world)
# ground: grass everywhere, paved berm inside the moat, dry moat between
put(np.ones((H, W), bool), 0, M_GRASS, 0, mode='set')
moat_out = rect_mask(wx(157), wy(458), wx(1716), wy(1810))
berm = rect_mask(wx(262), wy(563), wx(1611), wy(1705))
moat = moat_out & ~berm
MOAT_Z = -48
put(moat, MOAT_Z, M_MOAT, 1, mode='set')
put(berm, 0, M_BERM, 2, mode='set')
obj(1, kind='ground', face='revet')
obj(2, kind='ground', face='revet')
obj(0, kind='ground', face='revet')
# iron spikes on the moat floor, staggered rows
for gy in np.arange(wy(470), wy(1800), 22):
    for gx in np.arange(wx(170) + (11 if int(gy / 22) % 2 else 0), wx(1705), 22):
        if moat[int(gy), int(gx)]:
            m = rect_mask(gx, gy, gx + 2, gy + 2)
            put(m, MOAT_Z + 14, M_IRON, 3, mode='set')
obj(3, kind='spike')

# --- the body: four ranges around the cloister -------------------------------------------------------------------------
BX0, BY0, BX1, BY1 = wx(418), wy(718), wx(1457), wy(1549)      # outer face of the curtain
WALLT = 77 * S                                                    # curtain thickness (plan: 77 px)
CX0, CY0, CX1, CY1 = wx(768), wy(1042), wx(1107), wy(1224)       # open courtyard (arcade line)
WALK = 2 * STOREY                                                 # wall-walk level: top of the first floor
body = rect_mask(BX0, BY0, BX1, BY1)
court = rect_mask(CX0, CY0, CX1, CY1)
ranges = body & ~court
obj(10, kind='box', name='ranges', walk=WALK, courses=[STOREY, WALK])
put(ranges, WALK, M_WALK, 10)
# battered plinth (talus) along the outer foot of the curtain
dist_out = ndimage.distance_transform_edt(~body).astype(np.float32)
talus = (dist_out > 0) & (dist_out <= 12) & berm
put(talus, 30 * (1 - dist_out / 12), M_STONE, 10)
# roofs: hipped slate roof over the ranges, from the inner edge of the wall walk to the courtyard eaves
roof_fp = rect_mask(BX0 + WALLT, BY0 + WALLT, BX1 - WALLT, BY1 - WALLT) & ~court
d_roof = ndimage.distance_transform_cdt(roof_fp, metric='chessboard').astype(np.float32)   # straight hips
put(roof_fp, WALK + 2 + 0.42 * d_roof, M_SLATE, 11)      # ~23° pitch: ridge stays below the gatehouse and tower parapets
RIDGE = roof_fp & (ndimage.maximum_filter(d_roof, size=3) <= d_roof) & (d_roof > 3)
RIDGE = ndimage.binary_dilation(RIDGE, iterations=1) & roof_fp
obj(11, kind='roof')
# parapet on the outer edge of the curtain, with merlons
par = crenel_ring_mask(body, 10)
along = np.where((np.abs(YY - BY0) < 11) | (np.abs(YY - (BY1 - 1)) < 11), XX, YY)
put(par, WALK + 20, M_STONE, 10)
put(merlon_pattern(par, along), WALK + 34, M_STONE, 10)
# gutter/eaves stones along the courtyard edge
eave = crenel_ring_mask(rect_mask(CX0 - 6, CY0 - 6, CX1 + 6, CY1 + 6), 6) & ~court
put(eave, WALK + 4, M_STONE, 10)

# --- kitchen chimney (hearth in the north wall of the kitchen) -------------------------------------------------------
chim = rect_mask(wx(600), wy(742), wx(676), wy(800))
obj(12, kind='box', name='chimney', courses=[])
put(chim, WALK + 70, M_STONE, 12, mode='set')
put(rect_mask(wx(600) - 3, wy(742) - 3, wx(676) + 3, wy(800) + 3) & ~chim, WALK + 64, M_STONE, 12)  # cap
put(rect_mask(wx(615), wy(755), wx(661), wy(787)), WALK + 62, M_IRON, 12, mode='set')              # flue mouth

# --- corner towers -------------------------------------------------------------------------------------------------
TOWERS = {'NW': (443, 743), 'NE': (1431, 743), 'SW': (443, 1523), 'SE': (1431, 1523)}
TR = 129 * S
TOP_T = 3 * STOREY
for i, (k, (px, py)) in enumerate(TOWERS.items()):
    oid = 20 + i
    cx, cy = wx(px), wy(py)
    obj(oid, kind='cyl', cx=cx, cy=cy, r=TR, walk=TOP_T, courses=[STOREY, 2 * STOREY, TOP_T], name=k)
    c = circ_mask(cx, cy, TR)
    put(c, TOP_T, M_WALK, oid)
    dd = np.hypot(XX - cx, YY - cy)
    tal = (dd >= TR) & (dd < TR + 12) & berm
    put(tal, 30 * (1 - (dd - TR) / 12), M_STONE, oid)
    band = c & (dd > TR - 10)
    ang = (np.arctan2(YY - cy, XX - cx) * TR)
    put(band, TOP_T + 20, M_STONE, oid)
    put(merlon_pattern(band, ang - ang.min()), TOP_T + 34, M_STONE, oid)
    if k in ('NE', 'SW'):                 # spiral stairs come up into a capped stair head
        sid = 30 + i
        obj(sid, kind='cyl', cx=cx, cy=cy, r=30, courses=[], door=True)
        sc = circ_mask(cx, cy, 30)
        put(sc, TOP_T + 52, M_STONE, sid)
        put(sc, TOP_T + 52 + (30 - np.hypot(XX - cx, YY - cy)) * 1.6, M_SLATE, sid)
    else:                                   # lead flat with a hatch
        put(circ_mask(cx, cy, 18), TOP_T + 3, M_LEAD, oid)

# --- great tower (north side, King's tower) -----------------------------------------------------------------------
GX0, GY0, GX1, GY1 = wx(756), wy(666), wx(1119), wy(977)
UX0, UY0, UX1, UY1 = wx(784), wy(690), wx(1091), wy(953)          # levels 3-4, set back (plan)
G2 = 3 * STOREY                                                     # ground, first, second floor
G4 = 5 * STOREY                                                     # + levels 3 and 4
obj(40, kind='box', name='great', walk=G2, courses=[STOREY, 2 * STOREY, G2])
obj(41, kind='box', name='great_up', walk=G4, courses=[4 * STOREY, G4])
gt = rect_mask(GX0, GY0, GX1, GY1)
put(gt, G2, M_WALK, 40)
dd = ndimage.distance_transform_edt(~gt).astype(np.float32)
put((dd > 0) & (dd <= 12) & berm & ~body, 30 * (1 - dd / 12), M_STONE, 40)
gpar = crenel_ring_mask(gt, 10)
along = np.where((np.abs(YY - GY0) < 11) | (np.abs(YY - (GY1 - 1)) < 11), XX, YY)
put(gpar, G2 + 20, M_STONE, 40)
put(merlon_pattern(gpar, along), G2 + 34, M_STONE, 40)
up = rect_mask(UX0, UY0, UX1, UY1)
put(up, G4, M_WALK, 41)
upar = crenel_ring_mask(up, 10)
along = np.where((np.abs(YY - UY0) < 11) | (np.abs(YY - (UY1 - 1)) < 11), XX, YY)
put(upar, G4 + 20, M_STONE, 41)
put(merlon_pattern(upar, along), G4 + 34, M_STONE, 41)
# roof: stair head (spiral climbs every level) and the beacon
scx, scy = wx(1047), wy(820)
obj(42, kind='cyl', cx=scx, cy=scy, r=32, courses=[], door=True)
put(circ_mask(scx, scy, 32), G4 + 54, M_STONE, 42)
put(circ_mask(scx, scy, 32), G4 + 54 + (32 - np.hypot(XX - scx, YY - scy)) * 1.6, M_SLATE, 42)
bcx, bcy = wx(937), wy(819)
obj(43, kind='cyl', cx=bcx, cy=bcy, r=16, courses=[], name='beacon')
put(circ_mask(bcx, bcy, 26), G4 + 4, M_STONE, 43)                  # stone hearth for the beacon
put(circ_mask(bcx, bcy, 16), G4 + 22, M_IRON, 43)                  # iron fire basket
put(circ_mask(bcx, bcy, 11), G4 + 18, M_IRON, 44)                  # fire bed (lit later)
obj(44, kind='fire')

# --- gatehouse over the gate passage (east) ---------------------------------------------------------------------------
HX0, HY0, HX1, HY1 = wx(1172), wy(979), wx(1457), wy(1132)
obj(50, kind='box', name='gatehouse', walk=3 * STOREY, courses=[STOREY, 2 * STOREY, 3 * STOREY])
gh = rect_mask(HX0, HY0, HX1, HY1)
put(gh, 3 * STOREY, M_WALK, 50)
hpar = crenel_ring_mask(gh, 10)
along = np.where((np.abs(YY - HY0) < 11) | (np.abs(YY - (HY1 - 1)) < 11), XX, YY)
put(hpar, 3 * STOREY + 20, M_STONE, 50)
put(merlon_pattern(hpar, along), 3 * STOREY + 34, M_STONE, 50)
# gate approach across the berm and the drawbridge over the moat
appr = rect_mask(wx(1457), wy(1004), wx(1611), wy(1109))
put(appr, 0.5, M_COBBLE, 2, mode='set')
db = rect_mask(wx(1611), wy(1010), wx(1716), wy(1103))
obj(51, kind='box', name='drawbridge', courses=[])
put_float(db, -10, 0.0, M_DECK, 51)

# --- privy chute (west wall) -----------------------------------------------------------------------------------------
obj(52, kind='box', name='privy', courses=[STOREY])
pv = rect_mask(wx(366), wy(1056), wx(418), wy(1160))
put(pv, 2 * STOREY - 20 + (XX - wx(366)) * 0.3, M_SLATE, 52)

# --- covered bridge to the Sister's manor (first floor, south) ---------------------------------------------------------
KX0, KX1 = wx(596), wx(655)
br = rect_mask(KX0, BY1, KX1, H)
obj(53, kind='box', name='bridge', courses=[])
ridge = (KX0 + KX1) / 2
roofz = STOREY + 58 + (((KX1 - KX0) / 2) - np.abs(XX - ridge)) * 0.8
put_float(br, STOREY, roofz, M_SLATE, 53)
obj(54, kind='box', name='pier', courses=[])
pier = rect_mask(KX0 - 6, wy(1736), KX1 + 6, wy(1778))
put(pier, STOREY, M_STONE, 54, mode='set')

# --- courtyard: cobbles and the well ---------------------------------------------------------------------------------
put(court, 0, M_COBBLE, 2, mode='set')
wcx, wcy = wx(937), wy(1132)
obj(55, kind='cyl', cx=wcx, cy=wcy, r=26, courses=[], name='well')
wr = np.hypot(XX - wcx, YY - wcy)
put(wr < 26, 16, M_STONE, 55, mode='set')
put(wr < 17, -24, M_WATER, 55, mode='set')

# ---------------------------------------------------------------------------------------------------------------------
# PROJECTION: paint ground rows north → south; each cell fills screen rows y-z .. y (its top and its south face)
Hs = np.round(Hf).astype(np.int32) + ZB
B2s = np.round(B2).astype(np.int64) + ZB
T2s = np.round(T2).astype(np.int64) + ZB
OFF = int(max(Hs.max(), T2s[T2s < 1e8].max())) + 6
SH = H + OFF
GY = np.full((SH, W), -1, np.int32)
LAY = np.zeros((SH, W), np.int8)
ZS = np.zeros((SH, W), np.int32)
cols = np.arange(W)
for y in range(H):
    h = Hs[y]
    hm = int(h.max())
    z = np.arange(hm + 1)[:, None]
    mz, mx = np.nonzero(z <= h[None, :])
    sy = y + OFF - mz
    GY[sy, mx] = y; LAY[sy, mx] = 0; ZS[sy, mx] = mz
    t2 = T2s[y]
    has = t2 > -1e8
    if has.any():
        b2 = B2s[y]
        zlo, zhi = int(b2[has].min()), int(t2[has].max())
        z = np.arange(zlo, zhi + 1)[:, None]
        m = (z >= b2[None, :]) & (z <= t2[None, :]) & has[None, :]
        mz, mx = np.nonzero(m)
        sy = y + OFF - (mz + zlo)
        GY[sy, mx] = y; LAY[sy, mx] = 1; ZS[sy, mx] = mz + zlo

valid = GY >= 0
sy_idx, sx_idx = np.nonzero(valid)
gy = GY[valid]; gx = sx_idx; zz = ZS[valid] - ZB; lay = LAY[valid]
htop = np.where(lay == 0, Hs[gy, gx], T2s[gy, gx]) - ZB
is_top = zz >= htop
mat = np.where(lay == 0, MAT[gy, gx], MAT2[gy, gx])
oid = np.where(lay == 0, OBJ[gy, gx], OBJ2[gy, gx])
N = len(gy)
rng = np.random.default_rng(3)


def hsh(*a):
    v = np.zeros(len(a[0]), np.float64)
    for i, t in enumerate(a):
        v = v + np.asarray(t, np.float64) * (12.9898 + 31.4 * i)
    return (np.sin(v) * 43758.5453) % 1.0


# ---------------------------------------------------------------------------------------------------------------------
# SUN: low afternoon sun from the south-west. Shadow map = highest shadow line over each ground cell.
SUN = np.array([-0.62, 0.42, 0.66]); SUN = SUN / np.linalg.norm(SUN)
step_xy = np.array([SUN[0], SUN[1]]) / np.hypot(SUN[0], SUN[1])
rise = SUN[2] / np.hypot(SUN[0], SUN[1])
HfT = np.maximum(Hf, np.where(T2 > -1e8, T2, -1e9))
Ssh = np.full(Hf.shape, -1e9, np.float32)
for k in range(1, 900):
    dx, dy = int(round(step_xy[0] * k)), int(round(step_xy[1] * k))
    src = np.full(Hf.shape, -1e9, np.float32)
    ys0, ys1 = max(0, -dy), min(H, H - dy)
    xs0, xs1 = max(0, -dx), min(W, W - dx)
    src[ys0:ys1, xs0:xs1] = HfT[ys0 + dy:ys1 + dy, xs0 + dx:xs1 + dx]
    np.maximum(Ssh, src - k * rise, out=Ssh)
    if k * rise > 560: break

# normals for top surfaces from the height field gradient
Hsm = ndimage.gaussian_filter(Hf, 0.8)
gyd, gxd = np.gradient(Hsm)
nx, ny = -gxd, -gyd
nz = np.ones_like(nx)
nl = np.sqrt(nx ** 2 + ny ** 2 + nz ** 2)
lam_top = ((nx * SUN[0] + ny * SUN[1] + nz * SUN[2]) / nl)

col = np.zeros((N, 3), np.float64)

# ---- top surfaces --------------------------------------------------------------------------------------------------
t = is_top
tx, ty, tm, tz = gx[t], gy[t], mat[t], zz[t]
c = np.zeros((t.sum(), 3))
noise = rng.normal(0, 1, (t.sum(), 1))
# grass
m = tm == M_GRASS
c[m] = GRASS * (0.9 + 0.12 * hsh(tx[m] // 3, ty[m] // 3)[:, None]) + noise[m] * 4
tuft = m & (hsh(tx, ty) > 0.96)
c[tuft] = GRASS * 1.25
# berm & walk: flagstones 16x16 / 20x12
for mm, base, bw, bh in ((M_BERM, BERM, 20, 14), (M_WALK, STONE_TOP, 16, 12)):
    m = tm == mm
    row = ty[m] // bh
    xo = tx[m] + (row % 2) * (bw // 2)
    tone = 0.9 + 0.14 * hsh(xo // bw, row)
    cc = base * tone[:, None]
    joint = (ty[m] % bh == 0) | (xo % bw == 0)
    cc[joint] = MORTAR * 1.05
    hl = (ty[m] % bh == 1)
    cc[hl & ~joint] *= 1.07
    c[m] = cc + noise[m] * 2.5
# moat floor: earth, scuffed
m = tm == M_MOAT
c[m] = EARTH * (0.88 + 0.16 * hsh(tx[m] // 4, ty[m] // 4)[:, None]) + noise[m] * 4
# cobbles
m = tm == M_COBBLE
cx_, cy_ = tx[m], ty[m]
row = cy_ // 7
xo = cx_ + (row % 2) * 4
inside = ((xo % 8) - 3.5) ** 2 / 12 + ((cy_ % 7) - 3) ** 2 / 9 < 1
tone = 0.85 + 0.25 * hsh(xo // 8, row)
cc = COBBLE * tone[:, None]
cc[~inside] = MORTAR * 0.9
c[m] = cc + noise[m] * 3
# slate: courses follow the contour (rows by height), tiles staggered along the eaves direction
m = tm == M_SLATE
sx, syy, sz = tx[m], ty[m], tz[m]
grad_y = np.abs(gyd[syy, sx]) > np.abs(gxd[syy, sx])
alongc = np.where(grad_y, sx, syy)
row = np.floor(sz / 4.0).astype(int)
ao = alongc + (row % 2) * 5
tone = 0.84 + 0.24 * hsh(ao // 10, row)
cc = SLATE * tone[:, None]
cc[(np.floor(sz / 4.0) != np.floor((sz + 0.9) / 4.0))] = SLATE * 0.55           # lower lip of each course
cc[(ao % 10) == 0] = SLATE * 0.62
rg = RIDGE[syy, sx]
cc[rg] = np.array((150, 140, 134.)) * (0.9 + 0.15 * ((sx[rg] + syy[rg]) % 6 == 0))[:, None]   # ridge & hip capping
c[m] = cc + noise[m] * 2
# lead, iron, deck, water, timber
m = tm == M_LEAD; c[m] = LEAD * (0.95 + 0.06 * hsh(tx[m] // 12, ty[m])[:, None])
m = tm == M_IRON; c[m] = IRON + noise[m] * 3
m = tm == M_WATER; c[m] = np.array((40, 58, 74.)) + noise[m] * 3
m = tm == M_DECK
cc = TIMBER * (0.85 + 0.25 * hsh(ty[m] // 7, tx[m] // 40)[:, None])
cc[(ty[m] % 7) == 0] = TIMBER * 0.5
c[m] = cc
# stone tops that are not walk (merlon tops, plinths, chimney cap)
m = tm == M_STONE
row = ty[m] // 10
cc = STONE_TOP * (0.92 + 0.12 * hsh((tx[m] + (row % 2) * 8) // 16, row))[:, None]
cc[(ty[m] % 10 == 0) | (((tx[m] + (row % 2) * 8) % 16) == 0)] = MORTAR * 1.1
c[m] = cc + noise[m] * 2
# sunlight on tops (Lambert + ambient), the fire basket glows
lt = lam_top[ty, tx]
shade = 0.58 + 0.55 * np.clip(lt, 0, 1)
shadowed = tz < Ssh[ty, tx] - 1
shade = np.where(shadowed, 0.62 + 0.08 * np.clip(lt, 0, 1), shade)
c *= shade[:, None]
fire = oid[t] == 44
c[fire] = np.array((255, 170, 60.)) * (0.85 + 0.3 * hsh(tx[fire], ty[fire]))[:, None]
col[t] = c

# ---- faces (south-facing walls) --------------------------------------------------------------------------------------
f = ~is_top
fx, fy, fz, fo, fm = gx[f], gy[f], zz[f], oid[f], mat[f]
n = f.sum()
c = np.zeros((n, 3))
u = fx.astype(np.float64).copy()
lam = np.full(n, 0.0)
# horizontal normal: cylinders by angle; boxes face south
hn = np.tile(np.array([0.0, 1.0]), (n, 1))
for k, o in OBJS.items():
    if o.get('kind') == 'cyl':
        m = fo == k
        a = np.arctan2(fy[m] + 0.5 - o['cy'], fx[m] + 0.5 - o['cx'])
        hn[m, 0], hn[m, 1] = np.cos(a), np.sin(a)
        u[m] = (a - np.pi / 2) * o['r']           # arc length from the due-south point
lam = hn[:, 0] * SUN[0] + hn[:, 1] * SUN[1]
fshade = 0.52 + 0.42 * np.clip(lam / np.hypot(SUN[0], SUN[1]), 0, 1)
# ashlar: 8 px courses, 16 px blocks, half-bond
course = np.floor(fz / 8).astype(int)
uo = np.floor(u + (course % 2) * 8).astype(int)
tone = 0.88 + 0.16 * hsh(uo // 16, course, fo)
base = STONE[None, :] * tone[:, None]
joint = (np.floor(fz) % 8 == 0) | (uo % 16 == 0)
base[joint] = MORTAR
base[(np.floor(fz) % 8 == 7) & ~joint] *= 1.08                  # lit top arris of each block
mat_f = fm
# timber/slate faces keep their own colour
fht = htop[f]
base[(mat_f == M_SLATE) & (fo != 52) & (fz > fht - 5)] = SLATE * 0.6      # only the eaves lip is slate; below it is wall
base[mat_f == M_TIMBER] = TIMBER
base[mat_f == M_IRON] = IRON
base[mat_f == M_DECK] = TIMBER * 0.7
base[mat_f == M_MOAT] = EARTH * 0.8
base[mat_f == M_GRASS] = EARTH * 0.9


def paint(mask, color):
    base[mask] = color


# string courses: projecting band 3 px, lit top, shadow below
for k, o in OBJS.items():
    m0 = fo == k
    for zc in o.get('courses', []):
        b = m0 & (fz >= zc - 1) & (fz < zc + 2)
        paint(b, STONE_TOP * 1.04)
        paint(m0 & (fz >= zc - 3) & (fz < zc - 1), MORTAR * 0.8)
    if 'walk' in o:
        # corbel table (machicolation) under the parapet: corbels 6 px every 23 px, dark gaps (murder holes)
        zc = o['walk']
        b = m0 & (fz >= zc - 12) & (fz < zc)
        gap = ((np.floor(u) % 23) >= 14)
        paint(b & gap, np.array((44, 34, 32.)))
        paint(b & ~gap & (fz < zc - 9), STONE * 0.78)

# ---- openings ----------------------------------------------------------------------------------------------------
def loop(m, uc, z0, length=26):
    """Arrow loop: 3 px slit with a round oillet at each end, splayed reveal."""
    du = u - uc
    zr = fz - z0
    inn = m & (np.abs(du) <= 1.5) & (zr >= 0) & (zr < length)
    ends = m & (((du) ** 2 + (zr - 2) ** 2 < 6) | ((du) ** 2 + (zr - length + 2) ** 2 < 6))
    cross = m & (np.abs(zr - length / 2) <= 1) & (np.abs(du) <= 4)
    rev = m & (np.abs(du) <= 3.5) & (zr >= -1) & (zr < length + 1)
    paint(rev, STONE * 0.7)
    paint(inn | ends | cross, np.array((26, 20, 20.)))


def window(m, uc, z0, w=20, h=36, lights=2, glass=GLASS):
    """Arched window: dressed surround, leaded glass, mullion, projecting sill."""
    du = u - uc
    zr = fz - z0
    hw = w / 2
    arch_c = h - hw
    inside = (np.abs(du) < hw) & (zr >= 0) & ((zr < arch_c) | (du ** 2 + (zr - arch_c) ** 2 < hw ** 2))
    surround = (np.abs(du) < hw + 3) & (zr >= -2) & ((zr < arch_c) | (du ** 2 + (zr - arch_c) ** 2 < (hw + 3) ** 2))
    paint(m & surround, STONE_TOP * 1.02)
    lead = ((np.floor(du + zr) % 6) == 0) | ((np.floor(du - zr) % 6) == 0)
    g = m & inside
    base[g] = (glass * 1.0)
    base[g & lead] = glass * 0.55
    base[g & (zr > h * 0.55) & (du < 0)] = glass * 1.6                 # sky reflection, upper left
    if lights == 2:
        paint(m & inside & (np.abs(du) < 1.5), STONE_TOP)
    paint(m & (np.abs(du) < hw + 4) & (zr >= -4) & (zr < -1), STONE_TOP * 1.1)   # sill
    paint(m & (np.abs(du) < hw + 4) & (zr >= -6) & (zr < -4), MORTAR * 0.7)       # sill shadow


def door(m, uc, z0, w=16, h=30):
    du = u - uc; zr = fz - z0
    hw = w / 2; ac = h - hw
    ins = (np.abs(du) < hw) & (zr >= 0) & ((zr < ac) | (du ** 2 + (zr - ac) ** 2 < hw ** 2))
    sur = (np.abs(du) < hw + 3) & (zr >= 0) & ((zr < ac) | (du ** 2 + (zr - ac) ** 2 < (hw + 3) ** 2))
    paint(m & sur, STONE_TOP)
    plank = (np.floor(du + 100) % 4 == 0)
    paint(m & ins, TIMBER); paint(m & ins & plank, TIMBER * 0.6)
    paint(m & ins & ((np.abs(zr - 8) < 1) | (np.abs(zr - h + 12) < 1)), IRON)


def arcade(m, cols_u, z0, z1):
    """Cloister arcade at courtyard level: open arches (dark walk behind) between columns."""
    for a, b in zip(cols_u[:-1], cols_u[1:]):
        c0, c1 = a + 7, b - 7
        mid = (c0 + c1) / 2; hw = (c1 - c0) / 2
        spring = z1 - 10 - hw * 0.8
        du = u - mid; zr = fz - z0
        opening = (np.abs(du) < hw) & (zr >= 0) & ((fz < spring) | ((du / hw) ** 2 + ((fz - spring) / (hw * 0.8)) ** 2 < 1))
        dark = np.array((52, 44, 42.)) * (0.75 + 0.35 * (fz - z0) / (z1 - z0))[:, None] if False else None
        paint(m & opening, np.array((54, 46, 44.)))
        # glimpse of the walk floor and back wall at the foot
        paint(m & opening & (zr < 6), np.array((92, 84, 80.)))
        # voussoirs
        ring = (np.abs(du) < hw + 4) & (fz >= spring) & ((du / (hw + 4)) ** 2 + ((fz - spring) / (hw * 0.8 + 4)) ** 2 < 1) & ~opening
        paint(m & ring & (np.floor(np.arctan2(fz - spring, du) * 9) % 2 == 0), STONE_TOP * 1.05)
    for cu in cols_u:
        cm = m & (np.abs(u - cu) < 7) & (fz >= z0) & (fz < z1 - 8)
        paint(cm, STONE_TOP * 1.0)
        paint(cm & (u - cu > 3), STONE * 0.85)
        paint(m & (np.abs(u - cu) < 9) & (((fz >= z0) & (fz < z0 + 4)) | ((fz >= z1 - 22) & (fz < z1 - 17))), STONE_TOP * 1.1)


m_body = fo == 10
outer_south = m_body & (fy > wy(1500))                     # south face of the south range
court_face = m_body & (fy > CY0 - 3) & (fy < CY0 + 3)     # courtyard face of the north range
# south front: Stores | Lower hall | Guards' bunks below, Bridge lobby | Queen's solar | Guest chamber above.
# The plan draws no windows on the outer faces: the curtain gets arrow loops, staggered between storeys.
bays = np.arange(wx(560), wx(1340), 60)
for i, bx in enumerate(bays):
    loop(outer_south, bx + (30 if i % 2 else 0), 22, 28)
    loop(outer_south, bx + (0 if i % 2 else 30), STOREY + 22, 28)
# courtyard face: cloister arcade on the ground floor, gallery windows above (plan: two per side)
arcade(court_face, [wx(768), wx(845), wx(937), wx(1027), wx(1107)], 0, STOREY)
for wxp in (wx(862), wx(1015)):
    window(court_face, wxp, STOREY + 22, w=22, h=38, lights=2)
# corner towers: loops staggered round the tower, one ring per storey
for i in range(4):
    m = fo == 20 + i
    for s in range(3):
        for k2 in range(-3, 4):
            uc = (k2 + (0.5 if s % 2 else 0)) * 70
            loop(m, uc, s * STOREY + 24, 28)
# stair heads: door on the south side
for k in (31, 33, 42):
    if k in OBJS:
        door(fo == k, 0, (TOP_T if k != 42 else G4), 16, 30)
# great tower: loops on the lower storeys, lookout windows on level 4 (plan: north, south and west windows)
m = fo == 40
for s in range(3):
    for k2 in range(5):
        loop(m, wx(800) + k2 * (wx(1080) - wx(800)) / 4, s * STOREY + 24, 28)
m = fo == 41
for k2 in range(3):
    loop(m, wx(830) + k2 * (wx(1045) - wx(830)) / 2, 3 * STOREY + 24, 28)
window(m, wx(939), 4 * STOREY + 16, w=44, h=46, lights=2)
# gatehouse: winch room and watch room
m = fo == 50
for s in (1, 2):
    for k2 in range(3):
        loop(m, wx(1230) + k2 * (wx(1400) - wx(1230)) / 2, s * STOREY + 24, 28)
# privy: chute opening at the foot
m = fo == 52
paint(m & (fz < 14) & (np.abs(u - wx(392)) < 8), np.array((30, 24, 22.)))
# bridge: timber framed, glazed sides; its south end
m = fo == 53
paint(m, TIMBER)
paint(m & ((np.floor(u) % 12) < 2), TIMBER * 0.6)
# pier: cutwater courses
# moat revetment faces: ashlar already; darken towards the moat floor
rev = (fo <= 2) & (fz < 0)
base[rev] *= (0.7 + 0.3 * (fz[rev] + 48) / 48)[:, None]

# vertical faces shading + cast shadow
fsh = fz < Ssh[np.minimum(fy + 1, H - 1), fx] - 1
fs = np.where(fsh, 0.56, fshade)
# slope faces under roofs (eaves drops) are dark
c = base * fs[:, None] + rng.normal(0, 2.2, (n, 1))
col[f] = c

# ambient occlusion on the ground near tall things
ao = np.clip(ndimage.gaussian_filter(Hf, 10) - Hf, 0, 60) / 60
aot = ao[gy, gx]
col *= (1 - 0.35 * aot * (is_top & (mat != M_SLATE)))[:, None]

out = np.zeros((SH, W, 4), np.uint8)
out[sy_idx, sx_idx, :3] = np.clip(col, 0, 255).astype(np.uint8)
out[sy_idx, sx_idx, 3] = 255
img = Image.fromarray(out, 'RGBA')
TOPCROP = int(np.nonzero(out[..., 3].any(1))[0][0])

# beacon fire glow + smoke-free flame
from PIL import ImageDraw
d = ImageDraw.Draw(img)
fx0, fy0 = int(bcx), int(bcy + OFF - (G4 + 22 + ZB))
for r, a in ((26, 40), (16, 80), (9, 160)):
    glow = Image.new('RGBA', img.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((fx0 - r, fy0 - r - 8, fx0 + r, fy0 + r - 8), fill=(255, 170, 60, a))
    img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(4)))
d = ImageDraw.Draw(img)
d.polygon([(fx0 - 8, fy0), (fx0 + 8, fy0), (fx0 + 3, fy0 - 16), (fx0, fy0 - 24), (fx0 - 3, fy0 - 14)], fill=(255, 150, 40))
d.polygon([(fx0 - 4, fy0), (fx0 + 4, fy0), (fx0, fy0 - 12)], fill=(255, 230, 140))

img = img.crop((0, max(0, TOPCROP - 8), img.width, img.height))
out_path = sys.argv[1] if len(sys.argv) > 1 else 'holdfast_proto.png'
img.save(out_path)
print('saved', out_path, img.size, 'OFF', OFF, 'scale', round(S, 4))
