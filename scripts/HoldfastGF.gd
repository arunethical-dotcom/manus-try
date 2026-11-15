extends Node2D
## Holdfast ground floor (tools/build_holdfast_gf.py from the user's plan) with the keep's interior feel:
##   every room is dark until Kael walks in; the room he is in is fully lit, rooms he has seen stay dimly remembered,
##   unseen rooms stay black (shaders/keep_fog.gdshader, region map data/holdfast_gf_regions.png).
##   Night tint, a small light round Kael, flickering wall torches (lit only in the room in view), vignette,
##   room name shown on entering, fades in and out.
## E at the outer end of the drawbridge (east) returns to the courtyard.
## Command line (after --): --capture --out=f.png [--pos=x,y] [--zoom=z] [--frames=n] [--hideui] [--visited=all]
var D: Dictionary
var args := {}
var player: CharacterBody2D
var hint: Label
var room_lbl: Label
var toast: Label
var toast_t := 0.0
var fade_rect: ColorRect
var reg: Image
var alpha := PackedFloat32Array()
var aimg: Image
var atex: ImageTexture
var visited := {}
var cur_reg := -1
var names: Array
var torches: Array = []
var light_tex: Texture2D

func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		var kv := String(a).trim_prefix("--").split("=", true, 1)
		args[kv[0]] = kv[1] if kv.size() > 1 else "1"
	var map := {"move_up": [KEY_W, KEY_UP], "move_down": [KEY_S, KEY_DOWN], "move_left": [KEY_A, KEY_LEFT],
		"move_right": [KEY_D, KEY_RIGHT], "run": [KEY_SHIFT], "interact": [KEY_E], "attack": [KEY_SPACE]}
	for act in map:
		if not InputMap.has_action(act):
			InputMap.add_action(act)
			for k in map[act]:
				var e := InputEventKey.new(); e.physical_keycode = k; InputMap.action_add_event(act, e)
	D = JSON.parse_string(FileAccess.get_file_as_string("res://data/holdfast_gf.json"))
	names = D["region_names"]
	var gr := Gradient.new(); gr.set_color(0, Color(1, 1, 1, 1)); gr.set_color(1, Color(1, 1, 1, 0))
	var gt := GradientTexture2D.new(); gt.gradient = gr; gt.fill = GradientTexture2D.FILL_RADIAL
	gt.fill_from = Vector2(0.5, 0.5); gt.fill_to = Vector2(1.0, 0.5); gt.width = 256; gt.height = 256
	light_tex = gt
	var night := CanvasModulate.new(); night.color = Color(0.40, 0.42, 0.58); add_child(night)
	var sp := Sprite2D.new(); sp.texture = load(String(D["image"])); sp.centered = false
	add_child(sp)
	var body := StaticBody2D.new(); add_child(body)
	for r in D["solid"]:
		var cs := CollisionShape2D.new(); var rs := RectangleShape2D.new()
		rs.size = Vector2(r[2], r[3]); cs.shape = rs; cs.position = Vector2(r[0] + r[2] * 0.5, r[1] + r[3] * 0.5)
		body.add_child(cs)
	_torches()
	_fog()
	_player()
	_hud()
	if args.has("visited"):
		for i in range(1, names.size()): visited[i] = true
	if args.has("capture"):
		_capture()

func _v(a: Array) -> Vector2: return Vector2(float(a[0]), float(a[1]))

# ------------------------------------------------------------------ room reveal
func _fog() -> void:
	reg = Image.new()
	reg.load_png_from_buffer(FileAccess.get_file_as_bytes(String(D["regions"])))
	var fs := Sprite2D.new(); fs.centered = false; fs.z_index = 10; fs.light_mask = 0
	fs.texture = ImageTexture.create_from_image(reg); fs.scale = Vector2(16, 16)
	fs.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	aimg = Image.create(256, 1, false, Image.FORMAT_RGBA8); aimg.fill(Color(1, 0, 0, 1))
	atex = ImageTexture.create_from_image(aimg)
	var m := ShaderMaterial.new(); m.shader = load("res://shaders/keep_fog.gdshader")
	m.set_shader_parameter("alpha_tex", atex); m.set_shader_parameter("reg_tex", fs.texture)
	m.set_shader_parameter("cells", Vector2(reg.get_width(), reg.get_height()))
	fs.material = m
	add_child(fs)
	alpha.resize(256); alpha.fill(1.0)

