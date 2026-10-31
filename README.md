# Palace walls (Godot 4.4)

Outer wall ring only: **no inner walls, inner gatehouse or stairs**. Built from the supplied wall pieces
(`art/source/wall_pieces.png`), laid out as in `art/source/ring_reference.png`.

- Walk: WASD / arrows, **Shift** run, **M** expand / collapse the minimap.
- Scale: tile 16 px, Kael 28 px, viewport 960x540 (60x34 tiles).
- World: 466 x 239 tiles. Width is within the 400-500 target; depth is **below** the 300-400 target
  (the ring is wide and shallow, as in the reference).
- Collision comes from the wall art (footprint under each piece), not from sprite rectangles; the interior is sealed
  except the gate arch (`tools/ring_leaks.py`, and `--test` flood fill in-engine).

## Rebuild
```
python3 tools/build_assets.py art/source/floor_tile.png                     # floor, water, shore, Kael
python3 tools/build_ring.py art/source/wall_pieces.png art/source/ring_reference.png   # ring sprites, shadows, collision, data/layout.json, minimap
tools/capture.sh out.png --pos=x,y --zoom=0.5 [--bigmap] [--hideui]        # screenshot
tools/shots.sh                                                              # docs/screenshots
```
