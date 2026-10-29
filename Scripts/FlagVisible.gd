extends Node2D
## Container whose children are only visible once the story flag exists (e.g. revealed secret stair).
# Autoload accessor (resolved at runtime so the scene-baker can compile this script headless).
var Game:
	get: return get_node("/root/Game")

@export var flag: String = ""
func _ready() -> void:
	Game.flags_changed.connect(_refresh)
	_refresh()
func _refresh() -> void:
	visible = flag == "" or Game.has_flag(flag)
