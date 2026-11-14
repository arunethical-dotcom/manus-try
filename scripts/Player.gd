extends CharacterBody2D
## Kael: Swordsman lvl3 (craftpix, art/game/kael3/*.png): 64x64 frames, 4 rows (down, left, right, up), feet at
## frame y 45. Origin = feet (y-sort key). WASD / arrows to walk, Shift to run, Space to attack.
const SPEED := 110.0
const RUN_MULT := 1.8
const ANIMS := {                        # name: [frames, fps, loop]
	"idle": [12, 8.0, true], "walk": [6, 10.0, true], "run": [8, 14.0, true],
	"attack": [8, 16.0, false], "hurt": [5, 12.0, false], "death": [7, 10.0, false],
}
const ROWS := ["down", "left", "right", "up"]

var facing := "down"
var state := "idle"
var t := 0.0
var tex := {}
var locked := false                     # attack in progress

func _ready() -> void:
	motion_mode = CharacterBody2D.MOTION_MODE_FLOATING
	for a in ANIMS:
		tex[a] = load("res://art/game/kael3/%s.png" % a)
	_set_state("idle")

func _set_state(s: String) -> void:
	if s == state and ($Sprite as Sprite2D).texture == tex[s]:
		return
	state = s
	t = 0.0
	var sp := $Sprite as Sprite2D
	sp.texture = tex[s]
	sp.hframes = int(ANIMS[s][0]); sp.vframes = 4

func _physics_process(dt: float) -> void:
	var v := Input.get_vector("move_left", "move_right", "move_up", "move_down")
	var running := Input.is_action_pressed("run")
	if InputMap.has_action("attack") and Input.is_action_just_pressed("attack") and not locked:
		locked = true
		_set_state("attack")
	if locked:
		velocity = Vector2.ZERO
	else:
		velocity = v * SPEED * (RUN_MULT if running else 1.0)
		if v.length() > 0.1:
			if absf(v.x) > absf(v.y):
				facing = "right" if v.x > 0 else "left"
			else:
				facing = "down" if v.y > 0 else "up"
			_set_state("run" if running else "walk")
		else:
			_set_state("idle")
	move_and_slide()
	t += dt
	var a: Array = ANIMS[state]
	var n := int(a[0])
	var f := int(t * float(a[1]))
	if f >= n:
		if bool(a[2]):
			f = f % n
		else:
			f = n - 1
			if state == "attack":
				locked = false
				_set_state("idle")
				f = 0
	($Sprite as Sprite2D).frame = ROWS.find(facing) * int(($Sprite as Sprite2D).hframes) + f
