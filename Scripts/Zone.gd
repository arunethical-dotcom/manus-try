extends Area2D
## Shows a short title toast when the player enters (used for underground section names).
# Autoload accessor (resolved at runtime so the scene-baker can compile this script headless).
var Game:
	get: return get_node("/root/Game")

@export var title: String = ""
func _ready() -> void:
	collision_layer = 8
	collision_mask = 4
	body_entered.connect(func(b): if b.is_in_group("player") and title != "": Game.show_title(title))
