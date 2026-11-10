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
var fog := {}                    # level -> {sprite, reg, alpha, aimg, atex, visited, n}
var torches: Array = []          # {node, light, flame, level, reg}
var cur_reg := 0
var fade_rect: ColorRect
var toast: Label
var toast_t := 0.0
var hint_box: PanelContainer

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
	# room reveal fog
	var reg := Image.new()
	reg.load_png_from_buffer(FileAccess.get_file_as_bytes(String(L["regions"])))
	var fs := Sprite2D.new(); fs.name = "Fog"; fs.centered = false; fs.z_index = 10; fs.light_mask = 0
	fs.texture = ImageTexture.create_from_image(reg); fs.scale = Vector2(16, 16)
	fs.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	var aimg := Image.create(256, 1, false, Image.FORMAT_RGBA8); aimg.fill(Color(1, 0, 0, 1))
	var atex := ImageTexture.create_from_image(aimg)
	var m := ShaderMaterial.new(); m.shader = load("res://shaders/keep_fog.gdshader")
	m.set_shader_parameter("alpha_tex", atex); m.set_shader_parameter("reg_tex", fs.texture); m.set_shader_parameter("cells", Vector2(reg.get_width(), reg.get_height()))
	fs.material = m
	n.add_child(fs)
	var al := PackedFloat32Array(); al.resize(256); al.fill(1.0)
	fog[lv] = {"sprite": fs, "reg": reg, "alpha": al, "aimg": aimg, "atex": atex, "visited": {}, "names": L["region_names"]}
	# wall torches: flame + flickering light, lit only while their room is in view
	for tc in L["torches"]:
		var tn := Node2D.new(); tn.position = Vector2(tc[0], tc[1])
		var fl := Sprite2D.new(); fl.texture = t("res://art/game/keep/fx_fire_m.png"); fl.hframes = 4
		fl.scale = Vector2(0.5, 0.5); fl.centered = false
		fl.offset = Vector2(-fl.texture.get_width() / 8.0, -fl.texture.get_height())
		tn.add_child(fl)
		var lt := PointLight2D.new(); lt.texture = light_tex; lt.texture_scale = 1.05; lt.energy = 0.95
		lt.color = Color(1.0, 0.68, 0.36); lt.position = Vector2(0, 6); lt.enabled = false
		tn.add_child(lt)
		fx.add_child(tn)
		torches.append({"flame": fl, "light": lt, "level": lv, "reg": int(tc[2]), "x": float(tc[0])})

func _go(lv: String, pos: Vector2) -> void:
	var tw := create_tween()
	tw.tween_property(fade_rect, "color:a", 1.0, 0.22)
	tw.tween_callback(func(): _goto(lv, pos))
	tw.tween_property(fade_rect, "color:a", 0.0, 0.35)

func _goto(lv: String, pos: Vector2) -> void:
	cur_reg = -1
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
	var lt := PointLight2D.new(); lt.texture = light_tex; lt.texture_scale = 0.7; lt.energy = 0.45; lt.color = Color(1.0, 0.85, 0.65)
	lt.position = Vector2(0, -12)
	player.add_child(lt)
	cam = Camera2D.new(); cam.position = Vector2(0, -14)
	var sz: Array = D["size"]
	cam.limit_left = 0; cam.limit_top = 0; cam.limit_right = int(sz[0]) * 16; cam.limit_bottom = int(sz[1]) * 16
	cam.position_smoothing_enabled = true; cam.position_smoothing_speed = 7.0
	cam.zoom = Vector2(2, 2)
	if args.has("zoom"):
		var z := float(args["zoom"]); cam.zoom = Vector2(z, z)
	player.add_child(cam)
	player.z_index = 11; player.collision_layer = 0
	add_child(player)

# ------------------------------------------------------------------ HUD
func _label(sz: int, pos: Vector2, parent: Node, col: Color = Color(0.95, 0.92, 0.85)) -> Label:
	var l := Label.new()
	l.add_theme_font_size_override("font_size", sz)
	l.add_theme_color_override("font_color", col)
	l.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.9))
	l.add_theme_constant_override("outline_size", 4)
	l.position = pos
	parent.add_child(l)
	return l

