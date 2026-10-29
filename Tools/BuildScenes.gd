extends SceneTree
## Scene baker. Builds every .tscn from the processed sprite specs + level definitions in this file.
##   godot --headless --path . --script res://Tools/BuildScenes.gd
## Collision is hand-authored polygons (Art/sprite_specs.json "footprint"), never derived from sprite rectangles.

const CELL := 32
var specs: Dictionary = {}
var T: Dictionary = {}
var gid_counter := 0
var rng := RandomNumberGenerator.new()

const SC_APPROACH := "res://Scenes/Exterior/Approach.tscn"
const SC_COURT := "res://Scenes/Exterior/Courtyard.tscn"
const SC_YARD := "res://Scenes/Exterior/ServiceYard.tscn"
const SC_HALL := "res://Scenes/Interior/GreatHall.tscn"
const SC_KITCHEN := "res://Scenes/Interior/Kitchen.tscn"
const SC_CHAPEL := "res://Scenes/Interior/Chapel.tscn"
const SC_KEEP := "res://Scenes/Interior/Keep.tscn"
const SC_LIB := "res://Scenes/Interior/Library.tscn"
const SC_BARR := "res://Scenes/Interior/Barracks.tscn"
const SC_STABLE := "res://Scenes/Interior/Stable.tscn"
const SC_SMITH := "res://Scenes/Interior/Blacksmith.tscn"
const SC_UNDER := "res://Scenes/Underground/Underground.tscn"

func _init() -> void:
	specs = JSON.parse_string(FileAccess.get_file_as_string("res://Art/sprite_specs.json"))
	DirAccess.make_dir_recursive_absolute("res://Scenes/Exterior")
	DirAccess.make_dir_recursive_absolute("res://Scenes/Interior")
	DirAccess.make_dir_recursive_absolute("res://Scenes/Underground")
	DirAccess.make_dir_recursive_absolute("res://Scenes/Test")
	build_player()
	build_approach()
	build_courtyard()
	build_yard()
	build_interiors()
	build_underground()
	build_tests()
	print("BUILD DONE")
	quit()

# ------------------------------------------------------------------ basics
func tx(n: String) -> Texture2D:
	if not T.has(n):
		var p := "res://Art/Game/%s.png" % n
		if not FileAccess.file_exists(p):
			p = "res://Art/Generated/%s.png" % n
		T[n] = load(p)
	return T[n]

func save_scene(root: Node, path: String) -> void:
	_set_owners(root, root)
	var ps := PackedScene.new()
	var e := ps.pack(root)
	if e != OK:
		push_error("pack failed %s %d" % [path, e])
	var e2 := ResourceSaver.save(ps, path)
	if e2 != OK:
		push_error("save failed %s %d" % [path, e2])
	print("saved ", path)
	root.free()

func _set_owners(n: Node, o: Node) -> void:
	for c in n.get_children():
		c.owner = o
		_set_owners(c, o)

func make_level(title: String, bounds: Rect2, default_spawn: String, hint: bool = false) -> Node2D:
	var r := Node2D.new()
	r.name = "Level"
	r.set_script(load("res://Scripts/LevelBase.gd"))
	r.set("level_title", title)
	r.set("bounds", bounds)
	r.set("default_spawn", default_spawn)
	r.set("controls_hint", hint)
	for n in ["Ground", "Collision", "World", "Triggers", "Spawns"]:
		var c := Node2D.new()
		c.name = n
		r.add_child(c)
	r.get_node("World").y_sort_enabled = true
	return r

func spawn(level: Node, nm: String, p: Vector2, facing: String = "up") -> void:
	var m := Marker2D.new()
	m.name = nm
	m.position = p
	m.set_meta("facing", facing)
	level.get_node("Spawns").add_child(m)

func solid_poly(level: Node, pts: PackedVector2Array, nm: String = "Solid") -> void:
	var b := StaticBody2D.new()
	b.name = nm
	b.collision_layer = 1
	b.collision_mask = 0
	var c := CollisionPolygon2D.new()
	c.polygon = pts
	b.add_child(c)
	level.get_node("Collision").add_child(b)

func solid_rect(level: Node, r: Rect2, nm: String = "Solid") -> void:
	var b := StaticBody2D.new()
	b.name = nm
	b.collision_layer = 1
	b.collision_mask = 0
	var c := CollisionShape2D.new()
	var s := RectangleShape2D.new()
	s.size = r.size
	c.shape = s
	b.position = r.position + r.size * 0.5
	b.add_child(c)
	level.get_node("Collision").add_child(b)

func boundary(level: Node, b: Rect2) -> void:
	solid_rect(level, Rect2(b.position.x - 80, b.position.y - 80, b.size.x + 160, 80), "EdgeN")
	solid_rect(level, Rect2(b.position.x - 80, b.end.y, b.size.x + 160, 80), "EdgeS")
	solid_rect(level, Rect2(b.position.x - 80, b.position.y, 80, b.size.y), "EdgeW")
	solid_rect(level, Rect2(b.end.x, b.position.y, 80, b.size.y), "EdgeE")

func area_rect(level: Node, r: Rect2, script_path: String, props: Dictionary, nm: String) -> Area2D:
	var a := Area2D.new()
	a.name = nm
	a.set_script(load(script_path))
	for k in props:
		a.set(k, props[k])
	var c := CollisionShape2D.new()
	var s := RectangleShape2D.new()
	s.size = r.size
	c.shape = s
	a.position = r.position + r.size * 0.5
	a.add_child(c)
	level.get_node("Triggers").add_child(a)
	return a

func interact(level: Node, r: Rect2, props: Dictionary, nm: String) -> Area2D:
	return area_rect(level, r, "res://Scripts/Interactable.gd", props, nm)

func autodoor(level: Node, r: Rect2, target: String, sp: String, nm: String, req: String = "") -> Area2D:
	return area_rect(level, r, "res://Scripts/AutoDoor.gd", {"target_scene": target, "target_spawn": sp, "required_flag": req}, nm)

func ground_poly(level: Node, pts: PackedVector2Array, tex: String, mod: Color = Color.WHITE, nm: String = "Ground") -> Polygon2D:
	var p := Polygon2D.new()
	p.name = nm
	p.polygon = pts
	p.texture = tx(tex)
	p.texture_repeat = CanvasItem.TEXTURE_REPEAT_ENABLED
	p.color = mod
	level.get_node("Ground").add_child(p)
	return p

func ground_rect(level: Node, r: Rect2, tex: String, mod: Color = Color.WHITE, nm: String = "Ground") -> Polygon2D:
	return ground_poly(level, PackedVector2Array([r.position, Vector2(r.end.x, r.position.y), r.end, Vector2(r.position.x, r.end.y)]), tex, mod, nm)

func ground_sprite(level: Node, tex: String, pos: Vector2, nm: String = "GroundSprite") -> Sprite2D:
	var s := Sprite2D.new()
	s.name = nm
	s.texture = tx(tex)
	s.centered = false
	s.position = pos
	level.get_node("Ground").add_child(s)
	return s

func ribbon(pts: Array, width: float) -> PackedVector2Array:
	var left := PackedVector2Array()
	var right := PackedVector2Array()
	for i in pts.size():
		var d: Vector2
		if i == 0:
			d = (pts[1] - pts[0]).normalized()
		elif i == pts.size() - 1:
			d = (pts[i] - pts[i - 1]).normalized()
		else:
			d = ((pts[i + 1] - pts[i]).normalized() + (pts[i] - pts[i - 1]).normalized()).normalized()
		var n := Vector2(-d.y, d.x) * width * 0.5
		left.append(pts[i] + n)
		right.append(pts[i] - n)
	right.reverse()
	left.append_array(right)
	return left

func dist_poly(p: Vector2, pts: Array) -> float:
	var best := 1e9
	for i in pts.size() - 1:
		var q := Geometry2D.get_closest_point_to_segment(p, pts[i], pts[i + 1])
		best = minf(best, p.distance_to(q))
	return best

func edge_y(edge: Array, x: float) -> float:
	for i in edge.size() - 1:
		var a: Array = edge[i]
		var b: Array = edge[i + 1]
		if x >= a[0] and x <= b[0]:
			if b[0] == a[0]:
				return a[1]
			return lerpf(a[1], b[1], (x - a[0]) / (b[0] - a[0]))
	return edge[edge.size() - 1][1]

