shader_type canvas_item;
// Redraws only the wall pixels that stand in front of Kael: their ground line (16 bit, R=high G=low byte)
// is south of Kael's feet.
uniform sampler2D depth_tex : filter_nearest;
uniform float player_y = -100000.0;

void fragment() {
	vec4 d = texture(depth_tex, UV);
	float g = floor(d.r * 255.0 + 0.5) * 256.0 + floor(d.g * 255.0 + 0.5);
	vec4 c = texture(TEXTURE, UV);
	if (c.a < 0.5 || g <= player_y) {
		discard;
	}
	COLOR = c;
}
