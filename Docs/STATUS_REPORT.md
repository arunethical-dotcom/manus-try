# Status report — PASS / FAIL / NOT IMPLEMENTED

## What was actually run
* Godot 4.4.1 headless: `--import`, `Tools/BuildScenes.gd` (all scenes build with no errors), and the route bot `-- --bot --instant` -> **47 checks, 0 failed** (`Docs/playtest_report.txt`). The bot uses the real Player through simulated input events, real collision (the 20x12 footprint against physics layer 1) and the game's own doors; collision-true flood-fill/path planning proves traversability.
* Screenshots rendered with Godot under Xvfb (GL Compatibility, `Tools/capture.sh`) -> `Docs/screenshots/`.
* `Tools/verify_alpha.py` -> `Docs/alpha_report.txt`; SHA-256 of all 25 sources against the pack.
* **Not run**: the Godot editor GUI, a real GPU/display, gamepad/touch, long free-play sessions, other OSes. The bot proves routes and collision, not game feel or visual quality; screenshots were reviewed by me only.

## README acceptance checks
| # | Check | Result | Evidence / note |
|---|---|---|---|
| 1 | Elevated top-down 3/4 camera; no flat side-view/isometric reference in the playable scene | **PASS** | `a_gameplay_exterior_bridge.png`, `b_courtyard_keep_door_prompt.png`; overview PNGs are in no scene (grep) |
| 2 | Asymmetrical fortress / rooms | **PASS** | Courtyard.tscn: tallest keep far left, broad low hall right, chapel far right, library tower off-axis; Approach.tscn: west wall = 1 piece + tower, east = 3 pieces + tower (`b_courtyard_overview_collisions.png`, `a_exterior_overview_collisions.png`) |
| 3 | Player scale anchored at 64 px | **PASS** (placeholder art) | `Scenes/Player.tscn` sprite 32x64; bot check 1; `d_scale_player_vs_door_4x.png`, ScaleTest ruler. No player reference was supplied; the sprite is my own placeholder |
| 4 | All 25 images included; 23 individually importable | **PASS** | `Art/Source/` (23) + `Art/Source/reference_overviews/` (2), 25 `.import` files, SHA-256 identical; all 23 used in `Scenes/Test/AssetGallery.tscn` |
| 5 | Alpha correct, no magenta halo / opaque matte | **PASS** | `Docs/alpha_report.txt`, `e_alpha_gallery_overview.png`, `e_alpha_gallery_zoom_edges.png`. Source alpha was *not* clean (max 254, halos); fixed by thresholding in Art/Processed |
| 6 | Ground-tile edge repeat tested; seams fixed or used as patches | **FAIL (partially mitigated)** | Tested (`e_tile_seam_test.png`, seam ratios in `Docs/ASSET_PROVENANCE.md`). Derived seamless copies lower the ratio (cobble 5.69->4.06, grass 4.82->2.45, water 5.34->4.32) but not to ~1; tiles still repeat at 240 px. Not used as unique patches |
| 7 | Y-sorting and roof/occlusion work with player behind/in front | **PASS** (design note) | Bot checks (y-order + fade alpha) in ScaleTest; `d_ysort_behind_oak_fade.png`, `d_ysort_front_of_oak.png`, `d_ysort_behind_wall_fade.png`, `d_ysort_front_of_wall.png`, `d_ysort_behind_building_roof_fade.png`. Roofs are not a separate overlay layer: strips + fade zones |
| 8 | Exterior routes and all listed rooms connect through playable entrances | **PASS** | bot: approach->gate->courtyard->keep/library/chapel/hall/kitchen/barracks, east gate->stable/blacksmith, and back |
| 9 | Underground: hidden entrance, branch/loop, traversable exit/return | **PASS** | bot: well and pantry entrances (clue first), lever, loop legs reachable, sealed tunnel opened by wall push, exit to Approach at (2450,1075) outside the walls, grate back down, well ladder back up (`c_underground_*.png`) |
| 10 | Collision separate from art; every major path traversable | **PASS** (caveats) | `*_overview_collisions.png` show designed polygons; bot flood-fill. Caveats: garden hedges not solid; exterior polygons measured by eye |
| 11 | Screenshots show gameplay camera, scale, alpha and depth sorting | **PASS** | `Docs/screenshots/` (a-e sets) |

