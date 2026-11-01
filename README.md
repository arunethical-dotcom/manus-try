# Palace walls (Godot 4.4)

The outer palace wall ring from `art/source/walls/ring_design.png`, built at game scale. Walls only.

- Walk: WASD / arrows, **Shift** run, **M** expand / collapse the minimap.
- Scale: tile 16 px, Kael 28 px, viewport 960x540 (60x34 tiles). Only the walls are big:
  1 design px = 4 game px, so a curtain wall is ~250-300 px tall (about 10 Kaels) and a tower ~600 px.
- World: 493 x 307 tiles; the ring itself is 413 x 217 tiles.
- Two gates: the big south gatehouse (spawn is just outside it) and the small north gate.

## How it is built
- Wall art: the design upscaled 4x with Real-ESRGAN (anime 6B), run in plain numpy (`tools/upscale/`).
  The separate piece sheets in `art/source/walls/sheet_*.png` are kept for reference but are not used: they are
  drawn differently from the overall design, so they don't line up with it.
- Collision: the wall footprint on the ground, derived from the art (bands along the inside and outside edges of
  the ring plus the base line under each wall); the interior is sealed except at the two gates (checked by the build).
- Draw order: every wall pixel knows the ground point it stands on (`depth_*.png`). Kael is drawn over the walls and
  then the wall pixels standing in front of him are drawn again on top (`shaders/wall_front.gdshader`).
- Shadows are baked from the same ground map (one light from the upper-left).

## Rebuild
```
python3 tools/build_assets.py art/source/floor_tile.png          # floor, earth, Kael
python3 tools/upscale/esrgan_np.py art/source/walls/ring_design.png art/source/walls/ring_design_x4.png   # ~11 min on CPU, needs RealESRGAN_x4plus_anime_6B.pth (W=path)
python3 tools/build_walls.py art/source/walls/ring_design.png art/source/walls/ring_design_x4.png
tools/capture.sh out.png --pos=x,y [--zoom=z] [--bigmap] [--hideui]   # screenshot
godot --path . -- --test                                          # reachability test
```