func _panel_style(alpha: float = 0.78) -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.07, 0.05, 0.05, alpha)
	sb.border_color = Color(0.74, 0.57, 0.31, 0.95)
	sb.set_border_width_all(1)
	sb.set_corner_radius_all(3)
	sb.content_margin_left = 9; sb.content_margin_right = 9; sb.content_margin_top = 5; sb.content_margin_bottom = 6
	return sb

func _hud() -> void:
	var vg := CanvasLayer.new(); vg.layer = 8; add_child(vg)
	var vr := ColorRect.new(); vr.set_anchors_preset(Control.PRESET_FULL_RECT); vr.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var vm := ShaderMaterial.new(); vm.shader = load("res://shaders/vignette.gdshader"); vr.material = vm
	vg.add_child(vr)
	var cl := CanvasLayer.new(); cl.layer = 10; add_child(cl)
	var pc := PanelContainer.new(); pc.position = Vector2(10, 10); pc.add_theme_stylebox_override("panel", _panel_style())
	cl.add_child(pc)
	var vb := VBoxContainer.new(); vb.add_theme_constant_override("separation", 1); pc.add_child(vb)
	hud_obj = _label(11, Vector2.ZERO, vb)
	hud_obj.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART; hud_obj.custom_minimum_size = Vector2(300, 0)
	hud_stage = _label(10, Vector2.ZERO, vb, Color(0.92, 0.66, 0.38))
	toast = _label(17, Vector2(0, 30), cl, Color(1.0, 0.86, 0.55))
	toast.size = Vector2(960, 26); toast.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER; toast.modulate.a = 0
	hud_banner = _label(14, Vector2(0, 92), cl, Color(1.0, 0.9, 0.7))
	hud_banner.size = Vector2(960, 24); hud_banner.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	hint_box = PanelContainer.new(); hint_box.add_theme_stylebox_override("panel", _panel_style(0.85))
	cl.add_child(hint_box)
	hud_hint = _label(12, Vector2.ZERO, hint_box)
	var hb := PanelContainer.new(); hb.position = Vector2(822, 12); hb.add_theme_stylebox_override("panel", _panel_style())
	cl.add_child(hb)
	var hbg := Control.new(); hbg.custom_minimum_size = Vector2(110, 7); hb.add_child(hbg)
	var back := ColorRect.new(); back.color = Color(0.25, 0.07, 0.06); back.size = Vector2(110, 7); hbg.add_child(back)
	hp_bar = ColorRect.new(); hp_bar.color = Color(0.86, 0.24, 0.16); hp_bar.size = Vector2(110, 7); hbg.add_child(hp_bar)
	var fl := CanvasLayer.new(); fl.layer = 20; add_child(fl)
	fade_rect = ColorRect.new(); fade_rect.color = Color(0, 0, 0, 1); fade_rect.set_anchors_preset(Control.PRESET_FULL_RECT)
	fade_rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	fl.add_child(fade_rect)
	create_tween().tween_property(fade_rect, "color:a", 0.0, 0.8)
	_update_stage_label()

func _toast(s: String) -> void:
	if s == "":
		return
	toast.text = s
	toast_t = 2.2

func _objective(s: String) -> void:
	hud_obj.text = "Objective: " + s

func _banner(s: String, dur: float = 5.0) -> void:
	hud_banner.text = s
	banner_t = dur

func _update_stage_label() -> void:
	var s := "%s" % LV_NAME[cur] if cur != "" else ""
	if cur != "" and cur_reg > 0:
		var nm := String(fog[cur]["names"][cur_reg])
		if nm != "":
			s += "  -  " + nm
	if lit:
		var st: Array = _stages_sorted()
		var nm := String(st[max(0, stage_i - 1)]["id"]) if stage_i > 0 else "-"
		s += "     Fire %s  |  %d s" % [nm, int(fire_t)]
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
		var f := {"level": lv, "pos": pos, "t0": fire_t + delay * SPEED, "node": null, "light": i % 8 == 0}
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
		var lt := PointLight2D.new(); lt.texture = light_tex; lt.texture_scale = 1.8; lt.energy = 0.5
		lt.color = Color(1.0, 0.5, 0.18); lt.position = Vector2(0, -10); lt.name = "L"
		n.add_child(lt)
	host.add_child(n)
	f["node"] = n

