extends Area2D
## Roof / building-front occlusion. While the player stands in this zone (i.e. is behind the building
## and would be hidden by its roof), every sprite in `group_name` fades to `fade_alpha`.
@export var group_name: String = ""
@export var fade_alpha: float = 0.35
var _inside := 0
var _tween: Tween

func _ready() -> void:
	collision_layer = 0
	collision_mask = 4
	body_entered.connect(func(b): if b.is_in_group("player"): _bump(1))
	body_exited.connect(func(b): if b.is_in_group("player"): _bump(-1))

func _bump(d: int) -> void:
	_inside = maxi(0, _inside + d)
	var a := fade_alpha if _inside > 0 else 1.0
	for n in get_tree().get_nodes_in_group(group_name):
		var t := n.create_tween()
		t.tween_property(n, "modulate:a", a, 0.18)
