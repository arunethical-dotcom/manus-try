extends Area2D
## Door / stairs / search-spot / lever. Fully data-driven through exported properties.
## kind: "door" (changes scene), "search" (hint + flag), "lever" (sets a flag)
var Game:
	get: return get_node("/root/Game")

@export var kind: String = "door"
@export var label: String = "Enter"
@export var target_scene: String = ""
@export var target_spawn: String = ""
@export var required_flag: String = ""     # unavailable until this flag exists
@export var sets_flag: String = ""         # flag set when used
@export var concealed_flag: String = ""    # first use only shows `concealed_hint` and sets this flag
@export var concealed_hint: String = ""
@export var first_label: String = ""       # prompt shown until concealed_flag is set
@export var hide_when_flag: String = ""    # unavailable once this flag exists
@export var done_hint: String = ""

func _ready() -> void:
	collision_layer = 8
	collision_mask = 0
	Game.flags_changed.connect(_refresh)
	_refresh()

func _refresh() -> void:
	monitorable = is_available()

func is_available() -> bool:
	if required_flag != "" and not Game.has_flag(required_flag):
		return false
	if hide_when_flag != "" and Game.has_flag(hide_when_flag):
		return false
	return true

func prompt_text() -> String:
	if first_label != "" and concealed_flag != "" and not Game.has_flag(concealed_flag):
		return "[E] %s" % first_label
	return "[E] %s" % label

func interact(_p: Node) -> void:
	if not is_available():
		return
	if concealed_flag != "" and not Game.has_flag(concealed_flag):
		Game.set_flag(concealed_flag)
		if concealed_hint != "":
			Game.toast(concealed_hint, 5.0)
		return
	if sets_flag != "":
		Game.set_flag(sets_flag)
	match kind:
		"door":
			if target_scene != "":
				Game.go(target_scene, target_spawn)
		"search":
			var msg := done_hint if done_hint != "" else concealed_hint
			if msg != "":
				Game.toast(msg, 4.0)
		"lever":
			if done_hint != "":
				Game.toast(done_hint, 4.0)
