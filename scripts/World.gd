extends Node2D
## Builds the palace ring from data/layout.json (written by tools/build_ring.py):
##   Ground  - TileMapLayer, 16x16 tiles (floor slab, water, rocky shore)
##   Deco    - causeway bridge
##   Shadows - baked wall shadows (one light, upper-left)
##   World   - y-sorted: wall sprites cut into 32 px strips, each sorted by its own ground line, plus Kael
##   Walls   - collision rectangles derived from the art (separate from the sprites)
##   UI      - minimap (top-right, M to expand)
## Command line (after --):  --capture --out=f.png [--pos=x,y] [--frames=n] [--bigmap] [--zoom=z] [--hideui] [--hideplayer]
##                           --test   (collision flood-fill from the spawn)

const TILE := 16
var L: Dictionary
var world: Node2D
var player: CharacterBody2D
var walls_body: StaticBody2D
var shadows: Node2D
var tex := {}
var args := {}

func t(n: String) -> Texture2D:
	if not tex.has(n):
		tex[n] = load("res://art/game/%s.png" % n)
	return tex[n]

func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		var s := String(a).trim_prefix("--")
		var kv := s.split("=", true, 1)
		args[kv[0]] = kv[1] if kv.size() > 1 else "1"
	_inputs()
	L = JSON.parse_string(FileAccess.get_file_as_string("res://data/layout.json"))
	_ground()
	var deco := Node2D.new(); deco.name = "Deco"; add_child(deco)
	shadows = Node2D.new(); shadows.name = "Shadows"; add_child(shadows)
	world = Node2D.new(); world.name = "World"; world.y_sort_enabled = true; add_child(world)
	walls_body = StaticBody2D.new(); walls_body.name = "Walls"; add_child(walls_body)
	_water_collision()
	_bridge(deco)
	for sp in L["sprites"]:
		_wall_sprite(sp)
	for r in L["wall_rects"]:
		_rect_col(walls_body, Rect2(r[0], r[1], r[2], r[3]))
	_player()
	var mm = load("res://scripts/Minimap.gd").new()
	mm.setup(self)
	add_child(mm)
	if args.has("capture"):
		_capture(mm)
	elif args.has("test"):
		_test()

func _inputs() -> void:
	var map := {
		"move_up": [KEY_W, KEY_UP], "move_down": [KEY_S, KEY_DOWN],
		"move_left": [KEY_A, KEY_LEFT], "move_right": [KEY_D, KEY_RIGHT],
		"run": [KEY_SHIFT], "toggle_map": [KEY_M],
	}
	for act in map:
		if not InputMap.has_action(act):
			InputMap.add_action(act)
		for k in map[act]:
			var e := InputEventKey.new()
			e.physical_keycode = k
			InputMap.action_add_event(act, e)

# ------------------------------------------------------------------ ground
func _atlas(ts: TileSet, name: String, cells: int) -> int:
	var src := TileSetAtlasSource.new()
	src.texture = t(name)
	src.texture_region_size = Vector2i(TILE, TILE)
	for y in cells:
		for x in cells:
			src.create_tile(Vector2i(x, y))
	return ts.add_source(src)

func _ground() -> void:
	var ts := TileSet.new()
	ts.tile_size = Vector2i(TILE, TILE)
	var sf := _atlas(ts, "floor_atlas", 8)
	var sw := _atlas(ts, "water_atlas", 4)
	var ss := _atlas(ts, "shore_atlas", 4)
	var g := TileMapLayer.new()
	g.name = "Ground"
	g.tile_set = ts
	add_child(g)
	var grid: Array = L["grid"]
	for y in grid.size():
		var row: String = grid[y]
		for x in row.length():
			var c := row[x]
			if c == "F":
				g.set_cell(Vector2i(x, y), sf, Vector2i(x % 8, y % 8))
			elif c == "W":
				g.set_cell(Vector2i(x, y), sw, Vector2i(x % 4, y % 4))
			else:
				g.set_cell(Vector2i(x, y), ss, Vector2i(x % 4, y % 4))

func _water_collision() -> void:
	var b := StaticBody2D.new()
	b.name = "Water"
	add_child(b)
	for r in L["water_rects"]:
		var cs := CollisionShape2D.new()
		var rs := RectangleShape2D.new()
		rs.size = Vector2(r[2], r[3]) * TILE
		cs.shape = rs
		cs.position = Vector2(r[0], r[1]) * TILE + rs.size * 0.5
		b.add_child(cs)
	var ws: Array = L["world"]
	for e in [Rect2(-64, -64, ws[0] + 128, 64), Rect2(-64, ws[1], ws[0] + 128, 64), Rect2(-64, 0, 64, ws[1]), Rect2(ws[0], 0, 64, ws[1])]:
		_rect_col(b, e)

func _rect_col(body: Node, r: Rect2) -> void:
	var cs := CollisionShape2D.new()
	var rs := RectangleShape2D.new()
	rs.size = r.size
	cs.shape = rs
	cs.position = r.position + r.size * 0.5
	body.add_child(cs)

# ------------------------------------------------------------------ wall sprites
## Each sprite is cut into 32 px wide strips; a strip's origin is its lowest opaque row, so Kael sorts
## in front of / behind every part of the wall by the real ground contact line.
func _wall_sprite(sp: Dictionary) -> void:
	var tx := t(sp["img"])
	var sh: Dictionary = sp["shadow"]
	var ss := Sprite2D.new()
	ss.texture = t(sh["img"])
	ss.centered = false
	ss.position = Vector2(sh["x"], sh["y"])
	shadows.add_child(ss)
	var strips: Array = sp["strips"]
	var w: int = sp["w"]
	var h: int = sp["h"]
	for i in strips.size():
		var x0 := i * 32
		var sw := mini(32, w - x0)
		var foot: int = strips[i]
		var s := Sprite2D.new()
		s.texture = tx
		s.region_enabled = true
		s.region_rect = Rect2(x0, 0, sw, h)
		s.centered = false
		s.offset = Vector2(0, -foot)
		s.position = Vector2(sp["x"] + x0, sp["y"] + foot)
		world.add_child(s)

