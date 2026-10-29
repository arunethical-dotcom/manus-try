# Palace Walls (Godot 4.4)

The palace from the supplied blueprint, built in Godot with the supplied wall kit and floor slab.
Only the structure + a simple character (Kael), a minimap and running.

## Run
Open the folder in **Godot 4.4.x** and press F5 (main scene `scenes/Main.tscn`).

| Key | Action |
|---|---|
| WASD / arrows | walk |
| Shift (hold) | run (1.8x) |
| M | expand / collapse the minimap (top-right) |

## Scale
| | |
|---|---|
| Tile | 16 x 16 px |
| Kael | 28 px tall (16x28 frames, 4 directions x 4 walk frames) |
| Viewport | 960 x 540 (60 x 34 tiles), window 1920x1080, integer scaling, nearest filter, pixel snap |
| Palace | ~430 tiles wide x ~320 tiles deep (map 522 x 441 tiles incl. moat and quay) |

## How it is built
* `tools/build_assets.py <wall_kit_dir> <floor_tile.png> <blueprint.png>` makes everything in `art/game/` and `data/layout.json`:
  * wall centre-lines traced from the blueprint (left half, mirrored - the plan is symmetric); gaps for the 2 gatehouses and the stairs;
  * ground grid (water / paved floor / rocky shore) classified from the blueprint colours, 1 cell per 16 px tile;
  * floor tiles: the isometric slab un-warped to a flat square (8x8-tile atlas); wall face / walkway textures cut from `01_straight_wall` and `10_causeway`; towers, gatehouses, stairs, causeway sprites from the kit; Kael and the minimap image are generated.
* `scripts/World.gd` builds the level at runtime: TileMapLayer ground, wall chunks (top walkway + south face, y-sorted in 64 px chunks so Kael passes behind/in front), towers, gatehouses, stairs, causeway bridge, collision (wall bands, tower/gate bases, water), shadows, Kael and the minimap.
* Shadows: one light from the upper-left; walls, towers and gatehouses cast soft blue-violet shadows to the lower-right on a dedicated layer (no collision). Kael has a contact shadow.
* Originals are kept untouched in `art/source/`.

## Tests / evidence
* `godot --headless --path . -- --test` flood-fills the real collision from the spawn: quay, causeway, outer gate, central lane, inner gate/top court, both great courts, both upper terraces (via stairs), middle yards - all reachable (12/12 PASS).
* Screenshots (real 960x540 game view): `docs/screenshots/` (08 is a zoomed-out overview). `tools/capture.sh out.png [--pos=x,y] [--zoom=z] [--bigmap]` (needs xvfb).

## Not done / limits
* Only the structure (no buildings inside, no enemies, no height levels - stairs are walk-through openings).
* The isometric corner / T / cross / wall-end kit pieces don't match a top-down plan, so corners are made from the straight-wall textures; towers cover most joints.
* Not hand-played on a real display here; verified by the collision test and rendered screenshots.