# ------------------------------------------------------------------ objects
## place(): footpoint-sorted object. Buildings with an "edge" are cut into 32 px vertical strips,
## each with its own ground-contact Y (so diagonal fronts sort correctly against the player).
func place(level: Node, nm: String, anchor: Vector2, o: Dictionary = {}) -> Dictionary:
	var sp: Dictionary = specs[nm]
	var gs: Array = sp["game_size"]
	var w: int = gs[0]
	var h: int = gs[1]
	var foot: Array = sp.get("foot", [w / 2, h])
	var origin := Vector2(round(anchor.x - foot[0]), round(anchor.y - foot[1]))
	var world := level.get_node("World")
	var texture := tx(String(sp["game"]).get_file().get_basename())
	gid_counter += 1
	var gid := "occ_%s_%d" % [nm, gid_counter]
	var tag: String = o.get("tag", nm)
	var nodes: Array = []
	if sp.has("edge"):
		var edge: Array = sp["edge"]
		var x0 := 0
		while x0 < w:
			var sw: int = mini(32, w - x0)
			var ye: float = round(edge_y(edge, x0 + sw * 0.5))
			var s := Sprite2D.new()
			s.name = "%s_%d_s%d" % [tag, gid_counter, x0 / 32]
			s.texture = texture
			s.centered = false
			s.region_enabled = true
			s.region_rect = Rect2(x0, 0, sw, h)
			s.offset = Vector2(-sw * 0.5, -ye)
			s.position = origin + Vector2(x0 + sw * 0.5, ye)
			world.add_child(s)
			nodes.append(s)
			x0 += 32
	else:
		var s2 := Sprite2D.new()
		s2.name = "%s_%d" % [tag, gid_counter]
		s2.texture = texture
		s2.centered = false
		s2.offset = Vector2(-foot[0], -foot[1])
		s2.position = origin + Vector2(foot[0], foot[1])
		world.add_child(s2)
		nodes.append(s2)
	for n in nodes:
		n.add_to_group(gid, true)
	if o.get("decor", false):
		return {"origin": origin, "gid": gid, "nodes": nodes}
	# collision (designed polygons, never the sprite rectangle)
	var polys: Array = []
	if sp.has("footprint_blocks"):
		polys.append_array(sp["footprint_blocks"])
	elif sp.has("footprint") and sp["footprint"].size() > 2:
		polys.append(sp["footprint"])
	var pi := 0
	for poly in polys:
		var pts := PackedVector2Array()
		for p in poly:
			pts.append(origin + Vector2(p[0], p[1]))
		solid_poly(level, pts, "Col_%s_%d_%d" % [tag, gid_counter, pi])
		pi += 1
	# occlusion (roof / canopy fade zones)
	if not o.get("no_occ", false):
		var oi := 0
		for r in sp.get("occlusion", []):
			var rr := Rect2(origin.x + r[0], origin.y, r[2], float(r[1]) + r[3])
			area_rect(level, rr, "res://Scripts/Occluder.gd", {"group_name": gid, "fade_alpha": 0.4}, "Occ_%s_%d_%d" % [tag, gid_counter, oi])
			oi += 1
	# doors
	var doors: Dictionary = o.get("doors", {})
	for d in sp.get("doors", []):
		if doors.has(d["id"]):
			var r2: Array = d["rect"]
			var props: Dictionary = (doors[d["id"]] as Dictionary).duplicate()
			if not props.has("label"):
				props["label"] = d["label"]
			interact(level, Rect2(origin.x + r2[0], origin.y + r2[1], r2[2], r2[3]), props, "Door_%s_%s" % [tag, d["id"]])
	return {"origin": origin, "gid": gid, "nodes": nodes}

## Small generated prop (furniture etc.): bottom-centre anchor, base collider of depth `d`.
func prop(level: Node, nm: String, anchor: Vector2, d: int = 8, nocol: bool = false, mod: Color = Color.WHITE) -> Sprite2D:
	var t := tx(nm)
	var s := Sprite2D.new()
	gid_counter += 1
	s.name = "%s_%d" % [nm, gid_counter]
	s.texture = t
	s.centered = false
	s.offset = Vector2(-t.get_width() * 0.5, -t.get_height())
	s.position = anchor.round()
	s.modulate = mod
	level.get_node("World").add_child(s)
	if not nocol and d > 0:
		var w := t.get_width()
		solid_rect(level, Rect2(anchor.x - w * 0.5, anchor.y - d, w, d), "Col_%s_%d" % [nm, gid_counter])
	return s

func deco(level: Node, nm: String, anchor: Vector2, light: bool = false) -> Sprite2D:
	# no collision: torches, banners, flat decals. y-sorted by their base.
	var s := prop(level, nm, anchor, 0, true)
	return s

func trees(level: Node, count: int, area: Rect2, avoid: Callable, seed_v: int, pine_ratio: float = 0.5) -> void:
	rng.seed = seed_v
	var placed: Array = []
	var tries := 0
	while placed.size() < count and tries < count * 40:
		tries += 1
		var p := Vector2(rng.randf_range(area.position.x, area.end.x), rng.randf_range(area.position.y, area.end.y)).round()
		if avoid.call(p):
			continue
		var ok := true
		for q in placed:
			if p.distance_to(q) < 90:
				ok = false
				break
		if not ok:
			continue
		placed.append(p)
		place(level, "pine_tree" if rng.randf() < pine_ratio else "oak_tree", p, {"tag": "tree"})

# ------------------------------------------------------------------ player
func build_player() -> void:
	var p := CharacterBody2D.new()
	p.name = "Player"
	p.set_script(load("res://Scripts/Player.gd"))
	p.collision_layer = 4
	p.collision_mask = 1
	var spr := Sprite2D.new()
	spr.name = "Sprite"
	spr.texture = tx("player_sheet")
	spr.hframes = 4
	spr.vframes = 4
	spr.centered = false
	spr.offset = Vector2(-16, -64)
	p.add_child(spr)
	var cs := CollisionShape2D.new()
	cs.name = "Footprint"
	var rs := RectangleShape2D.new()
	rs.size = Vector2(20, 12)
	cs.shape = rs
	cs.position = Vector2(0, -6)
	p.add_child(cs)
	var sense := Area2D.new()
	sense.name = "Sense"
	sense.collision_layer = 0
	sense.collision_mask = 8
	var sc := CollisionShape2D.new()
	var ss := RectangleShape2D.new()
	ss.size = Vector2(44, 34)
	sc.shape = ss
	sc.position = Vector2(0, -10)
	sense.add_child(sc)
	p.add_child(sense)
	var cam := Camera2D.new()
	cam.name = "Cam"
	cam.position = Vector2(0, -32)
	cam.position_smoothing_enabled = false
	p.add_child(cam)
	save_scene(p, "res://Scenes/Player.tscn")

func line(level: Node, pts: Array, col: Color, w: float, nm: String = "Edge") -> void:
	var l := Line2D.new()
	l.name = nm
	l.width = w
	l.default_color = col
	for p in pts:
		l.add_point(p)
	level.get_node("Ground").add_child(l)

func water(level: Node, r: Rect2, nm: String, modv: Color = Color.WHITE) -> void:
	ground_rect(level, r, "river_water_tile", modv, nm)

func water_poly(level: Node, pts: PackedVector2Array, nm: String, modv: Color = Color.WHITE) -> void:
	ground_poly(level, pts, "river_water_tile", modv, nm)
	solid_poly(level, pts, "Col_" + nm)

