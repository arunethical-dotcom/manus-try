"""Front portal of the Holdfast, drawn pixel by pixel (stone arch, recessed oak double door with iron straps and studs,
two steps). Composited onto the Holdfast sprite by tools/build_keep_buildings.py, centred on the facade with its
bottom step on the building's ground line, so Kael has a door to walk up to.  draw_door() -> RGBA uint8 array."""
import numpy as np

W, H = 78, 104          # whole portal incl. steps
def draw_door():
    a = np.zeros((H, W, 4), np.uint8)
    def put(x, y, c):
        if 0 <= x < W and 0 <= y < H:
            a[y, x, :3] = c; a[y, x, 3] = 255
    cx = W / 2 - 0.5
    STEP = 10                                   # two steps at the bottom
    top_frame = 4
    R_out, R_in = 33, 22                        # arch radii (outer frame, door opening)
    spring = top_frame + R_out                  # y where the arch springs
    base = H - STEP                             # door threshold
    stone = [(196, 172, 164), (178, 153, 146), (160, 135, 128)]
    mortar = (112, 88, 82)
    dark_edge = (74, 54, 48)
    for y in range(top_frame, base):
        for x in range(W):
            dx = x - cx
            if y < spring:
                d = np.hypot(dx, y - spring)
                if d > R_out + 0.5: continue
                ring = d > R_in + 0.5
            else:
                if abs(dx) > R_out + 0.5: continue
                ring = abs(dx) > R_in + 0.5
            if ring:
                # voussoirs on the arch, ashlar blocks on the jambs
                if y < spring:
                    ang = np.degrees(np.arctan2(spring - y, dx))
                    joint = (int(ang) % 15 == 0) or abs(d - (R_in + 6)) < 0.5
                    shade = 0 if dx < 0 else 1
                else:
                    joint = ((y - spring) % 12 == 0) or (abs(abs(dx) - (R_in + 6)) < 0.5 and ((y - spring) // 12) % 2 == 0)
                    shade = 0 if dx < 0 else 1
                c = mortar if joint else stone[shade]
                edge = (y < spring and d > R_out - 0.6) or (y >= spring and abs(dx) > R_out - 0.6)
                if edge: c = dark_edge
                if (y < spring and R_in + 0.5 < d < R_in + 1.6) or (y >= spring and R_in + 0.5 < abs(dx) < R_in + 1.6):
                    c = (226, 206, 198) if dx < 0 else (130, 104, 98)   # lit / shaded reveal of the opening
                put(x, y, c)
            else:
                # recessed oak double door
                inner_spring = spring
                dd = np.hypot(dx, y - inner_spring) if y < inner_spring else abs(dx)
                if dd > R_in - 2.5:
                    put(x, y, (40, 26, 22)); continue                     # deep shadow of the recess
                plank = int((x - (cx - R_in)) // 5)
                base_c = np.array([118, 72, 40]) if plank % 2 else np.array([104, 62, 34])
                if int(x - (cx - R_in)) % 5 == 0: base_c = np.array([66, 38, 22])
                if abs(dx) < 1.0: base_c = np.array([46, 28, 18])          # meeting line of the two leaves
                t = (y - top_frame) / (base - top_frame)
                base_c = base_c * (0.82 + 0.25 * t)                       # darker at the top, inside the arch
                for sy in (spring + 8, base - 16):                        # iron hinge straps
                    if sy <= y <= sy + 2 and abs(dx) > 2: base_c = np.array([52, 50, 56]) if y != sy else np.array([92, 90, 98])
                if (y in (spring + 9, base - 15)) and int(abs(dx)) % 6 == 4: base_c = np.array([150, 148, 156])  # studs
                put(x, y, tuple(np.clip(base_c, 0, 255).astype(int)))
    for k, (lx, ly) in enumerate(((cx - 5, spring + 26), (cx + 4, spring + 26))):   # ring handles
        for t in np.linspace(0, 2 * np.pi, 20):
            put(int(round(lx + 2.5 * np.cos(t))), int(round(ly + 3 * np.sin(t))), (176, 168, 120))
    # steps: lower step wider than the upper one
    for i, (hw, c, cl) in enumerate(((R_out + 2, (170, 148, 140), (210, 190, 182)), (R_out + 6, (150, 128, 120), (196, 176, 168)))):
        y0 = base + i * 5
        for y in range(y0, y0 + 5):
            for x in range(int(cx - hw), int(cx + hw) + 2):
                col = cl if y == y0 else (dark_edge if y == y0 + 4 or x in (int(cx - hw), int(cx + hw) + 1) else c)
                put(x, y, col)
    return a
