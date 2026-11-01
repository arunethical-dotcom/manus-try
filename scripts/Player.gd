extends CharacterBody2D
## Kael: 16x28 px sprite, origin = feet (y-sort key). WASD / arrows to walk, hold Shift to run.
const SPEED := 110.0
const RUN_MULT := 1.8

var facing := "down"
var anim := 0.0

func _ready() -> void:
	motion_mode = CharacterBody2D.MOTION_MODE_FLOATING

func _physics_process(dt: float) -> void:
	var v := Input.get_vector("move_left", "move_right", "move_up", "move_down")
	var running := Input.is_action_pressed("run")
	velocity = v * SPEED * (RUN_MULT if running else 1.0)
	move_and_slide()
	if v.length() > 0.1:
		if absf(v.x) > absf(v.y):
			facing = "right" if v.x > 0 else "left"
		else:
			facing = "down" if v.y > 0 else "up"
		anim += dt * (14.0 if running else 8.0)
	else:
		anim = 0.0
	var row: int = ["down", "left", "right", "up"].find(facing)
	($Sprite as Sprite2D).frame = row * 4 + int(anim) % 4
