"""Interior floor renderer.

Draws a top-down (3/4) interior floor in the style of the painted Holdfast ground floor: stone wall tops with a
visible south face, floors per room (flagstone, planks, cobbles, packed earth), windows set into the outer walls with
daylight falling onto the floor, door openings, stairs, and furniture with soft drop shadows.

Usage (see tools/interior/floors/*.py):
    f = Floor(w, h, mat='sand', seed=1)
    f.floor((x0, y0, x1, y1), 'flag')
    f.wall((x0, y0, x1, y1), outer=True)
    f.opening(...) / f.window(...) / f.prop(fn, x, y, ...)
    img, meta = f.render()

Coordinates are world pixels (Kael is 26 px tall). All shapes are axis-aligned rects unless stated.
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

# --- stone materials, matched to each building's exterior --------------------------------------------------------
MATS = {
    # top, top_dark (mortar/outline), face, face_dark, floor flag base
    'sand':   dict(top=(214, 182, 122), mortar=(132, 100, 58), face=(170, 136, 82), face_d=(110, 82, 46),
                   flag=(176, 158, 128), flag_m=(118, 102, 80)),
    'grey':   dict(top=(178, 176, 186), mortar=(92, 90, 104), face=(134, 132, 146), face_d=(82, 80, 94),
                   flag=(150, 148, 156), flag_m=(100, 98, 108)),
    'rose':   dict(top=(196, 172, 166), mortar=(112, 90, 86), face=(152, 128, 122), face_d=(96, 76, 72),
                   flag=(160, 150, 150), flag_m=(104, 96, 98)),
    'marble': dict(top=(232, 222, 204), mortar=(150, 136, 112), face=(196, 184, 162), face_d=(132, 118, 96),
                   flag=(214, 206, 190), flag_m=(160, 150, 132)),
    'dark':   dict(top=(118, 112, 108), mortar=(62, 58, 56), face=(88, 82, 80), face_d=(52, 48, 46),
                   flag=(104, 98, 94), flag_m=(66, 62, 60)),
}
FACE_H = 18          # visible height of a wall's south face, px
SHADOW = (24, 18, 14)


def _rng(seed):
    return np.random.default_rng(seed)


def _clip(a):
    return np.clip(a, 0, 255)


# --- floor textures ----------------------------------------------------------------------------------------------
def tex_flag(w, h, base, mortar, rng, sx=(18, 30), sy=(14, 20)):
    """Irregular flagstones: rows of slabs, each slab its own tone, bevel light top-left, mortar seams."""
    a = np.zeros((h, w, 3), float)
    y = -rng.integers(0, 10)
    while y < h:
        rh = int(rng.integers(*sy))
        x = -int(rng.integers(0, 20))
        while x < w:
            sw = int(rng.integers(*sx))
            tone = np.array(base, float) * (0.9 + 0.16 * rng.random()) + rng.normal(0, 1.2, 3)
            y0, y1, x0, x1 = max(y, 0), min(y + rh, h), max(x, 0), min(x + sw, w)
            if y1 > y0 and x1 > x0:
                a[y0:y1, x0:x1] = tone
                # bevel
                if y >= 0: a[y0 + 1:y0 + 2, x0:x1] = tone * 1.10
                if x >= 0: a[y0:y1, x0 + 1:x0 + 2] = tone * 1.06
                if y + rh - 2 < h and y + rh - 2 >= 0: a[y + rh - 2, x0:x1] = tone * 0.86
                if x + sw - 2 < w and x + sw - 2 >= 0: a[y0:y1, x + sw - 2] = tone * 0.9
                # mortar
                if y >= 0: a[y0, x0:x1] = mortar
                if x >= 0: a[y0:y1, x0] = mortar
                # a crack or chip now and then
                if rng.random() < 0.12:
                    cx, cy = int(rng.integers(x0, x1)), int(rng.integers(y0, y1))
                    for _ in range(int(rng.integers(3, 8))):
                        if 0 <= cy < h and 0 <= cx < w: a[cy, cx] = np.array(mortar) * 1.05
                        cx += int(rng.integers(-1, 2)); cy += 1
            x += sw
        y += rh
    a += rng.normal(0, 2.4, (h, w, 1))
    return a


def tex_plank(w, h, base, rng, ph=8, vertical=False):
    """Wooden boards with staggered butt joints, grain streaks and nail heads."""
    if vertical:
        return np.transpose(tex_plank(h, w, base, rng, ph), (1, 0, 2))
    a = np.zeros((h, w, 3), float)
    seam = np.array(base) * 0.55
    for r, y in enumerate(range(0, h, ph)):
        x = -int(rng.integers(0, 80))
        while x < w:
            L = int(rng.integers(50, 130))
            tone = np.array(base, float) * (0.86 + 0.22 * rng.random())
            x0, x1 = max(x, 0), min(x + L, w)
            y1 = min(y + ph, h)
            if x1 > x0:
                blk = np.ones((y1 - y, x1 - x0, 3)) * tone
                # grain: a couple of long darker streaks
                for _ in range(2):
                    gy = int(rng.integers(1, max(2, y1 - y - 1)))
                    gx0 = int(rng.integers(0, max(1, x1 - x0)))
                    gl = int(rng.integers(10, 50))
                    blk[gy, gx0:gx0 + gl] *= 0.9
                blk[0] = blk[0] * 1.12                 # lit top edge of the board
                a[y:y1, x0:x1] = blk
                if x >= 0:
                    a[y:y1, x0] = seam
                    if y + 2 < h and x0 + 3 < w:
                        a[y + 2, x0 + 3] = (60, 50, 44); a[min(y + ph - 3, h - 1), x0 + 3] = (60, 50, 44)
            x += L
        if y + ph - 1 < h: a[y + ph - 1, :] = seam
    a += rng.normal(0, 2.5, (h, w, 1))
    return a


def tex_cobble(w, h, base, mortar, rng):
    a = np.ones((h, w, 3)) * np.array(mortar, float)
    pts = []
    for y in range(0, h + 8, 7):
        for x in range(-(y // 7 % 2) * 4, w + 8, 8):
            pts.append((x + rng.integers(-1, 2), y + rng.integers(-1, 2)))
    for (x, y) in pts:
        tone = np.array(base, float) * (0.85 + 0.25 * rng.random())
        for dy in range(-3, 3):
            for dx in range(-3, 4):
                if dx * dx / 10 + dy * dy / 7 <= 1:
                    xx, yy = x + dx, y + dy
                    if 0 <= xx < w and 0 <= yy < h:
                        k = 1.12 if (dx + dy) < -2 else (0.85 if dx + dy > 2 else 1.0)
                        a[yy, xx] = tone * k
    return a + rng.normal(0, 2.5, (h, w, 1))


def tex_earth(w, h, base, rng):
    a = np.ones((h, w, 3)) * np.array(base, float)
    n = rng.normal(0, 1, (h // 4 + 2, w // 4 + 2))
    n = np.kron(n, np.ones((4, 4)))[:h, :w]
    a *= (1 + 0.05 * n)[..., None]
    a += rng.normal(0, 4, (h, w, 1))
    for _ in range(w * h // 300):             # pebbles
        x, y = rng.integers(0, w - 2), rng.integers(0, h - 2)
        a[y:y + 2, x:x + 2] = np.array(base) * 1.25
        a[y + 2:y + 3, x:x + 2] = np.array(base) * 0.7 if y + 2 < h else a[y:y + 1, x:x + 2]
    return a


# --- the floor ---------------------------------------------------------------------------------------------------
class Floor:
    def __init__(self, w, h, mat='sand', seed=1, bg=(0, 0, 0, 0)):
        self.w, self.h = w, h
        self.m = MATS[mat]
        self.rng = _rng(seed)
        self.rgb = np.zeros((h, w, 3), float)
        self.inside = np.zeros((h, w), bool)        # covered by some floor
        self.wallm = np.zeros((h, w), bool)
        self.outer = np.zeros((h, w), bool)         # outer-wall pixels (get the coping rim)
        self.nofacem = np.zeros((h, w), bool)       # wall pixels that should not cast a face (e.g. thresholds)
        self.props = []                             # (z, fn, kwargs)
        self.lights = []                            # day light patches: (poly, strength)
        self.glows = []                             # torch glows (x, y, r)
        self.windows = []
        self.cut = []                               # rects carved out after walls (openings)
        self.post = []                              # draw callbacks after walls (window glass etc.)
        self.meta = dict(size=[w, h], doors=[], stairs=[], torches=[], windows=[], rooms=[], solid_extra=[])
        self.bg = bg

    # floors
    def floor(self, r, kind='flag', base=None, **kw):
        x0, y0, x1, y1 = map(int, r)
        w, h = x1 - x0, y1 - y0
        rng = self.rng
        if kind == 'flag':
            t = tex_flag(w, h, base or self.m['flag'], self.m['flag_m'], rng, **kw)
        elif kind == 'plank':
            t = tex_plank(w, h, base or (172, 108, 58), rng, **kw)
        elif kind == 'cobble':
            t = tex_cobble(w, h, base or (150, 144, 136), (92, 86, 80), rng)
        elif kind == 'earth':
            t = tex_earth(w, h, base or (120, 96, 70), rng)
        elif kind == 'slab':     # big dressed slabs (marble halls)
            t = tex_flag(w, h, base or self.m['flag'], self.m['flag_m'], rng, sx=(30, 44), sy=(30, 34))
        else:
            raise ValueError(kind)
        self.rgb[y0:y1, x0:x1] = t
        self.inside[y0:y1, x0:x1] = True

    def room(self, name, r):
        self.meta['rooms'].append(dict(name=name, rect=list(map(int, r))))

    # walls
    def wall(self, r, outer=False):
        x0, y0, x1, y1 = map(int, r)
        self.wallm[y0:y1, x0:x1] = True
        if outer: self.outer[y0:y1, x0:x1] = True

    def ring(self, r, t, outer=True):
        """Closed rectangular wall of thickness t whose OUTER edge is rect r."""
        x0, y0, x1, y1 = r
        self.wall((x0, y0, x1, y0 + t), outer); self.wall((x0, y1 - t, x1, y1), outer)
        self.wall((x0, y0, x0 + t, y1), outer); self.wall((x1 - t, y0, x1, y1), outer)

    def round_wall(self, cx, cy, r_out, t, outer=True):
        yy, xx = np.mgrid[0:self.h, 0:self.w]
        d = np.hypot(xx - cx, yy - cy)
        m = (d <= r_out) & (d >= r_out - t)
        self.wallm |= m
        if outer: self.outer |= m

    def opening(self, r, kind='door', name=None, to=None, leaf='open_in', side='S'):
        """Carve a door opening through a wall. kind: door | arch | exit. 'side' = which side of the room the wall is
        on (S = the opening is in a south wall, viewed from the north)."""
        x0, y0, x1, y1 = map(int, r)
        self.cut.append((x0, y0, x1, y1))
        self.meta['doors'].append(dict(name=name, rect=[x0, y0, x1, y1], kind=kind, to=to, side=side))
        self.post.append(('door', dict(r=(x0, y0, x1, y1), kind=kind, leaf=leaf, side=side)))

    def window(self, x0, x1, side='S', y=None, x=None, lights=2, reach=110, glass='lead'):
        """Window set in an outer wall. For S/N walls give x0..x1 and the wall band y (top,bottom) via y=(y0,y1);
        for E/W walls give y-range as x0..x1 and the band via x=(xa,xb)."""
        self.windows.append(dict(a=x0, b=x1, side=side, band=y if side in 'NS' else x, lights=lights, reach=reach,
                                 glass=glass))
        self.meta['windows'].append(dict(a=x0, b=x1, side=side, band=list(y if side in 'NS' else x)))

    def torch(self, x, y, room=0, side='N'):
        self.meta['torches'].append([int(x), int(y), room, 1])
        self.post.append(('torch', dict(x=x, y=y, side=side)))
        self.glows.append((x, y + 6, 70))

    def prop(self, fn, x, y, z=None, shadow=True, **kw):
        self.props.append((y if z is None else z, fn, x, y, shadow, kw))

    def stair(self, r, direction='up', name=None, to=None, axis='y', low='N'):
        """Straight stair in rect r. direction up: treads rise toward the far end. 'descend_to' gives which end is
        lower (for 'down' stairs the lower end goes dark)."""
        self.meta['stairs'].append(dict(name=name, rect=list(map(int, r)), dir=direction, to=to))
        self.post.append(('stair', dict(r=r, direction=direction, axis=axis, low=low)))

    def spiral(self, cx, cy, r, name=None, to=None, direction='up'):
        self.meta['stairs'].append(dict(name=name, rect=[cx - r, cy - r, cx + r, cy + r], dir=direction, to=to))
        self.post.append(('spiral', dict(cx=cx, cy=cy, r=r)))

    # ---------------------------------------------------------------------------------------------------------------
    def render(self):
        h, w = self.h, self.w
        m = self.m
        rng = self.rng
        for (x0, y0, x1, y1) in self.cut:
            self.wallm[y0:y1, x0:x1] = False
            self.outer[y0:y1, x0:x1] = False
        # carve window embrasures out of the solid mass later (they stay solid for collision)
        wall = self.wallm
        rgb = self.rgb.copy()
        inside = self.inside & ~wall
        # ambient occlusion on the floor next to walls
        wimg = Image.fromarray((wall * 255).astype(np.uint8))
        ao = np.array(wimg.filter(ImageFilter.GaussianBlur(7))).astype(float) / 255.0
        rgb *= (1 - 0.45 * ao)[..., None]
        # long soft shadow cast south-east by walls (light from the north-west windows/skylight)
        sh = np.zeros((h, w), float)
        sh[6:, 4:] = wall[:-6, :-4]
        sh = np.array(Image.fromarray((sh * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(5))) / 255.0
        rgb *= (1 - 0.30 * sh * ~wall)[..., None]

        # south faces of walls: floor pixels within FACE_H below a wall pixel (only where wall is directly above)
        face = np.zeros((h, w), bool)
        facek = np.zeros((h, w), int)
        below = wall.copy()
        for k in range(1, FACE_H + 1):
            src = np.zeros((h, w), bool)
            src[k:] = wall[:-k]
            nf = src & ~wall & ~face & ~self.nofacem
            # only continue a face column if every pixel between is face (contiguous)
            if k > 1:
                prev = np.zeros((h, w), bool); prev[1:] = face[:-1] | wall[:-1]
                nf &= prev
            facek[nf] = k
            face |= nf
        # don't draw faces over openings' thresholds outside the building
        face &= inside | self.inside
        self.face = face
        # face texture: ashlar courses 6 px high, darker towards the floor, lit top edge
        yy, xx = np.mgrid[0:h, 0:w]
        course = (facek - 1) // 6
        joint = ((facek - 1) % 6 == 5) | (((xx + course * 9) % 22) == 0)
        ft = np.array(m['face'], float) * (1.0 - 0.018 * facek)[..., None]
        ft = np.where(joint[..., None], np.array(m['face_d'], float), ft)
        ft += rng.normal(0, 3, (h, w, 1))
        ft[facek == 1] = np.array(m['top']) * 0.72        # under-lip shadow of the coping
        ft[facek == FACE_H] = np.array(m['face_d']) * 0.8  # foot of the wall
        rgb = np.where(face[..., None], ft, rgb)

        # wall tops: block pattern
        bh, bw = 10, 20
        row = yy // bh
        bx = (xx + (row % 2) * (bw // 2)) // bw
        blk_id = row * 997 + bx
        tone = 0.9 + 0.14 * ((np.sin(blk_id * 12.9898) * 43758.5453) % 1.0)
        top = np.array(m['top'], float) * tone[..., None]
        top += rng.normal(0, 2.5, (h, w, 1))
        jy = (yy % bh == 0)
        jx = ((xx + (row % 2) * (bw // 2)) % bw == 0)
        hl = (yy % bh == 1)
        top = np.where(hl[..., None], top * 1.08, top)
        top = np.where((jy | jx)[..., None], np.array(m['mortar'], float) * 1.15, top)
        # dark outline around the whole wall mass + coping rim on outer walls
        er = np.array(Image.fromarray((wall * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(3))) > 0
        edge = wall & ~er
        er2 = np.array(Image.fromarray((wall * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(7))) > 0
        rim = wall & ~er2 & ~edge
        top = np.where(rim[..., None], top * 1.07, top)
        top = np.where(edge[..., None], np.array(m['mortar'], float) * 0.75, top)
        rgb = np.where(wall[..., None], top, rgb)

        img = np.concatenate([_clip(rgb), np.zeros((h, w, 1))], 2)
        alpha = (self.inside | wall | face)
        img[..., 3] = alpha * 255
        canvas = Image.fromarray(img.astype(np.uint8), 'RGBA')

        # post-wall details: doors, stairs, window embrasures, torches
        for kind, kw in self.post:
            if kind == 'door': self._draw_door(canvas, **kw)
            elif kind == 'stair': self._draw_stair(canvas, **kw)
            elif kind == 'spiral': self._draw_spiral(canvas, **kw)
        for wd in self.windows: self._draw_window(canvas, wd)

        # props, back to front, each with a soft drop shadow
        shadow_layer = Image.new('L', (w, h), 0)
        sprites = []
        for z, fn, x, y, shadow, kw in sorted(self.props, key=lambda t: t[0]):
            spr, ox, oy = fn(rng=rng, **kw)
            px, py = int(x - ox), int(y - oy)
            sprites.append((spr, px, py))
            if shadow:
                a = spr.split()[3].point(lambda v: 150 if v > 0 else 0)
                shadow_layer.paste(a, (px + 3, py + 4), a)
        shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(2.5))
        sl = np.array(shadow_layer).astype(float) / 255.0
        arr = np.array(canvas).astype(float)
        arr[..., :3] *= (1 - 0.55 * sl)[..., None]
        canvas = Image.fromarray(_clip(arr).astype(np.uint8), 'RGBA')
        for spr, px, py in sprites:
            canvas.alpha_composite(spr, (px, py))
        for kind, kw in self.post:
            if kind == 'torch': self._draw_torch(canvas, **kw)

        # light: windows (daylight pools) + torch glow, additive warm
        light = Image.new('L', (w, h), 0)
        ld = ImageDraw.Draw(light)
        for poly, s in self.lights:
            ld.polygon(poly, fill=int(255 * s))
        light = light.filter(ImageFilter.GaussianBlur(14))
        L = np.array(light).astype(float) / 255.0
        glow = np.zeros((h, w), float)
        for (gx, gy, r) in self.glows:
            y0, y1, x0, x1 = max(0, gy - r), min(h, gy + r), max(0, gx - r), min(w, gx + r)
            if y1 <= y0 or x1 <= x0: continue
            yy2, xx2 = np.mgrid[y0:y1, x0:x1]
            d = np.hypot(xx2 - gx, yy2 - gy) / r
            glow[y0:y1, x0:x1] += np.clip(1 - d, 0, 1) ** 2
        arr = np.array(canvas).astype(float)
        day = np.array((255, 244, 214), float)
        fire = np.array((255, 170, 80), float)
        arr[..., :3] = arr[..., :3] * (0.80 + 0.42 * L[..., None]) + day * 0.12 * L[..., None]
        arr[..., :3] += fire * 0.22 * np.clip(glow, 0, 1.2)[..., None] * (arr[..., 3:4] > 0)
        out = Image.fromarray(_clip(arr).astype(np.uint8), 'RGBA')
        # solid mask: walls + faces + props flagged solid
        solid = wall | face
        self.solid = solid
        return out

    # ---- details ---------------------------------------------------------------------------------------------------
    def _draw_door(self, canvas, r, kind, leaf, side):
        x0, y0, x1, y1 = r
        d = ImageDraw.Draw(canvas)
        m = self.m
        sill = tuple(int(c * 1.05) for c in m['top'])
        if side in 'NS':
            # threshold stone across the opening
            d.rectangle((x0, y0, x1 - 1, y1 - 1), fill=sill)
            for x in range(x0, x1, 12): d.line((x, y0, x, y1 - 1), fill=m['mortar'])
            d.line((x0, y0, x1 - 1, y0), fill=m['mortar']); d.line((x0, y1 - 1, x1 - 1, y1 - 1), fill=m['mortar'])
            # jamb shadows
            d.rectangle((x0, y0, x0 + 1, y1 - 1), fill=m['face_d']); d.rectangle((x1 - 2, y0, x1 - 1, y1 - 1), fill=m['face_d'])
            if kind == 'exit':
                # daylight beyond: bright outer half + a pool of light spilling in
                d.rectangle((x0 + 2, y1 - 6, x1 - 3, y1 - 1), fill=(250, 238, 200))
                inner = y0 if side == 'S' else y1
                dirn = -1 if side == 'S' else 1
                L = 70
                self.lights.append(([(x0, inner), (x1, inner), (x1 + 16, inner + dirn * L), (x0 - 16, inner + dirn * L)], 0.75))
            if kind == 'exit':
                # worn rush mat inside the threshold
                inner = y0 if side == 'S' else y1
                dirn = -1 if side == 'S' else 1
                ya, yb = sorted((inner + dirn * 2, inner + dirn * 16))
                d.rectangle((x0 + 8, ya, x1 - 9, yb), fill=(150, 124, 70), outline=(92, 72, 36))
                for xx in range(x0 + 10, x1 - 10, 3): d.line((xx, ya + 1, xx, yb - 1), fill=(170, 142, 84))
            if leaf in ('open_in', 'double') and kind != 'exit':
                # two oak leaves swung back into the room, standing on edge against the jambs
                inner = y0 if side == 'S' else y1
                dirn = -1 if side == 'S' else 1
                half = (x1 - x0) // 2 if leaf == 'double' or (x1 - x0) > 50 else (x1 - x0)
                leaves = [(x0 + 1, 1)] + ([(x1 - 7, -1)] if half < (x1 - x0) else [])
                for lx, _ in leaves:
                    ya, yb = sorted((inner, inner + dirn * half))
                    d.rectangle((lx, ya, lx + 5, yb), fill=(118, 72, 40), outline=(54, 32, 18))
                    d.line((lx + 1, ya + 1, lx + 1, yb - 1), fill=(150, 98, 56))
                    for yy in (ya + 4, yb - 5):
                        d.rectangle((lx, yy, lx + 5, yy + 1), fill=(60, 60, 66))
        else:
            d.rectangle((x0, y0, x1 - 1, y1 - 1), fill=sill)
            for y in range(y0, y1, 12): d.line((x0, y, x1 - 1, y), fill=m['mortar'])
            if leaf in ('open_in', 'double', 'open'):
                inner = x1 if side == 'W' else x0
                dirn = 1 if side == 'W' else -1
                half = (y1 - y0)
                xa, xb = sorted((inner, inner + dirn * min(half, 30)))
                d.rectangle((xa, y0 + 1, xb, y0 + 5), fill=(118, 72, 40), outline=(54, 32, 18))

    def _draw_stair(self, canvas, r, direction, axis, low):
        """Straight stone stair with cheek walls. Each tread: lit nosing, flat top, shadowed riser below it.
        'up' stairs climb away from the low end and get lighter; 'down' stairs sink into darkness, with a low
        parapet on the open sides so the drop reads."""
        x0, y0, x1, y1 = map(int, r)
        # work in a local image laid out with the low end at the BOTTOM (y grows toward low end), then rotate
        if axis == 'y':
            L, Wd = y1 - y0, x1 - x0
        else:
            L, Wd = x1 - x0, y1 - y0
        m = self.m
        cheek = 5
        im = Image.new('RGBA', (Wd + 2 * cheek, L), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        tread = 8
        n = max(2, L // tread)
        for i in range(n):
            # i = 0 is the far (high for up / deep for down) end at the top of the local image
            t = i / (n - 1)
            if direction == 'up':
                k = 1.18 - 0.62 * t            # top end lightest
            else:
                k = 0.18 + 0.85 * t            # bottom of the well darkest (top of local image)
            ya = i * tread
            base = tuple(int(min(255, v * k)) for v in m['top'])
            d.rectangle((cheek, ya, cheek + Wd - 1, ya + tread - 1), fill=base)
            d.line((cheek, ya + tread - 1, cheek + Wd - 1, ya + tread - 1), fill=tuple(int(min(255, v * k * 1.25)) for v in m['top']))   # nosing
            d.line((cheek, ya, cheek + Wd - 1, ya), fill=tuple(int(v * k * 0.55) for v in m['face']))          # riser shadow
            for j in range(cheek + 6 + (i % 2) * 9, cheek + Wd - 2, 18):
                d.line((j, ya + 1, j, ya + tread - 2), fill=tuple(int(v * k * 0.8) for v in m['top']))
        # cheek walls (wall-top stone) on both sides
        for cx in (0, Wd + cheek):
            d.rectangle((cx, 0, cx + cheek - 1, L - 1), fill=m['top'], outline=m['mortar'])
            for yy in range(0, L, 10): d.line((cx, yy, cx + cheek - 1, yy), fill=m['mortar'])
        if direction == 'down':
            d.rectangle((0, 0, Wd + 2 * cheek - 1, cheek - 1), fill=m['top'], outline=m['mortar'])  # parapet at the deep end
        # orient: local bottom = low end
        rot = {('y', 'S'): 0, ('y', 'N'): 180, ('x', 'E'): 90, ('x', 'W'): -90}[(axis, low)]
        if direction == 'down':
            rot = {('y', 'S'): 180, ('y', 'N'): 0, ('x', 'E'): -90, ('x', 'W'): 90}[(axis, low)]
            # for down stairs the entry (top) is opposite the low end
        im = im.rotate(rot, expand=True)
        px = x0 - (cheek if axis == 'y' else 0)
        py = y0 - (cheek if axis == 'x' else 0)
        sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
        canvas.alpha_composite(im, (px, py))

    def _draw_spiral(self, canvas, cx, cy, r):
        d = ImageDraw.Draw(canvas)
        m = self.m
        d.ellipse((cx - r - 3, cy - r - 3, cx + r + 3, cy + r + 3), fill=m['mortar'])
        n = 14
        for i in range(n):
            a0 = 2 * np.pi * i / n - np.pi / 2
            a1 = a0 + 2 * np.pi / n
            k = 0.35 + 0.8 * i / n
            pts = [(cx, cy)] + [(cx + r * np.cos(a), cy + r * np.sin(a)) for a in np.linspace(a0, a1, 6)]
            d.polygon(pts, fill=tuple(int(min(255, v * k)) for v in m['top']))
            e = (cx + r * np.cos(a1), cy + r * np.sin(a1))
            d.line((cx, cy, e[0], e[1]), fill=tuple(int(min(255, v * k * 1.3)) for v in m['top']))
        rn = max(5, r // 4)
        d.ellipse((cx - rn, cy - rn, cx + rn, cy + rn), fill=m['top'], outline=m['mortar'])
        d.arc((cx - rn + 1, cy - rn + 1, cx + rn - 1, cy + rn - 1), 180, 270, fill=tuple(min(255, int(v * 1.2)) for v in m['top']))

    def _draw_window(self, canvas, wd):
        """Window seen from above, set in an outer wall: a splayed embrasure cut through the wall top, a sunlit stone
        sill, leaded glass at the outer face, and a pool of daylight thrown onto the floor inside."""
        d = ImageDraw.Draw(canvas)
        m = self.m
        a, b, side, band, n = wd['a'], wd['b'], wd['side'], wd['band'], wd['lights']
        glass = (150, 190, 222)
        glass_hi = (214, 236, 250)
        lead = (46, 52, 64)
        sp = 6
        reveal = tuple(int(v * 0.78) for v in m['face'])
        sill = tuple(int(min(255, v * 1.08)) for v in m['top'])
        # local drawing for a SOUTH window: wall band from yi (inner) to yo (outer, glass)
        if side in 'NS':
            ya, yb = band
            depth = yb - ya
            im = Image.new('RGBA', (b - a + 2 * sp + 2, depth), (0, 0, 0, 0))
            dd = ImageDraw.Draw(im)
            W2 = b - a
            # reveals: trapezoid, inner edge wide (top of local image), outer edge = glass width
            dd.polygon([(0, 0), (W2 + 2 * sp, 0), (W2 + sp, depth - 5), (sp, depth - 5)], fill=reveal)
            dd.polygon([(3, 0), (W2 + 2 * sp - 3, 0), (W2 + sp, depth - 6), (sp, depth - 6)], fill=sill)
            dd.line((0, 0, sp, depth - 5), fill=m['mortar']); dd.line((W2 + 2 * sp, 0, W2 + sp, depth - 5), fill=m['mortar'])
            # sill courses
            for yy in range(3, depth - 6, 6):
                dd.line((sp // 2 + 2, yy, W2 + 2 * sp - sp // 2 - 2, yy), fill=tuple(int(v * 0.92) for v in sill))
            # glass
            gy0, gy1 = depth - 6, depth - 2
            dd.rectangle((sp, gy0, sp + W2 - 1, gy1), fill=glass)
            for x in range(sp, sp + W2, 4): dd.line((x, gy0, x + 3, gy1), fill=lead)
            dd.line((sp, gy0, sp + W2 - 1, gy0), fill=glass_hi)
            dd.rectangle((sp, gy0, sp + W2 - 1, gy1), outline=lead)
            for k in range(1, n):
                mx = sp + W2 * k // n
                dd.rectangle((mx - 2, gy0 - 2, mx + 1, gy1 + 1), fill=m['top'], outline=m['mortar'])
            if side == 'N': im = im.transpose(Image.FLIP_TOP_BOTTOM)
            canvas.alpha_composite(im, (a - sp, ya))
            L = wd['reach']
            if side == 'S':
                self.lights.append(([(a - sp, ya), (b + sp, ya), (b + 30, ya - L), (a - 30, ya - L)], 0.9))
            else:
                self.lights.append(([(a - sp, yb), (b + sp, yb), (b + 30, yb + L), (a - 30, yb + L)], 0.9))
        else:
            xa, xb = band
            depth = xb - xa
            im = Image.new('RGBA', (b - a + 2 * sp + 2, depth), (0, 0, 0, 0))
            dd = ImageDraw.Draw(im)
            W2 = b - a
            dd.polygon([(0, 0), (W2 + 2 * sp, 0), (W2 + sp, depth - 5), (sp, depth - 5)], fill=reveal)
            dd.polygon([(3, 0), (W2 + 2 * sp - 3, 0), (W2 + sp, depth - 6), (sp, depth - 6)], fill=sill)
            gy0, gy1 = depth - 6, depth - 2
            dd.rectangle((sp, gy0, sp + W2 - 1, gy1), fill=glass, outline=lead)
            for x in range(sp, sp + W2, 4): dd.line((x, gy0, x + 3, gy1), fill=lead)
            for k in range(1, n):
                mx = sp + W2 * k // n
                dd.rectangle((mx - 2, gy0 - 2, mx + 1, gy1 + 1), fill=m['top'], outline=m['mortar'])
            # local top = inner side. For an E wall the inner side is west (xa): rotate so local top -> west
            im = im.rotate(90 if side == 'E' else -90, expand=True)
            canvas.alpha_composite(im, (xa, a - sp))
            L = wd['reach']
            if side == 'W':
                self.lights.append(([(xb, a - sp), (xb, b + sp), (xb + L, b + 30), (xb + L, a - 30)], 0.9))
            else:
                self.lights.append(([(xa, a - sp), (xa, b + sp), (xa - L, b + 30), (xa - L, a - 30)], 0.9))

    def _draw_torch(self, canvas, x, y, side):
        d = ImageDraw.Draw(canvas)
        # iron sconce + wrapped torch head; the flame itself is animated in game
        d.rectangle((x - 1, y - 2, x + 1, y + 8), fill=(70, 50, 34), outline=(34, 24, 18))
        d.polygon([(x - 4, y + 6), (x + 4, y + 6), (x + 2, y + 10), (x - 2, y + 10)], fill=(52, 52, 58), outline=(26, 26, 30))
        d.ellipse((x - 3, y - 5, x + 3, y + 1), fill=(255, 180, 70))
        d.ellipse((x - 1, y - 4, x + 1, y - 1), fill=(255, 240, 180))
