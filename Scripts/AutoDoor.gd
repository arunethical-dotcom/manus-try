extends Area2D
## Walk-through transition (gate passage, tunnel mouth, area edge). Fires when the player's footprint enters.
var Game:
	get: return get_node("/root/Game")

@export var target_scene: String = ""
@export var target_spawn: String = ""
@export var required_flag: String = ""

func _ready() -> void:
	collision_layer = 8
	collision_mask = 4
	body_entered.connect(_on_body)

func _on_body(b: Node) -> void:
	if not b.is_in_group("player"):
		return
	if required_flag != "" and not Game.has_flag(required_flag):
		return
	Game.go.call_deferred(target_scene, target_spawn)