# ------------------------------------------------------------------ APPROACH
func build_approach() -> void:
	var B := Rect2(0, 0, 2800, 1800)
	var L := make_level("The Forest Approach", B, "start", true)
	boundary(L, B)
	ground_rect(L, B, "grass_tile", Color.WHITE, "Grass")
	ground_rect(L, Rect2(0, 300, 2800, 340), "cobblestone_tile", Color(0.62, 0.62, 0.7), "CastleGround")
	# west cliff / rock edge (placeholder rock texture: pack has no rock tile)
	var cliff := PackedVector2Array([Vector2(0, 250), Vector2(250, 250), Vector2(262, 450), Vector2(240, 640), Vector2(0, 640)])
	ground_poly(L, cliff, "floor_flags", Color(0.8, 0.8, 0.82), "RockCliff")
	solid_poly(L, cliff, "Col_RockCliff")
	# moat / river (collision leaves a corridor exactly under the drawbridge)
	water_poly(L, PackedVector2Array([Vector2(0, 640), Vector2(1118, 640), Vector2(1082, 790), Vector2(0, 790)]), "MoatW")
	water_poly(L, PackedVector2Array([Vector2(1264, 640), Vector2(2800, 640), Vector2(2800, 790), Vector2(1252, 790)]), "MoatE")
	water(L, Rect2(1082, 640, 182, 150), "MoatUnderBridge")
	line(L, [Vector2(0, 792), Vector2(1082, 792)], Color(0.35, 0.34, 0.38), 8, "BankW")
	line(L, [Vector2(1252, 792), Vector2(2800, 792)], Color(0.35, 0.34, 0.38), 8, "BankE")
	# lower stream with a paved ford where the path crosses
	water_poly(L, PackedVector2Array([Vector2(0, 1180), Vector2(1180, 1180), Vector2(1180, 1290), Vector2(0, 1290)]), "StreamW")
	water_poly(L, PackedVector2Array([Vector2(1320, 1180), Vector2(2800, 1180), Vector2(2800, 1290), Vector2(1320, 1290)]), "StreamE")
	water(L, Rect2(1180, 1180, 140, 110), "StreamFordBed")
	# path
	var path: Array = [Vector2(1420, 1800), Vector2(1420, 1560), Vector2(1300, 1420), Vector2(1250, 1330), Vector2(1250, 1200), Vector2(1190, 1000), Vector2(1170, 800)]
	var rp := ribbon(path, 128.0)
	ground_poly(L, rp, "cobblestone_tile", Color(0.92, 0.88, 0.8), "Path")
	# branch toward the east hillside (escape grate)
	var path2: Array = [Vector2(1200, 1000), Vector2(1700, 990), Vector2(2200, 1010), Vector2(2440, 1040)]
	ground_poly(L, ribbon(path2, 90.0), "cobblestone_tile", Color(0.85, 0.8, 0.72), "PathEast")
	# drawbridge (ground layer) + gatehouse
	var gate_anchor := Vector2(1200, 700)
	var go := gate_anchor - Vector2(297, 448)
	ground_sprite(L, "gatehouse_bridge", go + Vector2(186, 368), "Drawbridge")
	place(L, "gatehouse_main", gate_anchor, {"tag": "gatehouse"})
	autodoor(L, Rect2(1148, 628, 115, 24), SC_COURT, "gate_in", "To_Courtyard")
	solid_rect(L, Rect2(1138, 540, 137, 84), "GatePassageBack")
	# wall run (west short, east long = asymmetry) + unequal towers
	place(L, "modular_wall", Vector2(672, 630), {"tag": "wallW", "no_occ": true})
	for cx in [1697, 2137, 2577]:
		place(L, "modular_wall", Vector2(cx, 630), {"tag": "wallE", "no_occ": true})
	solid_rect(L, Rect2(237, 560, 901, 80), "WallFillW")
	solid_rect(L, Rect2(1275, 560, 1485, 80), "WallFillE")
	place(L, "watchtower", Vector2(330, 670), {"tag": "towerW", "no_occ": true})
	place(L, "watchtower", Vector2(2700, 670), {"tag": "towerE", "no_occ": true})
	place(L, "waterfall", Vector2(115, 785), {"tag": "waterfall"})
	# the keep, hall, chapel and library roofs rise behind the wall (scenery only)
	place(L, "keep_asset", Vector2(640, 560), {"decor": true, "tag": "bgkeep"})
	place(L, "library_tower", Vector2(1380, 520), {"decor": true, "tag": "bglib"})
	place(L, "great_hall", Vector2(1900, 560), {"decor": true, "tag": "bghall"})
	place(L, "chapel", Vector2(2500, 545), {"decor": true, "tag": "bgchapel"})
	# hidden drain grate on the east hillside (escape return)
	var rock := PackedVector2Array([Vector2(2360, 920), Vector2(2540, 920), Vector2(2560, 1010), Vector2(2330, 1010)])
	ground_poly(L, rock, "floor_flags", Color(0.8, 0.8, 0.82), "RockOutcrop")
	prop(L, "prop_grate", Vector2(2450, 985), 0, true)
	interact(L, Rect2(2410, 960, 80, 60), {"kind": "search", "label": "Inspect grate", "hide_when_flag": "escape_open", "concealed_hint": "A rusted drain grate in the hillside. It is barred from below."}, "GrateLocked")
	interact(L, Rect2(2410, 960, 80, 60), {"kind": "door", "label": "Climb down the drain", "required_flag": "escape_open", "target_scene": SC_UNDER, "target_spawn": "escape_in"}, "GrateOpen")
	# forest
	var avoid := func(p: Vector2) -> bool:
		if dist_poly(p, path) < (160 if p.y < 1000 else 120): return true
		if dist_poly(p, path2) < 100: return true
		if p.y > 1140 and p.y < 1350: return true
		if p.y < 850: return true
		if p.distance_to(Vector2(2450, 1000)) < 190: return true
		if p.distance_to(Vector2(1420, 1700)) < 140: return true
		return false
	trees(L, 80, Rect2(30, 830, 2740, 930), avoid, 11)
	spawn(L, "start", Vector2(1420, 1730), "up")
	spawn(L, "gate_out", Vector2(1195, 735), "down")
	spawn(L, "escape", Vector2(2450, 1075), "down")
	save_scene(L, SC_APPROACH)

func wall_row(L: Node, foot_y: float, centers: Array, tag: String, no_occ: bool) -> void:
	for cx in centers:
		place(L, "modular_wall", Vector2(cx, foot_y), {"tag": tag, "no_occ": no_occ})

func rampart(L: Node, r: Rect2, nm: String) -> void:
	ground_rect(L, r, "wall_brick_dark", Color(1.2, 1.2, 1.25), nm)
	solid_rect(L, r, "Col_" + nm)

func octagon(c: Vector2, r: float) -> PackedVector2Array:
	var pts := PackedVector2Array()
	for i in 8:
		var a := TAU * (i + 0.5) / 8.0
		pts.append(c + Vector2(cos(a), sin(a)) * r)
	return pts

