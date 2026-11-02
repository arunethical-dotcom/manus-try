# Palace walls (Godot 4.4)

The outer palace wall ring, built from the single whole-ring image `art/source/walls/ring_magenta.png`. Walls only.

- Walk: WASD / arrows, **Shift** run, **M** expand / collapse the minimap.
- Scale: tile 16 px, Kael 28 px, viewport 960x540. Only the walls are big: 1 image px = 4 game px.
- World: 493 x 306 tiles (the ring ~413 x 216).
- Two gates: the gatehouse in the south (spawn just outside it) and the small gate in the north.

## How it is built
- The ring image is keyed off its magenta backdrop and upscaled 4x (Real-ESRGAN anime 6B, run in numpy:
  `tools/upscale/`), then made crisp pixel art by `tools/pixelize.py` (2x2 game-pixel blocks, 48-colour palette). Because it is one picture there are no joins between pieces.
- `tools/build_walls.py`: collision from the art (bands along the inside and outside edges of the ring and under each
  wall), sealed except at the two gate arches (the build fails otherwise); per-pixel ground map for draw order
  (`shaders/wall_front.gdshader` redraws the wall pixels standing in front of Kael); baked shadows; minimap.
- The older kit-assembly path (`tools/build_kit.py`, `tools/ring_layout.py`, `art/source/kit/`) is kept but not used.

## Rebuild
```
python3 tools/build_assets.py art/source/floor_tile.png       # floor, earth, Kael
W=RealESRGAN_x4plus_anime_6B.pth python3 tools/upscale/esrgan_np.py art/source/walls/ring_magenta.png art/source/walls/ring_magenta_x4.png alpha.png   # ~11 min CPU
python3 tools/pixelize.py art/source/walls/ring_magenta_x4.png art/source/walls/ring_magenta_px.png   # crisp 2x2-pixel art, 48 colours
python3 tools/build_walls.py art/source/walls/ring_magenta.png art/source/walls/ring_magenta_px.png
tools/shots.sh                                                 # docs/screenshots
godot --path . -- --test                                       # reachability test
```
