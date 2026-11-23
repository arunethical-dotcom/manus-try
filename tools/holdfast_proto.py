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
import sys, os
DOORS = os.environ.get('DOORS', 'edge')      # flat | south | edge | angled | real
SHEAR = float(os.environ.get('SHEAR', '0'))  # camera turned sideways: <0 sees east faces, >0 west faces
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

# ---------------------------------------------------------------------------------------------------------------------
# plan → world.  Plan coordinates are pixels of the full-size plan image (3800 x 4276), ground-floor drawing.
S = 1586 / (1561 - 314)              # castle incl. towers is 314..1561 on the plan
PX0, PY0 = 105, 406                   # top-left of the plan's grass border
EXTRA_S = 150                         # extra ground south of the plan


def wx(px): return (px - PX0) * S
def wy(py): return (py - PY0) * S


W = int(round(wx(1768)))
H = int(round(wy(1860))) + EXTRA_S
STOREY = 80
ZB = 64                               # height-field offset so the dry moat (negative z) stays >= 0

# ---------------------------------------------------------------------------------------------------------------------
# palette
STONE = np.array((214, 168, 104.))    # warm golden sandstone: the keep's other buildings (Great Hall, Barracks, Throne Hall)
STONE_TOP = np.array((236, 202, 142.))
MORTAR = np.array((138, 96, 48.))
SLATE = np.array((46, 90, 182.))      # the keep's bright blue roofs
LEAD = np.array((206, 162, 102.))     # flat roofs paved in the same sandstone as the walls
GRASS = np.array((92, 150, 58.))
BERM = np.array((206, 178, 134.))
EARTH = np.array((112, 78, 44.))
COBBLE = np.array((180, 150, 108.))
TIMBER = np.array((136, 84, 32.))
IRON = np.array((54, 54, 60.))
GLASS = np.array((30, 52, 108.))

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
put(roof_fp, WALK + 2, M_LEAD, 11)      # flat lead roof over the ranges, just above the wall walk, behind the parapets
RIDGE = np.zeros_like(roof_fp)
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
chim = rect_mask(wx(640), wy(766), wx(716), wy(810))   # on the inner face of the north wall, so the walk passes it
obj(12, kind='box', name='chimney', courses=[])
put(chim, WALK + 70, M_STONE, 12, mode='set')
put(rect_mask(wx(640) - 3, wy(766) - 3, wx(716) + 3, wy(810) + 3) & ~chim, WALK + 64, M_STONE, 12)  # cap
put(rect_mask(wx(655), wy(774), wx(701), wy(802)), WALK + 62, M_IRON, 12, mode='set')              # flue mouth

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

# --- doorway porches where the north and south wall walks run into the corner towers -------------------------------
# The walk meets these towers on their east/west sides, which face away from a 3/4 camera. So each tower gets a small
# vaulted doorway bay built out onto the inner half of the walk (the walk is ~98 px wide, so the outer half stays clear
# for passing guards). Its door faces south, onto the walk, and is Kael-sized (18 x 36).
PORCHES = []
for i, (k, (px, py)) in enumerate(TOWERS.items()):
    cx, cy = wx(px), wy(py)
    north = k in ('NW', 'NE')
    y0 = BY0 + 14 if north else BY1 - WALLT + 2
    y1 = BY0 + WALLT * 0.55 if north else BY1 - WALLT * 0.42
    if k in ('NW', 'SW'):
        x0, x1 = cx + TR - 24, cx + TR + 34
    else:
        x0, x1 = cx - TR - 34, cx - TR + 24
    pid = 60 + i
    obj(pid, kind='box', name='porch_' + k, courses=[])
    pm = rect_mask(x0, y0, x1, y1)
    facing = 'E' if k in ('NW', 'SW') else 'W'
    D = 30
    if DOORS == 'angled':      # end of the bay cut at 45 degrees, so the door looks along the walk and toward the camera
        if facing == 'E':
            pm &= ~((XX + YY) > (x1 + y1 - D))
        else:
            pm &= ~((YY - XX) > (y1 - D - x0))
    put(pm, WALK + 44, M_WALK, pid)                       # flat top
    put(crenel_ring_mask(pm, 4), WALK + 50, M_STONE, pid)  # low coping round the flat top
    yc = (y0 + y1) / 2
    # stone threshold step on the walk in front of the door
    if DOORS in ('edge', 'real'):
        tx0 = x1 if facing == 'E' else x0 - 9
        put(rect_mask(tx0, yc - 13, tx0 + 9, yc + 13), WALK + 3, M_STONE, 2)
    elif DOORS == 'angled':
        mx_, my_ = (x1 - D / 2, y1 - D / 2) if facing == 'E' else (x0 + D / 2, y1 - D / 2)
        sx_ = 1 if facing == 'E' else -1
        put(rect_mask(mx_ + sx_ * 6 - 9, my_ + 6 - 9, mx_ + sx_ * 6 + 9, my_ + 6 + 9) & ~pm, WALK + 3, M_STONE, 2)
    elif DOORS == 'south':
        put(rect_mask((x0 + x1) / 2 - 13, y1, (x0 + x1) / 2 + 13, y1 + 9), WALK + 3, M_STONE, 2)
    PORCHES.append((pid, x0, x1, y0, y1, facing))

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