# ------------------------------------------------------------------ COURTYARD
func build_courtyard() -> void:
	var B := Rect2(0, 0, 3400, 2250)
	var L := make_level("The Courtyard", B, "gate_in")
	boundary(L, B)
	ground_rect(L, B, "grass_tile", Color.WHITE, "OutsideGrass")
	ground_rect(L, Rect2(0, 300, 3400, 1850), "cobblestone_tile", Color(0.86, 0.83, 0.8), "CourtyardFloor")
	# service lane (east) and gate lane (south) darker paving
	ground_rect(L, Rect2(1430, 2130, 140, 120), "cobblestone_tile", Color(0.9, 0.86, 0.8), "GateThreshold")
	# ramparts (top-down brick bands) -- west and east
	rampart(L, Rect2(0, 300, 64, 1850), "RampartW")
	rampart(L, Rect2(3336, 300, 64, 1450), "RampartE1")
	rampart(L, Rect2(3336, 1950, 64, 200), "RampartE2")
	ground_rect(L, Rect2(3336, 1750, 64, 200), "cobblestone_tile", Color(0.9, 0.86, 0.8), "ServiceGateFloor")
	wall_row(L, 300, [220, 660, 1100, 1540, 1980, 2420, 2860, 3300], "wallN", true)
	wall_row(L, 2150, [1210, 770, 330, -110, 1790, 2230, 2670, 3110, 3550], "wallS", false)
	place(L, "watchtower", Vector2(130, 340), {"tag": "towerNW", "no_occ": true})
	place(L, "watchtower", Vector2(3270, 340), {"tag": "towerNE", "no_occ": true})
	place(L, "watchtower", Vector2(130, 2170), {"tag": "towerSW"})
	place(L, "watchtower", Vector2(3270, 2170), {"tag": "towerSE"})
	solid_rect(L, Rect2(0, 2150, 1430, 100), "SouthFillW")
	solid_rect(L, Rect2(1570, 2150, 1830, 100), "SouthFillE")
	autodoor(L, Rect2(1440, 2165, 120, 30), SC_APPROACH, "gate_out", "To_Approach")
	autodoor(L, Rect2(3352, 1760, 48, 180), SC_YARD, "from_courtyard", "To_ServiceYard")
	# central garden patch (ground-layer art) with designed collision
	var G := Vector2(1200, 1000)
	ground_sprite(L, "courtyard_garden", G, "Garden")
	for r in [Rect2(0, 0, 270, 100), Rect2(340, 0, 263, 100), Rect2(0, 490, 270, 100), Rect2(340, 490, 263, 100), Rect2(0, 0, 45, 590), Rect2(558, 0, 45, 590)]:
		solid_rect(L, Rect2(G + r.position, r.size), "Col_GardenWall")
	solid_poly(L, octagon(G + Vector2(376, 301), 72.0).duplicate(), "Col_GardenFountain")
	# buildings: tallest keep far left, broad low hall right, unequal heights / spacing, chapel far right
	place(L, "keep_asset", Vector2(640, 960), {"tag": "keep", "doors": {"main": {"kind": "door", "target_scene": SC_KEEP, "target_spawn": "from_courtyard"}}})
	place(L, "library_tower", Vector2(1500, 760), {"tag": "library", "doors": {"main": {"kind": "door", "target_scene": SC_LIB, "target_spawn": "from_courtyard"}}})
	place(L, "great_hall", Vector2(2250, 940), {"tag": "hall", "doors": {"main": {"kind": "door", "target_scene": SC_HALL, "target_spawn": "from_courtyard"}}})
	place(L, "chapel", Vector2(2900, 900), {"tag": "chapel", "doors": {"main": {"kind": "door", "target_scene": SC_CHAPEL, "target_spawn": "from_courtyard"}}})
	place(L, "kitchen_bakery", Vector2(620, 1560), {"tag": "kitchen", "doors": {"main": {"kind": "door", "target_scene": SC_KITCHEN, "target_spawn": "from_courtyard"}}})
	place(L, "barracks", Vector2(2700, 1700), {"tag": "barracks", "doors": {"main": {"kind": "door", "target_scene": SC_BARR, "target_spawn": "from_courtyard"}}})
	# well (secret descent) + fountain + clue props
	place(L, "stone_well", Vector2(1060, 1380), {"tag": "well", "no_occ": true})
	interact(L, Rect2(1010, 1383, 100, 44), {"kind": "door", "label": "Climb down the well", "first_label": "Look into the well", "concealed_flag": "well_clue", "concealed_hint": "Cold air breathes up the shaft. Iron rungs, and fresh scrape marks in the moss. Something lies below.", "target_scene": SC_UNDER, "target_spawn": "well_in"}, "Well")
	deco(L, "wall_torch", Vector2(1150, 1384))
	place(L, "fountain", Vector2(2030, 1530), {"tag": "fountain", "no_occ": true})
	var chest := place(L, "treasure_chest", Vector2(1130, 720), {"tag": "chest", "no_occ": true})
	interact(L, Rect2(1090, 725, 80, 36), {"kind": "search", "label": "Open chest", "concealed_hint": "A water-stained note: 'The old well was never sealed. Follow the draft - the torch by the well always leans toward the shaft.'", "sets_flag": "clue_note"}, "ChestNote")
	# training yard in front of the barracks
	prop(L, "prop_dummy", Vector2(2420, 1830), 8)
	prop(L, "prop_dummy", Vector2(2520, 1860), 8)
	prop(L, "prop_dummy", Vector2(2620, 1830), 8)
	prop(L, "prop_rack", Vector2(2330, 1790), 8)
	prop(L, "prop_barrel", Vector2(2830, 1790), 10)
	prop(L, "prop_crate", Vector2(2870, 1800), 12)
	# gate banners
	deco(L, "heraldic_banner", Vector2(1385, 2140))
	deco(L, "heraldic_banner", Vector2(1615, 2140))
	deco(L, "wall_torch", Vector2(2275, 905))
	deco(L, "wall_torch", Vector2(1130, 1130))
	# a few ornamental oaks / pines inside the walls
	for p in [Vector2(210, 1150), Vector2(230, 1620), Vector2(3240, 1250), Vector2(3260, 800)]:
		place(L, "oak_tree", p, {"tag": "oak"})
	for p in [Vector2(250, 760), Vector2(3180, 1550), Vector2(900, 2020), Vector2(2100, 2040)]:
		place(L, "pine_tree", p, {"tag": "pine"})
	spawn(L, "gate_in", Vector2(1500, 2070), "up")
	spawn(L, "from_keep", Vector2(522, 975), "down")
	spawn(L, "from_library", Vector2(1442, 790), "down")
	spawn(L, "from_hall", Vector2(2281, 940), "down")
	spawn(L, "from_chapel", Vector2(2815, 915), "down")
	spawn(L, "from_kitchen", Vector2(627, 1530), "down")
	spawn(L, "from_barracks", Vector2(2740, 1715), "down")
	spawn(L, "from_yard", Vector2(3290, 1850), "left")
	spawn(L, "well", Vector2(1060, 1450), "down")
	save_scene(L, SC_COURT)

# ------------------------------------------------------------------ SERVICE YARD
func build_yard() -> void:
	var B := Rect2(0, 0, 2400, 1500)
	var L := make_level("The Service Yard", B, "from_courtyard")
	boundary(L, B)
	ground_rect(L, B, "grass_tile", Color.WHITE, "OutsideGrass")
	ground_rect(L, Rect2(0, 250, 2400, 1200), "cobblestone_tile", Color(0.92, 0.82, 0.68), "YardFloor")
	rampart(L, Rect2(0, 250, 64, 800), "RampartW1")
	rampart(L, Rect2(0, 1250, 64, 200), "RampartW2")
	rampart(L, Rect2(2336, 250, 64, 1200), "RampartE")
	ground_rect(L, Rect2(0, 1050, 64, 200), "cobblestone_tile", Color(0.9, 0.86, 0.8), "WestGateFloor")
	wall_row(L, 250, [220, 660, 1100, 1540, 1980, 2420], "wallN", true)
	wall_row(L, 1450, [220, 660, 1100, 1540, 1980, 2420], "wallS", false)
	autodoor(L, Rect2(0, 1060, 44, 180), SC_COURT, "from_yard", "To_Courtyard")
	place(L, "stable", Vector2(760, 760), {"tag": "stable", "doors": {"main": {"kind": "door", "target_scene": SC_STABLE, "target_spawn": "from_yard"}}})
	place(L, "blacksmith", Vector2(1700, 880), {"tag": "blacksmith", "doors": {"main": {"kind": "door", "target_scene": SC_SMITH, "target_spawn": "from_yard"}}})
	prop(L, "prop_hay", Vector2(430, 900), 14)
	prop(L, "prop_hay", Vector2(500, 935), 14)
	prop(L, "prop_barrel", Vector2(1400, 1000), 10)
	prop(L, "prop_crate", Vector2(1440, 1010), 12)
	prop(L, "prop_barrel", Vector2(2050, 1010), 10)
	prop(L, "prop_anvilblock", Vector2(1820, 1000), 10)
	deco(L, "wall_torch", Vector2(1530, 880))
	place(L, "oak_tree", Vector2(2200, 520), {"tag": "oak"})
	place(L, "pine_tree", Vector2(200, 430), {"tag": "pine"})
	place(L, "pine_tree", Vector2(2250, 1250), {"tag": "pine"})
	spawn(L, "from_courtyard", Vector2(120, 1150), "right")
	spawn(L, "from_stable", Vector2(1070, 795), "down")
	spawn(L, "from_smith", Vector2(1630, 920), "down")
	save_scene(L, SC_YARD)

# ------------------------------------------------------------------ GRID ROOMS (interiors + underground)
func ground_color(L: Node, r: Rect2, c: Color, nm: String = "Fill") -> void:
	var p := Polygon2D.new()
	p.name = nm
	p.polygon = PackedVector2Array([r.position, Vector2(r.end.x, r.position.y), r.end, Vector2(r.position.x, r.end.y)])
	p.color = c
	L.get_node("Ground").add_child(p)

func _non_wall_near(g: Array, w: int, h: int, x: int, y: int, d: int) -> bool:
	for yy in range(maxi(0, y - d), mini(h, y + d + 1)):
		for xx in range(maxi(0, x - d), mini(w, x + d + 1)):
			if g[yy][xx] != 0:
				return true
	return false