func _bridge(parent: Node) -> void:
	var b: Array = L["bridge"]
	var cw := t("causeway")
	var y: float = b[1]
	while y < b[2]:
		var s := Sprite2D.new()
		s.texture = cw
		s.rotation = PI * 0.5
		s.position = Vector2(b[0], y + cw.get_width() * 0.5)
		parent.add_child(s)
		y += cw.get_width() - 2

# ------------------------------------------------------------------ Kael
func _player() -> void:
	player = CharacterBody2D.new()
	player.name = "Kael"
	player.set_script(load("res://scripts/Player.gd"))
	var sh := Sprite2D.new(); sh.name = "Shadow"; sh.texture = t("kael_shadow"); sh.position = Vector2(1, -1)
	player.add_child(sh)
	var sp := Sprite2D.new(); sp.name = "Sprite"; sp.texture = t("kael"); sp.hframes = 4; sp.vframes = 4
	sp.centered = false; sp.offset = Vector2(-8, -28)
	player.add_child(sp)
	var cs := CollisionShape2D.new()
	var rs := RectangleShape2D.new(); rs.size = Vector2(12, 6)
	cs.shape = rs; cs.position = Vector2(0, -3)
	player.add_child(cs)
	var cam := Camera2D.new(); cam.name = "Cam"; cam.position = Vector2(0, -14)
	var ws: Array = L["world"]
	cam.limit_left = 0; cam.limit_top = 0; cam.limit_right = int(ws[0]); cam.limit_bottom = int(ws[1])
	player.add_child(cam)
	var sp0: Array = L["spawn"]
	player.position = Vector2(sp0[0], sp0[1])
	world.add_child(player)

# ------------------------------------------------------------------ evidence + test hooks
func _capture(mm) -> void:
	if args.has("pos"):
		var q := str(args["pos"]).split(",")
		player.position = Vector2(float(q[0]), float(q[1]))
	if args.has("zoom"):
		var z := float(args["zoom"])
		(player.get_node("Cam") as Camera2D).zoom = Vector2(z, z)
		var c := player.get_node("Cam") as Camera2D
		c.limit_left = -100000; c.limit_top = -100000; c.limit_right = 100000; c.limit_bottom = 100000
	if args.has("hideui"):
		mm.visible = false
	if args.has("bigmap"):
		mm.toggle()
	if args.has("hideplayer"):
		player.get_node("Sprite").visible = false
		player.get_node("Shadow").visible = false
	for i in int(args.get("frames", "8")):
		await get_tree().process_frame
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	img.save_png(str(args.get("out", "/tmp/cap.png")))
	print("CAPTURED ", args.get("out"), " ", img.get_size())
	get_tree().quit()

## Flood fill over the real collision (Kael's 12x6 footprint, 16 px steps) from the spawn.
func _test() -> void:
	await get_tree().physics_frame
	await get_tree().physics_frame
	var space := get_world_2d().direct_space_state
	var q := PhysicsShapeQueryParameters2D.new()
	var rs := RectangleShape2D.new(); rs.size = Vector2(12, 6)
	q.shape = rs
	q.exclude = [player.get_rid()]
	var start := player.position
	var seen := {}
	var queue: Array[Vector2i] = [Vector2i(0, 0)]
	seen[Vector2i(0, 0)] = true
	var ws: Array = L["world"]
	while not queue.is_empty():
		var c: Vector2i = queue.pop_back()
		for d in [Vector2i(1, 0), Vector2i(-1, 0), Vector2i(0, 1), Vector2i(0, -1)]:
			var nc: Vector2i = c + d
			if seen.has(nc):
				continue
			var p := start + Vector2(nc) * 8.0
			if p.x < 0 or p.y < 0 or p.x > ws[0] or p.y > ws[1]:
				continue
			q.transform = Transform2D(0, p + Vector2(0, -3))
			if space.intersect_shape(q, 1).is_empty():
				seen[nc] = true
				queue.append(nc)
	var g: Array = L["gate"]
	var sd: Array = L["inside_seed"]
	var places := {
		"quay (spawn)": Vector2(L["spawn"][0], L["spawn"][1]),
		"causeway mid": Vector2(L["bridge"][0], (L["bridge"][1] + L["bridge"][2]) * 0.5),
		"gate arch": Vector2(g[0], g[1]),
		"inside the ring": Vector2(sd[0], sd[1]),
		"inside, far NW": Vector2(g[0] - 1500, sd[1] - 200),
		"inside, far NE": Vector2(g[0] + 1500, sd[1] - 200),
	}
	var fails := 0
	for k in places:
		var bp: Vector2 = places[k]
		var best := 1e9
		for c in seen:
			best = minf(best, (start + Vector2(c) * 8.0).distance_to(bp))
		var ok := best < 40.0
		if not ok:
			fails += 1
		print("%s  %s  (nearest reachable %.0f px)" % ["PASS" if ok else "FAIL", k, best])
	# (the outer shore is walkable by design; that the walls seal the interior is checked by tools/ring_leaks.py)
	print("reachable cells: ", seen.size(), "   failures: ", fails)
	get_tree().quit()
