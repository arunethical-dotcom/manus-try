extends CanvasLayer
## Top-right minimap (1 px = 1 tile image built from the blueprint). Press M to expand / collapse.
## Shows Kael (red dot) and the current camera view (white frame).
const SMALL_W := 200.0
const BIG_W := 600.0

var w: Node
var panel: Control
var overlay: Control
var img: TextureRect
var big := false
var map_px: Vector2

func setup(world_node: Node) -> void:
	w = world_node

func _ready() -> void:
	layer = 10
	var tex: Texture2D = load("res://art/game/minimap.png")
	map_px = tex.get_size()
	panel = Control.new()
	panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(panel)
	img = TextureRect.new()
	img.texture = tex
	img.texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR
	img.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	img.stretch_mode = TextureRect.STRETCH_SCALE
	panel.add_child(img)
	overlay = Control.new()
	overlay.mouse_filter = Control.MOUSE_FILTER_IGNORE
	panel.add_child(overlay)
	overlay.draw.connect(_draw_overlay)
	var hint := Label.new()
	hint.name = "Hint"
	hint.add_theme_font_size_override("font_size", 10)
	hint.add_theme_color_override("font_outline_color", Color.BLACK)
	hint.add_theme_constant_override("outline_size", 3)
	panel.add_child(hint)
	_layout()

func _layout() -> void:
	var vw := 960.0
	var wpx := BIG_W if big else SMALL_W
	var s := Vector2(wpx, wpx * map_px.y / map_px.x)
	panel.size = s
	panel.position = Vector2((vw - s.x) * 0.5, (540.0 - s.y) * 0.5) if big else Vector2(vw - s.x - 8, 8)
	img.size = s
	overlay.size = s
	var h := panel.get_node("Hint") as Label
	h.text = "M: close map" if big else "M: map"
	h.position = Vector2(4, s.y - 16)
	overlay.queue_redraw()

func toggle() -> void:
	big = not big
	_layout()

func _unhandled_input(e: InputEvent) -> void:
	if e.is_action_pressed("toggle_map"):
		toggle()

func _process(_dt: float) -> void:
	overlay.queue_redraw()

func _draw_overlay() -> void:
	var s := panel.size
	overlay.draw_rect(Rect2(Vector2.ZERO, s), Color(0.1, 0.08, 0.06), false, 2.0)
	if w == null or w.player == null:
		return
	var ws: Array = w.L["world"]
	var k := s.x / float(ws[0])
	var p: Vector2 = w.player.global_position * k
	var view := Vector2(960, 540) * k
	overlay.draw_rect(Rect2(p - view * 0.5, view), Color(1, 1, 1, 0.8), false, 1.0)
	overlay.draw_circle(p, 4.0 if big else 3.0, Color(0.9, 0.1, 0.1))
	overlay.draw_circle(p, 1.5, Color(1, 0.9, 0.8))
