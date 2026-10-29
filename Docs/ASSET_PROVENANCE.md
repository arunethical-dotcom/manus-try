# Asset provenance and import documentation

Pipeline: `Art/Source` (original, never modified) -> `Tools/process_assets.py` -> `Art/Processed` (full resolution, cleaned, cropped, traceable names) -> `Tools/make_game_sprites.py` -> `Art/Game` (integer box-downscale, used in scenes at scale 1.0) -> `Tools/BuildScenes.gd` -> `.tscn`.

All 25 source PNGs (23 individual + 2 overviews) are present and byte-identical to the pack (SHA-256 checked). The two overview images live in `Art/Source/reference_overviews/` and are referenced by no scene (reference only).

## Alpha findings (the pack's alpha is not what the README says)

* Building/prop sprites are **not** truly binary-clean: foreground alpha is 245-254 (never 255) and there are low-alpha halo pixels (1-127). `process_assets.py` snaps alpha >= 128 -> 255 and < 128 -> 0, then crops to visible bounds. No colour keying, no magenta anywhere.
* The three ground tiles ship with semi-transparent alpha (cobble 193-249, grass 225-247, water 196-247). They are forced opaque.
* Verification: `Tools/verify_alpha.py` -> `Docs/alpha_report.txt` (game-scale alpha strictly {0,255}, 0 magenta-ish opaque pixels, transparent corners) and `Docs/screenshots/e_alpha_gallery_*.png` (every sprite on a magenta|white split background).

## Ground tiles

| tile | seam ratio raw | seam ratio after derived fix | note |
|---|---|---|---|
| cobblestone_tile | 5.69 | 4.06 | `Art/Processed/cobblestone_tile_seamless.png` (half-offset smoothstep cross-blend) |
| grass_tile | 4.82 | 2.45 | `Art/Processed/grass_tile_seamless.png` (half-offset smoothstep cross-blend) |
| river_water_tile | 5.34 | 4.32 | `Art/Processed/river_water_tile_seamless.png` (half-offset smoothstep cross-blend) |

Seam ratio = mean abs difference across the wrap edge / mean abs difference between neighbouring pixels (1.0 = invisible). The fix reduces it but does not reach ~1, so seams are **mitigated, not eliminated**. Tiles are used as 240x240 px (1920 / 8) repeating textures. `Art/Processed/*_raw240.png` keep the unfixed version for comparison (`e_tile_seam_test.png`).

## Sprites: source -> processed -> game

Pivot rule everywhere: bottom-centre of the visible (cropped) bounds = ground-contact footpoint, except `gatehouse_main` (foot at (297,448): the tower base line, not the bridge tip). Buildings additionally carry a front-edge polyline; at build time they are cut into 32 px strips and each strip's sort key is its own point on that edge.