func merged(cat: Array, w: int, h: int, want: Array) -> Array:
	var out: Array = []
	var active: Dictionary = {}
	for y in h + 1:
		var runs: Dictionary = {}
		if y < h:
			var x := 0
			while x < w:
				if cat[y][x] in want:
					var x0 := x
					while x < w and cat[y][x] in want:
						x += 1
					runs["%d:%d" % [x0, x - x0]] = [x0, x - x0]
				else:
					x += 1
		for k in active.keys():
			if not runs.has(k):
				out.append(active[k])
				active.erase(k)
		for k in runs:
			if active.has(k):
				var rr: Rect2i = active[k]
				rr.size.y += 1
				active[k] = rr
			else:
				active[k] = Rect2i(runs[k][0], y, runs[k][1], 1)
	return out

## Carve rectangles (cell units) into solid rock/brick and render floors, water, wall faces and caps.
## Wall faces (brick) are drawn on wall cells that have walkable cells 1-2 rows below them: that is how the
## 3/4 camera sees the far wall. Everything else is a dark cap. Collision = wall cells next to walkable cells.
func grid_build(L: Node, w: int, h: int, floors: Array, waters: Array, bridges: Array, floor_tex: String, wall_tex: String, water_mod: Color, bg: Color, cap_col: Color) -> Array:
	var g: Array = []
	for y in h:
		var row: Array = []
		row.resize(w)
		row.fill(0)
		g.append(row)
	for r in floors:
		for yy in range(r[1], r[1] + r[3]):
			for xx in range(r[0], r[0] + r[2]):
				g[yy][xx] = 1
	for r in waters:
		for yy in range(r[1], r[1] + r[3]):
			for xx in range(r[0], r[0] + r[2]):
				g[yy][xx] = 2
	for r in bridges:
		for yy in range(r[1], r[1] + r[3]):
			for xx in range(r[0], r[0] + r[2]):
				g[yy][xx] = 1
	var vis: Array = []
	var col: Array = []
	for y in h:
		var vr: Array = []
		var cr: Array = []
		for x in w:
			var v := 0
			var c := 0
			if g[y][x] == 1:
				v = 1
			elif g[y][x] == 2:
				v = 2
				c = 1
			else:
				if y + 1 < h and g[y + 1][x] != 0 or y + 2 < h and g[y + 2][x] != 0:
					v = 3
				elif _non_wall_near(g, w, h, x, y, 2):
					v = 4
				if _non_wall_near(g, w, h, x, y, 1):
					c = 1
			vr.append(v)
			cr.append(c)
		vis.append(vr)
		col.append(cr)
	ground_color(L, Rect2(0, 0, w * CELL, h * CELL), bg, "Background")
	for r in merged(vis, w, h, [1]):
		ground_rect(L, Rect2(r.position * CELL, r.size * CELL), floor_tex, Color.WHITE, "Floor")
	for r in merged(vis, w, h, [2]):
		ground_rect(L, Rect2(r.position * CELL, r.size * CELL), "river_water_tile", water_mod, "Water")
	for r in merged(vis, w, h, [3]):
		ground_rect(L, Rect2(r.position * CELL, r.size * CELL), wall_tex, Color.WHITE, "WallFace")
	for r in merged(vis, w, h, [4]):
		ground_color(L, Rect2(r.position * CELL, r.size * CELL), cap_col, "WallCap")
	for r in merged(col, w, h, [1]):
		solid_rect(L, Rect2(r.position * CELL, r.size * CELL), "Col_Wall")
	return g

func cp(x: float, y: float) -> Vector2:
	return Vector2(x * CELL + 16, (y + 1) * CELL)

func exit_s(L: Node, cx: float, h: int, label: String, target: String, tsp: String, nm: String = "Exit") -> void:
	var t := tx("prop_mat")
	var s := Sprite2D.new()
	s.name = nm + "Mat"
	s.texture = t
	s.centered = false
	s.position = Vector2(cx * CELL + 16 - 32, (h - 1) * CELL - 14)
	L.get_node("Ground").add_child(s)
	interact(L, Rect2(cx * CELL + 16 - 44, (h - 2) * CELL - 8, 88, 44), {"kind": "door", "label": label, "target_scene": target, "target_spawn": tsp}, nm)

func door_n(L: Node, cx: float, label: String, target: String, tsp: String, nm: String, req: String = "") -> void:
	var s := prop(L, "prop_door", Vector2(cx * CELL + 16, 3 * CELL), 0, true)
	s.name = nm + "Door"
	interact(L, Rect2(cx * CELL + 16 - 36, 3 * CELL - 4, 72, 40), {"kind": "door", "label": label, "target_scene": target, "target_spawn": tsp, "required_flag": req}, nm)

func torch_wall(L: Node, cx: float, glow: bool = true) -> void:
	deco(L, "wall_torch", Vector2(cx * CELL + 16, 3 * CELL - 8))

func room_base(title: String, w: int, h: int, floor_tex: String, wall_tex: String, default_spawn: String, bg: Color = Color(0.04, 0.03, 0.05)) -> Node2D:
	var B := Rect2(0, 0, w * CELL, h * CELL)
	var L := make_level(title, B, default_spawn)
	boundary(L, B)
	grid_build(L, w, h, [[1, 3, w - 2, h - 4]], [], [], floor_tex, wall_tex, Color.WHITE, bg, Color(0.1, 0.09, 0.12))
	return L

