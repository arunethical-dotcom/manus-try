extends Node2D
## RED KEEP PROTOTYPE - interior of the keep, built from data/keep_proto.json (tools/build_keep_proto.py, plan v2).
##   3 levels (L-1 underground, L0 ground, L1 upper); one shown at a time, each with its own collision layer.
##   Night infiltration: you arrive through the river drain (way in A).  E at the oil & pitch store lights the oil;
##   the fire then spreads F0 -> F5 on a timer.  F2: alarm bell, Gold Cloaks run to the kitchens.
##   F3: the Kingsguard lower the drawbridge and open the King's door to fetch water -> the Holdfast is open.
## Command line (after --): --capture --out=f.png [--level=L0] [--pos=x,y] [--ignite] [--t=seconds] [--zoom=z] [--frames=n]

const SPEED := 2.5               # prototype runs the design timings 2.5x faster (F5 at 72 s instead of 180 s)
const LAYER := {"L0": 1, "L1": 2, "L-1": 4}
const TINT := {"L0": Color(0.42, 0.45, 0.62), "L1": Color(0.45, 0.47, 0.62), "L-1": Color(0.32, 0.31, 0.38)}
const LV_NAME := {"L0": "Ground floor", "L1": "Upper floor", "L-1": "Underground"}

var D: Dictionary
var args := {}
var levels := {}                 # level -> Node2D
var cur := ""
var player: CharacterBody2D
var cam: Camera2D
var night: CanvasModulate
var gates := {}                  # id -> {body, visuals[]}
var hud_obj: Label
var hud_banner: Label
var hud_hint: Label
var hud_stage: Label
var hp_bar: ColorRect
var hp := 100.0
var lit := false
var fire_t := 0.0
var stage_i := 0
var flames: Array = []           # {node, level, t0, big}
var tex := {}
var light_tex: Texture2D
var banner_t := 0.0
var interact: Dictionary = {}
var won := false
var dead := false
var smoke_t := 0.0

func t(p: String) -> Texture2D:
	if not tex.has(p):
		tex[p] = load(p)
	return tex[p]

func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		var s := String(a).trim_prefix("--")
		var kv := s.split("=", true, 1)
		args[kv[0]] = kv[1] if kv.size() > 1 else "1"
	_inputs()
	D = JSON.parse_string(FileAccess.get_file_as_string("res://data/keep_proto.json"))
	var g := Gradient.new()
	g.set_color(0, Color(1, 1, 1, 1)); g.set_color(1, Color(1, 1, 1, 0))
	var gt := GradientTexture2D.new()
	gt.gradient = g; gt.fill = GradientTexture2D.FILL_RADIAL; gt.fill_from = Vector2(0.5, 0.5); gt.fill_to = Vector2(1.0, 0.5)
	gt.width = 256; gt.height = 256
	light_tex = gt
	night = CanvasModulate.new()
	add_child(night)
	for lv in ["L-1", "L0", "L1"]:
		_build_level(lv)
	_gates()
	_guards()
	_player()
	_hud()
	var sp: Dictionary = D["spawn"]
	_goto(String(args.get("level", sp["level"])), _v(sp["pos"]) if not args.has("pos") else _parse_v(str(args["pos"])))
	_objective("Find the OIL & PITCH STORE (west, underground) and light it.")
	_banner("Night. You slipped in through the river drain.", 4.0)
	if args.has("ignite") or args.has("t"):
		_ignite()
		fire_t = float(args.get("t", "0"))
	if args.has("capture"):
		_capture()

func _v(a: Array) -> Vector2:
	return Vector2(float(a[0]), float(a[1]))

func _parse_v(s: String) -> Vector2:
	var q := s.split(",")
	return Vector2(float(q[0]), float(q[1]))

