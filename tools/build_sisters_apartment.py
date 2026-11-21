"""Scale the supplied apartment artwork and place its walkable approach."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'art/game/keep'


def build():
    source = Image.open(ROOT / 'art/source/keep/sisters_apartment.png').convert('RGBA')
    # Match the framed windows on the lower Holdfast facade at world scale.
    width = 1088
    height = round(source.height * width / source.width)
    sprite = source.resize((width, height), Image.Resampling.LANCZOS)
    sprite.save(OUT / 'sisters_apartment.png')
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
    # Extend the existing spur north to the source sprite's off-centre porch.
    extended = Image.new('RGBA', (421, 142))
    extended.paste(approach,(0,56))
    for row in range(57):
        extended.paste(swatch.crop((0,row % 32,48,row % 32+1)),(358,row))
    extended.save(OUT / 'sisters_approach.png')
    x, y = 1952, 2490
    # Original lower-wall and turret footprint, traced on the 577 x 429 reference.
    outline = [(6,305),(570,305),(570,406),(548,412),(501,410),
               (498,400),(78,400),(74,411),(25,412),(6,406)]
    footprint = [[x + round(dx*width/577), y + round(dy*height/429)] for dx,dy in outline]
    return dict(name="Sister's Apartment", image='res://art/game/keep/sisters_apartment.png',
                approach=dict(image='res://art/game/keep/sisters_approach.png', pos=[x + round(251 * width / 577) - 382, y + round(423 * height / 429) - 2]),
                pos=[x,y], size=[width,height], z_line=y+round(400*height/429),
                collision=[footprint])


if __name__ == '__main__':
    import json
    path = ROOT / 'data/keep_buildings.json'
    buildings = json.loads(path.read_text())
    buildings['sisters_apartment'] = build()
    path.write_text(json.dumps(buildings, indent=1))
