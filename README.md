# Palace walls (Godot 4.4)

The outer palace wall ring, assembled from the wall kit in `art/source/kit/` (your new pieces), laid out after
`art/source/walls/ring_design.png`. Walls only.

- Walk: WASD / arrows, **Shift** run, **M** expand / collapse the minimap.
- Scale: tile 16 px, Kael 28 px, viewport 960x540 (60x34 tiles). Only the walls are big: a curtain wall is
  ~300 px tall (about 11 Kaels), towers ~430 px.
- World: 528 x 317 tiles (the ring itself ~448 x 237).
- Two gates: the gatehouse in the south (spawn is just outside it) and the open gate in the north.

## How it is built
- Grid-fitted to the design: every tower roof in `art/source/walls/ring_design.png` was measured (24 towers, `DT`/`RIGHT`
  in `tools/ring_layout.py`). Each kit piece is placed so its tower roofs land on those measured roofs (mean error
  < 1 design px, see `docs/screenshots/00_grid_design_vs_built.png`). Between two towers the wall is resampled and
  sheared column by column so both ends hit their towers; towers themselves are never distorted. The west/east
  walls are the kit's steep run stretched between upright loose towers. The south straight walls use the design's
  measured wall top/base (y 733..855). Left and right halves are fitted separately (the design is not perfectly
  symmetric). Fully deterministic: same inputs, same output.
- `tools/build_kit.py` cuts the pieces off the magenta backdrop, builds the world, the ground map, shadows, collision
  (sealed except at the two gate arches; the build fails otherwise) and the minimap.
- Draw order: every wall pixel knows the ground point it stands on (`depth_*.png`); wall pixels in front of Kael are
  redrawn on top of him (`shaders/wall_front.gdshader`).

## Rebuild
```
python3 tools/build_assets.py art/source/floor_tile.png    # floor, earth, Kael
python3 tools/build_kit.py                                  # wall ring, collision, minimap, data/layout.json
tools/capture.sh out.png --pos=x,y [--zoom=z] [--bigmap] [--hideui]   # screenshot
tools/shots.sh                                              # docs/screenshots
godot --path . -- --test                                    # reachability test
```
