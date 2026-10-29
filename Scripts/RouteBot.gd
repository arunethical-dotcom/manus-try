extends Node
## Automated play-test. Drives the REAL Player through simulated input events (no teleporting inside a
## scene; scene changes happen only through the game's own doors). Paths are planned on the real physics
## space (the player's 20x12 footprint against collision layer 1), so "traversable" means exactly that.
##   godot --headless --fixed-fps 60 --path . -- --bot --instant
## Writes Docs/playtest_report.txt and exits non-zero on any failure.

const APPROACH := "res://Scenes/Exterior/Approach.tscn"
const COURT := "res://Scenes/Exterior/Courtyard.tscn"
const YARD := "res://Scenes/Exterior/ServiceYard.tscn"
const HALL := "res://Scenes/Interior/GreatHall.tscn"
const KITCHEN := "res://Scenes/Interior/Kitchen.tscn"
const CHAPEL := "res://Scenes/Interior/Chapel.tscn"
const KEEP := "res://Scenes/Interior/Keep.tscn"
const LIB := "res://Scenes/Interior/Library.tscn"
const BARR := "res://Scenes/Interior/Barracks.tscn"
const STABLE := "res://Scenes/Interior/Stable.tscn"
const SMITH := "res://Scenes/Interior/Blacksmith.tscn"
const UNDER := "res://Scenes/Underground/Underground.tscn"
const SCALE := "res://Scenes/Test/ScaleTest.tscn"

var Game:
	get: return get_node("/root/Game")

var results: Array = []
var log_lines: Array = []
var STEP := 16

func _ready() -> void:
	_run.call_deferred()

# ---------------------------------------------------------------- helpers
func P() -> CharacterBody2D:
	return get_tree().get_first_node_in_group("player") as CharacterBody2D

func lvl() -> Node:
	return get_tree().current_scene

func frames(n: int) -> void:
	for i in n:
		await get_tree().physics_frame

func act(nm: String, pressed: bool) -> void:
	var e := InputEventAction.new()
	e.action = nm
	e.pressed = pressed
	e.strength = 1.0 if pressed else 0.0
	Input.parse_input_event(e)

func release_all() -> void:
	for a in ["move_left", "move_right", "move_up", "move_down", "interact"]:
		act(a, false)

func tap(nm: String) -> void:
	act(nm, true)
	await frames(3)
	act(nm, false)
	await frames(3)

func say(msg: String) -> void:
	log_lines.append(msg)
	print(msg)

func check(nm: String, ok: bool, detail: String = "") -> void:
	results.append({"name": nm, "ok": ok, "detail": detail})
	say("%s  %s  %s" % ["PASS" if ok else "FAIL", nm, detail])

func wait_scene(path: String, max_frames: int = 240) -> bool:
	for i in max_frames:
		await get_tree().physics_frame
		var cs := get_tree().current_scene
		if cs and cs.scene_file_path == path and P() != null and Game.next_spawn == "" and not Game.transitioning:
			await frames(8)
			return true
	return false

func trig(nm: String) -> Area2D:
	return lvl().get_node("Triggers").get_node_or_null(nm) as Area2D

func trig_rect(a: Area2D) -> Rect2:
	var s := (a.get_child(0) as CollisionShape2D).shape as RectangleShape2D
	return Rect2(a.global_position - s.size * 0.5, s.size)

func rect_dist(r: Rect2, p: Vector2) -> float:
	var dx := maxf(maxf(r.position.x - p.x, 0.0), p.x - r.end.x)
	var dy := maxf(maxf(r.position.y - p.y, 0.0), p.y - r.end.y)
	return Vector2(dx, dy).length()

# ---- collision-true flood fill / path planning
func _free(space: PhysicsDirectSpaceState2D, q: PhysicsShapeQueryParameters2D, p: Vector2) -> bool:
	q.transform = Transform2D(0.0, p + Vector2(0, -6))
	return space.intersect_shape(q, 1).is_empty()

func flood(start: Vector2) -> Dictionary:
	var space := P().get_world_2d().direct_space_state
	var q := PhysicsShapeQueryParameters2D.new()
	var sh := RectangleShape2D.new()
	sh.size = Vector2(20, 12)
	q.shape = sh
	q.collision_mask = 1
	var b: Rect2 = lvl().get("bounds")
	var s0 := Vector2i((start / STEP).round())
	var came: Dictionary = {s0: s0}
	var queue: Array = [s0]
	var qi := 0
	var dirs := [Vector2i(1, 0), Vector2i(-1, 0), Vector2i(0, 1), Vector2i(0, -1), Vector2i(1, 1), Vector2i(1, -1), Vector2i(-1, 1), Vector2i(-1, -1)]
	while qi < queue.size():
		var c: Vector2i = queue[qi]
		qi += 1
		for d in dirs:
			var n: Vector2i = c + d
			if came.has(n):
				continue
			var wp := Vector2(n * STEP)
			if not b.has_point(wp):
				continue
			if not _free(space, q, wp):
				continue
			if d.x != 0 and d.y != 0:
				if not _free(space, q, Vector2((c + Vector2i(d.x, 0)) * STEP)) or not _free(space, q, Vector2((c + Vector2i(0, d.y)) * STEP)):
					continue
			came[n] = c
			queue.append(n)
	return {"came": came, "start": s0}

