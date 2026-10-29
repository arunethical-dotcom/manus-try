extends StaticBody2D
## Gate that opens when the named flag exists (lever-operated).
# Autoload accessor (resolved at runtime so the scene-baker can compile this script headless).
var Game:
	get: return get_node("/root/Game")

@export var open_flag: String = ""
func _ready() -> void:
	Game.flags_changed.connect(_refresh)
	_refresh()
func _refresh() -> void:
	var open: bool = open_flag != "" and Game.has_flag(open_flag)
	visible = not open
	for c in get_children():
		if c is CollisionShape2D:
			c.set_deferred("disabled", open)
