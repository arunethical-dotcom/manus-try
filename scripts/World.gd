extends Node2D
## Builds the palace wall ring from data/layout.json (written by tools/build_walls.py):
##   Ground  - TileMapLayer, 16x16 tiles (floor slab inside the ring, earth outside)      z 0
##   Shadows - baked wall shadows, 512 px chunks                                           z 1
##   Walls   - wall art, 512 px chunks                                                     z 2
##   Kael                                                                                  z 3
##   Front   - the same wall chunks again, drawn only where the wall stands in front of Kael z 4
##             (per-pixel ground line texture + shaders/wall_front.gdshader)
##   Walls body - collision = wall footprint on the ground (separate from the art)
##   UI      - minimap (top-right, M to expand)
## Command line (after --):  --capture --out=f.png [--pos=x,y] [--frames=n] [--bigmap] [--zoom=z] [--hideui] [--hideplayer]
##                           --test   (collision flood-fill from the spawn)

const TILE := 16
var L: Dictionary
var player: CharacterBody2D
var walls_body: StaticBody2D
var front: Array = []
var back: Array = []
## CrossCode-style see-through: the whole object (tower / wall stretch / gatehouse) Kael stands behind fades
var objmap: Image
var fade_img: Image
var fade_tex: ImageTexture
var fade := PackedFloat32Array()
const FADE_SPEED := 5.0
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
	if not args.has("capture") and not args.has("test"):
		_fit_window()
	L = JSON.parse_string(FileAccess.get_file_as_string("res://data/layout.json"))
	_ground()
	_walls()
	_player()
	_grade()
	var mm = load("res://scripts/Minimap.gd").new()
	mm.setup(self)
	add_child(mm)
	if args.has("capture"):
		_capture(mm)
	elif args.has("test"):
		_test()

func _process(dt: float) -> void:
	if player == null:
		return
	var foot := player.global_position
	var pr := Rect2(foot - Vector2(12, 34), Vector2(24, 38))
	var ch: float = L["chunk"]
	for f in front:
		var sp: Sprite2D = f
		var on: bool = Rect2(sp.position, Vector2(ch, ch)).intersects(pr)
		sp.visible = on
		if on:
			(sp.material as ShaderMaterial).set_shader_parameter("player_y", foot.y - 1.0)
	_update_fade(foot, dt)

## which objects cover Kael: sample his body; a wall pixel there whose ground line is south of his feet hides him
func _update_fade(foot: Vector2, dt: float) -> void:
	var hide := {}
	for oy in [-2, -8, -14, -20, -26]:
		for ox in [-6, 0, 6]:
			var p := (foot + Vector2(ox, oy)) * 0.5
			var x := int(p.x); var y := int(p.y)
			if x < 0 or y < 0 or x >= objmap.get_width() or y >= objmap.get_height():
				continue
			var c := objmap.get_pixel(x, y)
			var id := int(round(c.b * 255.0))
			if id == 0:
				continue
			var g := (int(round(c.r * 255.0)) * 256 + int(round(c.g * 255.0))) * 2
			if g > foot.y + 1:
				hide[id] = int(hide.get(id, 0)) + 1
	# when Kael is behind any wall, ALL walls fade together (rest of the scene stays solid)
	var behind := false
	for k in hide:
		if int(hide[k]) >= 4:
			behind = true
	var target := 1.0 if behind else 0.0
	var v := fade[0]
	var changed := false
	if v != target:
		v = move_toward(v, target, (1000.0 if args.has("capture") else FADE_SPEED) * dt)
		for id in range(256):
			fade[id] = v
		fade_img.fill(Color(v, 0, 0, 1))
		changed = true
	if changed:
		fade_tex.update(fade_img)

## Fill the screen: the 960x540 view is scaled up (fractional, aspect kept) to the window, which is sized to the
## usable screen area and maximized. (Running inside the editor's Game tab, the view scales to the tab instead.)
func _fit_window() -> void:
	var win := get_window()
	if win.mode == Window.MODE_FULLSCREEN or win.mode == Window.MODE_EXCLUSIVE_FULLSCREEN:
		return
	var scr := DisplayServer.window_get_current_screen()
	var r := DisplayServer.screen_get_usable_rect(scr)
	if r.size.x > 0 and r.size.y > 0:
		win.size = r.size
		win.position = r.position
	win.mode = Window.MODE_MAXIMIZED

var grade_rect: ColorRect

## colour grading over the world (below the minimap); G toggles it to compare
func _grade() -> void:
	var cl := CanvasLayer.new()
	cl.layer = 5
	add_child(cl)
	grade_rect = ColorRect.new()
	grade_rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	grade_rect.set_anchors_preset(Control.PRESET_FULL_RECT)
	var m := ShaderMaterial.new()
	m.shader = load("res://shaders/grade.gdshader")
	grade_rect.material = m
	cl.add_child(grade_rect)
	if args.has("nograde"):
		grade_rect.visible = false

