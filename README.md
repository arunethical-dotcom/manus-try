# Palace walls (Godot 4.4)

The outer palace wall ring, built from your wall pieces (`art/source/walls/pieces/`) joined into one picture
(`art/source/walls/ring_final.png`, transparent background). Walls only.

- Walk: WASD / arrows, **Shift** run, **M** expand / collapse the minimap.
- Scale: tile 16 px, Kael 28 px, viewport 960x540. Only the walls are big: the ring is 6604 x 3712 px
  (413 x 232 tiles), towers ~600 px tall.
- World: 493 x 322 tiles. Two gates: the gatehouse in the south (spawn just outside it) and the gate in the north.

## How it is built
- `ring_final.png` was assembled by hand-tuned joins of the six pieces (left half, mirrored about the gate axis):
  matched scale/position per piece, optimal-seam cuts through plain wall, merlon rows re-tiled where repeats did not
  divide evenly, tower outlines restored, magenta fringe removed. The one-off join scripts are in `tools/ringjoin/`.
- For the game it is scaled to 6604 px wide and saved on magenta as `ring_final_x4.png` (+ a 1/4 copy
  `ring_final_design.png` used for gate coordinates).
- `tools/build_walls.py`: collision from the art (bands along the inside and outside edges of the ring and under each
  wall), sealed except at the two gate arches (the build fails otherwise); per-pixel ground map for draw order
  (`shaders/wall_front.gdshader` redraws wall pixels standing in front of Kael); baked shadows; minimap.

## See-through (CrossCode style)
`tools/build_objects.py` splits the wall art into objects (52: each tower, each wall stretch, the gatehouses) and
stores the object id per pixel. When Kael walks behind one, that whole object fades smoothly to see-through and back
when he leaves (`shaders/wall_back.gdshader`, `wall_front.gdshader`, `World.gd _update_fade`).

## Stage 2: ground
- `tools/build_ground.py` paints the whole world from your grass tile sheets (`art/source/ground/grass_sheet_*.png`):
  seamless grass base, soft organic meadow / clover / flower / dirt patches, and a stone avenue (the floor tile)
  from the north gate through the south gate. Saved as 1024 px WebP chunks in `art/game/ground/`; the minimap shows it.
  Mud roads: your mud tiles (`mud_sheet_*.png`) laid evenly on a 128 px grid, in exactly the shape of your road
  plan (`road_plan.png`) scaled into the ring; its central spine runs from the north gate to the south gate,
  plus a road out of the north gate. The stone avenue now only runs outside the south gate. Layout references: `art/source/ground/reference_layout.png`, `reference_layout_2.png`.

## Rebuild
```
python3 tools/build_assets.py art/source/floor_tile.png       # floor, earth, Kael
FULL_ALPHA=1 python3 tools/build_walls.py art/source/walls/ring_final_design.png art/source/walls/ring_final_x4.png
python3 tools/build_objects.py                                 # split walls into objects (towers / stretches) for see-through
python3 tools/build_ground.py                                  # stage 2 ground (after build_walls)
tools/shots.sh                                                 # docs/screenshots
godot --path . -- --test                                       # reachability test
```
