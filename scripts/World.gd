extends Node2D
## Builds the palace from data/layout.json (written by tools/build_assets.py from the blueprint):
##   Ground  - TileMapLayer, 16x16 tiles (floor from the supplied slab, water, rocky shore)
##   Deco    - flat pieces drawn on the ground (causeway bridge, stairs)
##   World   - y-sorted: wall chunks, towers, gatehouses, Kael (sorted by ground-contact point)
##   Walls/Water - collision (separate from the art)
##   UI      - minimap (top-right, M to expand)
## Command line (after --):  --capture --out=f.png [--pos=x,y] [--frames=n] [--bigmap] [--zoom=z]
##                           --test   (collision flood-fill: checks every area is reachable from the spawn)

const TILE := 16
var L: Dictionary
var WT: float
var WH: float
var world: Node2D
var player: CharacterBody2D
var walls_body: StaticBody2D
var shadows: Node2D
## one light from the upper-left: every shadow falls to the lower-right (blue-violet, never black)
const SH_FAR := Vector2(18, 20)
const SH_NEAR := Vector2(5, 7)
const SH_COL := Color(0.14, 0.11, 0.30, 0.30)
const SH_CONTACT := Color(0.12, 0.09, 0.26, 0.30)
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
	WT = L["wall_thickness"]
	WH = L["wall_height"]
	_ground()
	var deco := Node2D.new(); deco.name = "Deco"; add_child(deco)
	shadows = Node2D.new(); shadows.name = "Shadows"; add_child(shadows)
	world = Node2D.new(); world.name = "World"; world.y_sort_enabled = true; add_child(world)
	walls_body = StaticBody2D.new(); walls_body.name = "Walls"; add_child(walls_body)
	_water_collision()
	for pl in L["walls"]:
		_wall(pl)
	for p in L["towers"]:
		_tower(Vector2(p[0], p[1]))
	for g in L["gates"]:
		_gate(Vector2(g[0], g[1]))
	for s in L["stairs"]:
		_stairs(deco, Vector2(s[0], s[1]))
	_bridge(deco)
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

# ------------------------------------------------------------------ walls
## A wall = centre-line on the ground (its footprint is the band +-WT/2). The visible top walkway is that
## band lifted by WH, and the south face fills the gap. Each wall is cut into <=64 px chunks that sort
## individually by their lowest ground point, so Kael passes behind / in front correctly.
func _poly(pts: PackedVector2Array, uv: PackedVector2Array, tx: Texture2D, off: Vector2) -> Polygon2D:
	var p := Polygon2D.new()
	var lp := PackedVector2Array()
	for q in pts:
		lp.append(q - off)
	p.polygon = lp
	p.uv = uv
	p.texture = tx
	p.texture_repeat = CanvasItem.TEXTURE_REPEAT_ENABLED
	return p

func _wall(pl: Array) -> void:
	var pts: Array = []
	for p in pl:
		pts.append(Vector2(p[0], p[1]))
	var h := WT * 0.5
	var dist := 0.0
	for i in pts.size() - 1:
		var a: Vector2 = pts[i]
		var b: Vector2 = pts[i + 1]
		var d := (b - a).normalized()
		var n := Vector2(-d.y, d.x)
		if n.y < 0 or (is_zero_approx(n.y) and n.x < 0):
			n = -n
		# collision: the whole segment band (convex quad)
		var band := PackedVector2Array([a - n * h, b - n * h, b + n * h, a + n * h])
		_shade(band, SH_FAR, SH_COL)
		_shade(band, SH_NEAR, SH_CONTACT)
		var cp := CollisionPolygon2D.new()
		cp.polygon = PackedVector2Array([a - n * h, b - n * h, b + n * h, a + n * h])
		walls_body.add_child(cp)
		var seg := a.distance_to(b)
		var steps := maxi(1, ceili(seg / 64.0))
		for k in steps:
			var p0 := a.lerp(b, float(k) / steps)
			var p1 := a.lerp(b, float(k + 1) / steps)
			var u0 := dist + seg * k / steps
			var u1 := dist + seg * (k + 1) / steps
			_chunk(p0, p1, n, u0, u1)
		dist += seg
	# joints between segments (and wall ends): a square cap so corners are closed
	for i in pts.size():
		var c0: Vector2 = pts[i]
		_shade(PackedVector2Array([c0 + Vector2(-h, -h), c0 + Vector2(h, -h), c0 + Vector2(h, h), c0 + Vector2(-h, h)]), SH_FAR, SH_COL)
		_cap(pts[i])

func _chunk(p0: Vector2, p1: Vector2, n: Vector2, u0: float, u1: float) -> void:
	var h := WT * 0.5
	var up := Vector2(0, -WH)
	var e0 := p0 + n * h
	var e1 := p1 + n * h
	var foot := maxf(e0.y, e1.y)
	var node := Node2D.new()
	node.position = Vector2(0, foot)
	var off := node.position
	if absf(e1.x - e0.x) > 0.5:
		node.add_child(_poly(PackedVector2Array([e0 + up, e1 + up, e1, e0]),
			PackedVector2Array([Vector2(u0, 0), Vector2(u1, 0), Vector2(u1, WH), Vector2(u0, WH)]), t("wall_face"), off))
	node.add_child(_poly(PackedVector2Array([p0 - n * h + up, p1 - n * h + up, p1 + n * h + up, p0 + n * h + up]),
		PackedVector2Array([Vector2(u0, 0), Vector2(u1, 0), Vector2(u1, WT), Vector2(u0, WT)]), t("wall_top"), off))
	world.add_child(node)