func _inputs() -> void:
	var map := {"move_up": [KEY_W, KEY_UP], "move_down": [KEY_S, KEY_DOWN], "move_left": [KEY_A, KEY_LEFT],
		"move_right": [KEY_D, KEY_RIGHT], "run": [KEY_SHIFT], "interact": [KEY_E]}
	for act in map:
		if not InputMap.has_action(act):
			InputMap.add_action(act)
			for k in map[act]:
				var e := InputEventKey.new(); e.physical_keycode = k
				InputMap.action_add_event(act, e)

# ------------------------------------------------------------------ levels
func _build_level(lv: String) -> void:
	var L: Dictionary = D["levels"][lv]
	var n := Node2D.new(); n.name = lv; n.visible = false
	add_child(n)
	var sp := Sprite2D.new(); sp.texture = t(L["image"]); sp.centered = false; sp.name = "Art"
	n.add_child(sp)
	var fx := Node2D.new(); fx.name = "FX"; fx.z_index = 2
	n.add_child(fx)
	var body := StaticBody2D.new(); body.name = "Solid"
	body.collision_layer = LAYER[lv]; body.collision_mask = 0
	n.add_child(body)
	for r in L["solid"]:
		var cs := CollisionShape2D.new(); var rs := RectangleShape2D.new()
		rs.size = Vector2(r[2], r[3]); cs.shape = rs; cs.position = Vector2(r[0] + r[2] * 0.5, r[1] + r[3] * 0.5)
		body.add_child(cs)
	levels[lv] = n

func _goto(lv: String, pos: Vector2) -> void:
	for k in levels:
		(levels[k] as Node2D).visible = (k == lv)
	cur = lv
	player.collision_mask = LAYER[lv]
	player.position = pos
	night.color = TINT[lv]
	cam.reset_smoothing()
	if hud_stage:
		_update_stage_label()

# ------------------------------------------------------------------ gates (closed at night; opened by the fire at F3)
func _gates() -> void:
	for id in D["dyn_gates"]:
		var gd: Dictionary = D["dyn_gates"][id]
		var lv := String(gd["level"])
		var r: Array = gd["rect"]
		var rect := Rect2(r[0], r[1], r[2], r[3])
		var body := StaticBody2D.new(); body.collision_layer = LAYER[lv]; body.collision_mask = 0
		var cs := CollisionShape2D.new(); var rs := RectangleShape2D.new()
		rs.size = rect.size; cs.shape = rs; cs.position = rect.get_center()
		body.add_child(cs)
		levels[lv].add_child(body)
		var vis: Array = []
		var host: Node2D = levels[lv].get_node("FX")
		match id:
			"bridge":
				var up := Sprite2D.new(); up.texture = t("res://art/game/keep/ov_bridge_up.png"); up.centered = false
				up.position = Vector2(rect.position.x, rect.end.y - up.texture.get_height())
				host.add_child(up); vis.append(up)
				var dn := Sprite2D.new(); dn.texture = t("res://art/game/keep/ov_bridge_down.png"); dn.centered = false
				dn.position = Vector2(rect.position.x, rect.end.y - dn.texture.get_height() + 6); dn.visible = false; dn.name = "down"
				host.add_child(dn); gd["down"] = dn
			"kings_door", "hold_gate", "main_outer", "main_inner":
				var sp := Sprite2D.new()
				sp.texture = t("res://art/game/keep/ov_door_locked.png" if id == "kings_door" else "res://art/game/keep/ov_portcullis.png")
				sp.centered = false
				var sc := rect.size.x / sp.texture.get_width()
				sp.scale = Vector2(sc, sc)
				sp.position = Vector2(rect.position.x, rect.end.y - sp.texture.get_height() * sc)
				host.add_child(sp); vis.append(sp)
			_:
				var cr := ColorRect.new(); cr.color = Color(0.15, 0.15, 0.17); cr.position = rect.position; cr.size = rect.size
				host.add_child(cr); vis.append(cr)
		gates[id] = {"body": body, "vis": vis, "data": gd}

