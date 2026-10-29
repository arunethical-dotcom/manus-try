extends CharacterBody2D
## Top-down player. Origin = feet (ground-contact point; this is the Y-sort key).
## Sprite is 32x64 (64 px tall = the scale anchor). Collision is a small 20x12 footprint at the feet,
## so the body is never a full-sprite rectangle and the player glides past decoration.
var Game:
	get: return get_node("/root/Game")

const HEIGHT := 64.0
const SPEED := 150.0

var facing: String = "down"
var anim_t := 0.0
var sense_areas: Array = []
var interact_target: Area2D = null
var level_bounds := Rect2(-100000, -100000, 200000, 200000)

@onready var sprite: Sprite2D = $Sprite
@onready var cam: Camera2D = $Cam
@onready var sense: Area2D = $Sense

func _ready() -> void:
	add_to_group("player")
	motion_mode = CharacterBody2D.MOTION_MODE_FLOATING
	sense.area_entered.connect(func(a): sense_areas.append(a))
	sense.area_exited.connect(func(a): sense_areas.erase(a))

func setup_camera(b: Rect2) -> void:
	level_bounds = b
	cam.limit_left = int(b.position.x)
	cam.limit_top = int(b.position.y)
	cam.limit_right = int(b.end.x)
	cam.limit_bottom = int(b.end.y)
	cam.reset_smoothing()

func _physics_process(dt: float) -> void:
	var v := Input.get_vector("move_left", "move_right", "move_up", "move_down")
	if Game.transitioning:
		v = Vector2.ZERO
	velocity = v * SPEED
	move_and_slide()
	if v.length() > 0.1:
		if absf(v.x) > absf(v.y) + 0.1:
			facing = "right" if v.x > 0 else "left"
		elif absf(v.y) > 0.1:
			facing = "down" if v.y > 0 else "up"
		anim_t += dt * 9.0
	else:
		anim_t = 0.0
	var row: int = ["down", "left", "right", "up"].find(facing)
	sprite.frame = row * 4 + (int(anim_t) % 4)
	_update_prompt()

func _update_prompt() -> void:
	var best: Area2D = null
	var bd := 1e9
	for a in sense_areas:
		if is_instance_valid(a) and a.has_method("is_available") and a.is_available():
			var d: float = global_position.distance_to(a.global_position)
			if d < bd:
				bd = d
				best = a
	interact_target = best
	Game.set_prompt(best.prompt_text() if best else "")

func _unhandled_input(e: InputEvent) -> void:
	if e.is_action_pressed("interact") and interact_target != null and not Game.transitioning:
		interact_target.interact(self)
