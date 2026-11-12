#!/usr/bin/env python3
"""Holdfast design sheet: a buildable courtyard castle that holds the nine rooms of the master plan.
Left: floor plan (1 tile = 16 game px).  Right: 3/4 front view massing (the game's view) with every way up for the watch.
Output: design/keep/holdfast_design.png"""
import os, math
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FB = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'; FR = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
def f(n, b=True): return ImageFont.truetype(FB if b else FR, n)

# ------------------------------------------------------------ layout in tiles (x east, y south)
COLS = [(0, 20), (20, 46), (46, 66)]
ROWS = [(0, 13), (13, 29), (29, 42)]
ROOMS = [["King's solar", "King's bed", "Queen's solar"],
         ["Princess", "WELL COURT", "Gate + winch"],
         ["Nursery", "Crown prince", "Waiting room"]]
MOAT = 9                                   # moat width around the curtain
TOWERS = {'NW': (0, 0), 'NE': (66, 0), 'SW': (0, 42), 'SE': (66, 42)}
TR = 5
WALL = 2                                    # outer wall / wall-walk width

# ------------------------------------------------------------ plan panel
S = 12; PX, PY = 60, 150
pw = (66 + 2 * MOAT) * S; ph = (42 + 2 * MOAT + 10) * S
plan = Image.new('RGB', (pw + 2 * PX, ph + PY + 40), (92, 140, 70)); d = ImageDraw.Draw(plan, 'RGBA')
T = lambda x, y: (PX + (x + MOAT) * S, PY + (y + MOAT) * S)
# moat
d.rounded_rectangle([T(-MOAT, -MOAT), T(66 + MOAT, 42 + MOAT)], 30, fill=(40, 32, 28), outline=(150, 135, 115), width=4)
for i in range(-MOAT + 1, 66 + MOAT, 3):
    for j in range(-MOAT + 1, 42 + MOAT, 3):
        if -1 <= i <= 67 and -1 <= j <= 43: continue
        x, y = T(i, j); d.polygon([(x, y + 5), (x + 3, y - 6), (x + 6, y + 5)], fill=(150, 150, 160))
# rooms
fills = {'WELL COURT': (165, 160, 145)}
for r, (y0, y1) in enumerate(ROWS):
    for c, (x0, x1) in enumerate(COLS):
        n = ROOMS[r][c]
        d.rectangle([T(x0, y0), T(x1, y1)], fill=fills.get(n, (178, 90, 82)), outline=(50, 30, 25), width=3)
# wall-walk band on the outer edge
d.rectangle([T(0, 0), T(66, 42)], outline=(222, 205, 170), width=WALL * S)
d.rectangle([T(0, 0), T(66, 42)], outline=(50, 30, 25), width=3)
# towers
for k, (x, y) in TOWERS.items():
    cx, cy = T(x, y); d.ellipse([cx - TR * S, cy - TR * S, cx + TR * S, cy + TR * S], fill=(160, 78, 70), outline=(50, 30, 25), width=3)
    for a in range(0, 360, 40):
        d.line([(cx, cy), (cx + 3.6 * S * math.cos(math.radians(a)), cy + 3.6 * S * math.sin(math.radians(a)))], fill=(230, 210, 180), width=2)
    d.text((cx - 9, cy - 9), 'S', font=f(16), fill=(30, 20, 15))
