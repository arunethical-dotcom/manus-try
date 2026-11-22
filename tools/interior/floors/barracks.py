"""Barracks & Armory interiors. Exterior is 1440 px wide in the world; three doors and the windows on the front (south)
wall are placed where the exterior art has them (doors x≈236-346, 686-758, 1118-1182)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from render import Floor
import props as P

W, H = 1440, 360
T = 28            # outer wall
TI = 20           # inner wall
SOUTH = (H - T, H)
NORTH = (0, T)
# partitions (between guard hall | armory | sergeants)
PX = [(550, 570), (870, 890)]
# exterior features, world x
GF_WIN = [(112, 163, 2), (440, 492, 2), (602, 620, 1), (827, 845, 1), (965, 1017, 2), (1270, 1322, 2)]
DOORS = [(236, 346, 'Guard hall'), (686, 758, 'Armory'), (1118, 1182, "Sergeants' room")]
UP_WIN = [(c - 26, c + 26, 2) for c in (148, 318, 480, 642, 800, 962, 1125, 1294)]


def build_ground(seed=7):
    f = Floor(W, H, mat='sand', seed=seed)
    # floors
    f.floor((0, 0, 560, H), 'flag')
    f.floor((560, 0, 880, H), 'flag', base=(166, 150, 124))
    f.floor((880, 0, W, H), 'plank', base=(168, 104, 56))
    f.room('Guard hall and mess', (T, T, PX[0][0], H - T))
    f.room('Armory', (PX[0][1], T, PX[1][0], H - T))
    f.room("Sergeants' room", (PX[1][1], T, 1200, H - T))
    f.room('Stores', (1216, T, W - T, H - T))
    # walls
    f.ring((0, 0, W, H), T)
    for a, b in PX: f.wall((a, 0, b, H))
    for a, b, name in DOORS:
        f.opening((a, H - T, b, H), kind='exit', name=name, to='outside', leaf='double', side='S')
    for a, b, n in GF_WIN:
        f.window(a, b, 'S', y=SOUTH, lights=n)

    # ---- guard hall & mess ----
    MAT = (f.m['top'], f.m['mortar'], f.m['face'])
    f.stair((40, T + FACE + 2, 168, T + FACE + 40), direction='up', name='Stair up', to='barracks_upper', axis='x', low='E')
    f.stair((44, 176, 84, 300), direction='down', name='Down to the dungeon', to='barracks_dungeon', axis='y', low='S')
    f.prop(P.big_hearth, 196, T - 10, mat=MAT, w=100, shadow=False)
    f.prop(P.firewood, 300, T + FACE + 2, w=28)
    f.prop(P.serving_table, 336, T + FACE + 4, w=64)
    f.prop(P.wall_rack_pegs, 410, T + 2, w=50, shadow=False)
    f.prop(P.weapon_rack, 476, T + 2, w=56, kind='spears')
    for ty in (112, 236):
        for tx in (140, 330):
            f.prop(P.bench, tx + 8, ty - 13, w=150)
            f.prop(P.table, tx, ty, w=166, h=28)
            f.prop(P.bench, tx + 8, ty + 34, w=150)
    for px in (130, 310, 500):
        f.prop(P.pillar, px, 190, mat=MAT, r=11)
    for x, y in ((470, 280), (494, 290), (476, 306), (510, 300)): f.prop(P.barrel, x, y)
    f.prop(P.water_butt, 186, 296)
    for x in (110, 128): f.prop(P.stool, x, 120)
    f.torch(118, T + 6, 1); f.torch(390, T + 6, 1); f.torch(310, 182, 1)

    # ---- armory ----
    for i, kind in enumerate(('spears', 'swords', 'spears', 'bows')):
        f.prop(P.weapon_rack, 590 + i * 66, T + 2, w=54, kind=kind)
    for i in range(6):
        f.prop(P.armour_stand, 594 + i * 44, 104)
    for i, kind in enumerate(('swords', 'spears')):         # free-standing racks down the middle
        f.prop(P.weapon_rack, 610 + i * 120, 168, w=90, kind=kind)
    f.prop(P.shield_stand, 820, 170)
    for x, y in ((830, 216), (848, 232), (826, 240)): f.prop(P.arrow_barrel, x, y)
    for x in (612, 650, 770, 808): f.prop(P.chest, x, 300, w=28, h=16)
    f.prop(P.workbench, 596, 226, w=80); f.prop(P.anvil, 700, 236); f.prop(P.grindstone, 740, 232)
    f.prop(P.stool, 640, 254)
    f.torch(640, T + 6, 2); f.torch(820, T + 6, 2)

    # ---- sergeants' room (west) | stores (east) ----
    f.wall((1200, 0, 1216, H))
    f.opening((1200, 150, 1216, 200), kind='door', name='Stores door', leaf='open', side='W')
    for i in range(3):
        f.prop(P.bed, 908 + i * 40, T + FACE + 2, blanket=[(60, 84, 150), (120, 50, 50), (70, 100, 70)][i])
        f.prop(P.chest, 908 + i * 40, T + FACE + 48, w=24, h=12, iron=False)
    f.prop(P.wardrobe, 1030, T + FACE - 4)
    f.prop(P.desk, 1110, T + FACE + 4, w=44); f.prop(P.chair, 1126, T + FACE + 28, facing='N')
    f.prop(P.rug, 924, 150, w=130, h=80)
    f.prop(P.table, 954, 174, w=70, h=28); f.prop(P.stool, 944, 206); f.prop(P.stool, 1000, 206)
    f.prop(P.stool, 976, 160)
    f.prop(P.wall_rack_pegs, 1070, T + 2, w=36, shadow=False)
    f.prop(P.barrel, 1170, 96); f.prop(P.water_butt, 1168, 120)
    # stores
    for i in range(7):
        for j in range(2):
            f.prop(P.crate, 1232 + i * 22, T + FACE + 2 + j * 24)
    for i in range(9): f.prop(P.sack, 1240 + (i % 5) * 16, 110 + (i // 5) * 18)
    for i in range(8): f.prop(P.barrel, 1336 + (i % 3) * 20, 120 + (i // 3) * 20)
    for i in range(4):
        for j in range(2):
            f.prop(P.crate, 1236 + i * 22, 250 + j * 24)
    f.torch(1000, T + 6, 3); f.torch(1300, T + 6, 4)
    return f


FACE = 18
