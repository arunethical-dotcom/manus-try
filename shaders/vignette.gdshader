shader_type canvas_item;
uniform float strength = 0.72;
void fragment() {
	vec2 d = (UV - 0.5) * vec2(1.0, 0.82);
	float v = smoothstep(0.28, 0.72, length(d));
	COLOR = vec4(0.0, 0.0, 0.02, v * strength);
}