# --- door bays at every other place a wall walk runs into a taller building --------------------------------------------
# Same rule as the four tower bays: each door faces along the walk it serves, the way it would in reality. Doors facing
# south can be seen from the camera; doors facing north, east or west are edge-on/hidden and only their step shows.
BAYS = []


def bay(name, x0, y0, x1, y1, facing):
    bid = 70 + len(BAYS)
    obj(bid, kind='box', name='bay_' + name, courses=[])
    m = rect_mask(x0, y0, x1, y1)
    put(m, WALK + 44, M_WALK, bid)
    put(crenel_ring_mask(m, 4), WALK + 50, M_STONE, bid)
    xc, yc = (x0 + x1) / 2, (y0 + y1) / 2
    step = {'S': (xc - 13, y1, xc + 13, y1 + 9), 'N': (xc - 13, y0 - 9, xc + 13, y0),
            'E': (x1, yc - 13, x1 + 9, yc + 13), 'W': (x0 - 9, yc - 13, x0, yc + 13)}[facing]
    put(rect_mask(*step), WALK + 3, M_STONE, 2)
    BAYS.append((bid, x0, y0, x1, y1, facing))


def tower_edge_y(k, xm, south):
    cx, cy = wx(TOWERS[k][0]), wy(TOWERS[k][1])
    dy = np.sqrt(max(TR ** 2 - (xm - cx) ** 2, 0))
    return cy + dy if south else cy - dy


# west walk (runs north-south): NW tower door faces south, SW tower door faces north
wa, wb = BX0 + 12, BX0 + WALLT * 0.55
ye = tower_edge_y('NW', (wa + wb) / 2, True);  bay('NW_w', wa, ye - 24, wb, ye + 34, 'S')
ye = tower_edge_y('SW', (wa + wb) / 2, False); bay('SW_w', wa, ye - 34, wb, ye + 24, 'N')
# east walk: NE tower faces south; gatehouse north side faces north, south side faces south; SE tower faces north
ea, eb = BX1 - WALLT * 0.55, BX1 - 12
ye = tower_edge_y('NE', (ea + eb) / 2, True);  bay('NE_e', ea, ye - 24, eb, ye + 34, 'S')
bay('gate_n', ea, HY0 - 34, eb, HY0 + 2, 'N')
bay('gate_s', ea, HY1 - 2, eb, HY1 + 34, 'S')
ye = tower_edge_y('SE', (ea + eb) / 2, False); bay('SE_e', ea, ye - 34, eb, ye + 24, 'N')
# north walk meets the great tower: west part's door faces west, east part's faces east
na, nb = BY0 + 14, BY0 + WALLT * 0.55
bay('great_w', GX0 - 34, na, GX0 + 2, nb, 'W')
bay('great_e', GX1 - 2, na, GX1 + 34, nb, 'E')