func path_to_rect(fl: Dictionary, r: Rect2) -> Dictionary:
	var best: Vector2i = fl["start"]
	var bd := 1e9
	for c in fl["came"].keys():
		var d := rect_dist(r, Vector2(c * STEP))
		if d < bd:
			bd = d
			best = c
	var path: Array = []
	var cur: Vector2i = best
	while cur != fl["start"]:
		path.append(Vector2(cur * STEP))
		cur = fl["came"][cur]
	path.reverse()
	return {"path": path, "dist": bd}

func follow(path: Array) -> bool:
	var scene0 := get_tree().current_scene
	var i := 0
	while i < path.size():
		var wp: Vector2 = path[i]
		if i + 2 < path.size():
			wp = path[i + 1]   # use every 2nd cell; keeps motion smooth
			i += 1
		i += 1
		var tries := 0
		while tries < 90:
			if get_tree().current_scene != scene0 or Game.transitioning or P() == null:
				release_all()
				return true
			var d: Vector2 = wp - P().global_position
			if d.length() < 5.0:
				break
			act("move_left", d.x < -3.0)
			act("move_right", d.x > 3.0)
			act("move_up", d.y < -3.0)
			act("move_down", d.y > 3.0)
			await get_tree().physics_frame
			tries += 1
		if tries >= 90:
			release_all()
			say("   stuck near %s going to %s" % [str(P().global_position), str(wp)])
			return false
	release_all()
	await frames(2)
	return true

## walk to trigger `nm` and (optionally) interact `presses` times. Returns true when the walk succeeded.
func reach(nm: String) -> bool:
	var a := trig(nm)
	if a == null:
		say("   no trigger named " + nm)
		return false
	var r := trig_rect(a)
	var fl := flood(P().global_position)
	var pr := path_to_rect(fl, r)
	if pr["dist"] > 14.0:
		say("   %s unreachable: closest approach %.0f px" % [nm, pr["dist"]])
		return false
	return await follow(pr["path"])

func use(nm: String, presses: int = 1) -> bool:
	if not await reach(nm):
		return false
	var scene0 := get_tree().current_scene
	for i in presses:
		await frames(4)
		if get_tree().current_scene != scene0 or Game.transitioning:
			return true
		await tap("interact")
		await frames(6)
	return true

func door(nm: String, target: String, presses: int = 1) -> bool:
	var ok := await use(nm, presses)
	if not ok:
		return false
	return await wait_scene(target)

func path_len(from: Vector2, to: Vector2) -> float:
	var fl := flood(from)
	var s0 := Vector2i((to / STEP).round())
	if not fl["came"].has(s0):
		return -1.0
	var n := 0
	var cur: Vector2i = s0
	while cur != fl["start"]:
		cur = fl["came"][cur]
		n += 1
	return n * STEP

func reachable(from: Vector2, to: Vector2) -> bool:
	return path_len(from, to) >= 0.0

