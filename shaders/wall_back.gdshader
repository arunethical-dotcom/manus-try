shader_type canvas_item;
// Base wall layer (drawn under Kael). Inside the see-through ellipse, pixels that stand in front of Kael are cut
// away so the ground behind shows (the front layer then draws them faintly on top).
uniform sampler2D depth_tex : filter_nearest;
uniform float player_y = 100000.0;
uniform vec2 player_c = vec2(-100000.0);
uniform vec2 radius = vec2(58.0, 70.0);
varying vec2 wp;

void vertex() {
	wp = (MODEL_MATRIX * vec4(VERTEX, 0.0, 1.0)).xy;
}

void fragment() {
	vec4 c = texture(TEXTURE, UV);
	vec4 d = texture(depth_tex, UV);
	float g = floor(d.r * 255.0 + 0.5) * 256.0 + floor(d.g * 255.0 + 0.5);
	float a = c.a;
	if (g > player_y) {
		float e = length((wp - player_c) / radius);
		a *= smoothstep(0.75, 1.0, e);
	}
	COLOR = vec4(c.rgb, a);
}
