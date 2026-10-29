#!/usr/bin/env python3
"""Processed (cleaned, cropped, full-res) -> Game-scale sprites (Art/Game), INTEGER box downscale.
Each asset gets one integer factor K (game_px = processed_px // K). Box filter on premultiplied
alpha, then hard alpha threshold -> crisp edges, no colour fringing. The engine draws them at
scale 1.0 with nearest filtering. Writes Art/Game/*.png + Art/sprite_specs.json
(door / footprint / foot metadata is merged in from Tools/sprite_meta.json)."""
import json, os
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC = os.path.join(ROOT, "Art", "Processed")
OUT = os.path.join(ROOT, "Art", "Game")

# name: integer factor
FACTORS = {
 "great_hall": 3, "keep_asset": 3, "gatehouse_asset": 3, "chapel": 3, "library_tower": 3,
 "barracks": 3, "blacksmith": 3, "stable": 3, "kitchen_bakery": 3,
 "watchtower": 5, "modular_wall": 5, "oak_tree": 8, "pine_tree": 8,
 "stone_well": 14, "fountain": 8, "courtyard_garden": 3, "treasure_chest": 36,
 "wall_torch": 36, "heraldic_banner": 20, "waterfall": 8,
}
TILE_FACTOR = 8   # 1920 -> 240 px tiles

def downscale(im, k):
    a = np.array(im).astype(np.float32)
    al = a[..., 3:4] / 255.0
    pm = np.concatenate([a[..., :3] * al, a[..., 3:4]], axis=2)
    w, h = im.width // k, im.height // k
    pm = pm[: h * k, : w * k]
    ch = [np.array(Image.fromarray(pm[..., c], "F").resize((w, h), Image.BOX)) for c in range(4)]
    pm2 = np.stack(ch, axis=2)
    alpha = pm2[..., 3:4]
    rgb = np.where(alpha > 1, pm2[..., :3] / np.maximum(alpha / 255.0, 1e-4), 0)
    out = np.concatenate([np.clip(rgb, 0, 255), np.where(alpha >= 128, 255, 0)], axis=2).astype(np.uint8)
    return Image.fromarray(out, "RGBA")

BRIDGE_POLY = [(222, 368), (366, 368), (348, 541), (176, 541)]   # game px in the gatehouse sprite

def split_gatehouse(specs, meta):
    """The drawbridge is ground-level walkable art, so it must NOT sort in front of the player.
    Split the (derived) gatehouse sprite into gatehouse_main (towers/arch, y-sorted) and
    gatehouse_bridge (flat, drawn on the ground layer). Pure pixel partition: nothing is repainted."""
    from PIL import ImageDraw
    g = Image.open(os.path.join(OUT, "gatehouse_asset.png")).convert("RGBA")
    m = Image.new("L", g.size, 0); ImageDraw.Draw(m).polygon(BRIDGE_POLY, fill=255)
    a = np.array(g); mk = np.array(m) > 0
    main = a.copy(); main[mk, 3] = 0
    br = a.copy(); br[~mk, 3] = 0
    bim = Image.fromarray(br, "RGBA"); bb = bim.getbbox()
    bim = bim.crop(bb); bim.save(os.path.join(OUT, "gatehouse_bridge.png"), optimize=True)
    Image.fromarray(main, "RGBA").save(os.path.join(OUT, "gatehouse_main.png"), optimize=True)
    base = specs["gatehouse_asset"]
    e = dict(base); e.update({"game": "Art/Game/gatehouse_main.png", "note": "gatehouse_asset minus drawbridge pixels"}); e.update(meta.get("gatehouse_main", {}))
    specs["gatehouse_main"] = e
    specs["gatehouse_bridge"] = {"source": base["source"], "processed": base["processed"], "game": "Art/Game/gatehouse_bridge.png",
        "game_size": [bim.width, bim.height], "origin_in_gatehouse": [bb[0], bb[1]], "kind": "ground-layer piece", "factor": base["factor"]}
    print("gatehouse split: bridge", bim.size, "origin", bb[:2])

def main():
    os.makedirs(OUT, exist_ok=True)
    meta_path = os.path.join(ROOT, "Tools", "sprite_meta.json")
    meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
    specs = {}
    for name, k in FACTORS.items():
        src = Image.open(os.path.join(PROC, name + ".png"))
        g = downscale(src, k)
        g.save(os.path.join(OUT, name + ".png"), optimize=True)
        e = {"source": "Art/Source/individual_%s.png" % name, "processed": "Art/Processed/%s.png" % name,
             "game": "Art/Game/%s.png" % name, "factor": k, "processed_size": list(src.size),
             "game_size": [g.width, g.height], "pivot": "bottom-center (ground footpoint)"}
        e.update(meta.get(name, {}))
        specs[name] = e
        print("%-18s k=%-3d %dx%d -> %dx%d" % (name, k, src.width, src.height, g.width, g.height))
    split_gatehouse(specs, meta)
    for t in ["cobblestone_tile", "grass_tile", "river_water_tile"]:
        src = Image.open(os.path.join(PROC, t + "_seamless.png"))
        g = src.resize((src.width // TILE_FACTOR, src.height // TILE_FACTOR), Image.BOX)
        g.save(os.path.join(OUT, t + ".png"), optimize=True)
        raw = Image.open(os.path.join(PROC, t + ".png")).convert("RGBA")
        raw.resize((raw.width // TILE_FACTOR, raw.height // TILE_FACTOR), Image.BOX).save(os.path.join(PROC, t + "_raw240.png"))
        specs[t] = {"source": "Art/Source/individual_%s.png" % t, "processed": "Art/Processed/%s_seamless.png" % t,
                    "game": "Art/Game/%s.png" % t, "factor": TILE_FACTOR, "game_size": [g.width, g.height], "kind": "tile"}
        print("%-18s tile %dx%d" % (t, g.width, g.height))
    with open(os.path.join(ROOT, "Art", "sprite_specs.json"), "w") as fh:
        json.dump(specs, fh, indent=1, sort_keys=True)

if __name__ == "__main__":
    main()