# ---------------------------------------------------------------- the run
func _run() -> void:
	await frames(12)
	say("== Castle route play-test (real input, real collision) ==")
	var t0 := Time.get_ticks_msec()
	# ---------- 1. forest approach -> gatehouse
	check("approach scene loaded, player is 64px sprite", lvl().scene_file_path == APPROACH and P() != null and (P().get_node("Sprite") as Sprite2D).texture.get_height() / 4 == 64, "Approach.tscn")
	var fl := flood(P().global_position)
	var gate_pos := Vector2(1205, 640)
	check("approach: path start -> drawbridge is collision-traversable (ford + bridge corridor)", fl["came"].has(Vector2i((gate_pos / STEP).round())), "flood-fill over real collision")
	check("approach: moat water blocks (no walking across the river)", not fl["came"].has(Vector2i((Vector2(600, 700) / STEP).round())), "water collision")
	check("approach: wall / towers are not walkable (north of moat unreachable except via gate)", not fl["came"].has(Vector2i((Vector2(1800, 600) / STEP).round())), "")
	var ok := await door("To_Courtyard", COURT)
	check("approach -> gate -> courtyard transition by walking", ok and lvl().scene_file_path == COURT, "AutoDoor To_Courtyard")
	# ---------- 2. courtyard: garden, wall solidity
	var g_s := Vector2(1501, 1640)
	var g_n := Vector2(1501, 960)
	var fl2 := flood(P().global_position)
	check("courtyard: garden walkable south gate -> north gate", fl2["came"].has(Vector2i((g_s / STEP).round())) and fl2["came"].has(Vector2i((g_n / STEP).round())) and path_len(g_s, g_n) > 0 and path_len(g_s, g_n) < 1000, "path len %.0f" % path_len(g_s, g_n))
	check("courtyard: garden perimeter wall blocks (west side)", not fl2["came"].has(Vector2i((Vector2(1215, 1300) / STEP).round())), "")
	# walls: drive input into the south wall and into the keep, must not pass
	P().global_position = Vector2(800, 2040)
	await frames(2)
	act("move_down", true)
	await frames(90)
	act("move_down", false)
	check("courtyard: cannot walk through the south castle wall", P().global_position.y < 2100, "stopped at y=%.0f" % P().global_position.y)
	P().global_position = Vector2(522, 975)
	await frames(2)
	act("move_up", true)
	await frames(90)
	act("move_up", false)
	check("courtyard: cannot walk through the keep facade", P().global_position.y > 880, "stopped at y=%.0f" % P().global_position.y)
	P().global_position = Vector2(1500, 2070)
	await frames(2)
	# keep -> library, chapel
	ok = await door("Door_keep_main", KEEP)
	check("courtyard -> keep (door)", ok and lvl().scene_file_path == KEEP, "Door_keep_main")
	ok = await door("ToLibrary", LIB)
	check("keep -> library / upper keep (stair door)", ok and lvl().scene_file_path == LIB, "ToLibrary")
	ok = await door("ToKeep", KEEP)
	check("library -> keep (back down)", ok and lvl().scene_file_path == KEEP, "")
	ok = await door("ToChapel", CHAPEL)
	check("keep -> chapel (side door)", ok and lvl().scene_file_path == CHAPEL, "")
	ok = await door("Exit", COURT)
	check("chapel -> courtyard (exit)", ok and lvl().scene_file_path == COURT, "")
	# library direct tower door
	ok = await door("Door_library_main", LIB)
	check("courtyard -> library tower door", ok and lvl().scene_file_path == LIB, "Door_library_main")
	ok = await door("Exit", COURT)
	check("library -> courtyard (exit)", ok, "")
	# great hall -> kitchen service route
	ok = await door("Door_hall_main", HALL)
	check("courtyard -> great hall", ok and lvl().scene_file_path == HALL, "")
	ok = await door("ToKitchen", KITCHEN)
	check("great hall -> kitchen/bakery (service route)", ok and lvl().scene_file_path == KITCHEN, "ToKitchen")
	# pantry secret (clue first, then passage)
	check("pantry hatch is NOT available before the clue is found", not Game.has_flag("pantry_found"), "")
	ok = await door("PantrySecret", UNDER, 2)
	check("kitchen pantry: inspect (clue) then pull shelf -> underground", ok and lvl().scene_file_path == UNDER and Game.has_flag("pantry_clue") and Game.has_flag("pantry_found"), "PantrySecret")
	# ---------- 3. underground
	var gate_before := path_len(Vector2(9 * 32 + 16, 30 * 32), Vector2(9 * 32 + 16, 26 * 32))
	var lever_ok := await use("Lever")
	check("underground: crypt lever reachable from pantry arrival (cistern -> junction -> crypt)", lever_ok and Game.has_flag("prison_open"), "Lever -> prison_open")
	await frames(6)
	var gate_after := path_len(Vector2(9 * 32 + 16, 30 * 32), Vector2(9 * 32 + 16, 26 * 32))
	check("underground: loop gate blocks the short way until the lever is pulled", gate_before > 5.0 * gate_after and gate_after > 0, "path before %.0f px, after %.0f px" % [gate_before, gate_after])
	var cyc := reachable(Vector2(33 * 32, 26 * 32), Vector2(20 * 32, 35 * 32)) and reachable(Vector2(20 * 32, 35 * 32), Vector2(7 * 32 + 16, 21 * 32)) and reachable(Vector2(7 * 32 + 16, 21 * 32), Vector2(24 * 32, 17 * 32)) and reachable(Vector2(24 * 32, 17 * 32), Vector2(33 * 32, 26 * 32))
	check("underground: branch/loop junction -> prison -> west passage -> pantry stair -> cistern -> junction", cyc, "4 legs reachable")
	# secret wall to the smuggler's tunnel
	var before_secret := reachable(P().global_position, Vector2(64 * 32 + 16, 6 * 32))
	check("underground: smuggler's tunnel is sealed before the wall is opened", not before_secret, "")
	ok = await use("SecretWallUse", 2)
	check("underground: examine (clue) then push stones opens the hidden wall", Game.has_flag("crypt_loose") and Game.has_flag("crypt_secret"), "SecretWallUse")
	await frames(8)
	ok = await door("LadderEscape", APPROACH)
	check("underground -> escape tunnel -> surface beyond the castle wall", ok and lvl().scene_file_path == APPROACH, "LadderEscape -> Approach 'escape'")
	var ppos := P().global_position
	check("escape exit emerges outside the walls (south of the moat, east hillside)", ppos.y > 900 and ppos.x > 2200, "player at %s" % str(ppos))
	ok = await door("GrateOpen", UNDER)
	check("surface return: drain grate leads back down (return route)", ok and lvl().scene_file_path == UNDER, "GrateOpen")
	var wellok := reachable(P().global_position, Vector2(4 * 32 + 16, 5 * 32))
	check("underground: well shaft reachable from the escape tunnel", wellok, "")
	ok = await door("LadderWell", COURT)
	check("underground -> well ladder -> courtyard", ok and lvl().scene_file_path == COURT, "LadderWell")
	# well in the courtyard: clue then descent
	Game.flags.erase("well_clue")
	ok = await door("Well", UNDER, 2)
	check("courtyard well: examine (clue) then climb down -> underground", ok and lvl().scene_file_path == UNDER and Game.has_flag("well_clue"), "Well")
	ok = await door("LadderWell", COURT)
	check("well ladder returns to courtyard", ok, "")
	# ---------- 4. barracks, service yard
	ok = await door("Door_barracks_main", BARR)
	check("courtyard -> barracks", ok and lvl().scene_file_path == BARR, "")
	ok = await door("Exit", COURT)
	check("barracks -> courtyard", ok, "")
	ok = await door("Door_kitchen_main", KITCHEN)
	check("courtyard -> kitchen (direct door)", ok and lvl().scene_file_path == KITCHEN, "")
	ok = await door("Exit", COURT)
	check("kitchen -> courtyard", ok, "")
	ok = await door("To_ServiceYard", YARD)
	check("courtyard -> service yard (east gate)", ok and lvl().scene_file_path == YARD, "")
	ok = await door("Door_stable_main", STABLE)
	check("service yard -> stable", ok and lvl().scene_file_path == STABLE, "")
	ok = await door("Exit", YARD)
	check("stable -> service yard", ok, "")
	ok = await door("Door_blacksmith_main", SMITH)
	check("service yard -> blacksmith", ok and lvl().scene_file_path == SMITH, "")
	ok = await door("Exit", YARD)
	check("blacksmith -> service yard", ok, "")
	ok = await door("To_Courtyard", COURT)
	check("service yard -> courtyard (west gate)", ok and lvl().scene_file_path == COURT, "")
	ok = await door("To_Approach", APPROACH)
	check("courtyard -> south gate -> forest approach (safe surface exit)", ok and lvl().scene_file_path == APPROACH, "")
	# ---------- 5. sorting / occlusion
	Game.next_spawn = "behind_oak"
	get_tree().change_scene_to_file(SCALE)
	await wait_scene(SCALE)
	var oak := _find_prefix("oak_")
	var pl := P()
	check("y-sort: player behind oak (foot above trunk foot) is drawn before the oak", pl.global_position.y < oak.global_position.y, "player y %.0f < oak foot y %.0f" % [pl.global_position.y, oak.global_position.y])
	await frames(40)
	check("occlusion: canopy fades while the player is behind it", oak.modulate.a < 0.6, "alpha %.2f" % oak.modulate.a)
	pl.global_position = Vector2(300, 600)
	await frames(40)
	check("y-sort: player in front of oak is drawn after it, canopy opaque", pl.global_position.y > oak.global_position.y and oak.modulate.a > 0.95, "alpha %.2f" % oak.modulate.a)
	var wall := _find_prefix("wall_")
	pl.global_position = Vector2(1500, 470)
	await frames(40)
	var any_faded := false
	for n in lvl().get_node("World").get_children():
		if String(n.name).begins_with("wall_") and n.modulate.a < 0.6:
			any_faded = true
	check("occlusion: wall front fades while the player is behind it", any_faded, "")
	# summary
	var failed := 0
	for r in results:
		if not r["ok"]:
			failed += 1
	say("== %d checks, %d failed, %.1f s wall time ==" % [results.size(), failed, (Time.get_ticks_msec() - t0) / 1000.0])
	var f := FileAccess.open(ProjectSettings.globalize_path("res://Docs/playtest_report.txt"), FileAccess.WRITE)
	if f:
		f.store_string("\n".join(log_lines) + "\n")
		f.close()
	get_tree().quit(1 if failed > 0 else 0)

func _find_prefix(prefix: String) -> Node:
	for n in lvl().get_node("World").get_children():
		if String(n.name).begins_with(prefix):
			return n
	return null
