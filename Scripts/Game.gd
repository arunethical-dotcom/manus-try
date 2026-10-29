extends Node
## Autoload "Game": input map, scene transitions, story flags, HUD (title / toast / prompt) and the
## command-line capture + test hooks used for evidence screenshots and automated play-tests.
##   godot --path . -- --capture --scene=res://... --out=file.png [--spawn=name] [--pos=x,y] [--zoom=z]
##                      [--size=WxH] [--flags=a,b] [--noplayer] [--hidehud] [--collisions] [--frames=n]
## Engine scale: 1 world unit = 1 game pixel, camera zoom 1.0 at a 960x540 viewport (integer-scaled x2 to 1080p).
## The player is 64 px tall (scale anchor).

const START_SCENE := "res://Scenes/Exterior/Approach.tscn"

signal flags_changed

var flags: Dictionary = {}
var next_spawn: String = ""
var instant: bool = false
var args: Dictionary = {}
var transitioning: bool = false
var current_level: Node = null

var _layer: CanvasLayer
var _fade: ColorRect
var _toast: Label
var _prompt: Label
var _title: Label
var _toast_t: float = 0.0
var _title_t: float = 0.0

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_register_inputs()
	for a in OS.get_cmdline_user_args():
		var s := String(a).trim_prefix("--")
		if "=" in s:
			var kv := s.split("=", true, 1)
			args[kv[0]] = kv[1]
		else:
			args[s] = true
	instant = args.has("instant") or args.has("capture")
	if args.has("collisions"):
		get_tree().debug_collisions_hint = true
	_build_hud()
	if args.has("capture"):
		_run_capture.call_deferred()
	if args.has("bot"):
		var bot := Node.new()
		bot.name = "RouteBot"
		bot.set_script(load("res://Scripts/RouteBot.gd"))
		add_child(bot)

func _register_inputs() -> void:
	var map := {
		"move_left": [KEY_A, KEY_LEFT], "move_right": [KEY_D, KEY_RIGHT],
		"move_up": [KEY_W, KEY_UP], "move_down": [KEY_S, KEY_DOWN],
		"interact": [KEY_E, KEY_ENTER, KEY_SPACE], "restart": [KEY_R],
	}
	for action in map:
		if not InputMap.has_action(action):
			InputMap.add_action(action, 0.2)
		for k in map[action]:
			var ev := InputEventKey.new()
			ev.physical_keycode = k
			InputMap.action_add_event(action, ev)

func _unhandled_input(e: InputEvent) -> void:
	if e.is_action_pressed("restart") and not transitioning and not args.has("capture"):
		flags.clear()
		go(START_SCENE, "")

func _build_hud() -> void:
	_layer = CanvasLayer.new()
	_layer.layer = 100
	add_child(_layer)
	_fade = ColorRect.new()
	_fade.color = Color(0, 0, 0, 0)
	_fade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_fade.set_anchors_preset(Control.PRESET_FULL_RECT)
	_layer.add_child(_fade)
	_title = _make_label(Vector2(12, 8), 16, HORIZONTAL_ALIGNMENT_LEFT)
	_toast = _make_label(Vector2(0, 40), 14, HORIZONTAL_ALIGNMENT_CENTER)
	_prompt = _make_label(Vector2(0, 488), 14, HORIZONTAL_ALIGNMENT_CENTER)

func _make_label(pos: Vector2, size: int, align: int) -> Label:
	var l := Label.new()
	l.position = pos
	l.size = Vector2(960 - (pos.x * 2 if align == HORIZONTAL_ALIGNMENT_LEFT else 0), 24)
	l.horizontal_alignment = align as HorizontalAlignment
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", Color(1, 0.96, 0.82))
	l.add_theme_color_override("font_outline_color", Color(0.05, 0.04, 0.08))
	l.add_theme_constant_override("outline_size", 4)
	l.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_layer.add_child(l)
	return l

func _process(dt: float) -> void:
	if _toast_t > 0.0:
		_toast_t -= dt
		if _toast_t <= 0.0:
			_toast.text = ""
	if _title_t > 0.0:
		_title_t -= dt
		_title.modulate.a = clampf(_title_t, 0.0, 1.0)
		if _title_t <= 0.0:
			_title.text = ""

func toast(text: String, secs: float = 3.5) -> void:
	_toast.text = text
	_toast_t = secs

func set_prompt(text: String) -> void:
	_prompt.text = text

func show_title(text: String) -> void:
	_title.text = text
	_title.modulate.a = 1.0
	_title_t = 3.0

# ---- flags ----------------------------------------------------------------
func has_flag(n: String) -> bool:
	return flags.has(n)

func set_flag(n: String) -> void:
	if not flags.has(n):
		flags[n] = true
		flags_changed.emit()

# ---- transitions ----------------------------------------------------------
func consume_spawn(default_spawn: String) -> String:
	var s := next_spawn if next_spawn != "" else default_spawn
	next_spawn = ""
	return s

func go(path: String, spawn: String) -> void:
	if transitioning:
		return
	transitioning = true
	if not instant:
		var t := create_tween()
		t.tween_property(_fade, "color:a", 1.0, 0.2)
		await t.finished
	next_spawn = spawn
	_prompt.text = ""
	get_tree().change_scene_to_file(path)
	await get_tree().process_frame
	await get_tree().process_frame
	if not instant:
		var t2 := create_tween()
		t2.tween_property(_fade, "color:a", 0.0, 0.2)
		await t2.finished
	transitioning = false

# ---- capture hook (evidence screenshots) ----------------------------------
func _run_capture() -> void:
	await get_tree().process_frame
	var size_s: String = str(args.get("size", ""))
	if size_s != "":
		var wh := size_s.split("x")
		get_window().content_scale_mode = Window.CONTENT_SCALE_MODE_DISABLED
		get_window().size = Vector2i(int(wh[0]), int(wh[1]))
		await get_tree().process_frame
	if args.has("flags"):
		for f in str(args["flags"]).split(","):
			flags[f] = true
	next_spawn = str(args.get("spawn", ""))
	get_tree().change_scene_to_file(str(args.get("scene", START_SCENE)))
	for i in 3:
		await get_tree().process_frame
	var lvl := get_tree().current_scene
	var player = lvl.get("player")
	if args.has("noplayer") and player:
		player.visible = false
	if args.has("hidehud"):
		_layer.visible = false
	if args.has("pplace") and player:
		var q := str(args["pplace"]).split(",")
		player.global_position = Vector2(float(q[0]), float(q[1]))
	if args.has("collisions") and lvl.has_node("Collision"):
		lvl.get_node("Collision").z_index = 100   # debug shapes are otherwise drawn under the sprites
	var cam := Camera2D.new()
	lvl.add_child(cam)
	cam.limit_left = -100000
	cam.limit_right = 100000
	cam.limit_top = -100000
	cam.limit_bottom = 100000
	if args.has("pos"):
		var p := str(args["pos"]).split(",")
		cam.global_position = Vector2(float(p[0]), float(p[1]))
	elif player:
		cam.global_position = player.global_position + Vector2(0, -32)
	var z := float(str(args.get("zoom", "1")))
	cam.zoom = Vector2(z, z)
	cam.make_current()
	if player and player.has_node("Cam"):
		player.get_node("Cam").enabled = false
	for i in int(str(args.get("frames", "10"))):
		await get_tree().physics_frame
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	img.save_png(str(args.get("out", "/tmp/capture.png")))
	print("CAPTURED ", args.get("out", "/tmp/capture.png"), " size=", img.get_size())
	get_tree().quit()
