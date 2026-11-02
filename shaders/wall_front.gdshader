shader_type canvas_item;
// Redraws the wall pixels that stand in front of Kael (their ground line - 16 bit, R=high G=low byte - is south of
// Kael's feet). CrossCode-style see-through: inside a soft ellipse around Kael they are drawn faint, so he stays
// visible behind tall walls / towers / buildings.
uniform sampler2D depth_tex : filter_nearest;
uniform float player_y = -100000.0;
uniform vec2 player_c = vec2(-100000.0);
uniform vec2 radius = vec2(58.0, 70.0);
uniform float see_alpha = 0.32;
varying vec2 wp;

void vertex() {
	wp = (MODEL_MATRIX * vec4(VERTEX, 0.0, 1.0)).xy;
}

void fragment() {
	vec4 d = texture(depth_tex, UV);
	float g = floor(d.r * 255.0 + 0.5) * 256.0 + floor(d.g * 255.0 + 0.5);
	vec4 c = texture(TEXTURE, UV);
	if (c.a < 0.5 || g <= player_y) {
		discard;
	}
	float e = length((wp - player_c) / radius);
	float s = smoothstep(0.75, 1.0, e);          // 0 inside, 1 outside
	COLOR = vec4(c.rgb, mix(see_alpha, 1.0, s));
}