func _update_fog(dt: float) -> void:
	var c := Vector2i(int(player.position.x / 16.0), int(player.position.y / 16.0 - 0.2))
	if c.x >= 0 and c.y >= 0 and c.x < reg.get_width() and c.y < reg.get_height():
		var id := int(round(reg.get_pixel(c.x, c.y).r * 255.0))
		if id > 0 and id != cur_reg:
			if not visited.has(id) or cur_reg == -1:
				_toast(String(names[id]))
			cur_reg = id
			visited[id] = true
			room_lbl.text = "The Holdfast  -  ground floor  -  " + String(names[id])
	var changed := false
	for i in range(1, names.size()):
		var target := 1.0
		if i == cur_reg: target = 0.0
		elif visited.has(i): target = 0.8
		if alpha[i] != target:
			alpha[i] = move_toward(alpha[i], target, (100.0 if args.has("capture") else 4.0) * dt)
			aimg.set_pixel(i, 0, Color(alpha[i], 0, 0, 1)); changed = true
	if changed: atex.update(aimg)
	var fr := int(Time.get_ticks_msec() / 120)
	for tc in torches:
		var on: bool = alpha[int(tc["reg"])] < 0.5
		var lt: PointLight2D = tc["light"]
		lt.enabled = on
		if on:
			lt.energy = 0.85 + 0.12 * sin(Time.get_ticks_msec() * 0.011 + tc["x"]) + 0.05 * sin(Time.get_ticks_msec() * 0.031 + tc["x"] * 0.3)
			(tc["flame"] as Sprite2D).frame = (fr + int(tc["x"])) % 4

func _torches() -> void:
	for tc in D["torches"]:
		var tn := Node2D.new(); tn.position = Vector2(tc[0], tc[1]); tn.z_index = 2
		var fl := Sprite2D.new(); fl.texture = load("res://art/game/keep/fx_fire_m.png"); fl.hframes = 4
		fl.scale = Vector2(0.5, 0.5); fl.centered = false
		fl.offset = Vector2(-fl.texture.get_width() / 8.0, -fl.texture.get_height())
		tn.add_child(fl)
		var painted: bool = tc.size() > 3 and int(tc[3]) == 1     # flame already painted in the floor art
		if painted:                                   # our animated flame sits over the painted one
			tn.position += Vector2(0, 16)
			fl.scale = Vector2(0.95, 0.95)
			fl.modulate = Color(1, 1, 1, 0.92)
			fl.offset = Vector2(-fl.texture.get_width() / 8.0, -fl.texture.get_height())
		var lt := PointLight2D.new(); lt.texture = light_tex; lt.texture_scale = 1.3; lt.energy = 0.95
		lt.color = Color(1.0, 0.68, 0.36); lt.position = Vector2(0, -6 if painted else 10); lt.enabled = false
		tn.add_child(lt)
		add_child(tn)
		torches.append({"flame": fl, "light": lt, "reg": int(tc[2]), "x": float(tc[0])})

# ------------------------------------------------------------------ Kael
func _player() -> void:
	player = CharacterBody2D.new(); player.name = "Kael"; player.set_script(load("res://scripts/Player.gd"))
	var sh := Sprite2D.new(); sh.name = "Shadow"; sh.texture = load("res://art/game/kael3/shadow.png"); sh.position = Vector2(0, -5)
	player.add_child(sh)
	var ks := Sprite2D.new(); ks.name = "Sprite"; ks.texture = load("res://art/game/kael3/idle.png"); ks.hframes = 12; ks.vframes = 4
	ks.centered = false; ks.offset = Vector2(-32, -46); player.add_child(ks)
	var cs := CollisionShape2D.new(); var r2 := RectangleShape2D.new(); r2.size = Vector2(12, 6); cs.shape = r2; cs.position = Vector2(0, -3)
	player.add_child(cs)
	var lt := PointLight2D.new(); lt.texture = light_tex; lt.texture_scale = 0.75; lt.energy = 0.5
	lt.color = Color(1.0, 0.85, 0.65); lt.position = Vector2(0, -12); player.add_child(lt)
	var cam := Camera2D.new(); cam.position = Vector2(0, -14); cam.zoom = Vector2(2, 2)
	var sz: Array = D["size"]
	cam.limit_left = 0; cam.limit_top = 0; cam.limit_right = int(sz[0]); cam.limit_bottom = int(sz[1])
	cam.position_smoothing_enabled = true; cam.position_smoothing_speed = 7.0
	if args.has("zoom"):
		var z := float(args["zoom"]); cam.zoom = Vector2(z, z)
	player.add_child(cam)
	player.position = _v(D["spawn"]) + Vector2(-24, 0)
	if args.has("pos"):
		var q := String(args["pos"]).split(","); player.position = Vector2(float(q[0]), float(q[1]))
	player.z_index = 11
	add_child(player)