func _grow(f: Dictionary) -> void:
	var fs: Sprite2D = (f["node"] as Node2D).get_node("F")
	fs.texture = t("res://art/game/keep/fx_fire_l.png")
	fs.offset = Vector2(-fs.texture.get_width() / 8.0, -fs.texture.get_height() + 4)
	f["big"] = true

func _update_fog(dt: float) -> void:
	var F: Dictionary = fog[cur]
	var reg: Image = F["reg"]
	var c := Vector2i(int(player.position.x / 16.0), int(player.position.y / 16.0 - 0.2))
	if c.x >= 0 and c.y >= 0 and c.x < reg.get_width() and c.y < reg.get_height():
		var id := int(round(reg.get_pixel(c.x, c.y).r * 255.0))
		if id > 0 and id != cur_reg:
			if cur_reg != -1 or true:
				var nm := String(F["names"][id])
				if not F["visited"].has(id) or cur_reg == -1:
					_toast(nm)
			cur_reg = id
			F["visited"][id] = true
			_update_stage_label()
	var al: PackedFloat32Array = F["alpha"]
	var aimg: Image = F["aimg"]
	var changed := false
	var n: int = (F["names"] as Array).size()
	for i in range(1, n):
		var target := 1.0
		if i == cur_reg:
			target = 0.0
		elif F["visited"].has(i):
			target = 0.8
		if al[i] != target:
			al[i] = move_toward(al[i], target, (100.0 if args.has("capture") else 4.0) * dt)
			aimg.set_pixel(i, 0, Color(al[i], 0, 0, 1))
			changed = true
	F["alpha"] = al
	if changed:
		(F["atex"] as ImageTexture).update(aimg)
	var fr := int(Time.get_ticks_msec() / 120)
	for tc in torches:
		if tc["level"] != cur:
			continue
		var on: bool = al[int(tc["reg"])] < 0.5
		var lt: PointLight2D = tc["light"]
		lt.enabled = on
		if on:
			lt.energy = 0.85 + 0.12 * sin(Time.get_ticks_msec() * 0.011 + tc["x"]) + 0.05 * sin(Time.get_ticks_msec() * 0.031 + tc["x"] * 0.3)
			(tc["flame"] as Sprite2D).frame = (fr + int(tc["x"])) % 4

func _process(dt: float) -> void:
	_update_fog(dt)
	if toast_t > 0:
		toast_t -= dt
		toast.modulate.a = clampf(minf(2.2 - toast_t, toast_t) * 3.0, 0.0, 1.0)
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
					lt.energy = 0.5 + 0.12 * sin(Time.get_ticks_msec() * 0.013 + f["pos"].x)
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
	s.position = f["pos"] + Vector2(randf_range(-6, 6), -20); s.modulate = Color(0.55, 0.55, 0.6, 0.0); s.z_index = 2
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
	var ht := String(interact.get("text", ""))
	hud_hint.text = ht.replace("E: ", "[E]  ")
	hint_box.visible = ht != ""
	hint_box.reset_size()
	hint_box.position = Vector2(480 - hint_box.size.x * 0.5, 498)

func _unhandled_input(e: InputEvent) -> void:
	if not e.is_action_pressed("interact") or interact.is_empty() or dead:
		return
	match String(interact["kind"]):
		"ignite":
			_ignite()
		"link":
			_go(String(interact["to"]), interact["pos"])
		"exit":
			Engine.set_meta("from_keep", true)
			var tw := create_tween()
			tw.tween_property(fade_rect, "color:a", 1.0, 0.4)
			tw.tween_callback(func(): get_tree().change_scene_to_file("res://scenes/Main.tscn"))

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