# --- privy chute (west wall) -----------------------------------------------------------------------------------------
obj(52, kind='box', name='privy', courses=[STOREY])
pv = rect_mask(wx(366), wy(1056), wx(418), wy(1160))
put(pv, 2 * STOREY - 20 + (XX - wx(366)) * 0.3, M_SLATE, 52)


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
KY = 0.62          # 3/4 view: ground depth foreshortened, heights drawn full
YS = np.round(np.arange(H) * KY).astype(np.int64)
zmax_all = int(max(Hs.max(), T2s[T2s < 1e8].max())) - ZB
XOFF = int(np.ceil(max(0, -SHEAR * zmax_all))) + int(np.ceil(abs(SHEAR) * ZB)) + 2
SWID = W + XOFF + int(np.ceil(max(0, SHEAR * zmax_all))) + int(np.ceil(abs(SHEAR) * ZB)) + 2
SH = int(YS[-1]) + 1 + OFF
GY = np.full((SH, SWID), -1, np.int32)
GXB = np.full((SH, SWID), -1, np.int32)
LAY = np.zeros((SH, SWID), np.int8)
ZS = np.zeros((SH, SWID), np.int32)
DEP = np.full((SH, SWID), -1e18)


def splat(y, mz, mx, layer):
    zr = mz - ZB
    sx = mx + XOFF + np.round(SHEAR * zr).astype(np.int64)
    sy = YS[y] + OFF - mz
    dep = -SHEAR * mx + y / KY + zr                      # nearness to the camera
    keep = dep > DEP[sy, sx]
    sx, sy, dep, mz, mx = sx[keep], sy[keep], dep[keep], mz[keep], mx[keep]
    o = np.argsort(dep, kind='stable')                   # repeated pixels: the nearest is written last
    sx, sy, dep, mz, mx = sx[o], sy[o], dep[o], mz[o], mx[o]
    GY[sy, sx] = y; GXB[sy, sx] = mx; LAY[sy, sx] = layer; ZS[sy, sx] = mz; DEP[sy, sx] = dep


for y in range(H):
    h = Hs[y]
    hm = int(h.max())
    z = np.arange(hm + 1)[:, None]
    mz, mx = np.nonzero(z <= h[None, :])
    splat(y, mz, mx, 0)
    t2 = T2s[y]
    has = t2 > -1e8
    if has.any():
        b2 = B2s[y]
        zlo, zhi = int(b2[has].min()), int(t2[has].max())
        z = np.arange(zlo, zhi + 1)[:, None]
        m = (z >= b2[None, :]) & (z <= t2[None, :]) & has[None, :]
        mz, mx = np.nonzero(m)
        splat(y, mz + zlo, mx, 1)