# watchtower over NW (taller) marked
# gallery round the well court (upper floor, timber) + court stair
d.rectangle([T(20, 13), T(46, 29)], outline=(140, 95, 50), width=2 * S // 2)
x0, y0 = T(28, 13.4); x1, y1 = T(38, 15.6)
d.rectangle([x0, y0, x1, y1], fill=(210, 195, 160), outline=(60, 40, 30), width=2)
for i in range(1, 10):
    xx = x0 + i * (x1 - x0) / 10; d.line([(xx, y0), (xx, y1)], fill=(90, 70, 50), width=1)
d.polygon([(x1 - 2, (y0 + y1) / 2), (x1 - 16, y0 + 3), (x1 - 16, y1 - 3)], fill=(60, 40, 30))
# well
cx, cy = T(33, 22); d.ellipse([cx - 22, cy - 22, cx + 22, cy + 22], fill=(110, 110, 110), outline=(40, 40, 40), width=3); d.ellipse([cx - 12, cy - 12, cx + 12, cy + 12], fill=(40, 70, 120))
# gates / passages
def door(x, y, o, n=3, col=(120, 80, 45)):
    a = T(x, y); b = T(x + n, y) if o == 'h' else T(x, y + n)
    d.line([a, b], fill=col, width=8)
door(46, 19.5, 'v'); door(66, 19.5, 'v', 3, (30, 30, 30)); door(20, 19.5, 'v'); door(31.5, 29, 'h'); door(31.5, 13, 'h')
door(8, 29, 'h'); door(54, 29, 'h'); door(8, 13, 'h'); door(54, 13, 'h'); door(20, 5, 'v'); door(46, 5, 'v'); door(20, 34, 'v'); door(46, 34, 'v')
# drawbridge east
d.rectangle([T(66, 19), T(66 + MOAT, 23)], fill=(150, 100, 55), outline=(50, 30, 25), width=3)
# covered bridge south-west
d.rectangle([T(7, 42), T(13, 42 + MOAT + 6)], fill=(178, 90, 82), outline=(50, 30, 25), width=3)
d.rectangle([T(8.5, 42), T(11.5, 42 + MOAT + 6)], fill=(200, 180, 150))
# privy chute west (way in D)
x, y = T(0, 18); d.rectangle([x - 2.5 * S, y, x, y + 2 * S], fill=(110, 90, 70), outline=(40, 30, 25), width=2)
# secret stair K, Kingsguard posts
cx, cy = T(20, 13); d.ellipse([cx - 10, cy - 10, cx + 10, cy + 10], fill=(60, 210, 170), outline=(20, 40, 30), width=2)
for (x, y) in [(33, 13.9), (64.5, 11.5), (66 + MOAT + 1, 25), (46.8, 19)]:
    cx, cy = T(x, y); d.polygon([(cx, cy - 11), (cx + 11, cy), (cx, cy + 11), (cx - 11, cy)], fill=(235, 238, 245), outline=(30, 30, 40))
# labels
for r, (y0, y1) in enumerate(ROWS):
    for c, (x0, x1) in enumerate(COLS):
        n = ROOMS[r][c]; cx, cy = T((x0 + x1) / 2, (y0 + y1) / 2 + (2.2 if n == 'WELL COURT' else 0))
        for k_, line in enumerate(n.split(' ') if len(n) > 12 else [n]):
            pass
        lines = {"King's solar": ["King's", 'solar'], "King's bed": ["King's", 'bedchamber'], "Queen's solar": ["Queen's", 'solar'],
                 'Gate + winch': ['Gate +', 'winch'], 'Crown prince': ['Crown', 'prince'], 'Waiting room': ['Waiting', 'room']}.get(n, [n])
        for k_, l in enumerate(lines):
            tw = d.textlength(l, font=f(17)); d.text((cx - tw / 2, cy - 12 * len(lines) + 24 * k_), l, font=f(17), fill='white', stroke_width=3, stroke_fill=(40, 20, 15))
def lab(x, y, t, col=(255, 255, 255), n=15):
    X, Y = T(x, y); d.text((X, Y), t, font=f(n), fill=col, stroke_width=3, stroke_fill=(20, 15, 10))
lab(28, 10.6, 'court stair', (255, 235, 180), 13); lab(20.6, 27.4, 'timber gallery (upper floor)', (255, 220, 160), 12)
lab(67, 16.6, 'DRAWBRIDGE', (255, 220, 150)); lab(14, 46, 'covered bridge to', (255, 255, 255), 13); lab(14, 47.6, "the sister's apartments", (255, 255, 255), 13)
lab(-8.5, 15.6, 'D privy', (255, 255, 255), 13); lab(-8.5, 21, 'chute', (255, 255, 255), 13); lab(5, -7.6, 'DRY MOAT, IRON SPIKES (9 tiles = 144 px)', (230, 230, 230), 15)
d.text((PX, PY - 70), 'FLOOR PLAN', font=f(30), fill='white')
d.text((PX, PY - 34), 'Curtain 66 x 42 tiles (1056 x 672 px) + 9-tile moat.  S = spiral stair in each corner tower.', font=f(16, False), fill=(235, 240, 230))

# ------------------------------------------------------------ 3/4 massing panel (game view: fronts face south, tops foreshortened)
K = 0.62; Z = 1.0; S2 = 13
mw = (66 + 2 * MOAT + 8) * S2; mh = int((42 + 2 * MOAT) * K * S2 + 30 * S2 + 80)
ms = Image.new('RGB', (mw + 80, mh + 80), (92, 140, 70)); m = ImageDraw.Draw(ms, 'RGBA')
OX, OY = 40 + (MOAT + 4) * S2, 60 + (30 + MOAT * K) * S2
P = lambda x, y, z=0: (OX + x * S2, OY + (y * K - z * Z) * S2)
BRICK, BRICK_D, ROOF, ROOF_D, STONE, OUT = (188, 88, 78), (140, 60, 54), (78, 86, 112), (58, 64, 86), (205, 190, 160), (45, 28, 24)
def box(x0, y0, x1, y1, z, top=BRICK, front=BRICK_D, crenel=False, roof=False):
    m.polygon([P(x0, y1, z), P(x1, y1, z), P(x1, y1, 0), P(x0, y1, 0)], fill=front, outline=OUT)
    for yy in range(1, int(z)):                       # brick courses
        m.line([P(x0, y1, yy), P(x1, y1, yy)], fill=(120, 52, 46), width=1)
    if roof:
        ym = (y0 + y1) / 2
        m.polygon([P(x0, y1, z), P(x1, y1, z), P(x1, ym, z + 3), P(x0, ym, z + 3)], fill=ROOF, outline=OUT)
        m.polygon([P(x0, y0, z), P(x1, y0, z), P(x1, ym, z + 3), P(x0, ym, z + 3)], fill=ROOF_D, outline=OUT)
    else:
        m.polygon([P(x0, y0, z), P(x1, y0, z), P(x1, y1, z), P(x0, y1, z)], fill=top, outline=OUT)
    if crenel:
        for xx in range(int(x0), int(x1), 2):
            m.rectangle([P(xx, y1, z + 1.6), P(xx + 1, y1, z)], fill=front, outline=OUT)
def tower(cx, cy, r, z, cone=True, label=None):
    def ell(zz):
        (x0, y0), (x1, y1) = P(cx - r, cy - r, zz), P(cx + r, cy + r, zz)
        return [x0, y0, x1, y1]
    e0, e1 = ell(0), ell(z)
    m.ellipse(e0, fill=BRICK_D, outline=OUT)
    m.rectangle([e1[0], (e1[1] + e1[3]) / 2, e1[2], (e0[1] + e0[3]) / 2], fill=BRICK_D)
    m.line([(e1[0], (e1[1] + e1[3]) / 2), (e0[0], (e0[1] + e0[3]) / 2)], fill=OUT, width=1)
    m.line([(e1[2], (e1[1] + e1[3]) / 2), (e0[2], (e0[1] + e0[3]) / 2)], fill=OUT, width=1)
    m.ellipse(e1, fill=STONE, outline=OUT)
    for k in range(12):
        ang = k * math.pi / 6
        if math.sin(ang) < -0.2: continue
        px_, py_ = P(cx + r * math.cos(ang), cy + r * math.sin(ang), z)
        m.rectangle([px_ - 4, py_ - 9, px_ + 4, py_], fill=BRICK, outline=OUT)
    if cone:
        apx, apy = P(cx, cy, z + r * 1.4)
        m.polygon([(e1[0], (e1[1] + e1[3]) / 2), (e1[2], (e1[1] + e1[3]) / 2), (apx, apy)], fill=ROOF, outline=OUT)
    for k in range(int(z // 2.2)):                    # stair slits winding up (the spiral inside)
        sx = cx + r * 0.6 * math.sin(k * 1.5); px_, py_ = P(sx, cy + r, 1.2 + k * 2.2)
        m.rectangle([px_ - 2, py_ - 7, px_ + 2, py_], fill=(30, 20, 18))
# moat
m.rounded_rectangle([P(-MOAT, -MOAT)[0], P(-MOAT, -MOAT)[1], P(66 + MOAT, 42 + MOAT)[0], P(66 + MOAT, 42 + MOAT)[1]], 24, fill=(40, 32, 28), outline=(150, 135, 115), width=4)
m.rectangle([P(-MOAT, -MOAT)[0] + 4, P(-MOAT, -MOAT)[1] + 4, P(66 + MOAT, -MOAT)[0] - 4, P(66 + MOAT, -MOAT)[1] + 5 * S2], fill=(70, 60, 54))
for i in range(-MOAT + 1, 66 + MOAT, 3):
    for j in (-MOAT + 3, 42 + MOAT - 2):
        x, y = P(i, j); m.polygon([(x, y), (x + 3, y - 14), (x + 6, y)], fill=(160, 160, 170))
for j in range(-MOAT + 4, 42 + MOAT - 2, 4):
    for i in (-MOAT + 2, 66 + MOAT - 2):
        x, y = P(i, j); m.polygon([(x, y), (x + 3, y - 14), (x + 6, y)], fill=(160, 160, 170))
# rock base under the castle (stands on the moat floor)

H_R, H_T, H_W = 7, 11, 16
# back to front
box(0, 0, 66, 13, H_R, roof=True)                                     # north range
m.polygon([P(0, 0, H_R), P(66, 0, H_R), P(66, 2, H_R), P(0, 2, H_R)], fill=STONE, outline=OUT)
for xx in range(0, 66, 2): m.rectangle([P(xx, 0, H_R + 1.6), P(xx + 1, 0, H_R)], fill=BRICK, outline=OUT)
tower(0, 0, TR, H_W, label='watch')                                     # NW watchtower (tallest, beacon)
bx, by = P(0, 0, H_W + TR * 1.4 + 1.5); m.ellipse([bx - 8, by - 8, bx + 8, by + 8], fill=(255, 150, 40))
tower(66, 0, TR, H_T)
box(0, 13, 20, 29, H_R, roof=True); box(46, 13, 66, 29, H_R, roof=True)  # west / east ranges
box(20, 13, 46, 29, 0.6, top=(165, 160, 145), front=(130, 125, 112))    # well court floor
# timber gallery round the court (upper floor) + court stair up to it
for (x0_, x1_) in ((20, 46),):
    m.polygon([P(20, 15, 4), P(46, 15, 4), P(46, 15, 3.4), P(20, 15, 3.4)], fill=(140, 95, 50), outline=OUT)
    for xx in range(21, 46, 2): m.line([P(xx, 15, 4), P(xx, 15, 5.4)], fill=(110, 75, 40), width=2)
m.line([P(20, 15, 5.4), P(46, 15, 5.4)], fill=(110, 75, 40), width=3)
for k in range(4):                                                      # stair steps rising east, against the north range
    m.rectangle([P(28 + k * 1.5, 15.6, k + 1)[0], P(28 + k * 1.5, 15.6, k + 1)[1], P(29.5 + k * 1.5, 15.6, 0)[0], P(29.5 + k * 1.5, 15.6, 0)[1]], fill=STONE, outline=OUT)
cx_, cy_ = P(33, 22, 0.6); m.ellipse([cx_ - 18, cy_ - 11, cx_ + 18, cy_ + 11], fill=(110, 110, 110), outline=OUT); m.ellipse([cx_ - 10, cy_ - 6, cx_ + 10, cy_ + 6], fill=(40, 70, 120))
# east gatehouse tower over the gate + drawbridge
box(66, 19, 66 + MOAT, 23, 0.8, top=(150, 100, 55), front=(110, 72, 40))
box(60, 17, 68, 25, H_T - 1, crenel=True)
m.rectangle([P(66.2, 25, 4)[0], P(66.2, 25, 4)[1], P(67.8, 25, 0)[0], P(67.8, 25, 0)[1]], fill=(30, 22, 18))
box(0, 29, 66, 42, H_R, roof=True)                                     # south range (front)
for xx in range(0, 66, 2): m.rectangle([P(xx, 42, H_R + 1.6), P(xx + 1, 42, H_R)], fill=BRICK, outline=OUT)
# south gate door + windows on the front
m.rectangle([P(31.5, 42, 3.5)[0], P(31.5, 42, 3.5)[1], P(34.5, 42, 0)[0], P(34.5, 42, 0)[1]], fill=(110, 70, 40), outline=OUT)
for xx in list(range(4, 30, 5)) + list(range(38, 64, 5)):
    for zz in (1.5, 4.5):
        m.rectangle([P(xx, 42, zz + 1.5)[0], P(xx, 42, zz + 1.5)[1], P(xx + 1.2, 42, zz)[0], P(xx + 1.2, 42, zz)[1]], fill=(30, 22, 18))
tower(0, 42, TR, H_T); tower(66, 42, TR, H_T)
# covered bridge SW
box(7, 42, 13, 42 + MOAT + 6, 4, top=ROOF, front=BRICK_D)
# privy chute on the west wall
m.rectangle([P(-2, 20, 6)[0], P(-2, 20, 6)[1], P(0, 20, 0)[0], P(0, 20, 3)[1]], fill=(120, 95, 70), outline=OUT)
# numbered callouts
def call(n, x, y, z):
    X, Y = P(x, y, z); m.ellipse([X - 15, Y - 15, X + 15, Y + 15], fill=(255, 220, 90), outline=(30, 20, 10), width=2)
    tw = m.textlength(str(n), font=f(17)); m.text((X - tw / 2, Y - 11), str(n), font=f(17), fill=(30, 20, 10))
call(1, -7, 0, H_W - 2); call(2, 31, 16, 6); call(3, 22, 15, 6.5); call(4, 33, 0, H_R + 4); call(5, 72, 18, 3); call(6, 64, 21, H_T + 3)
call(7, 15, 50, 4); call(8, -4, 20, 6); call(9, 36, 42, 5); call(10, 72, 42, H_T - 3)
ms_d = ImageDraw.Draw(ms); ms_d.text((40, 14), '3/4 VIEW (game view) - how the watch climbs', font=f(30), fill='white')

# ------------------------------------------------------------ sheet
key = ['1  NW watchtower, tallest (beacon on top): spiral stair from the court to the roof',
       '2  Court stair: from the well court up to the timber gallery',
       '3  Timber gallery: upper floor, runs round the court, doors into every room + all 4 towers',
       '4  Wall-walk: on top of the outer walls of all four ranges, joins the 4 tower tops',
       '5  Drawbridge (east), raised at night',
       '6  Gate tower over the gate + winch room; its stair reaches the wall-walk',
       "7  Covered bridge to the sister's apartments (locked both sides at night)",
       '8  Privy chute into the moat (way in D)',
       '9  South door of the Crown prince range (service, barred at night)',
       '10 Corner towers NE / SE / SW: spiral stairs ground -> gallery -> wall-walk -> tower top',
       'Watch route: court stair or any tower -> gallery -> tower -> wall-walk loop -> 4 tower tops.',
       'Ground floor = the 9 rooms of the plan.  Upper floor = more royal rooms off the gallery.']
W_ = plan.width + ms.width + 30; H_ = max(plan.height, ms.height) + 110 + len(key) * 26 + 30
sheet = Image.new('RGB', (W_, H_), (14, 14, 18)); sd = ImageDraw.Draw(sheet)
sd.rectangle([0, 0, W_, 90], fill=(0, 0, 0))
sd.text((20, 12), 'THE HOLDFAST - DESIGN (castle within the castle)', font=f(40), fill='white')
sd.text((22, 60), 'Courtyard castle round the well court. Nine ground-floor rooms as in the master plan. Red brick, slate roofs, dry spiked moat.', font=f(18, False), fill=(210, 210, 215))
sheet.paste(plan, (0, 100)); sheet.paste(ms, (plan.width + 30, 100))
y = 110 + max(plan.height, ms.height)
for k in key:
    sd.text((24, y), k, font=f(18, k[0].isdigit() and False), fill=(240, 235, 220)); y += 26
out = os.path.join(ROOT, 'design/keep/holdfast_design.png'); sheet.save(out); print(out, sheet.size)
