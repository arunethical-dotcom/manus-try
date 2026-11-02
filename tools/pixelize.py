"""Turns the soft 4x upscale into crisp pixel art: down to a 2x pixel grid, 48-colour palette (no dithering),
then nearest-neighbour back to 4x, so every art pixel is a hard-edged 2x2 game-pixel block.
  python3 tools/pixelize.py <ring_x4.png> <out.png> [colours]"""
import sys
import numpy as np
from PIL import Image
im = Image.open(sys.argv[1]).convert("RGB")
# magenta bleed from the backdrop: turn pinkish edge pixels into the dark outline colour
a = np.array(im).astype(int)
r, g, b = a[..., 0], a[..., 1], a[..., 2]
pink = (r - g > 50) & (b - g > 40) & (b > 90)
a[pink] = (46, 34, 38)
im = Image.fromarray(a.astype(np.uint8))
n = int(sys.argv[3]) if len(sys.argv) > 3 else 48
w2, h2 = im.width // 2, im.height // 2
q = im.resize((w2, h2), Image.LANCZOS).quantize(colors=n, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
q.convert("RGB").resize((w2 * 2, h2 * 2), Image.NEAREST).save(sys.argv[2])
