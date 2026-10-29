extends Node2D
## Root script of every level. Spawns the player into the Y-sorted "World" node at the requested Marker2D.
var Game:
	get: return get_node("/root/Game")

@export var level_title: String = ""
@export var bounds: Rect2 = Rect2(0, 0, 2400, 1800)
@export var default_spawn: String = "start"
@export var controls_hint: bool = false

var player: CharacterBody2D = null

func _ready() -> void:
	Game.current_level = self
	var want: String = Game.consume_spawn(default_spawn)
	var marker := get_node_or_null("Spawns/" + want) as Marker2D
	if marker == null:
		push_warning("Missing spawn '%s' in %s; using default" % [want, name])
		marker = get_node("Spawns/" + default_spawn) as Marker2D
	player = (load("res://Scenes/Player.tscn") as PackedScene).instantiate()
	get_node("World").add_child(player)
	player.global_position = marker.global_position
	player.facing = str(marker.get_meta("facing", "up"))
	player.setup_camera(bounds)
	Game.show_title(level_title)
	if controls_hint:
		Game.toast("WASD / arrows: move   -   E / Enter: interact   -   R: restart", 7.0)