func build_interiors() -> void:
	# ---- Great Hall
	var L := room_base("The Great Hall", 34, 20, "floor_flags", "wall_brick", "from_courtyard")
	ground_rect(L, Rect2(14 * CELL, 3 * CELL, 6 * CELL, 15 * CELL), "carpet_red", Color.WHITE, "Carpet")
	prop(L, "prop_throne", cp(16.5, 4.6), 12)
	for p in [Vector2(5, 8), Vector2(5, 13), Vector2(23, 8), Vector2(23, 13)]:
		prop(L, "prop_table", cp(p.x + 1, p.y), 20)
		prop(L, "prop_table", cp(p.x + 3, p.y), 20)
		prop(L, "prop_bench", cp(p.x + 1.5, p.y + 1.6), 8)
		prop(L, "prop_bench", cp(p.x + 3.5, p.y + 1.6), 8)
	for p in [Vector2(11, 7), Vector2(11, 15), Vector2(22, 7), Vector2(22, 15)]:
		prop(L, "prop_pillar", cp(p.x, p.y), 8)
	deco(L, "heraldic_banner", cp(8, 3) + Vector2(0, -6))
	deco(L, "heraldic_banner", cp(25, 3) + Vector2(0, -6))
	torch_wall(L, 12)
	torch_wall(L, 21)
	door_n(L, 30, "Go to the kitchens", SC_KITCHEN, "from_hall", "ToKitchen")
	exit_s(L, 16.5, 20, "Leave the hall", SC_COURT, "from_hall")
	spawn(L, "from_courtyard", Vector2(16.5 * CELL + 16, 18 * CELL + 16), "up")
	spawn(L, "from_kitchen", Vector2(30 * CELL + 16, 3 * CELL + 52), "down")
	save_scene(L, SC_HALL)
	# ---- Kitchen / bakery (with the pantry secret)
	L = room_base("The Kitchen and Bakery", 30, 18, "floor_flags", "wall_brick", "from_courtyard")
	prop(L, "prop_stove", cp(14, 4.4), 20)
	prop(L, "prop_table", cp(11, 9), 20)
	prop(L, "prop_table", cp(18, 9), 20)
	prop(L, "prop_table", cp(15, 13), 20)
	prop(L, "prop_barrel", cp(25, 6), 10)
	prop(L, "prop_barrel", cp(26, 6), 10)
	prop(L, "prop_crate", cp(25, 9), 12)
	prop(L, "prop_shelf_jars", cp(21, 3.6), 8)
	# pantry nook, west: the middle shelf is a false front
	prop(L, "prop_shelf_jars", cp(3, 3.6), 8)
	var fs := prop(L, "prop_shelf_jars", cp(6.2, 3.6), 8)
	fs.name = "FalseShelf"
	prop(L, "prop_shelf_jars", cp(9.4, 3.6), 8)
	prop(L, "prop_crate", cp(3, 6), 12)
	deco(L, "wall_torch", cp(7.8, 3) + Vector2(0, -8))
	interact(L, Rect2(4.5 * CELL, 3 * CELL + 6, 4 * CELL, 44), {"kind": "door", "label": "Pull the shelf aside", "first_label": "Inspect the shelves", "concealed_flag": "pantry_clue", "concealed_hint": "The middle shelf is cleaner than the rest, and the flagstones below it are scuffed in an arc. It swings out...", "sets_flag": "pantry_found", "target_scene": SC_UNDER, "target_spawn": "pantry_in"}, "PantrySecret")
	door_n(L, 27, "Go to the great hall", SC_HALL, "from_kitchen", "ToHall")
	exit_s(L, 14.5, 18, "Leave the kitchen", SC_COURT, "from_kitchen")
	spawn(L, "from_courtyard", Vector2(14.5 * CELL + 16, 16 * CELL + 16), "up")
	spawn(L, "from_hall", Vector2(27 * CELL + 16, 3 * CELL + 52), "down")
	spawn(L, "pantry_out", Vector2(6.6 * CELL, 3 * CELL + 70), "down")
	save_scene(L, SC_KITCHEN)
	# ---- Chapel
	L = room_base("The Chapel", 30, 20, "floor_flags_dark", "wall_brick_dark", "from_courtyard")
	ground_rect(L, Rect2(13 * CELL, 3 * CELL, 4 * CELL, 15 * CELL), "carpet_red", Color(0.7, 0.7, 0.9), "Carpet")
	prop(L, "prop_altar", cp(14.5, 4.4), 16)
	for y in [8, 11, 14]:
		prop(L, "prop_bench", cp(8.5, y), 8)
		prop(L, "prop_bench", cp(9.9, y), 8)
		prop(L, "prop_bench", cp(18.6, y), 8)
		prop(L, "prop_bench", cp(20, y), 8)
	interact(L, Rect2(12 * CELL, 5 * CELL + 10, 5 * CELL, 40), {"kind": "search", "label": "Read the inscription", "concealed_hint": "Carved under the altar: 'Where the water sleeps, the old faith kept its dead. Mind the loose stones.'", "sets_flag": "chapel_clue"}, "AltarClue")
	torch_wall(L, 9)
	torch_wall(L, 20)
	door_n(L, 25, "Go to the keep", SC_KEEP, "from_chapel", "ToKeep")
	exit_s(L, 14.5, 20, "Leave the chapel", SC_COURT, "from_chapel")
	spawn(L, "from_courtyard", Vector2(14.5 * CELL + 16, 18 * CELL + 16), "up")
	spawn(L, "from_keep", Vector2(25 * CELL + 16, 3 * CELL + 52), "down")
	save_scene(L, SC_CHAPEL)
	# ---- Keep (ground hall)
	L = room_base("The Keep", 32, 18, "floor_planks", "wall_brick", "from_courtyard")
	ground_rect(L, Rect2(13 * CELL, 3 * CELL, 5 * CELL, 13 * CELL), "carpet_red", Color.WHITE, "Carpet")
	prop(L, "prop_table", cp(15.5, 8), 20)
	prop(L, "prop_bench", cp(14.2, 9.7), 8)
	prop(L, "prop_bench", cp(16.8, 9.7), 8)
	prop(L, "prop_bookcase", cp(11, 3.6), 10)
	prop(L, "prop_bookcase", cp(21, 3.6), 10)
	prop(L, "prop_barrel", cp(3, 6), 10)
	torch_wall(L, 9)
	torch_wall(L, 23)
	door_n(L, 27, "Climb the stair to the library", SC_LIB, "from_keep", "ToLibrary")
	door_n(L, 4, "Go to the chapel", SC_CHAPEL, "from_keep", "ToChapel")
	exit_s(L, 15.5, 18, "Leave the keep", SC_COURT, "from_keep")
	spawn(L, "from_courtyard", Vector2(15.5 * CELL + 16, 16 * CELL + 16), "up")
	spawn(L, "from_chapel", Vector2(4 * CELL + 16, 3 * CELL + 52), "down")
	spawn(L, "from_library", Vector2(27 * CELL + 16, 3 * CELL + 52), "down")
	save_scene(L, SC_KEEP)
	# ---- Library (upper keep)
	L = room_base("The Library (Upper Keep)", 30, 18, "floor_planks", "wall_brick", "from_courtyard")
	for x in [3, 7, 11, 18, 22]:
		prop(L, "prop_bookcase", cp(x, 3.6), 10)
	prop(L, "prop_table", cp(10, 9), 20)
	prop(L, "prop_table", cp(19, 9), 20)
	prop(L, "prop_bench", cp(10, 10.6), 8)
	prop(L, "prop_bench", cp(19, 10.6), 8)
	interact(L, Rect2(8.5 * CELL, 9 * CELL - 2, 3 * CELL, 40), {"kind": "search", "label": "Read the open ledger", "concealed_hint": "A ledger: 'Cistern cleaned. Crypt key lost. Prison gate lever is in the crypt, behind the third coffin.'", "sets_flag": "ledger_clue"}, "Ledger")
	torch_wall(L, 14)
	door_n(L, 26, "Back down to the keep", SC_KEEP, "from_library", "ToKeep")
	exit_s(L, 14.5, 18, "Leave the tower", SC_COURT, "from_library")
	spawn(L, "from_courtyard", Vector2(14.5 * CELL + 16, 16 * CELL + 16), "up")
	spawn(L, "from_keep", Vector2(26 * CELL + 16, 3 * CELL + 52), "down")
	save_scene(L, SC_LIB)
	# ---- Barracks / training
	L = room_base("The Barracks", 34, 18, "floor_planks", "wall_brick_dark", "from_courtyard")
	for i in 4:
		prop(L, "prop_cot", cp(3 + i * 3, 5.2), 30)
		prop(L, "prop_cot", cp(21 + i * 3, 5.2), 30)
	prop(L, "prop_rack", cp(15, 3.6), 8)
	prop(L, "prop_rack", cp(18, 3.6), 8)
	prop(L, "prop_dummy", cp(10, 10), 8)
	prop(L, "prop_dummy", cp(13, 12), 8)
	prop(L, "prop_dummy", cp(21, 10), 8)
	prop(L, "prop_dummy", cp(24, 12), 8)
	prop(L, "prop_table", cp(17, 13), 20)
	torch_wall(L, 8)
	torch_wall(L, 26)
	exit_s(L, 16.5, 18, "Leave the barracks", SC_COURT, "from_barracks")
	spawn(L, "from_courtyard", Vector2(16.5 * CELL + 16, 16 * CELL + 16), "up")
	save_scene(L, SC_BARR)
	# ---- Stable
	L = room_base("The Stable", 32, 18, "floor_planks", "wall_brick", "from_yard")
	for i in 4:
		prop(L, "prop_hay", cp(3 + i * 6, 5), 16)
		prop(L, "prop_crate", cp(6 + i * 6, 5.2), 12)
	prop(L, "prop_barrel", cp(28, 12), 10)
	prop(L, "prop_hay", cp(6, 12), 16)
	prop(L, "prop_hay", cp(20, 12), 16)
	torch_wall(L, 10)
	torch_wall(L, 22)
	exit_s(L, 15.5, 18, "Leave the stable", SC_YARD, "from_stable")
	spawn(L, "from_yard", Vector2(15.5 * CELL + 16, 16 * CELL + 16), "up")
	save_scene(L, SC_STABLE)
	# ---- Blacksmith
	L = room_base("The Blacksmith", 30, 18, "floor_flags_dark", "wall_brick_dark", "from_yard")
	prop(L, "prop_stove", cp(14, 4.4), 20)
	prop(L, "prop_anvilblock", cp(10, 9), 12)
	prop(L, "prop_rack", cp(4, 3.6), 8)
	prop(L, "prop_rack", cp(24, 3.6), 8)
	prop(L, "prop_barrel", cp(25, 10), 10)
	prop(L, "prop_crate", cp(5, 10), 12)
	prop(L, "prop_table", cp(19, 11), 20)
	torch_wall(L, 10)
	torch_wall(L, 20)
	exit_s(L, 14.5, 18, "Leave the smithy", SC_YARD, "from_smith")
	spawn(L, "from_yard", Vector2(14.5 * CELL + 16, 16 * CELL + 16), "up")
	save_scene(L, SC_SMITH)

