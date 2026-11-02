# Palace walls (Godot 4.4)

The outer palace wall ring, assembled from the wall kit in `art/source/kit/` (your new pieces), laid out after
`art/source/walls/ring_design.png`. Walls only.

- Walk: WASD / arrows, **Shift** run, **M** expand / collapse the minimap.
- Scale: tile 16 px, Kael 28 px, viewport 960x540 (60x34 tiles). Only the walls are big: a curtain wall is
  ~300 px tall (about 11 Kaels), towers ~430 px.
- World: 490 x 311 tiles (the ring itself ~409 x 230).
- Two gates: the gatehouse in the south (spawn is just outside it) and the open gate in the north.

## How it is built
- `tools/ring_layout.py` places every kit piece on the matching tower of `art/source/walls/ring_design.png`: each tower in
  the design (found by its blue roof) is the anchor for the piece's tower at the same scale, and diagonal pieces are
  shortened so the next tower lands exactly on the next design tower. The right half is the mirror image about the
  gate axis. Pieces are used at (or below) native resolution, so nothing is upscaled.
- `tools/build_kit.py` cuts the pieces off the magenta backdrop, builds the world, the ground map, shadows, collision
  (a band above each piece's base line, bridged where two pieces meet; the build fails if the ring is not sealed
  except at the two gate arches) and the minimap.
- Draw order: every wall pixel knows the ground point it stands on (`depth_*.png`). Kael is drawn over the walls and
  then the wall pixels standing in front of him are drawn again on top (`shaders/wall_front.gdshader`).
- Shadows are baked from the same ground map (one light from the upper-left).
- Kit pieces not used: `curve`, `side`, `tower` (the loose tower).

## Rebuild
```
python3 tools/build_assets.py art/source/floor_tile.png    # floor, earth, Kael
python3 tools/build_kit.py                                  # wall ring, collision, minimap, data/layout.json
tools/capture.sh out.png --pos=x,y [--zoom=z] [--bigmap] [--hideui]   # screenshot
tools/shots.sh                                              # docs/screenshots
godot --path . -- --test                                    # reachability test
```
