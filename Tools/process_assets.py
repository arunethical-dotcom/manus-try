#!/usr/bin/env python3
"""Source (Art/Source/individual_*.png)  ->  Art/Processed (cleaned, cropped, full-res).
Originals are never modified.

FINDINGS (measured, see Art/Processed/manifest.json):
  * The supplied 'true alpha' is soft: foreground pixels sit at alpha 245-254 (never 255) and
    there are stray alpha 1-31 specks around sprites. Ground tiles are alpha 224-254 everywhere
    (i.e. slightly see-through, which would show the clear colour through the ground).
Policy (deterministic):
  sprites : alpha >= ALPHA_CUT -> 255, else 0 (hard pixel-art edge); RGB of kept pixels untouched;
            crop to visible bounds; report counts of removed low-alpha pixels.
  tiles   : alpha forced to 255; edge-seam metric measured; a seamless derivative
            (<name>_seamless.png) is produced by half-offset cross-blend (see make_seamless).
  garden  : unique patch (not a tile); processed like a sprite.
"""
import json, os, glob
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "Art", "Source")
DST = os.path.join(ROOT, "Art", "Processed")
ALPHA_CUT = 128
TILES = ["cobblestone_tile", "grass_tile", "river_water_tile"]

def seam_metric(rgb):
    f = rgb.astype(np.float32)
    wrap_h = np.abs(f[:, 0] - f[:, -1]).mean()
    wrap_v = np.abs(f[0] - f[-1]).mean()
    adj_h = np.abs(f[:, 1:] - f[:, :-1]).mean()
    adj_v = np.abs(f[1:] - f[:-1]).mean()
    return float(wrap_h), float(wrap_v), float(adj_h), float(adj_v)

def make_seamless(rgb):
    h, w, _ = rgb.shape
    f = rgb.astype(np.float32)
    rolled = np.roll(np.roll(f, h // 2, axis=0), w // 2, axis=1)
    yy = np.minimum(np.arange(h), h - 1 - np.arange(h)).astype(np.float32) / (h / 2.0)
    xx = np.minimum(np.arange(w), w - 1 - np.arange(w)).astype(np.float32) / (w / 2.0)
    wy = np.clip(yy * 2.0, 0, 1)[:, None]  # 0 at the edge -> 1 at 25% in
    wx = np.clip(xx * 2.0, 0, 1)[None, :]
    wgt = (np.minimum(wy, wx) ** 1.0)[..., None]
    wgt = wgt * wgt * (3 - 2 * wgt)  # smoothstep
    out = f * wgt + rolled * (1 - wgt)
    return np.clip(out, 0, 255).astype(np.uint8)

def main():
    os.makedirs(DST, exist_ok=True)
    manifest = {}
    for p in sorted(glob.glob(os.path.join(SRC, "individual_*.png"))):
        name = os.path.basename(p)[len("individual_"):-4]
        im = Image.open(p).convert("RGBA")
        a = np.array(im)
        al = a[..., 3]
        st = {"source": "Art/Source/individual_%s.png" % name, "size_src": [im.width, im.height],
              "alpha_min": int(al.min()), "alpha_max": int(al.max()),
              "pixels_alpha_eq_255": int((al == 255).sum()),
              "pixels_alpha_245_254": int(((al >= 245) & (al < 255)).sum()),
              "pixels_alpha_1_127": int(((al > 0) & (al < ALPHA_CUT)).sum())}
        if name in TILES:
            rgb = a[..., :3]
            wh, wv, ah, av = seam_metric(rgb)
            st.update({"kind": "tile", "wrap_edge_diff_h": round(wh, 2), "wrap_edge_diff_v": round(wv, 2),
                       "adjacent_px_diff_h": round(ah, 2), "adjacent_px_diff_v": round(av, 2),
                       "seam_ratio": round(max(wh / ah, wv / av), 2)})
            opaque = np.dstack([rgb, np.full(al.shape, 255, np.uint8)])
            Image.fromarray(opaque, "RGBA").save(os.path.join(DST, name + ".png"), optimize=True)
            sl = make_seamless(rgb)
            wh2, wv2, ah2, av2 = seam_metric(sl)
            st.update({"seamless_derivative": "Art/Processed/%s_seamless.png" % name,
                       "seamless_wrap_edge_diff_h": round(wh2, 2), "seamless_wrap_edge_diff_v": round(wv2, 2),
                       "seamless_seam_ratio": round(max(wh2 / ah2, wv2 / av2), 2)})
            Image.fromarray(np.dstack([sl, np.full(al.shape, 255, np.uint8)]), "RGBA").save(
                os.path.join(DST, name + "_seamless.png"), optimize=True)
            st["processed"] = "Art/Processed/%s.png" % name
            st["processed_size"] = [im.width, im.height]
        else:
            keep = al >= ALPHA_CUT
            st["kind"] = "sprite"
            st["alpha_cut"] = ALPHA_CUT
            st["opaque_pixels_after"] = int(keep.sum())
            out = a.copy()
            out[..., 3] = np.where(keep, 255, 0)
            ys, xs = np.where(keep)
            x0, x1, y0, y1 = int(xs.min()), int(xs.max()) + 1, int(ys.min()), int(ys.max()) + 1
            crop = out[y0:y1, x0:x1]
            # report isolated opaque specks (not removed; they are often sparkles/flame sparks)
            lab, n = ndi.label(crop[..., 3] > 0, structure=np.ones((3, 3)))
            sizes = ndi.sum(np.ones_like(lab), lab, range(1, n + 1)) if n else []
            st["crop_rect"] = [x0, y0, x1 - x0, y1 - y0]
            st["components"] = int(n)
            st["tiny_components_lt_16px"] = int(sum(1 for s in sizes if s < 16))
            Image.fromarray(crop, "RGBA").save(os.path.join(DST, name + ".png"), optimize=True)
            st["processed"] = "Art/Processed/%s.png" % name
            st["processed_size"] = [crop.shape[1], crop.shape[0]]
            st["pivot_rule"] = "bottom-center of visible bounds"
        manifest[name] = st
        print(name, st["kind"], st["processed_size"], {k: v for k, v in st.items() if k in ("seam_ratio", "seamless_seam_ratio", "tiny_components_lt_16px", "pixels_alpha_1_127")})
    with open(os.path.join(DST, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=1, sort_keys=True)

if __name__ == "__main__":
    main()