func open_gate(id: String) -> void:
	if not gates.has(id):
		return
	var g: Dictionary = gates[id]
	(g["body"] as StaticBody2D).collision_layer = 0
	for v in g["vis"]:
		(v as CanvasItem).visible = false
	if g["data"].has("down"):
		(g["data"]["down"] as Sprite2D).visible = true

# ------------------------------------------------------------------ guards (visual posts + runners)
var posts: Array = []
func _guard_sprite(col: Color) -> Sprite2D:
	var s := Sprite2D.new(); s.texture = t("res://art/game/kael.png"); s.hframes = 4; s.vframes = 4
	s.centered = false; s.offset = Vector2(-8, -28); s.modulate = col; s.z_index = 3
	return s

func _guards() -> void:
	for lv in D["guards"]:
		for p in D["guards"][lv]:
			var s := _guard_sprite(Color(1.0, 0.55, 0.45))
			s.position = _v(p)
			levels[lv].add_child(s)
			posts.append(s)

func _runners(route_id: String, n: int, col: Color, end_spread: Rect2) -> void:
	var route: Array = D["routes"][route_id]
	for i in n:
		var s := _guard_sprite(col)
		s.position = _v(route[0]) + Vector2(randf_range(-10, 10), randf_range(-6, 6))
		levels["L0"].add_child(s)
		var tw := create_tween()
		tw.tween_interval(i * 0.6)
		var prev := s.position
		for k in range(1, route.size()):
			var q := _v(route[k]) + Vector2(randf_range(-8, 8), randf_range(-4, 4))
			var d := prev.distance_to(q)
			var dir := q - prev
			var row := 0
			if absf(dir.x) > absf(dir.y):
				row = 2 if dir.x > 0 else 1
			else:
				row = 0 if dir.y > 0 else 3
			tw.tween_callback(func(): s.frame = row * 4)
			tw.tween_property(s, "position", q, d / 150.0)
			prev = q
		var dest := Vector2(randf_range(end_spread.position.x, end_spread.end.x), randf_range(end_spread.position.y, end_spread.end.y))
		tw.tween_property(s, "position", dest, prev.distance_to(dest) / 150.0)
		tw.tween_callback(func(): s.frame = 3 * 4)    # face the fire (up), bucket line

# ------------------------------------------------------------------ Kael
func _player() -> void:
	player = CharacterBody2D.new(); player.name = "Kael"
	player.set_script(load("res://scripts/Player.gd"))
	var sh := Sprite2D.new(); sh.name = "Shadow"; sh.texture = t("res://art/game/kael_shadow.png"); sh.position = Vector2(1, -1)
	player.add_child(sh)
	var sp := Sprite2D.new(); sp.name = "Sprite"; sp.texture = t("res://art/game/kael.png"); sp.hframes = 4; sp.vframes = 4
	sp.centered = false; sp.offset = Vector2(-8, -28)
	player.add_child(sp)
	var cs := CollisionShape2D.new(); var rs := RectangleShape2D.new(); rs.size = Vector2(12, 6)
	cs.shape = rs; cs.position = Vector2(0, -3)
	player.add_child(cs)
	var lt := PointLight2D.new(); lt.texture = light_tex; lt.texture_scale = 1.1; lt.energy = 0.55; lt.color = Color(1.0, 0.9, 0.75)
	lt.position = Vector2(0, -12)
	player.add_child(lt)
	cam = Camera2D.new(); cam.position = Vector2(0, -14)
	var sz: Array = D["size"]
	cam.limit_left = 0; cam.limit_top = 0; cam.limit_right = int(sz[0]) * 16; cam.limit_bottom = int(sz[1]) * 16
	cam.position_smoothing_enabled = true; cam.position_smoothing_speed = 8.0
	if args.has("zoom"):
		var z := float(args["zoom"]); cam.zoom = Vector2(z, z)
	player.add_child(cam)
	player.z_index = 3; player.collision_layer = 0
	add_child(player)