| asset | src size | crop rect (x,y,w,h in src) | processed | factor | game size | footprint polygons | door rects |
|---|---|---|---|---|---|---|---|
| barracks | [2176, 1632] | [22, 95, 2133, 1434] | `Art/Processed/barracks.png` | 1/3 | 711x478 | 1 | 1 |
| blacksmith | [2176, 1632] | [212, 11, 1889, 1542] | `Art/Processed/blacksmith.png` | 1/3 | 629x514 | 1 | 1 |
| chapel | [2176, 1632] | [510, 15, 1290, 1555] | `Art/Processed/chapel.png` | 1/3 | 430x518 | 1 | 1 |
| courtyard_garden | [1920, 1920] | [55, 74, 1810, 1772] | `Art/Processed/courtyard_garden.png` | 1/3 | 603x590 | 0 | 0 |
| fountain | [1920, 1920] | [177, 240, 1567, 1462] | `Art/Processed/fountain.png` | 1/8 | 195x182 | 1 | 0 |
| gatehouse_asset | [2176, 1632] | [222, 2, 1793, 1620] | `Art/Processed/gatehouse_asset.png` | 1/3 | 597x540 | 0 | 0 |
| gatehouse_bridge | - | - | `Art/Processed/gatehouse_asset.png` | 1/3 | 181x172 | 0 | 0 |
| gatehouse_main | [2176, 1632] | [222, 2, 1793, 1620] | `Art/Processed/gatehouse_asset.png` | 1/3 | 597x540 | 2 | 0 |
| great_hall | [2176, 1632] | [47, 17, 2094, 1567] | `Art/Processed/great_hall.png` | 1/3 | 698x522 | 1 | 1 |
| heraldic_banner | [1536, 2304] | [286, 34, 954, 2207] | `Art/Processed/heraldic_banner.png` | 1/20 | 47x110 | 0 | 0 |
| keep_asset | [2176, 1632] | [274, 12, 1687, 1591] | `Art/Processed/keep_asset.png` | 1/3 | 562x530 | 1 | 1 |
| kitchen_bakery | [2176, 1632] | [185, 5, 1852, 1602] | `Art/Processed/kitchen_bakery.png` | 1/3 | 617x534 | 1 | 1 |
| library_tower | [2176, 1632] | [655, 0, 1097, 1568] | `Art/Processed/library_tower.png` | 1/3 | 365x522 | 1 | 1 |
| modular_wall | [2304, 1536] | [50, 334, 2204, 865] | `Art/Processed/modular_wall.png` | 1/5 | 440x173 | 1 | 0 |
| oak_tree | [1536, 2304] | [16, 152, 1510, 1920] | `Art/Processed/oak_tree.png` | 1/8 | 188x240 | 1 | 0 |
| pine_tree | [1536, 2304] | [125, 56, 1293, 2116] | `Art/Processed/pine_tree.png` | 1/8 | 161x264 | 1 | 0 |
| stable | [2176, 1632] | [20, 4, 2127, 1561] | `Art/Processed/stable.png` | 1/3 | 709x520 | 1 | 1 |
| stone_well | [1920, 1920] | [245, 60, 1434, 1818] | `Art/Processed/stone_well.png` | 1/14 | 102x129 | 1 | 0 |
| treasure_chest | [1920, 1920] | [113, 128, 1723, 1720] | `Art/Processed/treasure_chest.png` | 1/36 | 47x47 | 1 | 0 |
| wall_torch | [1920, 1920] | [526, 46, 965, 1771] | `Art/Processed/wall_torch.png` | 1/36 | 26x49 | 0 | 0 |
| watchtower | [1536, 2304] | [249, 9, 1039, 2255] | `Art/Processed/watchtower.png` | 1/5 | 207x451 | 1 | 0 |
| waterfall | [1536, 2304] | [76, 108, 1392, 2107] | `Art/Processed/waterfall.png` | 1/8 | 174x263 | 1 | 0 |

Factors: main buildings 1/3 (doors come out ~80-140 px vs the 64 px player; 1/4 gave ~50 px doors, smaller than the player), watchtower/wall 1/5, trees 1/8, well 1/14, fountain 1/8, garden 1/3, chest/torch 1/36, banner 1/20, waterfall 1/8. Each is an integer box-filter downscale on premultiplied alpha followed by the hard alpha threshold. Full-resolution processed copies stay in `Art/Processed`.

`gatehouse_asset` is partitioned (no repainting) into `gatehouse_main` (towers/arch, Y-sorted) and `gatehouse_bridge` (flat drawbridge, drawn on the ground layer so the player walks over it).

## Generated placeholders (NOT pack art)

`Art/Generated/*` via `Tools/make_generated.py` (fixed seeds): player sheet (4 facings x 4 frames, 32x64), interior floor/wall/carpet tiles, cave rock, furniture boxes, door, exit mat, ladder. Used for interiors, the underground and the west cliff because the pack has no interior or rock art.

## Engine import settings

Project default texture filter = Nearest; every PNG import: `compress/mode=0` (lossless), `mipmaps/generate=false` (see any `Art/**/*.png.import`). Pixel snapping enabled in project settings.

## Y-sort / sorting documentation

* Each level has a `World` node with `y_sort_enabled`; every sortable thing is a direct child positioned at its ground-contact point (sprites use `offset` so the node origin is the foot).
* Trees, well, fountain, wall pieces, chest: one sprite, foot at bottom-centre. Buildings: 32 px strips, per-strip sort Y from the front-edge polyline. Player origin = feet.
* Fade zones (`Scripts/Occluder.gd`) fade the matching sprites to 40 % while the player's body is inside a rectangle behind the object.
* Collision is separate: `Collision/Col_*` StaticBody2D polygons authored in `Tools/sprite_meta.json` (`footprint`, `footprint_blocks`), never the sprite rectangle. Interiors/underground use 32 px grid-merged wall rectangles.
