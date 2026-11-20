"""Assemble the five-bay residence from the original painted architectural details."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
import random
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'art/game/keep'
POSITION = (1954, 2444)


def build():
    source = Image.open(ROOT / 'art/source/keep/sisters_apartment.png').convert('RGBA')
    source.thumbnail((577, 429), Image.Resampling.BOX)
    sprite = Image.new('RGBA', (640, 576))
    draw = ImageDraw.Draw(sprite)
    rng = random.Random(31)

    def detail(box, position, size):
        tile = source.crop(box).resize(size, Image.Resampling.LANCZOS)
        sprite.alpha_composite(tile, position)

    def masonry(left, top, width, bottom, curved=False):
        for row, y in enumerate(range(top, bottom, 20)):
            for x in range(left - (21 if row % 2 else 0), left + width, 42):
                start, end = max(left, x), min(left + width, x + 42)
                tone = rng.randrange(-8, 9)
                for col in range(start, end):
                    u = (col - left) / width
                    shade = int(32 * (1 - (2*u-0.76)**2) - 24) if curved else 0
                    color = tuple(max(0,min(255,c + tone + shade)) for c in (217,186,137))
                    draw.line((col,y,col,min(y+19,bottom-1)),fill=color)
                draw.line((start,y,end-1,y),fill='#f1dab0')
                draw.line((end-1,y,end-1,min(y+19,bottom-1)),fill='#917654')
                draw.line((start,min(y+19,bottom-1),end-1,min(y+19,bottom-1)),fill='#897252')

    masonry(94,216,452,576)
    # Reuse the continuous slate between chimneys for the central roof slope.
    source.paste(source.crop((201,149,234,189)), (169,149))
    source.paste(source.crop((338,149,375,189)), (375,149))
    detail((76,149,500,250),(84,116),(472,100))
    for x in (192,448):
        for y in (267,447):
            detail((331,262,378,311),(x-20,y),(40,70))
    detail((206,306,297,417),(271,441),(98,132))
    detail((233,349,271,404),(295,476),(50,90))
    detail((207,406,295,425),(269,566),(102,10))
    for x in (0,544):
        masonry(x+2,126,92,576,True)
        detail((1,0,81,86),(x,46),(96,80))
        detail((1,85,81,126),(x,126),(96,39))
        for y in (271,451):
            detail((31,148,52,198),(x+40,y),(16,48))
        detail((4,389,78,411),(x,554),(96,22))
    # Weather the new stone faces using the same tile texture as the courtyard.
    pixels = np.array(sprite)
    texture = np.array(Image.open(ROOT / 'art/game/floor_atlas.png').convert('L'), dtype=float)
    yy, xx = np.indices(pixels.shape[:2])
    grain = texture[yy % texture.shape[0], xx % texture.shape[1]]
    grain = np.clip((grain-grain.mean()) * 0.3, -12, 12)
    stone = (pixels[:,:,0] > 130) & (pixels[:,:,1] > 110) & (pixels[:,:,3] > 0)
    pixels[:,:,:3] = np.clip(pixels[:,:,:3].astype(float) + (grain*stone)[:,:,None],0,255)
    sprite = Image.fromarray(pixels)
    alpha = sprite.getchannel('A')
    outline = Image.new('RGBA', sprite.size, '#392921')
    outline.putalpha(alpha.filter(ImageFilter.MaxFilter(5)))
    outline.alpha_composite(sprite)
    # Preserve the measured cap height and flat base.
    outline.paste((0,0,0,0),(0,0,640,46))
    outline.save(OUT / 'sisters_apartment.png')
    # A curved dirt approach joins the steps to the existing western lane.
    ground = Image.open(ROOT / 'art/game/ground/g_1024_2048.webp').convert('RGB')
    swatch = ground.crop((1844-1024, 3036-2048, 1908-1024, 3068-2048))
    approach = Image.new('RGBA', (421, 86))
    for py in range(0, approach.height, swatch.height):
        for px in range(0, approach.width, swatch.width):
            approach.paste(swatch, (px,py))
    mask = Image.new('L', approach.size)
    ImageDraw.Draw(mask).polygon([(0,42),(136,50),(247,49),(321,33),(355,8),
                                  (358,0),(406,0),(399,27),(368,54),(280,77),
                                  (145,81),(0,74)],fill=255)
    approach.putalpha(mask.filter(ImageFilter.GaussianBlur(2)))
    approach.save(OUT / 'sisters_approach.png')
    x,y = POSITION
    return dict(name="Sister's Apartment", image='res://art/game/keep/sisters_apartment.png',
                approach=dict(image='res://art/game/keep/sisters_approach.png', pos=[1890,3011]),
                pos=[x,y], size=[640,576], z_line=y+566,
                collision=[[[x+3,y+486],[x+637,y+486],[x+637,y+575],
                            [x+544,y+575],[x+544,y+565],[x+96,y+565],
                            [x+96,y+575],[x+3,y+575]]])


if __name__ == '__main__':
    import json
    path = ROOT / 'data/keep_buildings.json'
    buildings = json.loads(path.read_text())
    buildings['sisters_apartment'] = build()
    path.write_text(json.dumps(buildings, indent=1))
