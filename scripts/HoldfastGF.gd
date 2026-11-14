extends Node2D
## Holdfast ground floor (tools/build_holdfast_gf.py from the user's plan): one map image + solid rects, Kael, room names.
## E at the outer end of the drawbridge (east) returns to the courtyard.
## Command line (after --): --capture --out=f.png [--pos=x,y] [--zoom=z] [--frames=n] [--hideui]
var D: Dictionary
var args := {}
var player: CharacterBody2D
var room_lbl: Label
var hint: Label

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
	var sp := Sprite2D.new(); sp.texture = load(String(D["image"])); sp.centered = false
	add_child(sp)
	var body := StaticBody2D.new(); add_child(body)
	for r in D["solid"]:
		var cs := CollisionShape2D.new(); var rs := RectangleShape2D.new()
		rs.size = Vector2(r[2], r[3]); cs.shape = rs; cs.position = Vector2(r[0] + r[2] * 0.5, r[1] + r[3] * 0.5)
		body.add_child(cs)
	player = CharacterBody2D.new(); player.name = "Kael"; player.set_script(load("res://scripts/Player.gd"))
	var sh := Sprite2D.new(); sh.name = "Shadow"; sh.texture = load("res://art/game/kael3/shadow.png"); sh.position = Vector2(0, -5)
	player.add_child(sh)
	var ks := Sprite2D.new(); ks.name = "Sprite"; ks.texture = load("res://art/game/kael3/idle.png"); ks.hframes = 12; ks.vframes = 4
	ks.centered = false; ks.offset = Vector2(-32, -46); player.add_child(ks)
	var cs2 := CollisionShape2D.new(); var r2 := RectangleShape2D.new(); r2.size = Vector2(12, 6); cs2.shape = r2; cs2.position = Vector2(0, -3)
	player.add_child(cs2)
	var cam := Camera2D.new(); cam.position = Vector2(0, -14)
	var sz: Array = D["size"]
	cam.limit_left = 0; cam.limit_top = 0; cam.limit_right = int(sz[0]); cam.limit_bottom = int(sz[1])
	cam.position_smoothing_enabled = true
	if args.has("zoom"):
		var z := float(args["zoom"]); cam.zoom = Vector2(z, z)
	player.add_child(cam)
	player.position = _v(D["spawn"]) + Vector2(-24, 0)
	if args.has("pos"):
		var q := String(args["pos"]).split(","); player.position = Vector2(float(q[0]), float(q[1]))
	add_child(player)
	var cl := CanvasLayer.new(); add_child(cl)
	room_lbl = _label(cl, Vector2(12, 10), 16)
	hint = _label(cl, Vector2(0, 500), 14); hint.size = Vector2(960, 24); hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	if args.has("capture"):
		if args.has("hideui"): cl.visible = false
		for i in int(args.get("frames", "20")): await get_tree().process_frame
		await RenderingServer.frame_post_draw
		get_viewport().get_texture().get_image().save_png(String(args.get("out", "/tmp/gf.png")))
		print("CAPTURED ", args.get("out")); get_tree().quit()

func _v(a: Array) -> Vector2: return Vector2(float(a[0]), float(a[1]))

func _label(p: Node, pos: Vector2, s: int) -> Label:
	var l := Label.new(); l.position = pos; l.add_theme_font_size_override("font_size", s)
	l.add_theme_color_override("font_outline_color", Color.BLACK); l.add_theme_constant_override("outline_size", 5)
	p.add_child(l); return l

func _process(_dt: float) -> void:
	var best := ""; var bd := 1e9
	for r in D["rooms"]:
		var d := player.position.distance_to(_v(r["pos"]))
		if d < bd: bd = d; best = String(r["name"])
	room_lbl.text = "The Holdfast - ground floor   |   " + (best if bd < 260 else "")
	var near_exit := player.position.distance_to(_v(D["exit"])) < 60
	var st := ""
	for s in D["stairs"]:
		if player.position.distance_to(_v(s["pos"])) < 40: st = String(s["name"])
	hint.text = "E: leave over the drawbridge" if near_exit else (st + "  (not built yet)" if st != "" else "")

func _unhandled_input(e: InputEvent) -> void:
	if e.is_action_pressed("interact") and player.position.distance_to(_v(D["exit"])) < 60:
		Engine.set_meta("from_holdfast", true)
		get_tree().change_scene_to_file("res://scenes/Main.tscn")
