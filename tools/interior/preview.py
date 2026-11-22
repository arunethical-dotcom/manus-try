"""Render a floor to a preview PNG on a dark ground, with Kael standing in it for scale.
python3 tools/interior/preview.py barracks build_ground out.png [kx ky] [crop x0 y0 x1 y1] [zoom]"""
import sys, os, importlib
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'floors'))
from PIL import Image

mod, fn, out = sys.argv[1:4]
f = getattr(importlib.import_module(mod), fn)()
img = f.render()
bg = Image.new('RGBA', img.size, (34, 30, 28, 255))
bg.alpha_composite(img)
root = os.path.join(os.path.dirname(__file__), '..', '..')
kael = Image.open(os.path.join(root, 'art/game/kael3/idle.png')).convert('RGBA').crop((0, 0, 64, 64))
args = sys.argv[4:]
spots = []
while len(args) >= 2 and args[0] != 'crop':
    spots.append((int(args[0]), int(args[1]))); args = args[2:]
for kx, ky in spots:
    bg.alpha_composite(kael, (kx - 32, ky - 45))
if args and args[0] == 'crop':
    x0, y0, x1, y1 = map(int, args[1:5]); bg = bg.crop((x0, y0, x1, y1)); args = args[5:]
z = float(args[0]) if args else 1
if z != 1:
    bg = bg.resize((int(bg.width * z), int(bg.height * z)), Image.NEAREST)
bg.convert('RGB').save(out)
print(out, bg.size)