# ------------------------------------------------------------------ HUD
func _label(sz: int, pos: Vector2, parent: Node) -> Label:
	var l := Label.new()
	l.add_theme_font_size_override("font_size", sz)
	l.add_theme_color_override("font_outline_color", Color.BLACK)
	l.add_theme_constant_override("outline_size", 5)
	l.position = pos
	parent.add_child(l)
	return l

func _hud() -> void:
	var cl := CanvasLayer.new(); cl.layer = 10; add_child(cl)
	hud_obj = _label(13, Vector2(10, 8), cl)
	hud_stage = _label(13, Vector2(10, 28), cl)
	hud_banner = _label(18, Vector2(0, 60), cl)
	hud_banner.size = Vector2(960, 30); hud_banner.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	hud_banner.add_theme_color_override("font_color", Color(1.0, 0.85, 0.5))
	hud_hint = _label(15, Vector2(0, 500), cl)
	hud_hint.size = Vector2(960, 24); hud_hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	var bg := ColorRect.new(); bg.color = Color(0, 0, 0, 0.6); bg.position = Vector2(838, 10); bg.size = Vector2(112, 12)
	cl.add_child(bg)
	hp_bar = ColorRect.new(); hp_bar.color = Color(0.85, 0.2, 0.15); hp_bar.position = Vector2(840, 12); hp_bar.size = Vector2(108, 8)
	cl.add_child(hp_bar)
	_update_stage_label()

func _objective(s: String) -> void:
	hud_obj.text = "Objective: " + s

func _banner(s: String, dur: float = 5.0) -> void:
	hud_banner.text = s
	banner_t = dur

func _update_stage_label() -> void:
	var s := "%s" % LV_NAME[cur] if cur != "" else ""
	if lit:
		var st: Array = _stages_sorted()
		var nm := String(st[max(0, stage_i - 1)]["id"]) if stage_i > 0 else "-"
		s += "    Fire: %s   (%d s since the oil was lit)" % [nm, int(fire_t)]
	hud_stage.text = s

# ------------------------------------------------------------------ fire
var _st_cache: Array = []
func _stages_sorted() -> Array:
	if _st_cache.is_empty():
		for lv in D["levels"]:
			for s in D["levels"][lv]["fire"]:
				var c: Dictionary = s.duplicate(); c["level"] = lv
				_st_cache.append(c)
		_st_cache.sort_custom(func(a, b): return float(a["t"]) < float(b["t"]))
	return _st_cache

func _ignite() -> void:
	if lit:
		return
	lit = true
	fire_t = 0.0
	_banner("The oil catches! Get out before the smoke gives you away.", 5.0)
	_objective("Get clear of the fire. Wait for the alarm, then head for the Holdfast.")

func _start_stage(st: Dictionary) -> void:
	var lv := String(st["level"])
	var org := _v(st["origin"])
	var pts: Array = st["points"].duplicate()
	pts.sort_custom(func(a, b): return org.distance_to(_v(a)) < org.distance_to(_v(b)))
	var host: Node2D = levels[lv].get_node("FX")
	var i := 0
	for p in pts:
		var pos := _v(p) + Vector2(randf_range(-4, 4), randf_range(-3, 3))
		var delay := org.distance_to(pos) / 90.0
		var f := {"level": lv, "pos": pos, "t0": fire_t + delay * SPEED, "node": null, "light": i % 5 == 0}
		flames.append(f)
		i += 1
	match String(st["id"]):
		"F2":
			_banner("ALARM! The bell rings - fire in the kitchens! The Gold Cloaks run to the fire.", 6.0)
			_runners("gold", 8, Color(1.0, 0.75, 0.3), Rect2(26 * 16, 73 * 16, 20 * 16, 9 * 16))
		"F3":
			_banner("The Kingsguard lower the DRAWBRIDGE and open the King's door to fetch water. The Holdfast is open!", 7.0)
			for id in ["bridge", "hold_gate", "lane_w", "lane_e", "kings_door"]:
				open_gate(id)
			_runners("kingsguard", 4, Color(1.6, 1.6, 1.7), Rect2(44 * 16, 60 * 16, 12 * 16, 6 * 16))
			for s in posts:                                    # the bridge posts leave with them
				var sp := s as Sprite2D
				if sp.get_parent() == levels["L0"] and sp.position.distance_to(Vector2(126 * 16, 40 * 16)) < 9 * 16:
					sp.visible = false
			_objective("Cross the drawbridge, go through the King's door and up the Holdfast grand stair to the King's door (upper floor).")
		"F4":
			_banner("The servants' dormitory above the kitchens is burning.", 4.0)
		"F5":
			_banner("The fire has reached the GREAT HALL.", 4.0)

