# Manus 2.0 — Castle Action-RPG Build Prompt

> Use this prompt with the regenerated `castle_crosscode_rework_pack.zip` extracted into the existing game project.

---

## Goal

Turn the existing project into a polished, explorable first chapter of an original 2D medieval action-RPG, using the supplied castle art assets. The target is a **rich, colorful, detailed top-down 3/4 action-RPG presentation**: dense pixel clusters, layered height shading, readable depth, lively environment and strong light/color contrast. Take those broad genre-level qualities as direction only; do not copy any particular game's maps, characters, layouts, UI, proprietary assets or distinctive designs.

First inspect the existing project: determine its engine, rendering pipeline, resolution, controls, player controller, scene structure and current work. Preserve the project and its conventions; do not reset, replace or migrate it without explicit approval.

## Mandatory visual rules

- Camera: elevated top-down 3/4 gameplay view. Show walkable ground surfaces plus roof planes, wall thickness and near-side entrances. Make front facades readable as part of the overhead world.
- Do **not** use flat side-scroller elevation, a full diamond-isometric board, perspective-camera rendering, or arbitrary sprite rotation to force a viewpoint.
- Keep the castle asymmetrical: tallest keep offset left; broader/lower wing to right; unequal towers and varied wall lengths. Avoid mirroring.
- Use the 64-game-pixel character reference as a scale anchor. Record the engine scale and maintain consistent door, path and stair proportions.
- Use the regenerated `assets/` images, not the previous straight-on asset pack. The overview images are reference images only; do not place the complete overview map as a gameplay background in place of modular playable geometry.
- Individual building and prop art is intended to have true alpha. Verify alpha on import. Ground tile images are not guaranteed to be perfectly seamless; test their edges before repeating.
- Preserve source images. Put cropped/downscaled working derivatives in the project's processed-art folder and keep filenames/provenance traceable.
- For pixel art: nearest-neighbor filtering, no lossy texture compression, no mipmaps, uniform/integer scaling where feasible, and pixel snapping if supported.
- Configure footpoint-based Y-sorting (or engine equivalent). The player should pass behind tree canopies/building front layers and in front of them according to ground contact. Keep roofs on a deliberate overlay/occlusion layer.

## World requirements

Build a coherent opening chapter as connected playable rooms/areas, not a collage:

1. Forest/river approach with traversable paths, water edge, rock edge and waterfall landmark.
2. Castle gatehouse, drawbridge and wall route.
3. Main courtyard with well/fountain, garden and a route to major rooms.
4. Great hall and connected kitchen/bakery service route.
5. Chapel and library/upper keep route.
6. Barracks/training route.
7. Stable and blacksmith service yard.
8. A hidden passage entrance discoverable from the well or pantry.
9. Underground cistern, crypt/prison junction, a branch or loop, and an escape route that returns/emerges beyond the castle wall.

Every room must have real traversable entrances. Add any required stairs, ladders, doors and bridge/platform pieces with the existing project’s control scheme. A decorative doorway without a walkable transition does not count. Secret routes need player-discoverable clues, collision-tested traversal and a connected exit/return.

## Implementation stages

1. Inspect and report the existing project's engine, key scenes, target resolution, player scale and asset-import conventions.
2. Create a scale-test scene: player, floor, wall, one building entrance, tree and one roof/occlusion test. Tune camera and sprite sorting first.
3. Graybox exterior route and room connections. Keep collision and navigation separate from images.
4. Implement connected interior scenes/rooms and underground route; validate traversal before decoration.
5. Import and crop the supplied sprites without overwriting source art. Establish pivots/footpoints, sorting layers and reusable prefabs/scenes.
6. Replace graybox art progressively; add props, tile surfaces, lighting, particles and effects only after readability and route validation.
7. Test all transitions from the opening approach through the secret dungeon and back to a safe surface exit.

## Technical quality gates

- No full-sprite-rectangle colliders: use designed collision shapes for walls, floors, obstacles, doors and ledges.
- Use grid-aligned collision and navigation. Verify player cannot snag on decorative pixels or pass through castle walls.
- Test Y-sorting with the player moving behind/in front of pine, oak, well, fountain, wall and building-front layers.
- Review ground-tile edges at target scale. Fix visible repeats/seams in derivatives or use the generated tile as a unique patch.
- Keep UI out of the artwork unless already part of the project. Do not bake labels or route arrows into gameplay sprites.

## Deliverables and proof

1. Updated playable opening-level project, not just a plan or map image.
2. Connected exterior, interiors and underground route.
3. Source art preserved; imported assets/pivots/sorting documented.
4. A short run guide listing changed files/scenes, controls, scale, route and known limitations.
5. Evidence screenshots: (a) gameplay exterior, (b) courtyard/building access, (c) underground map/scene, (d) Y-sort test, (e) import/alpha check.

## Final status report

For each requirement above and each README acceptance check, report **PASS**, **FAIL** or **NOT IMPLEMENTED**. For every PASS, cite a project scene/file and preferably an evidence screenshot. State clearly what was run and tested. Do not claim perfect or 100% accuracy for unchecked items; report blockers and the smallest next step instead.

---