# ------------------------------------------------------------------ UNDERGROUND
func light(L: Node, p: Vector2, energy: float = 1.1, sc: float = 2.6, col: Color = Color(1.0, 0.72, 0.4)) -> void:
	var l := PointLight2D.new()
	l.name = "Light"
	l.position = p
	l.energy = energy
	l.color = col
	var gt := GradientTexture2D.new()
	var gr := Gradient.new()
	gr.colors = PackedColorArray([Color(1, 1, 1, 1), Color(1, 1, 1, 0)])
	gr.offsets = PackedFloat32Array([0.0, 1.0])
	gt.gradient = gr
	gt.fill = GradientTexture2D.FILL_RADIAL
	gt.fill_from = Vector2(0.5, 0.5)
	gt.fill_to = Vector2(1.0, 0.5)
	gt.width = 256
	gt.height = 256
	l.texture = gt
	l.texture_scale = sc
	L.get_node("Triggers").add_child(l)

func ug_torch(L: Node, cx: float, row: float) -> void:
	deco(L, "wall_torch", Vector2(cx * CELL + 16, row * CELL - 4))
	light(L, Vector2(cx * CELL + 16, row * CELL + 40))

func gate_node(L: Node, r: Rect2, flag: String, brick: bool, nm: String) -> Node2D:
	var g := StaticBody2D.new()
	g.name = nm
	g.set_script(load("res://Scripts/Gate.gd"))
	g.set("open_flag", flag)
	g.collision_layer = 1
	g.collision_mask = 0
	var cs := CollisionShape2D.new()
	var rs := RectangleShape2D.new()
	rs.size = r.size
	cs.shape = rs
	cs.position = r.position + r.size * 0.5
	g.add_child(cs)
	if brick:
		var p := Polygon2D.new()
		p.name = "Bricks"
		p.polygon = PackedVector2Array([r.position, Vector2(r.end.x, r.position.y), r.end, Vector2(r.position.x, r.end.y)])
		p.texture = tx("wall_brick")
		p.texture_repeat = CanvasItem.TEXTURE_REPEAT_ENABLED
		p.color = Color(0.8, 0.8, 0.86)
		g.add_child(p)
		var ln := Line2D.new()
		ln.name = "Crack"
		ln.width = 2
		ln.default_color = Color(0.1, 0.08, 0.1)
		for pt in [Vector2(0.3, 0.05), Vector2(0.6, 0.3), Vector2(0.35, 0.5), Vector2(0.7, 0.75), Vector2(0.45, 0.98)]:
			ln.add_point(r.position + Vector2(pt.x * r.size.x, pt.y * r.size.y))
		g.add_child(ln)
	else:
		var n := int(r.size.x / 28.0)
		for i in n:
			var s := Sprite2D.new()
			s.name = "Bar%d" % i
			s.texture = tx("prop_cage")
			s.centered = false
			s.position = Vector2(r.position.x + i * (r.size.x / n), r.position.y - 40)
			g.add_child(s)
	L.get_node("World").add_child(g)
	return g

func build_underground() -> void:
	var W := 70
	var H := 41
	var B := Rect2(0, 0, W * CELL, H * CELL)
	var L := make_level("Beneath the Castle", B, "well_in")
	boundary(L, B)
	var floors := [
		[3, 3, 8, 6], [11, 5, 3, 2], [13, 2, 23, 16], [14, 18, 2, 3], [5, 19, 9, 5], [8, 24, 3, 11],
		[8, 34, 22, 3], [31, 18, 3, 5], [26, 23, 15, 8], [41, 26, 5, 3], [46, 21, 13, 13], [31, 31, 3, 3],
		[26, 34, 15, 5], [59, 26, 6, 3], [63, 8, 3, 19], [60, 4, 8, 5]]
	var waters := [[17, 5, 15, 9]]
	var bridges := [[24, 5, 2, 9]]
	grid_build(L, W, H, floors, waters, bridges, "floor_flags_dark", "wall_brick_dark", Color(0.45, 0.62, 0.85), Color(0.02, 0.02, 0.03), Color(0.06, 0.06, 0.09))
	var cm := CanvasModulate.new()
	cm.name = "Ambient"
	cm.color = Color(0.3, 0.32, 0.46)
	L.add_child(cm)
	# --- A: well shaft landing
	var lad := prop(L, "prop_ladder", Vector2(4 * CELL + 16, 3 * CELL + 4), 0, true)
	light(L, Vector2(4 * CELL + 16, 5 * CELL), 1.0, 3.0, Color(0.7, 0.85, 1.0))
	interact(L, Rect2(3 * CELL, 3 * CELL, 64, 56), {"kind": "door", "label": "Climb up the well shaft", "target_scene": SC_COURT, "target_spawn": "well"}, "LadderWell")
	ug_torch(L, 8, 3)
	area_rect(L, Rect2(3 * CELL, 3 * CELL, 8 * CELL, 6 * CELL), "res://Scripts/Zone.gd", {"title": "The Well Shaft"}, "Zone_Shaft")
	# --- cistern
	for p in [Vector2(14, 4), Vector2(34, 4), Vector2(14, 16), Vector2(34, 16)]:
		prop(L, "prop_pillar", cp(p.x, p.y), 8)
	ug_torch(L, 15, 2)
	ug_torch(L, 33, 2)
	ug_torch(L, 24, 2)
	area_rect(L, Rect2(13 * CELL, 2 * CELL, 23 * CELL, 16 * CELL), "res://Scripts/Zone.gd", {"title": "The Cistern"}, "Zone_Cistern")
	# --- pantry alcove (ladder up to the kitchen pantry) + loop gate
	prop(L, "prop_ladder", Vector2(7 * CELL + 16, 19 * CELL + 4), 0, true)
	interact(L, Rect2(6 * CELL, 19 * CELL, 64, 56), {"kind": "door", "label": "Climb up to the pantry", "target_scene": SC_KITCHEN, "target_spawn": "pantry_out"}, "LadderPantry")
	prop(L, "prop_crate", cp(11, 21), 12)
	prop(L, "prop_barrel", cp(12, 22), 10)
	ug_torch(L, 10, 19)
	area_rect(L, Rect2(5 * CELL, 19 * CELL, 9 * CELL, 5 * CELL), "res://Scripts/Zone.gd", {"title": "The Old Pantry Stair"}, "Zone_Alcove")
	gate_node(L, Rect2(8 * CELL, 28 * CELL, 3 * CELL, 28), "prison_open", false, "LoopGate")
	interact(L, Rect2(8 * CELL, 26 * CELL, 3 * CELL, 64), {"kind": "search", "label": "Inspect the rusted gate", "hide_when_flag": "prison_open", "concealed_hint": "A rusted gate bars the passage. There must be a lever somewhere."}, "LoopGateHint")
	# --- junction
	ug_torch(L, 28, 23)
	ug_torch(L, 38, 23)
	prop(L, "prop_barrel", cp(27, 29), 10)
	area_rect(L, Rect2(26 * CELL, 23 * CELL, 15 * CELL, 8 * CELL), "res://Scripts/Zone.gd", {"title": "Crypt and Prison Junction"}, "Zone_Junction")
	# --- crypt
	for x in [49, 53, 57]:
		prop(L, "prop_sarcophagus", cp(x, 25), 22)
	prop(L, "prop_altar", cp(52, 30), 16)
	prop(L, "prop_lever", Vector2(57 * CELL + 16, 23 * CELL + 12), 6)
	interact(L, Rect2(56 * CELL, 22 * CELL + 6, 64, 40), {"kind": "lever", "label": "Pull the lever", "done_hint": "Clunk... a gate grinds open somewhere in the dark.", "sets_flag": "prison_open"}, "Lever")
	ug_torch(L, 48, 21)
	ug_torch(L, 56, 21)
	ug_torch(L, 58, 26)
	area_rect(L, Rect2(46 * CELL, 21 * CELL, 13 * CELL, 13 * CELL), "res://Scripts/Zone.gd", {"title": "The Crypt"}, "Zone_Crypt")
	# secret wall (east side of the crypt): looks like newer brickwork; the torch beside it leans toward it
	gate_node(L, Rect2(59 * CELL, 26 * CELL, CELL, 3 * CELL), "crypt_secret", true, "SecretWall")
	interact(L, Rect2(57 * CELL, 26 * CELL, 64, 96), {"kind": "search", "label": "Push the loose stones", "first_label": "Examine the east wall", "concealed_flag": "crypt_loose", "concealed_hint": "This brickwork is newer than the rest, and the torch flame leans toward it. A draft seeps through the cracks.", "sets_flag": "crypt_secret", "done_hint": "The stones grind aside, revealing a narrow tunnel!"}, "SecretWallUse")
	# --- prison
	for x in [28, 31, 34]:
		prop(L, "prop_cage", cp(x, 35.6), 24)
	var ch := place(L, "treasure_chest", cp(38.5, 37.6), {"tag": "chest", "no_occ": true})
	interact(L, Rect2(37 * CELL, 37 * CELL, 80, 50), {"kind": "search", "label": "Open chest", "concealed_hint": "A rusty key and a scrap: 'The crypt's east wall is hollow. The tunnel leads out beyond the walls.'", "sets_flag": "prison_note"}, "PrisonChest")
	ug_torch(L, 28, 34)
	ug_torch(L, 38, 34)
	area_rect(L, Rect2(26 * CELL, 34 * CELL, 15 * CELL, 5 * CELL), "res://Scripts/Zone.gd", {"title": "The Prison"}, "Zone_Prison")
	# --- escape tunnel + stairs to the surface (beyond the wall)
	ug_torch(L, 62, 4)
	ug_torch(L, 66, 4)
	prop(L, "prop_ladder", Vector2(64 * CELL + 16, 4 * CELL + 4), 0, true)
	interact(L, Rect2(63 * CELL, 4 * CELL, 64, 56), {"kind": "door", "label": "Climb up to the surface", "target_scene": SC_APPROACH, "target_spawn": "escape", "sets_flag": "escape_open"}, "LadderEscape")
	area_rect(L, Rect2(60 * CELL, 4 * CELL, 8 * CELL, 5 * CELL), "res://Scripts/Zone.gd", {"title": "The Smuggler's Stair"}, "Zone_Escape")
	spawn(L, "well_in", cp(4, 5), "down")
	spawn(L, "pantry_in", cp(7, 21), "down")
	spawn(L, "escape_in", cp(64, 6), "up")
	save_scene(L, SC_UNDER)