## Build-prompt requirements
| Requirement | Result | Evidence / note |
|---|---|---|
| Inspect existing project, preserve conventions | **PASS (n/a)** | The target repo was empty (no commits), so there was nothing to preserve. An earlier side-view build was discarded at your instruction ("a change in whole") and is not in the repo |
| Camera rules: no side elevation / diamond board / perspective / sprite rotation | **PASS** | no `rotation` anywhere; plain Camera2D |
| 64 px scale anchor; engine scale recorded; consistent door/path/stair proportions | **PASS** | `Docs/RUN_GUIDE.md` (scale section) |
| Asymmetric castle | **PASS** | see check 2 |
| Use regenerated individual assets; overviews reference-only | **PASS** | overviews in `Art/Source/reference_overviews`, unused by scenes |
| Source preserved; processed folder with provenance | **PASS** | `Art/Source` untouched; `Art/Processed/manifest.json`, `Docs/ASSET_PROVENANCE.md` |
| Nearest, no mipmaps, no lossy compression, integer downscale, pixel snapping | **PASS** | `project.godot`; `.import` files; factors in `Art/sprite_specs.json` |
| Footpoint Y-sort | **PASS** | `Tools/BuildScenes.gd place()`; bot sorting checks |
| Roofs on a deliberate overlay/occlusion layer | **PASS (as fade zones)** | `Scripts/Occluder.gd`; not a separate roof sprite layer |
| Verify alpha on import | **PASS** | `Docs/alpha_report.txt` |
| Ground tile edges tested and fixed or used as patches | **FAIL (partial)** | see check 6 |
| Collision and navigation independent of art, designed shapes, no full-sprite rectangles | **PASS (collision) / NOT IMPLEMENTED (navigation)** | no NavigationRegion/agents exist; nothing needs AI |
| No labels/arrows baked into sprites | **PASS** | ruler lines/labels in ScaleTest/Gallery are nodes; sprites contain none |
| W1 Forest/river approach: paths, water edge, rock edge, waterfall | **PASS** (placeholder rock) | Approach.tscn; `a_waterfall_cliff_rock_edge.png`. The cliff/outcrop texture is a generated placeholder |
| W2 Gatehouse, drawbridge, wall route | **PASS (partial scope)** | walk-through gate over a ground-layer drawbridge, moat corridor; "wall route" = bank along the wall, no wall-walk |
| W3 Courtyard: well/fountain, garden, routes to rooms | **PASS** | Courtyard.tscn, `b_courtyard_*` |
| W4 Great hall + kitchen/bakery service route | **PASS** | GreatHall <-> Kitchen door |
| W5 Chapel and library/upper-keep route | **PASS** | Keep -> Library stair door; Keep <-> Chapel (stairs are transitions) |
| W6 Barracks/training | **PASS (minimal)** | Barracks.tscn + dummies/racks; no training mechanic |
| W7 Stable and blacksmith service yard | **PASS** | ServiceYard.tscn |
| W8 Hidden passage from well or pantry with discoverable clues | **PASS** | both implemented; clues: chest note, leaning torch, scuffed shelf, altar inscription, library ledger, prison note |
| W9 Cistern, crypt/prison junction, branch/loop, escape emerging beyond the wall | **PASS** | Underground.tscn + bot |
| Real traversable entrances on every room | **PASS** | bot |
| Stage 2 scale-test scene | **PASS** | `Scenes/Test/ScaleTest.tscn` |
| Stage 3 graybox-first workflow | **NOT IMPLEMENTED** | built straight with art; traversability was validated by the bot, not on a separate graybox |
| Grid-aligned collision | **PARTIAL / FAIL for exterior** | interiors and underground are 32 px grid-derived; exterior polygons are free-form |
| Player cannot snag on decoration / pass through walls | **PASS (tested for walls)** | bot drives into the south wall and keep facade; small 20x12 footprint; decoration snagging not exhaustively tested |
| Deliverable: playable project | **PASS** | |
| Deliverable: run guide | **PASS** | `Docs/RUN_GUIDE.md` |
| Deliverable: screenshots (a)-(e) | **PASS** | `Docs/screenshots/` |

## Smallest next steps
1. Replace the generated placeholders (player, interiors, rock) with real art.
2. Fix tile seams properly (re-generate tiles or use them as unique patches).
3. Add hedge colliders in the garden and pixel-verify exterior footprints against the collision overlay.
4. Decide whether roofs should become a separate overlay sprite layer.