func _unhandled_input(e: InputEvent) -> void:
	if e is InputEventKey and e.pressed and not e.echo and e.physical_keycode == KEY_G:
		grade_rect.visible = not grade_rect.visible
	if e is InputEventKey and e.pressed and not e.echo and e.physical_keycode == KEY_F11:
		var win := get_window()
		win.mode = Window.MODE_MAXIMIZED if win.mode == Window.MODE_FULLSCREEN else Window.MODE_FULLSCREEN

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
	# stage 2: painted ground (tools/build_ground.py) in 1024 px chunks
	var g := Node2D.new()
	g.name = "Ground"
	add_child(g)
	for c in L["ground_chunks"]:
		var sp := Sprite2D.new()
		sp.texture = load("res://art/game/ground/g_%d_%d.webp" % [int(c[0]), int(c[1])])
		sp.centered = false
		sp.position = Vector2(c[0], c[1])
		g.add_child(sp)

func _rect_col(body: Node, r: Rect2) -> void:
	var cs := CollisionShape2D.new()
	var rs := RectangleShape2D.new()
	rs.size = r.size
	cs.shape = rs
	cs.position = r.position + r.size * 0.5
	body.add_child(cs)

# ------------------------------------------------------------------ walls
func _walls() -> void:
	var sh_layer := Node2D.new(); sh_layer.name = "Shadows"; sh_layer.z_index = 1; add_child(sh_layer)
	var w_layer := Node2D.new(); w_layer.name = "Walls"; w_layer.z_index = 2; add_child(w_layer)
	var f_layer := Node2D.new(); f_layer.name = "Front"; f_layer.z_index = 4; add_child(f_layer)
	objmap = Image.new()
	objmap.load_png_from_buffer(FileAccess.get_file_as_bytes("res://data/objmap.bin"))   # PNG data, kept un-imported
	fade.resize(256)
	fade_img = Image.create(256, 1, false, Image.FORMAT_RGBA8)
	fade_img.fill(Color(0, 0, 0, 1))
	fade_tex = ImageTexture.create_from_image(fade_img)
	var shader: Shader = load("res://shaders/wall_front.gdshader")
	var back_shader: Shader = load("res://shaders/wall_back.gdshader")
	for c in L["chunks"]:
		var pos := Vector2(c["x"], c["y"])
		var id := "%d_%d" % [int(c["x"]), int(c["y"])]
		if c.has("shadow"):
			sh_layer.add_child(_chunk_sprite(t("walls/shadow_" + id), pos))
		if c.has("wall"):
			var wt := t("walls/wall_" + id)
			var bs := _chunk_sprite(wt, pos)
			var bm := ShaderMaterial.new()
			bm.shader = back_shader
			bm.set_shader_parameter("depth_tex", t("walls/depth_" + id))
			bm.set_shader_parameter("fade_tex", fade_tex)
			bs.material = bm
			w_layer.add_child(bs)
			back.append(bs)
			var fs := _chunk_sprite(wt, pos)
			var m := ShaderMaterial.new()
			m.shader = shader
			m.set_shader_parameter("depth_tex", t("walls/depth_" + id))
			m.set_shader_parameter("fade_tex", fade_tex)
			fs.material = m
			fs.visible = false
			f_layer.add_child(fs)
			front.append(fs)
	walls_body = StaticBody2D.new(); walls_body.name = "WallsBody"; add_child(walls_body)
	for r in L["wall_rects"]:
		_rect_col(walls_body, Rect2(r[0], r[1], r[2], r[3]))
	var ws: Array = L["world"]
	for e in [Rect2(-64, -64, ws[0] + 128, 64), Rect2(-64, ws[1], ws[0] + 128, 64), Rect2(-64, 0, 64, ws[1]), Rect2(ws[0], 0, 64, ws[1])]:
		_rect_col(walls_body, e)

func _chunk_sprite(tx: Texture2D, pos: Vector2) -> Sprite2D:
	var s := Sprite2D.new()
	s.texture = tx
	s.centered = false
	s.position = pos
	return s

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
	player.z_index = 3
	add_child(player)

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
	var gs: Dictionary = L["gates"]
	var sg: Array = gs["south"]
	var ng: Array = gs["north"]
	var ins: Array = L["inside"]
	var places := {
		"spawn (outside south gate)": Vector2(L["spawn"][0], L["spawn"][1]),
		"south gate passage": Vector2(sg[0], sg[1] - 30),
		"inside the ring": Vector2(ins[0], ins[1]),
		"north gate passage": Vector2(ng[0], ng[1] - 20),
		"outside, north of the north gate": Vector2(ng[0], ng[1] - 400),
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
	# (that the walls seal the interior except at the two gates is checked by tools/build_walls.py)
	print("reachable cells: ", seen.size(), "   failures: ", fails)
	get_tree().quit()