# ------------------------------------------------------------------ TEST SCENES
func label(L: Node, text: String, pos: Vector2, size: int = 12) -> void:
	var l := Label.new()
	l.text = text
	l.position = pos
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", Color(1, 1, 1))
	l.add_theme_color_override("font_outline_color", Color(0, 0, 0))
	l.add_theme_constant_override("outline_size", 4)
	L.get_node("Ground").add_child(l)

func box_outline(L: Node, r: Rect2, col: Color, nm: String) -> void:
	line(L, [r.position, Vector2(r.end.x, r.position.y), r.end, Vector2(r.position.x, r.end.y), r.position], col, 2, nm)

func build_tests() -> void:
	# ---------- scale + Y-sort test
	var B := Rect2(0, 0, 1800, 1000)
	var L := make_level("Scale / Y-sort / occlusion test", B, "start")
	boundary(L, B)
	ground_rect(L, B, "grass_tile", Color.WHITE, "Grass")
	ground_rect(L, Rect2(0, 700, 1800, 150), "cobblestone_tile", Color(0.92, 0.88, 0.8), "WalkablePath")
	# scale rulers (nodes, not baked into sprites): 64 px player height, 32 px grid ticks
	box_outline(L, Rect2(60, 636, 32, 64), Color(1, 0.2, 0.9), "Ruler64")
	label(L, "64 px = player", Vector2(40, 606), 12)
	for i in 5:
		line(L, [Vector2(120, 700 - i * 16), Vector2(136, 700 - i * 16)], Color(1, 1, 1), 1, "Tick")
	line(L, [Vector2(128, 700), Vector2(128, 636)], Color(1, 1, 1), 1, "RulerLine")
	label(L, "ground row y=560 (footpoints)", Vector2(200, 596), 12)
	line(L, [Vector2(0, 560), Vector2(1800, 560)], Color(1, 1, 0.3, 0.5), 1, "FootRow")
	place(L, "oak_tree", Vector2(300, 560), {"tag": "oak"})
	place(L, "pine_tree", Vector2(520, 560), {"tag": "pine"})
	place(L, "stone_well", Vector2(740, 560), {"tag": "well", "no_occ": true})
	place(L, "fountain", Vector2(980, 560), {"tag": "fountain", "no_occ": true})
	place(L, "treasure_chest", Vector2(1160, 560), {"tag": "chest", "no_occ": true})
	place(L, "modular_wall", Vector2(1500, 560), {"tag": "wall"})
	# building entrance + roof/occlusion test
	place(L, "kitchen_bakery", Vector2(900, 330), {"tag": "kitchen", "doors": {"main": {"kind": "door", "target_scene": SC_KITCHEN, "target_spawn": "from_courtyard"}}})
	label(L, "door", Vector2(930, 340), 12)
	spawn(L, "start", Vector2(900, 790), "up")
	spawn(L, "behind_oak", Vector2(300, 480), "down")
	spawn(L, "front_oak", Vector2(300, 600), "up")
	spawn(L, "behind_wall", Vector2(1500, 470), "down")
	spawn(L, "front_wall", Vector2(1500, 600), "up")
	spawn(L, "behind_building", Vector2(900, 120), "down")
	save_scene(L, "res://Scenes/Test/ScaleTest.tscn")
	# ---------- asset / alpha gallery (every individual asset, game-scale, on magenta|white split cells)
	var G := make_level("Asset and alpha gallery", Rect2(0, 0, 3200, 2300), "start")
	var names := ["great_hall", "keep_asset", "gatehouse_asset", "chapel", "library_tower", "barracks", "blacksmith", "stable", "kitchen_bakery", "watchtower", "modular_wall", "oak_tree", "pine_tree", "stone_well", "fountain", "courtyard_garden", "treasure_chest", "wall_torch", "heraldic_banner", "waterfall"]
	var x := 20.0
	var y := 20.0
	var rowh := 0.0
	for n in names:
		var sz: Array = specs[n]["game_size"]
		var cw: float = sz[0] + 16
		var ch: float = sz[1] + 40
		if x + cw > 3180:
			x = 20.0
			y += rowh + 12
			rowh = 0.0
		ground_color(G, Rect2(x, y, cw / 2.0, ch), Color(1, 0, 1), "BgMagenta_" + n)
		ground_color(G, Rect2(x + cw / 2.0, y, cw / 2.0, ch), Color(1, 1, 1), "BgWhite_" + n)
		ground_sprite(G, String(specs[n]["game"]).get_file().get_basename(), Vector2(x + 8, y + 32), "Img_" + n)
		label(G, "%s %dx%d" % [n, sz[0], sz[1]], Vector2(x + 4, y + 4), 12)
		x += cw + 12
		rowh = maxf(rowh, ch)
	y += rowh + 24
	# tiles: raw (unfixed) vs seamless derivative, 3x3 repeat at game scale
	var tx_x := 20.0
	for t in ["cobblestone_tile", "grass_tile", "river_water_tile"]:
		for variant in ["raw", "seamless"]:
			var pth: String = "res://Art/Processed/%s_raw240.png" % t if variant == "raw" else "res://Art/Game/%s.png" % t
			var tex: Texture2D = load(pth)
			var pp := Polygon2D.new()
			pp.name = "Tile_%s_%s" % [t, variant]
			pp.polygon = PackedVector2Array([Vector2(tx_x, y + 24), Vector2(tx_x + 720, y + 24), Vector2(tx_x + 720, y + 744), Vector2(tx_x, y + 744)])
			pp.texture = tex
			pp.texture_repeat = CanvasItem.TEXTURE_REPEAT_ENABLED
			G.get_node("Ground").add_child(pp)
			label(G, "%s (%s) 3x3" % [t, variant], Vector2(tx_x, y), 12)
			tx_x += 740
			if tx_x > 3000:
				tx_x = 20.0
				y += 780
	spawn(G, "start", Vector2(40, 40), "down")
	save_scene(G, "res://Scenes/Test/AssetGallery.tscn")
