# Palace walls (Godot 4.4)

The outer palace wall ring, assembled from the wall kit in `art/source/kit/` (your new pieces), laid out after
`art/source/walls/ring_design.png`. Walls only.

- Walk: WASD / arrows, **Shift** run, **M** expand / collapse the minimap.
- Scale: tile 16 px, Kael 28 px, viewport 960x540 (60x34 tiles). Only the walls are big: a curtain wall is
  ~300 px tall (about 11 Kaels), towers ~430 px.
- World: 482 x 298 tiles; the ring itself is ~401 x 217 tiles.
- Two gates: the gatehouse in the south (spawn is just outside it) and the open gate in the north.

## How it is built
- `tools/build_kit.py` cuts every piece off its magenta backdrop, scales the pieces to one common size (the kit's
  pieces are drawn at different scales; they are normalised by tower width / merlon size) and assembles the left
  half: gatehouse + straight walls with towers, diagonal SW corner, four steep side runs, diagonal NW corner, north
  wall with the open gate. The right half is the mirror image. Pieces are used at (or below) their native
  resolution, so nothing is upscaled.
- Collision: a band above the base line of every piece; the build fails if the ring is not sealed apart from the
  two gate arches.
- Draw order: every wall pixel knows the ground point it stands on (`depth_*.png`). Kael is drawn over the walls and
  then the wall pixels standing in front of him are drawn again on top (`shaders/wall_front.gdshader`).
- Shadows are baked from the same ground map (one light from the upper-left).
- Kit pieces not used in this layout: `curve`, `corner_l`, `side`, `diag_towers_b`, `wall_tower`.

## Rebuild
```
python3 tools/build_assets.py art/source/floor_tile.png    # floor, earth, Kael
python3 tools/build_kit.py                                  # wall ring, collision, minimap, data/layout.json
tools/capture.sh out.png --pos=x,y [--zoom=z] [--bigmap] [--hideui]   # screenshot
tools/shots.sh                                              # docs/screenshots
godot --path . -- --test                                    # reachability test
```
