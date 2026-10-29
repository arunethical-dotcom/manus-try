# Run guide

## Engine, scale, camera
* Godot 4.4.1, GL Compatibility renderer. Viewport **960x540**, window override 1920x1080, stretch mode `viewport`, scale mode `integer` (exact 2x).
* **Engine scale: 1 world unit = 1 game pixel, camera zoom 1.0.** Player sprite is **32x64 px (64 px tall = the scale anchor)**; footprint collider 20x12 at the feet.
* Reference proportions at this scale: building doors are ~80-140 px tall (1.25-2x the player), the drawbridge corridor is ~150 px wide, the garden gates are 70 px wide, interior doors 44x66 px.
* Default texture filter = Nearest, no mipmaps, lossless import (`compress/mode=0`), `snap_2d_transforms_to_pixel` + `snap_2d_vertices_to_pixel` on.
* Camera: plain `Camera2D` following the player at pixel positions (no rotation, no perspective, no isometric board). Building art is the pack's elevated 3/4 art.

## Controls
| Key | Action |
|---|---|
| WASD / arrow keys | move (8 directions) |
| E / Enter / Space | interact (doors, well, search spots, lever) |
| R | restart from the forest |

Walk-through transitions (gate arch, east/west yard gates, south gate) trigger by walking into them.

## Route (every link is exercised by `Docs/playtest_report.txt`)
1. **Approach** (`Scenes/Exterior/Approach.tscn`): start at the south edge, follow the cobble path over the paved ford, up to the drawbridge, walk through the gate arch.
2. **Courtyard** (`Courtyard.tscn`): garden with fountain bed (walkable south<->north), well, chest note, keep (tall, left), library tower, great hall (broad, right), chapel, kitchen/bakery, barracks + training dummies. East gate -> **Service Yard** (`ServiceYard.tscn`): stable, blacksmith. South gate returns to the approach.
3. **Interiors** (`Scenes/Interior/`): Keep -> stair door -> Library (upper keep); Keep <-> Chapel; Great Hall <-> Kitchen (service door); Barracks; Stable; Blacksmith. Every room has a door back out.
4. **Secret descent, two entrances**: (a) *Well* in the courtyard: examine it (clue: cold draft, scrape marks; the torch beside it leans toward the shaft; the courtyard chest holds a note), then climb down. (b) *Kitchen pantry*: inspect the shelves (clue), then pull the false shelf.
5. **Underground** (`Scenes/Underground/Underground.tscn`, one dark scene): well shaft landing -> cistern (water pool, stone ledges, causeway) -> junction -> crypt (lever behind the third coffin) and prison (cages, chest note). Loop: junction -> prison -> west passage -> old pantry stair (ladder up to the kitchen) -> cistern -> junction. The west passage is barred by a rusted gate until the crypt lever is pulled.
6. **Escape**: examine the crypt's east wall (newer brickwork, torch leans toward it), push the stones, follow the smuggler's tunnel to the ladder -> surface on the forest hillside **outside the castle wall**. The drain grate there leads back down (return route).

## Changed / added files
* `project.godot`, `.gitignore`
* `Scripts/` Game (autoload: input map, HUD, transitions, flags, capture hooks), Player, Interactable, AutoDoor, Occluder, Gate, Zone, FlagVisible, LevelBase, RouteBot
* `Scenes/` all `.tscn` are **generated** by `Tools/BuildScenes.gd` (re-run to rebuild): Player, Exterior/{Approach,Courtyard,ServiceYard}, Interior/{GreatHall,Kitchen,Chapel,Keep,Library,Barracks,Stable,Blacksmith}, Underground/Underground, Test/{ScaleTest,AssetGallery}
* `Tools/` process_assets.py -> make_game_sprites.py -> BuildScenes.gd; make_generated.py (placeholder art); verify_alpha.py; capture.sh; sprite_meta.json (hand-measured doors, footprints, front edges, occlusion zones)
* `Art/Source` (untouched) / `Art/Processed` (alpha-normalised, cropped, full-res, seamless tile derivatives) / `Art/Game` (integer-downscaled, used by the game) / `Art/Generated` (placeholders) / `Art/sprite_specs.json`

## Rebuild and test
```
godot --headless --import --path .
python3 Tools/process_assets.py && python3 Tools/make_game_sprites.py     # only if art changes
godot --headless --path . --script res://Tools/BuildScenes.gd             # regenerate scenes
godot --headless --fixed-fps 60 --path . -- --bot --instant               # 47-check route/collision/sorting play-test
Tools/capture.sh res://Scenes/Exterior/Courtyard.tscn out.png --spawn=from_keep --collisions   # screenshot (needs xvfb)
```

## Known limitations
* Pack art covers exteriors only. **Player sprite, interior floors/walls, furniture, door/mat/ladder sprites, the cave/rock texture used for the west cliff and underground** are generated placeholders (`Art/Generated`, `Tools/make_generated.py`), not pack art, and are of a different pixel density than the downscaled pack sprites.
* No player reference image was in the zip; the 64 px player is an original placeholder.
* Ground tiles are not perfectly seamless even after the derived fix (see STATUS_REPORT).
* Hedges inside the garden patch have no collision (only the garden walls and fountain bed do). Exterior footprint polygons were measured by eye from gridded views, not pixel-verified.
* Roofs are not a separate overlay sprite layer: each building is cut into 32 px vertical strips that are Y-sorted by their own ground-contact line, and a fade zone makes the building translucent when the player is behind it.
* Stairs/ladders are interact-to-transition doors, not walkable stair geometry. The "wall route" is the paved/grass bank along the moat; there is no wall-walk.
* No enemies, combat, NPCs, audio or save system (not requested). No navigation mesh/AI (nothing needs one).
* The south and north walls inside the courtyard reuse the pack's outward-facing wall art.