# ------------------------------------------------------------------ HUD
func _style(alpha_: float) -> StyleBoxFlat:
	var sb := StyleBoxFlat.new(); sb.bg_color = Color(0.07, 0.05, 0.05, alpha_)
	sb.border_color = Color(0.74, 0.57, 0.31, 0.95); sb.set_border_width_all(1); sb.set_corner_radius_all(3)
	sb.content_margin_left = 9; sb.content_margin_right = 9; sb.content_margin_top = 5; sb.content_margin_bottom = 6
	return sb

func _label(p: Node, s: int, col: Color) -> Label:
	var l := Label.new(); l.add_theme_font_size_override("font_size", s); l.add_theme_color_override("font_color", col)
	l.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.9)); l.add_theme_constant_override("outline_size", 4)
	p.add_child(l); return l

func _hud() -> void:
	var vg := CanvasLayer.new(); vg.layer = 8; add_child(vg)
	var vr := ColorRect.new(); vr.set_anchors_preset(Control.PRESET_FULL_RECT); vr.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var vm := ShaderMaterial.new(); vm.shader = load("res://shaders/vignette.gdshader"); vr.material = vm
	vg.add_child(vr)
	var cl := CanvasLayer.new(); cl.layer = 10; add_child(cl)
	var pc := PanelContainer.new(); pc.position = Vector2(10, 10); pc.add_theme_stylebox_override("panel", _style(0.78))
	cl.add_child(pc)
	room_lbl = _label(pc, 11, Color(0.95, 0.92, 0.85)); room_lbl.text = "The Holdfast  -  ground floor"
	toast = _label(cl, 17, Color(1.0, 0.86, 0.55)); toast.position = Vector2(0, 40); toast.size = Vector2(960, 26)
	toast.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER; toast.modulate.a = 0
	var hb := PanelContainer.new(); hb.add_theme_stylebox_override("panel", _style(0.85)); hb.name = "HintBox"
	cl.add_child(hb)
	hint = _label(hb, 12, Color(0.95, 0.92, 0.85))
	var fl := CanvasLayer.new(); fl.layer = 20; add_child(fl)
	fade_rect = ColorRect.new(); fade_rect.color = Color(0, 0, 0, 1); fade_rect.set_anchors_preset(Control.PRESET_FULL_RECT)
	fade_rect.mouse_filter = Control.MOUSE_FILTER_IGNORE; fl.add_child(fade_rect)
	if args.has("capture"): fade_rect.color.a = 0
	else: create_tween().tween_property(fade_rect, "color:a", 0.0, 0.8)
	if args.has("hideui"): cl.visible = false

func _toast(s: String) -> void:
	if s == "": return
	toast.text = s; toast_t = 2.2

func _process(dt: float) -> void:
	_update_fog(dt)
	if toast_t > 0:
		toast_t -= dt
		toast.modulate.a = clampf(minf(2.2 - toast_t, toast_t) * 3.0, 0.0, 1.0)
	var t := ""
	if player.position.distance_to(_v(D["exit"])) < 60:
		t = "[E]  leave over the drawbridge"
	else:
		for s in D["stairs"]:
			if player.position.distance_to(_v(s["pos"])) < 40: t = String(s["name"]) + "  (not built yet)"
	hint.text = t
	var hb: PanelContainer = hint.get_parent()
	hb.visible = t != ""
	hb.reset_size(); hb.position = Vector2(480 - hb.size.x * 0.5, 498)

func _unhandled_input(e: InputEvent) -> void:
	if e.is_action_pressed("interact") and player.position.distance_to(_v(D["exit"])) < 60:
		Engine.set_meta("from_holdfast", true)
		var tw := create_tween()
		tw.tween_property(fade_rect, "color:a", 1.0, 0.4)
		tw.tween_callback(func(): get_tree().change_scene_to_file("res://scenes/Main.tscn"))

func _capture() -> void:
	for i in int(args.get("frames", "30")): await get_tree().process_frame
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png(String(args.get("out", "/tmp/gf.png")))
	print("CAPTURED ", args.get("out")); get_tree().quit()