valid = GY >= 0
sy_idx, sx_idx = np.nonzero(valid)
gy = GY[valid]; gx = GXB[valid]; zz = ZS[valid] - ZB; lay = LAY[valid]
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
m = tm == M_LEAD
row = ty[m] // 14
xo = tx[m] + (row % 2) * 12
cc = LEAD * (0.9 + 0.14 * hsh(xo // 24, row))[:, None]          # large roof flags, 24 x 14, half-bond
joint = (ty[m] % 14 == 0) | (xo % 24 == 0)
cc[joint] = MORTAR * 1.05
cc[(ty[m] % 14 == 1) & ~joint] *= 1.06
c[m] = cc + noise[m] * 1.5
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
side_face = np.zeros(n, bool)
if SHEAR != 0:
    dxs = 1 if SHEAR < 0 else -1                          # neighbour on the camera side
    lay_f = lay[f]
    Hn_side = Hf[fy, np.clip(fx + dxs, 0, W - 1)]
    Hn_south = Hf[np.clip(fy + 1, 0, H - 1), fx]
    side_face = (lay_f == 0) & (Hn_side < fz) & ~(Hn_south < fz)
    hn[side_face] = (dxs, 0.0)
    u[side_face] = fy[side_face]
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
    """Cross arrow loop (ground floor, defensive): dressed stone frame, splayed reveal, slit with round oillets at
    the ends and on a short cross-arm for sighting."""
    du = u - uc
    zr = fz - z0
    # dressed frame: one tall stone each side + lintel and sill blocks, outlined with mortar
    frame = m & (np.abs(du) <= 6) & (zr >= -4) & (zr < length + 4)
    paint(frame, STONE_TOP * 1.04)
    paint(frame & ((np.abs(du) > 5.2) | (zr < -3) | (zr >= length + 3)), MORTAR)
    paint(frame & ((np.abs(zr + 1) < 0.6) | (np.abs(zr - length - 1) < 0.6)), MORTAR)       # lintel/sill joints
    paint(frame & (zr >= length) & (du < -2), STONE_TOP * 1.15)                               # lit lintel edge
    # splayed reveal, darker inward
    rev = m & (np.abs(du) <= 3.5) & (zr >= 0) & (zr < length)
    paint(rev, STONE * 0.62)
    paint(rev & (du > 1.5), STONE * 0.48)                                                     # shaded side
    dark = np.array((22, 16, 16.))
    slit = m & (np.abs(du) <= 1.0) & (zr >= 1) & (zr < length - 1)
    arm = m & (np.abs(zr - length * 0.55) <= 0.8) & (np.abs(du) <= 5)
    ends = m & (((du ** 2 + (zr - 2) ** 2) < 5) | ((du ** 2 + (zr - length + 2) ** 2) < 5) |
                (((du - 4.5) ** 2 + (zr - length * 0.55) ** 2) < 3.2) | (((du + 4.5) ** 2 + (zr - length * 0.55) ** 2) < 3.2))
    paint(slit | arm | ends, dark)


def lancet(m, uc, z0, w=12, h=32, bars=False):
    """Lancet window (upper floors): pointed arch of two arcs, dressed jambs and voussoirs, leaded glass with a sky
    glint, projecting sill with its shadow, and a hood mould over the arch."""
    du = u - uc
    zr = fz - z0
    hw = w / 2
    spring = h - w * 0.85                                    # where the arch starts
    def pointed(r_extra):
        R = w + r_extra                                      # equilateral-ish arch: arcs centred on the far jamb
        lw = hw + r_extra
        left = ((du + hw) ** 2 + (zr - spring) ** 2) < R ** 2
        right = ((du - hw) ** 2 + (zr - spring) ** 2) < R ** 2
        return (np.abs(du) < lw) & (zr >= 0) & ((zr < spring) | (left & right))
    opening = m & pointed(0)
    surround = m & pointed(3) & (zr >= -2)
    hood = m & pointed(5) & ~pointed(3) & (zr >= spring - 2)
    paint(hood, STONE_TOP * 1.12)
    paint(m & pointed(6) & ~pointed(5) & (zr >= spring - 2), MORTAR * 0.75)                # hood shadow line
    paint(surround, STONE_TOP * 1.02)
    # voussoir joints on the arch, block joints on the jambs
    ang = np.arctan2(zr - spring, du)
    paint(surround & ~opening & (zr >= spring) & ((np.floor(ang * 5.5) % 2) == 0), STONE_TOP * 0.9)
    paint(surround & ~opening & (zr < spring) & ((np.floor(zr) % 9) == 0), MORTAR)
    # glass: dark leaded panes, diamond lead lines, upper-left sky glint, deep shadow at the top of the reveal
    g = opening
    paint(g, GLASS)
    lead = ((np.floor(du + zr) % 5) == 0) | ((np.floor(du - zr + 40) % 5) == 0)
    paint(g & lead, GLASS * 0.5)
    paint(g & (du < -1) & (zr > spring * 0.5) & (zr < spring + 3) & ~lead, GLASS * 1.7)
    paint(g & (np.abs(du) >= hw - 1.2), GLASS * 0.45)                                       # reveal shadow
    if bars:                                              # ground floor: iron grille set in the reveal
        paint(g & ((np.floor(du + hw) % 4) == 1), IRON * 1.3)
        paint(g & (np.abs(zr - spring * 0.5) < 0.8), IRON * 1.3)
    # sill
    paint(m & (np.abs(du) < hw + 4) & (zr >= -4) & (zr < -1), STONE_TOP * 1.12)
    paint(m & (np.abs(du) < hw + 4) & (zr >= -6) & (zr < -4), MORTAR * 0.6)


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
    lancet(outer_south, bx + (0 if i % 2 else 30), 30, w=12, h=26, bars=True)   # high sill, barred
    lancet(outer_south, bx + (0 if i % 2 else 30), STOREY + 22)
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
            (lancet(m, uc, 30, w=12, h=26, bars=True) if s == 0 else lancet(m, uc, s * STOREY + 22))
# stair heads: door on the south side
for k in (31, 33, 42):
    if k in OBJS:
        door(fo == k, 0, (TOP_T if k != 42 else G4), 16, 30)
# doors onto the wall walk (Kael-sized: 18 x 36 px), where the walk runs into a taller building's south face
for bid, x0, y0, x1, y1, facing in BAYS:
    if facing == 'S':
        door((fo == bid) & ~side_face, (x0 + x1) / 2, WALK, 18, 36)
    elif SHEAR != 0 and ((facing == 'E' and SHEAR < 0) or (facing == 'W' and SHEAR > 0)):
        door((fo == bid) & side_face, (y0 + y1) / 2, WALK, 18, 36)
for pid, x0, x1, y0, y1, facing in PORCHES:
    m = fo == pid
    yc = (y0 + y1) / 2
    if DOORS == 'south':
        door(m & ~side_face, (x0 + x1) / 2, WALK, 18, 36)
    elif DOORS == 'angled':
        D = 30
        if facing == 'E':
            ch = m & (np.abs(fx + fy - (x1 + y1 - D)) <= 2)
            hn[ch] = (0.7071, 0.7071); u[ch] = (fx[ch] - fy[ch]) / 1.4142 * 1.0
            door(ch, (x1 - y1) / 1.4142, WALK, 18, 36)
        else:
            ch = m & (np.abs(fy - fx - (y1 - D - x0)) <= 2)
            hn[ch] = (-0.7071, 0.7071); u[ch] = (fx[ch] + fy[ch]) / 1.4142
            door(ch, (x0 + y1) / 1.4142, WALK, 18, 36)
    elif DOORS == 'real':
        door(m & side_face, yc, WALK, 18, 36)
# great tower: loops on the lower storeys, lookout windows on level 4 (plan: north, south and west windows)
m = fo == 40
for s in range(3):
    for k2 in range(5):
        lancet(m, wx(800) + k2 * (wx(1080) - wx(800)) / 4, s * STOREY + 22)
m = fo == 41
for k2 in range(3):
    lancet(m, wx(830) + k2 * (wx(1045) - wx(830)) / 2, 3 * STOREY + 22)
window(m, wx(939), 4 * STOREY + 16, w=44, h=46, lights=2)
# gatehouse: winch room and watch room
m = fo == 50
for s in (1, 2):
    for k2 in range(3):
        lancet(m, wx(1230) + k2 * (wx(1400) - wx(1230)) / 2, s * STOREY + 22)
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
lam = hn[:, 0] * SUN[0] + hn[:, 1] * SUN[1]
fshade = 0.52 + 0.42 * np.clip(lam / np.hypot(SUN[0], SUN[1]), 0, 1)
fs = np.where(fsh, 0.56, fshade)
# slope faces under roofs (eaves drops) are dark
c = base * fs[:, None] + rng.normal(0, 2.2, (n, 1))
col[f] = c

# ambient occlusion on the ground near tall things
ao = np.clip(ndimage.gaussian_filter(Hf, 10) - Hf, 0, 60) / 60
aot = ao[gy, gx]
col *= (1 - 0.35 * aot * (is_top & (mat != M_SLATE)))[:, None]

out = np.zeros((SH, SWID, 4), np.uint8)
out[sy_idx, sx_idx, :3] = np.clip(col, 0, 255).astype(np.uint8)
out[sy_idx, sx_idx, 3] = 255
img = Image.fromarray(out, 'RGBA')
TOPCROP = int(np.nonzero(out[..., 3].any(1))[0][0])

# beacon fire glow + smoke-free flame
from PIL import ImageDraw
d = ImageDraw.Draw(img)
fx0, fy0 = int(bcx + XOFF + SHEAR * (G4 + 22)), int(round(bcy * KY) + OFF - (G4 + 22 + ZB))
for r, a in ((26, 40), (16, 80), (9, 160)):
    glow = Image.new('RGBA', img.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((fx0 - r, fy0 - r - 8, fx0 + r, fy0 + r - 8), fill=(255, 170, 60, a))
    img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(4)))
d = ImageDraw.Draw(img)
d.polygon([(fx0 - 8, fy0), (fx0 + 8, fy0), (fx0 + 3, fy0 - 16), (fx0, fy0 - 24), (fx0 - 3, fy0 - 14)], fill=(255, 150, 40))
d.polygon([(fx0 - 4, fy0), (fx0 + 4, fy0), (fx0, fy0 - 12)], fill=(255, 230, 140))


# ---- side doors (3/4 RPG convention) ---------------------------------------------------------------------------------
# The tower doors face east or west, along the walk. A 3/4 camera cannot see east/west faces, so, as in top-down RPGs,
# the doorway is drawn into the top of the door bay: a sideways arch with its oak door, opening onto the walk, with the
# threshold step lying on the walk in front of it.
def side_door(img, x0, x1, y0, y1, facing):
    d = ImageDraw.Draw(img)
    yc = (y0 + y1) / 2
    top = round(yc * KY) + OFF - (WALK + 44 + ZB)          # screen row of the bay's top, at its centre line
    walk = round(yc * KY) + OFF - (WALK + ZB)              # screen row of the walk surface
    L, R = 34, 9                                           # door length (its height, laid sideways), half-width
    sgn = 1 if facing == 'E' else -1
    xe = (x1 if facing == 'E' else x0) + XOFF               # the end of the bay that meets the walk
    xi = xe - sgn * L                                      # inner end (arch head)
    xa, xb = sorted((xi, xe))
    stone_l, stone_d = (222, 204, 196), (120, 100, 96)
    # dressed surround
    d.rectangle((xa - 2, top - R - 3, xb, top + R + 3), fill=stone_l)
    d.ellipse((xi - R - 3, top - R - 3, xi + R + 3, top + R + 3), fill=stone_l)
    # door: oak planks running along the door's height, two iron straps, ring handle
    d.rectangle((xa, top - R, xb - 1, top + R), fill=(132, 86, 48))
    d.ellipse((xi - R, top - R, xi + R, top + R), fill=(132, 86, 48))
    for yy in range(int(top - R) + 3, int(top + R), 4):
        d.line((min(xi, xe), yy, max(xi, xe), yy), fill=(84, 52, 28))
    for k in (8, L - 10):
        xs = xe - sgn * k
        d.line((xs, top - R + 1, xs, top + R - 1), fill=(56, 56, 62), width=2)
    d.ellipse((xe - sgn * 18 - 2, top + 2, xe - sgn * 18 + 2, top + 6), outline=(190, 180, 120))
    d.arc((xi - R - 3, top - R - 3, xi + R + 3, top + R + 3), 0, 360, fill=stone_d)
    # threshold step on the walk in front of the door
    xt0, xt1 = sorted((xe, xe + sgn * 9))
    d.rectangle((xt0, walk - R - 2, xt1, walk + R + 2), fill=(214, 196, 186), outline=stone_d)
    d.line((xt0, walk - R - 1, xt1, walk - R - 1), fill=(236, 222, 214))


for pid, x0, x1, y0, y1, facing in (PORCHES if DOORS == 'flat' else []):
    img = img.convert('RGBA')
    side_door(img, x0, x1, y0, y1, facing)

img = img.crop((0, max(0, TOPCROP - 8), img.width, img.height))
out_path = sys.argv[1] if len(sys.argv) > 1 else 'holdfast_proto.png'
img.save(out_path)
print('saved', out_path, img.size, 'OFF', OFF, 'scale', round(S, 4))