func _spawn_flame(f: Dictionary) -> void:
	var host: Node2D = levels[f["level"]].get_node("FX")
	var n := Node2D.new(); n.position = f["pos"]
	var sc := Sprite2D.new(); sc.texture = t("res://art/game/keep/fx_scorch.png"); sc.hframes = 3; sc.frame = randi() % 3
	sc.modulate = Color(1, 1, 1, 0.8); sc.position = Vector2(0, -4)
	n.add_child(sc)
	var fs := Sprite2D.new(); fs.name = "F"; fs.texture = t("res://art/game/keep/fx_fire_m.png"); fs.hframes = 4
	fs.centered = false
	fs.offset = Vector2(-fs.texture.get_width() / 8.0, -fs.texture.get_height())
	n.add_child(fs)
	var ar := Area2D.new(); ar.collision_layer = 0; ar.collision_mask = 0; ar.monitorable = false
	var cs := CollisionShape2D.new(); var c := CircleShape2D.new(); c.radius = 9; cs.shape = c; cs.position = Vector2(0, -3)
	ar.add_child(cs); n.add_child(ar)
	if f["light"]:
		var lt := PointLight2D.new(); lt.texture = light_tex; lt.texture_scale = 1.4; lt.energy = 1.1
		lt.color = Color(1.0, 0.55, 0.2); lt.position = Vector2(0, -10); lt.name = "L"
		n.add_child(lt)
	host.add_child(n)
	f["node"] = n

func _grow(f: Dictionary) -> void:
	var fs: Sprite2D = (f["node"] as Node2D).get_node("F")
	fs.texture = t("res://art/game/keep/fx_fire_l.png")
	fs.offset = Vector2(-fs.texture.get_width() / 8.0, -fs.texture.get_height() + 4)
	f["big"] = true

func _process(dt: float) -> void:
	if banner_t > 0:
		banner_t -= dt
		if banner_t <= 0:
			hud_banner.text = ""
	if lit:
		fire_t += dt * SPEED
		var st: Array = _stages_sorted()
		while stage_i < st.size() and fire_t >= float(st[stage_i]["t"]):
			_start_stage(st[stage_i])
			stage_i += 1
		var frame := int(Time.get_ticks_msec() / 110)
		var near := false
		for f in flames:
			if f["node"] == null:
				if fire_t >= float(f["t0"]):
					_spawn_flame(f)
				continue
			var n: Node2D = f["node"]
			if not f.get("big", false) and fire_t > float(f["t0"]) + 14.0 and int(f["pos"].x) % 3 == 0:
				_grow(f)
			if f["level"] == cur:
				(n.get_node("F") as Sprite2D).frame = (frame + int(f["pos"].x)) % 4
				var lt := n.get_node_or_null("L") as PointLight2D
				if lt:
					lt.energy = 1.0 + 0.25 * sin(Time.get_ticks_msec() * 0.013 + f["pos"].x)
				if player.position.distance_to(f["pos"]) < 13.0:
					near = true
		if near and not dead and not won:
			hp -= 40.0 * dt
			player.modulate = Color(1, 0.5, 0.4)
			if hp <= 0:
				_die()
		else:
			player.modulate = Color.WHITE
		smoke_t -= dt
		if smoke_t <= 0:
			smoke_t = 0.25
			_smoke()
		_update_stage_label()
	hp_bar.size.x = 108.0 * clampf(hp, 0, 100) / 100.0
	_check_interact()
	if not won and lit and cur == String(D["goal"]["level"]) and player.position.distance_to(_v(D["goal"]["pos"])) < 40:
		won = true
		_banner("You reached the King's door while the keep burns. END OF PROTOTYPE", 30.0)
		_objective("Done.")