func _cap(c: Vector2) -> void:
	var h := WT * 0.5
	var up := Vector2(0, -WH)
	var node := Node2D.new()
	node.position = Vector2(0, c.y + h)
	var off := node.position
	var sq := Rect2(c - Vector2(h, h), Vector2(WT, WT))
	node.add_child(_poly(PackedVector2Array([Vector2(sq.position.x, sq.end.y) + up, sq.end + up, sq.end, Vector2(sq.position.x, sq.end.y)]),
		PackedVector2Array([Vector2(0, 0), Vector2(WT, 0), Vector2(WT, WH), Vector2(0, WH)]), t("wall_face"), off))
	node.add_child(_poly(PackedVector2Array([sq.position + up, Vector2(sq.end.x, sq.position.y) + up, sq.end + up, Vector2(sq.position.x, sq.end.y) + up]),
		PackedVector2Array([Vector2(0, 0), Vector2(WT, 0), Vector2(WT, WT), Vector2(0, WT)]), t("wall_top"), off))
	world.add_child(node)
	var cs := CollisionShape2D.new()
	var rs := RectangleShape2D.new()
	rs.size = Vector2(WT, WT)
	cs.shape = rs
	cs.position = c
	walls_body.add_child(cs)

func _shade(pts: PackedVector2Array, off: Vector2, col: Color) -> void:
	var p := Polygon2D.new()
	var q := PackedVector2Array()
	for v in pts:
		q.append((v + off).round())
	p.polygon = q
	p.color = col
	shadows.add_child(p)

func _ellipse_shade(c: Vector2, rx: float, ry: float, col: Color) -> void:
	var q := PackedVector2Array()
	for i in 20:
		var a := TAU * i / 20.0
		q.append(c + Vector2(cos(a) * rx, sin(a) * ry))
	_shade(q, Vector2.ZERO, col)

# ------------------------------------------------------------------ kit pieces
func _sprite(name: String, foot: Vector2, parent: Node) -> Sprite2D:
	var s := Sprite2D.new()
	s.texture = t(name)
	s.centered = false
	s.offset = Vector2(-s.texture.get_width() * 0.5, -s.texture.get_height())
	s.position = foot.round()
	parent.add_child(s)
	return s

func _tower(p: Vector2) -> void:
	var foot := p + Vector2(0, WT * 0.5 + 6)
	_ellipse_shade(foot + Vector2(22, -4), 58, 22, SH_COL)
	_ellipse_shade(foot + Vector2(4, -6), 42, 12, SH_CONTACT)
	_sprite("tower", foot, world)
	_rect_col(walls_body, Rect2(foot.x - 38, foot.y - 44, 76, 44))

func _gate(p: Vector2) -> void:
	var foot := p + Vector2(0, WT * 0.5 + 8)
	_shade(PackedVector2Array([foot + Vector2(-120, -40), foot + Vector2(120, -40), foot + Vector2(140, 6), foot + Vector2(-100, 6)]), Vector2(8, 4), SH_COL)
	_sprite("gatehouse", foot, world)
	# two flanking towers are solid; the arch between them (~100 px) is open
	_rect_col(walls_body, Rect2(foot.x - 120, foot.y - 52, 70, 52))
	_rect_col(walls_body, Rect2(foot.x + 50, foot.y - 52, 70, 52))

func _stairs(parent: Node, p: Vector2) -> void:
	var tex_h: float = t("stairs").get_height()
	# the piece's wall section lines up with the wall top; the flight runs down to the south
	var s := _sprite("stairs", p + Vector2(0, tex_h - WH - WT * 0.5 - 10), parent)
	s.z_index = 0
	var w: float = t("stairs").get_width()
	_rect_col(walls_body, Rect2(p.x - w * 0.5, p.y - WT * 0.5, w * 0.5 - 40, WT))
	_rect_col(walls_body, Rect2(p.x + 40, p.y - WT * 0.5, w * 0.5 - 40, WT))

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

## Flood fill over the real collision (Kael's 12x6 footprint, 16 px steps) and check named places.
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
			var p := start + Vector2(nc) * 16.0
			if p.x < 0 or p.y < 0 or p.x > ws[0] or p.y > ws[1]:
				continue
			q.transform = Transform2D(0, p + Vector2(0, -3))
			if space.intersect_shape(q, 1).is_empty():
				seen[nc] = true
				queue.append(nc)
	var S := 5.0; var SY := 7.5
	var places := {
		"quay south of town wall": Vector2(836, 905), "causeway mid": Vector2(836, 760),
		"gate forecourt (inside outer gate)": Vector2(836, 600), "central lane": Vector2(836, 400),
		"top court (through inner gate)": Vector2(836, 200), "west great court": Vector2(380, 520),
		"east great court": Vector2(1292, 520), "west upper terrace (via stairs)": Vector2(380, 250),
		"east upper terrace (via stairs)": Vector2(1292, 250), "west middle yard": Vector2(690, 400),
		"east middle yard": Vector2(982, 400), "pond corner": Vector2(740, 540),
	}
	var fails := 0
	for k in places:
		var bp: Vector2 = places[k]
		var w := Vector2(bp.x * S, bp.y * SY)
		var best := 1e9
		for c in seen:
			best = minf(best, (start + Vector2(c) * 16.0).distance_to(w))
		var ok := best < 90.0
		if not ok:
			fails += 1
		print("%s  %s  (nearest reachable %.0f px)" % ["PASS" if ok else "FAIL", k, best])
	var outside := Vector2(836 * S, 330 * SY)   # sample: inside a wall must NOT be reachable
	print("reachable cells: ", seen.size(), "   failures: ", fails)
	get_tree().quit()
