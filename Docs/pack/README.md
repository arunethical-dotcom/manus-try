# Castle Opening-Level Pack — Top-Down Action RPG Edition

A fully regenerated asset set for a colorful, detailed 2D action-RPG castle environment. It uses an **original** visual direction built from broad genre traits—dense handcrafted pixel clusters, elevated 3/4 gameplay camera, layered height shading, saturated natural colors, warm lighting and readable environmental storytelling. It is not a reproduction of CrossCode's specific artwork, characters, maps or assets.

## Pack contents

- `assets/` — 25 new PNGs: 2 overview maps and 23 standalone assets. The individual building/prop images use true alpha transparency; ground tiles are intended as tile textures.
- `MANUS_2_BUILD_PROMPT.md` — copy-ready project prompt for an AI game builder.
- `ASSET_MANIFEST.csv` — dimensions and usage notes for every image.
- `visual_blueprint.png` — a schematic, top-down level and route assembly diagram.
- `visual_blueprint.html` — editable source for that diagram.

## Camera and art direction

Use a **top-down 3/4 gameplay camera**: show traversable ground planes and roof planes, with building fronts readable on the near/lower edge. Avoid flat front elevation, side-scroller facades, pure diamond-isometric maps, arbitrary sprite rotation and perspective-camera effects. The intended feel is a richly layered action-RPG world, not flat platformer scenery.

Use the attached player reference as a scale cue: about 64 game pixels tall. Generated source artwork is high-resolution concept/sprite art and may need careful cropping and downscaling to the project's pixel grid. Pick an integer scale for the final game, retain nearest-neighbor filtering, and verify readability at native gameplay size.

## Asset pipeline

1. Preserve every original PNG. Work on copies under `Art/Processed`.
2. Building and prop sprites have native alpha transparency; verify the alpha channel before import. Do not add a magenta background or key out image colors from these transparent assets.
3. Grass, cobblestone and river images are ground-tile candidates. Before repeating, verify all four edges at target resolution. Generated art is not guaranteed seamless; correct seams in derived copies or use the images as unique terrain patches.
4. Crop transparent margins to visible bounds and define consistent bottom-center pivots for standing objects. For trees, separate the foot/root anchor from the canopy sorting extent if the engine supports it. Record import rectangles/pivots in metadata.
5. Use nearest-neighbor filtering, no lossy compression, no mipmaps for pixel art, and pixel snapping where supported. Downscale uniformly using integer factors; do not distort proportions.
6. Use a Y-sort or equivalent depth-sorting rule based on each actor/prop's ground-contact point. Keep tree crowns in front of/behind the player according to footpoint order. Roofs may be a separate overlay or an occlusion layer.
7. Use collision/navigation geometry independent of painted art. The overview images are visual references, not collision maps or automatically walkable game scenes.

## Recommended build sequence

1. Inspect the existing project and retain its engine, controller, resolution and scene conventions.
2. Establish the camera and a scale-test scene with the 64 px player, walkable path tile, building entrance and height-sorting test.
3. Graybox exterior connectivity before decorating: gate → outer yard → main courtyard → keep/hall wing → service yard.
4. Build interiors and the underground as connected scenes or rooms: great hall, chapel, barracks, stable, blacksmith, kitchen, library, cistern, crypt/prison and escape passage.
5. Include a discoverable secret entrance (well or service pantry), a branching/looping route, and a surface exit/return. Ensure the secret route is playable, not merely drawn into the map.
6. Replace graybox with new assets. Add ground, walls, roofs, foliage, props, lighting and particles only after route/collision tests pass.
7. Play-test at intended resolution and produce screenshots of exterior, interior/yard, underground and asset sorting/alpha checks.

## Acceptance checks

- [ ] Camera uses elevated top-down 3/4 gameplay framing; no flat side-view/isometric reference images are placed in the playable scene.
- [ ] Main fortress silhouette and room layout remain intentionally asymmetrical.
- [ ] Player scale is anchored at 64 game pixels (or a documented engine-unit equivalent).
- [ ] All 25 regenerated images are included; all 23 individual assets are individually importable.
- [ ] Transparent art keeps correct alpha; no magenta halo or unwanted opaque matte appears.
- [ ] Ground-tile edge repeat is tested; seams are fixed or tiles are used as non-repeating patches.
- [ ] Y-sorting and roof/occlusion layers work correctly with the player walking behind and in front of objects.
- [ ] Exterior routes and all listed rooms connect through playable entrances.
- [ ] Underground has a hidden entrance, a branch/loop, and a traversable exit/return.
- [ ] Collision is separate from art and every major path is traversable.
- [ ] Screenshots show the final gameplay camera, scale, alpha and depth sorting.

No prompt can guarantee perfect implementation. Require the builder to label each checklist item PASS/FAIL/NOT IMPLEMENTED and cite a scene/file or screenshot as evidence for each PASS. Do not report unchecked items as complete.