func _smoke() -> void:
	var live: Array = []
	for f in flames:
		if f["node"] != null and f["level"] == cur:
			live.append(f)
	if live.is_empty():
		return
	var f: Dictionary = live[randi() % live.size()]
	var s := Sprite2D.new(); s.texture = t("res://art/game/keep/fx_smoke.png"); s.hframes = 5; s.frame = randi() % 5
	s.position = f["pos"] + Vector2(randf_range(-6, 6), -20); s.modulate = Color(0.55, 0.55, 0.6, 0.0); s.z_index = 4
	(levels[cur].get_node("FX") as Node2D).add_child(s)
	var tw := create_tween().set_parallel(true)
	tw.tween_property(s, "position", s.position + Vector2(randf_range(-20, 20), -70), 3.0)
	tw.tween_property(s, "modulate:a", 0.75, 0.6)
	tw.tween_property(s, "scale", Vector2(1.8, 1.8), 3.0)
	tw.chain().tween_property(s, "modulate:a", 0.0, 0.8)
	tw.chain().tween_callback(s.queue_free)

func _die() -> void:
	dead = true
	_banner("You were caught in the fire. Restarting...", 3.0)
	await get_tree().create_timer(2.5).timeout
	get_tree().reload_current_scene()

# ------------------------------------------------------------------ interaction
func _check_interact() -> void:
	interact = {}
	var p := player.position
	if not lit and cur == String(D["ignite"]["level"]) and p.distance_to(_v(D["ignite"]["pos"])) < 64:
		interact = {"kind": "ignite", "text": "E: light the oil & pitch"}
	for l in D["links"]:
		if interact.size() > 0:
			break
		for side in [["a", "pa", "b", "pb"], ["b", "pb", "a", "pa"]]:
			if String(l[side[0]]) == cur and p.distance_to(_v(l[side[1]])) < 24:
				var up := ["L-1", "L0", "L1"].find(String(l[side[2]])) > ["L-1", "L0", "L1"].find(cur)
				interact = {"kind": "link", "to": l[side[2]], "pos": _v(l[side[3]]),
					"text": "E: %s %s (%s)" % ["climb up" if up else "go down", String(l["label"]), LV_NAME[String(l[side[2]])]]}
				break
	if interact.is_empty():
		for e in D["exits"]:
			if String(e["level"]) == cur and p.distance_to(_v(e["pos"])) < 32:
				interact = {"kind": "exit", "text": "E: " + String(e["label"])}
	hud_hint.text = String(interact.get("text", ""))

func _unhandled_input(e: InputEvent) -> void:
	if not e.is_action_pressed("interact") or interact.is_empty() or dead:
		return
	match String(interact["kind"]):
		"ignite":
			_ignite()
		"link":
			_goto(String(interact["to"]), interact["pos"])
		"exit":
			Engine.set_meta("from_keep", true)
			get_tree().change_scene_to_file("res://scenes/Main.tscn")

# ------------------------------------------------------------------ capture (previews)
func _capture() -> void:
	if args.has("hideui"):
		for c in get_children():
			if c is CanvasLayer:
				(c as CanvasLayer).visible = false
	for i in int(args.get("frames", "30")):
		await get_tree().process_frame
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	img.save_png(str(args.get("out", "/tmp/keep.png")))
	print("CAPTURED ", args.get("out"))
	get_tree().quit()
